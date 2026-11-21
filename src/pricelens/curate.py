"""Curation: raw Eurostat snapshots -> normalized Parquet tables in data/curated/.

Tables
------
hicp_index      geo, coicop, period, date, unit (I25|I15), value, flag, level, source_version
hicp_rates      geo, coicop, period, date, unit (RCH_M|RCH_A), value, flag, source_version
hicp_weights    geo, coicop, year, weight_per_1000, flag, level, source_version
coicop          code, label, level, parent, division
hbs_raw         geo, quintile, coicop1999, wave, share_per_1000, flag, source_version
hbs_quintile    geo, quintile, wave, division, share, method, flags   (ECOICOP v2 divisions, CP042 removed,
                renormalized to sum 1 per geo-quintile-wave)
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from pricelens.config import CURATED, ROOT, eurostat_dataset, hicp_units, warehouse_geos
from pricelens.sources.eurostat import latest_snapshot, parse_codelists, parse_tsv

DIVISIONS = [f"CP{i:02d}" for i in range(1, 14)]
HBS_WAVES = ["2015", "2020"]
# Fallback split for countries that publish CP091 but not its 4-digit children: the part of old CP091
# that moves to ver.2 CP08, in proportion to the country's ver.2 class weights.
CP091_FALLBACK = {"CP08": ["CP0813", "CP0814", "CP0815", "CP0835"], "CP09": ["CP0911", "CP0941", "CP0952"]}


def _version(snap: Path) -> str:
    return json.loads((snap / "manifest.json").read_text())["source_version"]


def coicop_level(code: pl.Expr) -> pl.Expr:
    digits = code.str.len_chars() - 2
    return (
        pl.when(code == "TOTAL")
        .then(pl.lit("total"))
        .when(code.str.contains(r"^CP\d+$"))
        .then(
            pl.when(digits == 2)
            .then(pl.lit("division"))
            .when(digits == 3)
            .then(pl.lit("group"))
            .when(digits == 4)
            .then(pl.lit("class"))
            .when(digits == 5)
            .then(pl.lit("subclass"))
            .otherwise(pl.lit("item"))
        )
        .otherwise(pl.lit("special"))
    )


def build_coicop(structure: Path) -> pl.DataFrame:
    labels = parse_codelists(structure)["COICOP18"]
    df = pl.DataFrame({"code": list(labels), "label": list(labels.values())})
    return df.with_columns(level=coicop_level(pl.col("code"))).with_columns(
        parent=pl.when(pl.col("level") == "division")
        .then(pl.lit("TOTAL"))
        .when(pl.col("level").is_in(["group", "class", "subclass", "item"]))
        .then(pl.col("code").str.slice(0, pl.col("code").str.len_chars() - 1))
        .otherwise(None),
        division=pl.when(pl.col("code").str.contains(r"^CP\d+$"))
        .then(pl.col("code").str.slice(0, 4))
        .otherwise(None),
    )


def curate_hicp() -> tuple[pl.DataFrame, pl.DataFrame]:
    snap = latest_snapshot(eurostat_dataset("hicp_monthly").id)
    long = parse_tsv(snap / "data.tsv.gz", keep={"geo": warehouse_geos(), "unit": hicp_units()})
    long = long.rename({"coicop18": "coicop", "time": "period"}).drop("freq")
    long = long.with_columns(
        date=pl.col("period").str.to_date("%Y-%m"),
        source_version=pl.lit(_version(snap)),
    )
    index = long.filter(pl.col("unit").is_in(["I25", "I15"])).with_columns(
        level=coicop_level(pl.col("coicop"))
    )
    rates = long.filter(pl.col("unit").is_in(["RCH_M", "RCH_A"]))
    cols = ["geo", "coicop", "period", "date", "unit", "value", "flag"]
    return (
        index.select(*cols, "level", "source_version").sort("geo", "coicop", "unit", "date"),
        rates.select(*cols, "source_version").sort("geo", "coicop", "unit", "date"),
    )


def curate_weights() -> pl.DataFrame:
    snap = latest_snapshot(eurostat_dataset("hicp_weights").id)
    w = parse_tsv(snap / "data.tsv.gz", keep={"geo": warehouse_geos()})
    return (
        w.rename({"coicop18": "coicop", "value": "weight_per_1000"})
        .with_columns(year=pl.col("time").cast(pl.Int32), source_version=pl.lit(_version(snap)))
        .with_columns(level=coicop_level(pl.col("coicop")))
        .select("geo", "coicop", "year", "weight_per_1000", "flag", "level", "source_version")
        .sort("geo", "coicop", "year")
    )


def curate_hbs_raw() -> pl.DataFrame:
    snap = latest_snapshot(eurostat_dataset("hbs_quintile").id)
    h = parse_tsv(snap / "data.tsv.gz", keep={"geo": warehouse_geos()})
    return (
        h.filter(pl.col("quant_inc").str.starts_with("QU"))
        .rename({"quant_inc": "quintile", "coicop": "coicop1999", "time": "wave", "value": "share_per_1000"})
        .with_columns(source_version=pl.lit(_version(snap)))
        .select("geo", "quintile", "coicop1999", "wave", "share_per_1000", "flag", "source_version")
        .sort("geo", "quintile", "coicop1999", "wave")
    )


def load_bridge(path: Path | None = None) -> pl.DataFrame:
    return pl.read_csv(path or ROOT / "configs" / "hbs_to_ecoicop2.csv", infer_schema=False)


def _split_fraction(
    weights: pl.DataFrame, geo: str, year: int, groups: dict[str, list[str]]
) -> dict[str, float]:
    """Share of a split HBS code going to each target division, from the country's ver.2 class weights.

    Falls back to equal shares when the country publishes no weight for any target class.
    """
    w = weights.filter((pl.col("geo") == geo) & (pl.col("year") == year))
    tot = {
        div: float(w.filter(pl.col("coicop").is_in(codes))["weight_per_1000"].fill_null(0).sum())
        for div, codes in groups.items()
    }
    s = sum(tot.values())
    if s <= 0:
        return {div: 1 / len(groups) for div in groups}
    return {div: v / s for div, v in tot.items()}


def parse_split(spec: str) -> dict[str, list[str]]:
    """'CP08:CP0815|CP09:CP0952,CP0941' -> {'CP08': ['CP0815'], 'CP09': ['CP0952', 'CP0941']}"""
    return {part.split(":")[0]: part.split(":")[1].split(",") for part in spec.split("|")}


CP091_CHILDREN_MOVING = ["CP0911", "CP0913", "CP0914", "CP0915"]


def bridge_quintile(
    vals: dict[str, float | None],
    bridge: list[dict],
    split_fracs: dict[str, dict[str, float]],
    cp091_fallback_frac: dict[str, float] | None,
) -> tuple[dict[str, float], list[str], str]:
    """Bridge one quintile's HBS shares (per 1000, COICOP 1999) to ECOICOP ver.2 divisions.

    Starts from the 12 HBS division totals (identity rows), then applies explicit moves:
    exclusions (imputed rent), moves between divisions, and weight-proportional splits.
    Returns (per-1000 amounts by ver.2 division, missing required codes, method).
    """
    acc = dict.fromkeys(DIVISIONS, 0.0)
    missing: list[str] = []
    method = "bridge"
    have = {k for k, v in vals.items() if v is not None}
    use_fallback = (
        not (set(CP091_CHILDREN_MOVING) & have) and "CP091" in have and cp091_fallback_frac is not None
    )
    for r in bridge:
        code, m = r["hbs_code"], r["method"]
        if use_fallback and code in CP091_CHILDREN_MOVING:
            continue
        v = vals.get(code)
        if v is None:
            if m in ("identity", "exclude") or code in ("CP081", "CP125", "CP126"):
                missing.append(code)
            continue
        if m == "identity":
            acc[r["to_division"]] += v
        elif m == "exclude":
            acc[r["from_division"]] -= v
        elif m == "move":
            acc[r["from_division"]] -= v
            acc[r["to_division"]] += v
        elif m == "split":
            for div, f in split_fracs[code].items():
                if div != r["from_division"]:
                    acc[r["from_division"]] -= v * f
                    acc[div] += v * f
    if use_fallback:
        method = "bridge+cp091_fallback"
        v = vals["CP091"] or 0.0
        moved = v * cp091_fallback_frac.get("CP08", 0.0)
        acc["CP09"] -= moved
        acc["CP08"] += moved
    return acc, missing, method


def map_hbs_to_ecoicop2(hbs: pl.DataFrame, weights: pl.DataFrame, bridge: pl.DataFrame) -> pl.DataFrame:
    """Map HBS COICOP 1999 shares to ECOICOP ver.2 divisions per geo/quintile/wave.

    Imputed rent (CP042) is removed and the result renormalized to sum to 1 (`share`).
    Rows whose required codes are missing keep `share` but list them in `missing_codes`;
    the QA step decides usability.
    """
    rows: list[dict] = []
    br = list(bridge.iter_rows(named=True))
    for (geo, wave), g in hbs.filter(pl.col("wave").is_in(HBS_WAVES)).group_by("geo", "wave"):
        year = int(wave)
        split_fracs = {
            r["hbs_code"]: _split_fraction(weights, geo, year, parse_split(r["split_classes"]))
            for r in br
            if r["method"] == "split"
        }
        fb = _split_fraction(weights, geo, year, CP091_FALLBACK)
        for (quintile,), q in g.group_by("quintile"):
            vals = dict(zip(q["coicop1999"].to_list(), q["share_per_1000"].to_list(), strict=True))
            acc, missing, method = bridge_quintile(vals, br, split_fracs, fb)
            total = sum(acc.values())
            for d in DIVISIONS:
                rows.append(
                    {
                        "geo": geo,
                        "quintile": quintile,
                        "wave": year,
                        "division": d,
                        "share": acc[d] / total if total > 0 else None,
                        "per_1000_ex_imputed": acc[d],
                        "method": method,
                        "imputed_rent_per_1000": vals.get("CP042"),
                        "hbs_total_per_1000": sum(
                            v
                            for k, v in vals.items()
                            if k in [f"CP{i:02d}" for i in range(1, 13)] and v is not None
                        ),
                        "missing_codes": ",".join(sorted(missing)),
                    }
                )
    return pl.DataFrame(rows).sort("geo", "wave", "quintile", "division")


def write_all(out: Path = CURATED) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    index, rates = curate_hicp()
    weights = curate_weights()
    snap = latest_snapshot(eurostat_dataset("hicp_monthly").id)
    coicop = build_coicop(snap / "structure.xml")
    hbs = curate_hbs_raw()
    quint = map_hbs_to_ecoicop2(hbs, weights, load_bridge())
    tables = {
        "hicp_index": index,
        "hicp_rates": rates,
        "hicp_weights": weights,
        "coicop": coicop,
        "hbs_raw": hbs,
        "hbs_quintile": quint,
    }
    for name, df in tables.items():
        df.write_parquet(out / f"{name}.parquet", compression="zstd")
    return {k: v.height for k, v in tables.items()}
