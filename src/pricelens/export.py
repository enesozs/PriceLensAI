"""Static export for the web app: compact JSON in app/public/data (committed; the site builds without the pipeline).

Files
-----
meta.json            geos, codes, labels, latest months, source versions, attribution
rates.json           official annual rates (RCH_A) for every geo x headline code x month (columnar)
geo/<GEO>.json       index levels (I25), annual rates, annual weights, contributions to the headline rate
quality.json         reconstruction gate summary per geo (from M1 QA)
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import polars as pl

from pricelens.config import CURATED, EXPORT, warehouse_geos
from pricelens.contrib import contributions
from pricelens.curate import DIVISIONS
from pricelens.sources.eurostat import latest_snapshot, parse_codelists

AGGREGATES = ["NRG", "FOOD", "IGD_NNRG", "SERV"]
HEADLINE_CODES = ["TOTAL", *AGGREGATES, *DIVISIONS]
START = date(2000, 1, 1)

SHORT = {
    "TOTAL": "All items",
    "NRG": "Energy",
    "FOOD": "Food, alcohol & tobacco",
    "IGD_NNRG": "Non-energy industrial goods",
    "SERV": "Services",
    "CP01": "Food & soft drinks",
    "CP02": "Alcohol & tobacco",
    "CP03": "Clothing & footwear",
    "CP04": "Housing, water & energy",
    "CP05": "Furnishings & household",
    "CP06": "Health",
    "CP07": "Transport",
    "CP08": "Information & communication",
    "CP09": "Recreation & culture",
    "CP10": "Education",
    "CP11": "Restaurants & accommodation",
    "CP12": "Insurance & financial",
    "CP13": "Personal care & misc.",
}
GEO_NAME_OVERRIDE = {"EA": "Euro area", "EU27_2020": "European Union"}
ATTRIBUTION = (
    "Source: Eurostat (PRC_HICP_MINR, PRC_HICP_IW, HBS_STR_T223). Data transformed by PriceLens; "
    "Eurostat bears no responsibility for the results."
)


def _months(d0: date, d1: date) -> list[date]:
    return pl.date_range(d0, d1, "1mo", eager=True).to_list()


def _r(x: float | None, nd: int) -> float | None:
    return None if x is None else round(float(x), nd)


def _series(df: pl.DataFrame, months: list[date], code: str, nd: int) -> list[float | None]:
    m = dict(
        zip(
            df.filter(pl.col("coicop") == code)["date"].to_list(),
            df.filter(pl.col("coicop") == code)["value"].to_list(),
            strict=True,
        )
    )
    return [_r(m.get(d), nd) for d in months]


def _dump(path: Path, obj: object) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, separators=(",", ":"), allow_nan=False)
    path.write_text(text)
    return len(text)


def export(out: Path = EXPORT) -> dict[str, int]:
    index = pl.read_parquet(CURATED / "hicp_index.parquet").filter(
        (pl.col("unit") == "I25") & pl.col("coicop").is_in(HEADLINE_CODES) & pl.col("value").is_not_null()
    )
    rates = pl.read_parquet(CURATED / "hicp_rates.parquet").filter(
        (pl.col("unit") == "RCH_A") & pl.col("coicop").is_in(HEADLINE_CODES) & pl.col("value").is_not_null()
    )
    weights = pl.read_parquet(CURATED / "hicp_weights.parquet").filter(pl.col("coicop").is_in(HEADLINE_CODES))
    gate = pl.read_parquet(CURATED / "reconstruction_gate.parquet")
    hbs = pl.read_parquet(CURATED / "hbs_quintile.parquet")
    qa = json.loads((CURATED / "qa.json").read_text())
    geos = warehouse_geos()

    last = index["date"].max()
    # latest month with a complete (non-flash) release for the euro area divisions
    full = index.filter((pl.col("geo") == "EA") & pl.col("coicop").is_in(DIVISIONS))["date"].max()
    flash_month = last if last > full else None
    months = _months(START, last)
    sizes: dict[str, int] = {}

    # ---------------------------------------------------------------- rates.json (columnar)
    r = rates.filter(pl.col("date") >= START)
    lookup = {(g, c, d): v for g, c, d, v in r.select("geo", "coicop", "date", "value").iter_rows()}
    flags = {(g, c, d): f for g, c, d, f in r.select("geo", "coicop", "date", "flag").iter_rows() if f}
    sizes["rates.json"] = _dump(
        out / "rates.json",
        {
            "months": [d.strftime("%Y-%m") for d in months],
            "geos": geos,
            "codes": HEADLINE_CODES,
            "values": [
                [[_r(lookup.get((g, c, d)), 1) for d in months] for c in HEADLINE_CODES] for g in geos
            ],
            "estimated": sorted(
                {f"{g}|{c}|{d:%Y-%m}" for (g, c, d), f in flags.items() if "e" in f and d == last}
            ),
        },
    )

    # ---------------------------------------------------------------- geo/<GEO>.json
    idx_months = _months(date(1999, 12, 1), last)
    comp = index.filter(pl.col("coicop").is_in(AGGREGATES)).select("geo", "coicop", "date", "value")
    tot = index.filter(pl.col("coicop") == "TOTAL").select("geo", "date", "value")
    w_agg = weights.filter(pl.col("coicop").is_in(AGGREGATES)).rename({"weight_per_1000": "weight"})
    contrib = contributions(comp, w_agg, tot)
    for g in geos:
        gi = index.filter(pl.col("geo") == g)
        gr = rates.filter(pl.col("geo") == g)
        gw = weights.filter(pl.col("geo") == g)
        gc = contrib.filter((pl.col("geo") == g) & (pl.col("date") >= START))
        c_months = sorted(set(gc["date"].to_list()))
        c_vals = {
            code: [
                _r(v, 3)
                for v in gc.filter(pl.col("coicop") == code).sort("date")["contribution_pp"].to_list()
            ]
            for code in AGGREGATES
        }
        pub = dict(
            zip(
                gr.filter(pl.col("coicop") == "TOTAL")["date"].to_list(),
                gr.filter(pl.col("coicop") == "TOTAL")["value"].to_list(),
                strict=True,
            )
        )
        residual = [
            _r(pub[d] - sum(c_vals[code][k] for code in AGGREGATES), 3) if d in pub else None
            for k, d in enumerate(c_months)
        ]
        years = sorted(set(gw["year"].to_list()))
        sizes[f"geo/{g}.json"] = _dump(
            out / "geo" / f"{g}.json",
            {
                "geo": g,
                "months": [d.strftime("%Y-%m") for d in idx_months],
                "index": {c: _series(gi, idx_months, c, 2) for c in HEADLINE_CODES},
                "yoy": {c: _series(gr, idx_months, c, 1) for c in HEADLINE_CODES},
                "weights": {
                    str(y): {
                        c: _r(v, 2)
                        for c, v in gw.filter(pl.col("year") == y)
                        .select("coicop", "weight_per_1000")
                        .iter_rows()
                        if v is not None
                    }
                    for y in years
                },
                "contrib": {
                    "months": [d.strftime("%Y-%m") for d in c_months],
                    "values": c_vals,
                    "residual": residual,
                },
            },
        )

    # ---------------------------------------------------------------- quality.json
    gate_rows = [
        {k: (_r(v, 3) if isinstance(v, float) else v) for k, v in row.items()}
        for row in gate.select("geo", "p95_abs_pp", "max_abs_pp", "gate").iter_rows(named=True)
    ]
    hbs_ok = (
        hbs.group_by("geo", "wave")
        .agg(missing=pl.col("missing_codes").first(), total=pl.col("hbs_total_per_1000").first())
        .filter((pl.col("missing") == "") & ((pl.col("total") - 1000).abs() <= 6))
    )
    sizes["quality.json"] = _dump(
        out / "quality.json",
        {
            "qa_ok": qa["ok"],
            "checks": qa["checks"],
            "reconstruction": gate_rows,
            "hbs_waves": {g: sorted(hbs_ok.filter(pl.col("geo") == g)["wave"].to_list()) for g in geos},
        },
    )

    # ---------------------------------------------------------------- meta.json
    snap = latest_snapshot("PRC_HICP_MINR")
    geo_labels = parse_codelists(snap / "structure.xml")["GEO"]
    versions = sorted(
        set(index["source_version"].unique().to_list()) | set(weights["source_version"].unique().to_list())
    )
    sizes["meta.json"] = _dump(
        out / "meta.json",
        {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source_versions": versions,
            "latest_month": last.strftime("%Y-%m"),
            "latest_full_month": full.strftime("%Y-%m"),
            "flash_month": flash_month.strftime("%Y-%m") if flash_month else None,
            "index_base": "2025=100",
            "classification": "ECOICOP ver. 2",
            "geos": [
                {
                    "code": g,
                    "name": GEO_NAME_OVERRIDE.get(g, geo_labels.get(g, g)),
                    "aggregate": g in GEO_NAME_OVERRIDE,
                }
                for g in geos
            ],
            "aggregates": AGGREGATES,
            "divisions": DIVISIONS,
            "labels": SHORT,
            "attribution": ATTRIBUTION,
        },
    )
    return sizes
