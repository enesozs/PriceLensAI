"""M0 source audit: coverage, flags and weight-sum semantics, written to reports/m0_source_audit.md.

This is a pipeline report, not an ad-hoc exploration: it is rerun on every new snapshot.
"""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from pricelens.config import REPORTS, eurostat_dataset, forecast_geos, hicp_units, warehouse_geos
from pricelens.sources.eurostat import latest_snapshot, parse_codelists, parse_tsv

DIVISION = r"^CP\d{2}$"
SPECIAL_AGGREGATES = ["NRG", "FOOD", "IGD_NNRG", "SERV"]


def _md(df: pl.DataFrame) -> str:
    cols = df.columns
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.iter_rows():
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(lines)


def audit() -> str:
    geos = warehouse_geos()
    out: list[str] = [
        "# M0 source audit (generated)",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by `uv run pricelens audit`.",
        "",
    ]

    # ---------------------------------------------------------------- HICP monthly
    ds = eurostat_dataset("hicp_monthly")
    snap = latest_snapshot(ds.id)
    m = parse_tsv(snap / "data.tsv.gz", keep={"geo": geos, "unit": hicp_units()})
    cl = parse_codelists(snap / "structure.xml")
    out += [f"## {ds.id} — snapshot `{snap.name}`", ""]
    out.append(
        f"Rows (warehouse geos × units {hicp_units()}): {m.height:,}. "
        f"Codes in codelist: {len(cl['COICOP18'])}."
    )
    levels = (
        m.filter(pl.col("unit") == "I25")
        .select("coicop18")
        .unique()
        .with_columns(
            level=pl.when(pl.col("coicop18") == "TOTAL")
            .then(pl.lit("total"))
            .when(pl.col("coicop18").str.contains(r"^CP\d+$"))
            .then(pl.concat_str(pl.lit("digits_"), (pl.col("coicop18").str.len_chars() - 2).cast(pl.Utf8)))
            .otherwise(pl.lit("special_aggregate"))
        )
        .group_by("level")
        .len()
        .sort("level")
    )
    out += ["", "Published I25 codes by level:", "", _md(levels), ""]

    i25 = m.filter(pl.col("unit") == "I25")
    tot = (
        i25.filter(pl.col("coicop18") == "TOTAL")
        .group_by("geo")
        .agg(
            first=pl.col("time").min(),
            last=pl.col("time").max(),
            last_flag=pl.col("flag").sort_by("time").last(),
        )
    )
    div = (
        i25.filter(pl.col("coicop18").str.contains(DIVISION) & pl.col("value").is_not_null())
        .group_by("geo", "time")
        .agg(n=pl.col("coicop18").n_unique())
        .filter(pl.col("n") == 13)
        .group_by("geo")
        .agg(all_13_divisions_from=pl.col("time").min())
    )
    agg = (
        i25.filter(pl.col("coicop18").is_in(SPECIAL_AGGREGATES) & pl.col("value").is_not_null())
        .group_by("geo", "time")
        .agg(n=pl.col("coicop18").n_unique())
        .filter(pl.col("n") == len(SPECIAL_AGGREGATES))
        .group_by("geo")
        .agg(ecb_4_aggregates_from=pl.col("time").min())
    )
    cov = (
        pl.DataFrame({"geo": geos})
        .join(tot, on="geo", how="left")
        .join(div, on="geo", how="left")
        .join(agg, on="geo", how="left")
        .with_columns(forecast_scope=pl.col("geo").is_in(forecast_geos()))
    )
    out += ["### Coverage of index (2025=100) by geo", "", _md(cov), ""]

    flags = m.group_by("unit", "flag").len().sort("unit", "flag")
    out += ["### Observation flags", "", _md(flags), ""]
    est = m.filter(pl.col("flag").str.contains("e") & (pl.col("unit") == "I25"))
    last_month = i25["time"].max()
    est_summary = (
        est.with_columns(
            period=pl.when(pl.col("time") == last_month)
            .then(pl.lit(f"latest month {last_month} (flash)"))
            .when(pl.col("time") < "2025-05")
            .then(pl.lit("back-calculated history (< 2025-05)"))
            .otherwise(pl.lit("other"))
        )
        .group_by("period")
        .agg(
            rows=pl.len(),
            geos=pl.col("geo").unique().sort().str.join(","),
            codes=pl.col("coicop18").n_unique(),
            first=pl.col("time").min(),
            last=pl.col("time").max(),
        )
        .sort("period")
    )
    flash_codes = sorted(est.filter(pl.col("time") == last_month)["coicop18"].unique().to_list())
    out += [
        "Estimated (`e`) I25 observations by period. The flash estimate for the latest month is published "
        f"inside this dataset for codes {flash_codes}; the older `e` rows are ECOICOP ver.2 back-calculations.",
        "",
        _md(est_summary),
        "",
    ]

    # precision check: YoY recomputed from published (2-decimal) indices vs published RCH_A
    piv = (
        m.filter(pl.col("unit").is_in(["I25", "I15", "RCH_A"]) & (pl.col("coicop18") == "TOTAL"))
        .pivot(on="unit", index=["geo", "time"], values="value")
        .sort("geo", "time")
        .with_columns(
            yoy25=(pl.col("I25") / pl.col("I25").shift(12).over("geo") - 1) * 100,
            yoy15=(pl.col("I15") / pl.col("I15").shift(12).over("geo") - 1) * 100,
        )
        .drop_nulls(["yoy25", "yoy15", "RCH_A"])
        .with_columns(
            gap25=(pl.col("yoy25") - pl.col("RCH_A")).abs(),
            gap15=(pl.col("yoy15") - pl.col("RCH_A")).abs(),
            era=pl.when(pl.col("time") >= "2005-01").then(pl.lit(">=2005")).otherwise(pl.lit("<2005")),
        )
    )
    prec = (
        piv.group_by("era")
        .agg(
            months=pl.len(),
            max_gap_I25=pl.col("gap25").max().round(3),
            max_gap_I15=pl.col("gap15").max().round(3),
            share_I25_gt_0p05=(pl.col("gap25") > 0.05).mean().round(4),
        )
        .sort("era")
    )
    worst = piv.sort("gap25", descending=True).head(5).select("geo", "time", "I25", "RCH_A", "yoy25", "gap25")
    out += [
        "### Precision check: all-items YoY recomputed from published indices vs published annual rate",
        "",
        "Published rates are computed from unrounded indices. Indices are published with 2 decimals, so "
        "low index levels (early years, high-inflation countries) lose precision when rates are recomputed.",
        "",
        _md(prec),
        "",
        "Worst cases:",
        "",
        _md(worst.with_columns(pl.col("yoy25").round(3), pl.col("gap25").round(3))),
        "",
    ]

    # ---------------------------------------------------------------- weights
    ds = eurostat_dataset("hicp_weights")
    snap = latest_snapshot(ds.id)
    w = parse_tsv(snap / "data.tsv.gz", keep={"geo": geos})
    out += [f"## {ds.id} — snapshot `{snap.name}`", ""]
    sums = (
        w.filter(pl.col("coicop18").str.contains(DIVISION) & pl.col("value").is_not_null())
        .group_by("geo", "time")
        .agg(div_sum=pl.col("value").sum(), n=pl.len())
    )
    out.append(
        f"Division weights per geo-year: {sums.height} geo-years; n_divisions==13 in "
        f"{(sums['n'] == 13).mean():.3f} of them; |sum−1000| max = {(sums['div_sum'] - 1000).abs().max():.2f}, "
        f"share > 0.05 = {((sums['div_sum'] - 1000).abs() > 0.05).mean():.3f} (rounding of published weights)."
    )
    yrs = (
        w.filter(pl.col("coicop18") == "TOTAL")
        .group_by("geo")
        .agg(first_year=pl.col("time").min(), last_year=pl.col("time").max())
    )
    out += ["", _md(pl.DataFrame({"geo": geos}).join(yrs, on="geo", how="left")), ""]
    out += ["### Weight flags", "", _md(w.group_by("flag").len().sort("flag")), ""]

    # ---------------------------------------------------------------- HBS
    ds = eurostat_dataset("hbs_quintile")
    snap = latest_snapshot(ds.id)
    h = parse_tsv(snap / "data.tsv.gz")
    out += [f"## {ds.id} — snapshot `{snap.name}`", ""]
    q = h.filter(pl.col("quant_inc").str.starts_with("QU") & pl.col("coicop").str.contains(DIVISION))
    waves = (
        q.filter(pl.col("time").is_in(["2015", "2020"]) & pl.col("value").is_not_null())
        .group_by("geo", "time")
        .agg(n_div=pl.col("coicop").n_unique(), n_q=pl.col("quant_inc").n_unique())
        .with_columns(ok=(pl.col("n_div") == 12) & (pl.col("n_q") == 5))
        .pivot(on="time", index="geo", values="ok")
    )
    hbs_geos = [g for g in geos if g != "EA"]
    out += [
        "Complete quintile × 12-division coverage per wave (True = usable):",
        "",
        _md(pl.DataFrame({"geo": hbs_geos}).join(waves, on="geo", how="left").select("geo", "2015", "2020")),
        "",
    ]
    gaps = (
        q.filter(pl.col("time").is_in(["2015", "2020"]))
        .group_by("geo", "time")
        .agg(
            n_div_with_value=pl.col("coicop").filter(pl.col("value").is_not_null()).n_unique(),
            n_quintiles=pl.col("quant_inc").filter(pl.col("value").is_not_null()).n_unique(),
            flags=pl.col("flag").unique().sort().str.join(","),
        )
        .filter((pl.col("n_div_with_value") < 12) | (pl.col("n_quintiles") < 5))
        .sort("geo", "time")
    )
    out += ["Incomplete geo-waves (diagnosis):", "", _md(gaps) if gaps.height else "none", ""]
    cp042 = (
        h.filter(
            (pl.col("coicop") == "CP042")
            & pl.col("quant_inc").str.starts_with("QU")
            & pl.col("geo").is_in(["EU27_2020", "DE", "FR", "ES"])
            & pl.col("time").is_in(["2015", "2020"])
        )
        .pivot(on="quant_inc", index=["geo", "time"], values="value")
        .sort("geo", "time")
    )
    out += [
        "Imputed rent (CP042, ‰ of total expenditure) — outside HICP scope, must be removed and the rest "
        "renormalised:",
        "",
        _md(cp042) if cp042.height else "no CP042 rows published for these geos",
        "",
    ]
    cp042_avail = (
        h.filter((pl.col("coicop") == "CP042") & pl.col("value").is_not_null())
        .group_by("time")
        .agg(geos=pl.col("geo").n_unique())
        .sort("time")
    )
    out += ["CP042 availability (geos with a value) by wave:", "", _md(cp042_avail), ""]
    out += ["### HBS flags", "", _md(h.group_by("flag").len().sort("flag")), ""]
    return "\n".join(out)


def write_audit() -> str:
    REPORTS.mkdir(exist_ok=True)
    text = audit()
    (REPORTS / "m0_source_audit.md").write_text(text)
    return text
