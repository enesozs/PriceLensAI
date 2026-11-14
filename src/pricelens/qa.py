"""M1 QA: data-contract checks and the official-HICP reconstruction gate.

Writes reports/m1_qa.md and data/curated/qa.json. Returns False when any hard check fails.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import polars as pl

from pricelens.config import CURATED, REPORTS, forecast_geos, warehouse_geos
from pricelens.curate import DIVISIONS
from pricelens.reconstruction import chain_links, price_update_weights, reconstruct, yoy_gaps

# Reconstruction gate (fixed at M1; rationale in reports/m1_qa.md and docs/DATA_CONTRACT.md)
GATE_FROM = "2001-01"  # first years have incomplete component coverage in several countries
GATE_P95_PP = 0.10  # 95th percentile |YoY gap| per geo, percentage points
GATE_MAX_PP = 0.30  # worst single month per geo, percentage points
WEIGHT_SUM_TOL = 0.05  # per 1000
HBS_SUM_TOL = 6.0  # per 1000: 12 integer-rounded division shares can miss 1000 by up to ±6
# Geos whose published all-items index is not reproducible from published divisions and annual weights for
# reasons on the source side. Each entry must cite the diagnostic evidence in reports/m1_qa.md.
KNOWN_EXCEPTIONS = {
    "IT": (
        "Gap persists in every year (p95 ≈ 0.17 pp), December levels match (≈0.00%) while other months deviate "
        "≈0.05%; price-updating the weights makes it worse (rejected). Consistent with intra-year varying weights "
        "in the Italian HICP (e.g. seasonal items) — not verified against ISTAT documentation. Italian published "
        "series are used as-is; custom baskets for IT carry a caveat."
    )
}


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN
    detail: str


def _md(df: pl.DataFrame) -> str:
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for row in df.iter_rows():
        lines.append(
            "| "
            + " | ".join("" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v)) for v in row)
            + " |"
        )
    return "\n".join(lines)


def table_hash(df: pl.DataFrame) -> str:
    return hashlib.sha256(df.sort(df.columns).write_csv().encode()).hexdigest()[:16]


def load(name: str) -> pl.DataFrame:
    return pl.read_parquet(CURATED / f"{name}.parquet")


def reconstruction_report(
    index: pl.DataFrame, weights: pl.DataFrame, rates: pl.DataFrame, price_update: bool = False
) -> pl.DataFrame:
    div = index.filter(
        (pl.col("unit") == "I25") & pl.col("coicop").is_in(DIVISIONS) & pl.col("value").is_not_null()
    )
    w = weights.filter(pl.col("coicop").is_in(DIVISIONS)).rename({"weight_per_1000": "weight"})
    pub = index.filter((pl.col("unit") == "I25") & (pl.col("coicop") == "TOTAL")).select(
        "geo", "date", "value"
    )
    rch = rates.filter((pl.col("unit") == "RCH_A") & (pl.col("coicop") == "TOTAL")).select(
        "geo", "date", "value"
    )
    if price_update:
        w = price_update_weights(div, w)
    rec = reconstruct(chain_links(div, w, n_components=len(DIVISIONS)), pub)
    return yoy_gaps(rec, rch)


def run_qa() -> bool:
    checks: list[Check] = []
    index, rates, weights = load("hicp_index"), load("hicp_rates"), load("hicp_weights")
    hbs = load("hbs_quintile")
    geos = warehouse_geos()

    # 1. keys and values
    dup = index.group_by("geo", "coicop", "unit", "date").len().filter(pl.col("len") > 1).height
    checks.append(Check("unique key hicp_index", "PASS" if dup == 0 else "FAIL", f"{dup} duplicate keys"))
    neg = index.filter(pl.col("value") < 0).height
    core_zero = index.filter(
        (pl.col("value") == 0) & pl.col("level").is_in(["total", "division", "special"])
    ).height
    detail_zero = index.filter(
        (pl.col("value") == 0) & ~pl.col("level").is_in(["total", "division", "special"])
    )
    checks.append(
        Check(
            "positive index values (total, divisions, aggregates)",
            "PASS" if neg == 0 and core_zero == 0 else "FAIL",
            f"{neg} negative, {core_zero} zero at core levels",
        )
    )
    checks.append(
        Check(
            "zero indices at detailed levels",
            "WARN" if detail_zero.height else "PASS",
            f"{detail_zero.height} published 0.00 values (items made free or rounded to zero) in "
            f"{sorted(detail_zero['geo'].unique().to_list())}; never used as basket components",
        )
    )
    conf = index.filter(pl.col("value").is_null()).height
    checks.append(
        Check(
            "no null values with flags in index",
            "PASS" if conf == 0 else "WARN",
            f"{conf} rows (e.g. confidential)",
        )
    )
    missing_geo = sorted(set(geos) - set(index["geo"].unique().to_list()))
    checks.append(
        Check("all warehouse geos present", "PASS" if not missing_geo else "FAIL", f"missing: {missing_geo}")
    )

    # 2. weights
    sums = (
        weights.filter(pl.col("coicop").is_in(DIVISIONS) & pl.col("weight_per_1000").is_not_null())
        .group_by("geo", "year")
        .agg(s=pl.col("weight_per_1000").sum(), n=pl.len())
    )
    bad = sums.filter((pl.col("n") == 13) & ((pl.col("s") - 1000).abs() > WEIGHT_SUM_TOL))
    incomplete = sums.filter(pl.col("n") != 13)
    checks.append(
        Check(
            "division weights sum to 1000",
            "PASS" if bad.height == 0 else "FAIL",
            f"{sums.height} geo-years; {bad.height} outside ±{WEIGHT_SUM_TOL}; {incomplete.height} with <13 divisions",
        )
    )

    # 3. forecast-scope continuity (I25, ECB aggregates + divisions, 2001 onward, no gaps)
    last = index.filter(pl.col("unit") == "I25")["date"].max()
    expected_months = pl.date_range(pl.date(2001, 1, 1), last, "1mo", eager=True).len()
    cont = (
        index.filter(
            (pl.col("unit") == "I25")
            & pl.col("geo").is_in(forecast_geos())
            & pl.col("coicop").is_in(["TOTAL", "NRG", "FOOD", "IGD_NNRG", "SERV", *DIVISIONS])
            & (pl.col("date") >= pl.date(2001, 1, 1))
            & pl.col("value").is_not_null()
        )
        .group_by("geo", "coicop")
        .agg(n=pl.len())
    )
    gaps = cont.filter(pl.col("n") < expected_months - 1)  # last month may be flash-only for divisions
    checks.append(
        Check(
            "forecast scope continuous 2001→latest",
            "PASS" if gaps.height == 0 and cont.height == len(forecast_geos()) * 18 else "FAIL",
            f"{cont.height} series; {gaps.height} with gaps (expected {expected_months} months)",
        )
    )

    # 4. rates recomputed from I25 vs published RCH_A
    tot = index.filter((pl.col("unit") == "I25") & (pl.col("coicop") == "TOTAL")).select(
        "geo", "date", "value"
    )
    lag = tot.select("geo", pl.col("date").dt.offset_by("12mo").alias("date"), pl.col("value").alias("l12"))
    rch = rates.filter((pl.col("unit") == "RCH_A") & (pl.col("coicop") == "TOTAL")).select(
        "geo", "date", pl.col("value").alias("rch_a")
    )
    prec = (
        tot.join(lag, on=["geo", "date"])
        .join(rch, on=["geo", "date"])
        .with_columns(gap=((pl.col("value") / pl.col("l12") - 1) * 100 - pl.col("rch_a")).abs())
    )
    mx = prec["gap"].max()
    checks.append(
        Check(
            "YoY from I25 matches published RCH_A",
            "PASS" if mx <= 0.051 else "FAIL",
            f"max |gap| {mx:.3f} pp over {prec.height} geo-months (RCH_A has 1 decimal)",
        )
    )

    # 5. reconstruction gate
    g = reconstruction_report(index, weights, rates)
    gate = (
        g.filter(pl.col("date") >= pl.lit(GATE_FROM).str.to_date("%Y-%m"))
        .group_by("geo")
        .agg(
            months=pl.len(),
            from_=pl.col("date").min().dt.strftime("%Y-%m"),
            median_abs_pp=pl.col("gap_pp").abs().median(),
            p95_abs_pp=pl.col("gap_pp").abs().quantile(0.95),
            max_abs_pp=pl.col("gap_pp").abs().max(),
            chain_drift_last_pct=pl.col("chain_drift_pct").sort_by("date").last(),
        )
        .with_columns(
            gate=pl.when((pl.col("p95_abs_pp") <= GATE_P95_PP) & (pl.col("max_abs_pp") <= GATE_MAX_PP))
            .then(pl.lit("PASS"))
            .otherwise(pl.lit("FAIL"))
        )
        .sort("geo")
    )
    failed = gate.filter(pl.col("gate") == "FAIL")["geo"].to_list()
    excepted = [x for x in failed if x in KNOWN_EXCEPTIONS]
    failed = [x for x in failed if x not in KNOWN_EXCEPTIONS]
    fc_failed = [x for x in failed if x in forecast_geos()]
    missing_rec = sorted(set(geos) - set(gate["geo"].to_list()))
    checks.append(
        Check(
            "official HICP reconstruction (forecast geos)",
            "PASS" if not fc_failed and not excepted else ("WARN" if not fc_failed else "FAIL"),
            f"p95 ≤ {GATE_P95_PP} pp and max ≤ {GATE_MAX_PP} pp from {GATE_FROM}; failing: {fc_failed}; "
            f"documented exceptions: {excepted}",
        )
    )
    checks.append(
        Check(
            "official HICP reconstruction (all geos)",
            "PASS" if not failed and not missing_rec else "WARN",
            f"failing: {failed}; not reconstructable: {missing_rec}",
        )
    )
    pu = reconstruction_report(index, weights, rates, price_update=True)
    pu_gate = (
        pu.filter(pl.col("date") >= pl.lit(GATE_FROM).str.to_date("%Y-%m"))
        .group_by("geo")
        .agg(p95_abs_pp_price_updated=pl.col("gap_pp").abs().quantile(0.95))
    )
    hypothesis = gate.select("geo", "p95_abs_pp").join(pu_gate, on="geo").sort("geo")
    worst = (
        g.filter(pl.col("date") >= pl.lit(GATE_FROM).str.to_date("%Y-%m"))
        .with_columns(abs_gap=pl.col("gap_pp").abs())
        .sort("abs_gap", descending=True)
        .head(10)
        .select("geo", pl.col("date").dt.strftime("%Y-%m").alias("month"), "yoy_pub", "yoy_rec", "gap_pp")
    )

    # 6. HBS bridge usability
    hb = (
        hbs.group_by("geo", "wave", "quintile")
        .agg(
            share_sum=pl.col("share").sum(),
            min_share=pl.col("share").min(),
            missing=pl.col("missing_codes").first(),
            hbs_total=pl.col("hbs_total_per_1000").first(),
            imputed=pl.col("imputed_rent_per_1000").first(),
            method=pl.col("method").first(),
        )
        .with_columns(
            usable=(pl.col("missing") == "")
            & ((pl.col("share_sum") - 1).abs() < 1e-9)
            & (pl.col("min_share") >= 0)
            & ((pl.col("hbs_total") - 1000).abs() <= HBS_SUM_TOL)
        )
    )
    usable = (
        hb.group_by("geo", "wave")
        .agg(
            usable=pl.col("usable").all(),
            method=pl.col("method").first(),
            missing=pl.col("missing").unique().str.join(";"),
        )
        .sort("geo", "wave")
    )
    countries = [x for x in geos if x not in ("EA", "EU27_2020")]
    usable_any = usable.filter(pl.col("usable"))["geo"].unique().to_list()
    not_usable = sorted(set(countries) - set(usable_any))
    checks.append(
        Check(
            "HBS quintile bridge",
            "PASS" if len(usable_any) > 0 else "FAIL",
            f"{len(set(usable_any) & set(countries))} countries usable in ≥1 wave; not usable: {not_usable}",
        )
    )

    # 7. reproducibility fingerprint
    hashes = {n: table_hash(load(n)) for n in ["hicp_weights", "coicop", "hbs_quintile"]}
    hashes["hicp_index_I25_total"] = table_hash(
        index.filter((pl.col("unit") == "I25") & (pl.col("coicop") == "TOTAL"))
    )

    ok = all(c.status != "FAIL" for c in checks)
    lines = [
        "# M1 QA report (generated)",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by `uv run pricelens qa`. "
        f"Source versions: {', '.join(sorted(set(index['source_version'].unique().to_list() + weights['source_version'].unique().to_list())))}.",
        "",
        f"**Overall: {'PASS' if ok else 'FAIL'}**",
        "",
        _md(pl.DataFrame([asdict(c) for c in checks])),
        "",
        "## Official HICP reconstruction",
        "",
        "All-items HICP rebuilt from the 13 ECOICOP ver.2 division indices (I25) and PRC_HICP_IW division weights "
        "with annual chain-linking through December of the previous year, anchored each year on the published "
        "December value (see src/pricelens/reconstruction.py). Gap = reconstructed minus published annual rate, in percentage points. "
        "`chain_drift_last_pct` = level drift of the fully chained (never re-anchored) reconstruction at the "
        "latest month.",
        "",
        f"Gate: per geo, 95th percentile |gap| ≤ {GATE_P95_PP} pp and max |gap| ≤ {GATE_MAX_PP} pp from {GATE_FROM}. "
        "Rationale: published indices have 2 decimals and weights are rounded to 0.01‰, so exact equality is "
        "impossible; a correct method should stay within about a tenth of a point, while a wrong link month or "
        "wrong weight year produces gaps of several tenths during price shocks.",
        "",
        _md(gate.rename({"from_": "from"})),
        "",
        "### Documented exceptions",
        "",
        "\n".join(f"- **{k}**: {v}" for k, v in KNOWN_EXCEPTIONS.items()),
        "",
        "### Hypothesis test: are the published weights already price-updated to December?",
        "",
        "Same reconstruction with weights re-valued from average y-1 prices to December y-1. If published weights "
        "were *not* price-updated, this variant would shrink the gaps. It widens them everywhere, so the published "
        "weights are used as-is.",
        "",
        _md(hypothesis),
        "",
        "Largest single-month gaps:",
        "",
        _md(worst),
        "",
        "## HBS quintile bridge usability (per geo × wave)",
        "",
        _md(usable),
        "",
        "## Table fingerprints",
        "",
        "\n".join(f"- `{k}`: `{v}`" for k, v in hashes.items()),
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "m1_qa.md").write_text("\n".join(lines))
    (CURATED / "qa.json").write_text(
        json.dumps({"ok": ok, "checks": [asdict(c) for c in checks], "hashes": hashes}, indent=2)
    )
    gate.write_parquet(CURATED / "reconstruction_gate.parquet")
    g.write_parquet(CURATED / "reconstruction.parquet")
    return ok
