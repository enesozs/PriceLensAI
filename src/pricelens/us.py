"""M8 United States view: BLS CPI-U, shown separately from the HICP and never combined with it.

Derived weights
---------------
The CPI-U is a Laspeyres-type index linked each December, like the HICP. For year y and months t in y:

    I_t / I_Dec(y-1) - 1 = sum_i w_{i,y} (I_{i,t} / I_{i,Dec(y-1)} - 1),   sum_i w_{i,y} = 1,  w >= 0

where w_{i,y} are the December relative importances. BLS publishes them only on its website, which refuses
automated clients without a personal contact e-mail, so PriceLens *derives* them from this identity by
least squares over the months of each year, lightly shrunk towards the previous year's weights for stability.
They are labelled "derived", and how well they reproduce the published all-items index is reported.

Missing month: BLS published no October 2025 CPI (2025 federal government shutdown). Annual rates that need it
are left missing, never interpolated.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy.optimize import lsq_linear

from pricelens.config import EXPORT, REPORTS
from pricelens.contrib import contributions
from pricelens.sources.bls import latest_snapshot

PARTS = [
    "SA0E",
    "SAF1",
    "SACL1E",
    "SASLE",
]  # energy, food, core goods, core services: a partition of all items
GROUPS = ["SAF", "SAH", "SAA", "SAT", "SAM", "SAR", "SAE", "SAG"]
SHRINK = 0.05  # penalty pulling each year's weights towards the previous year's (stability in calm years)
LABEL = {
    "SA0": "All items",
    "SA0E": "Energy",
    "SAF1": "Food",
    "SACL1E": "Core goods",
    "SASLE": "Core services",
    "SAF": "Food & beverages",
    "SAH": "Housing",
    "SAA": "Apparel",
    "SAT": "Transportation",
    "SAM": "Medical care",
    "SAR": "Recreation",
    "SAE": "Education & communication",
    "SAG": "Other goods & services",
    "SAH1": "Shelter",
    "SA0L2": "All items less shelter",
}


def derive_weights(cpi: pl.DataFrame) -> pl.DataFrame:
    """year, code, weight (sums to 1), fit_rmse (index points of the link, x100)."""
    v = {(c, d): x for c, d, x in cpi.select("code", "date", "value").iter_rows()}
    years = sorted({d.year for d in cpi["date"].to_list()})
    rows, prev = [], None
    for y in years:
        dec = date(y - 1, 12, 1)
        if any((c, dec) not in v for c in [*PARTS, "SA0"]):
            continue
        A, b = [], []
        for m in range(1, 13):
            t = date(y, m, 1)
            if all((c, t) in v for c in [*PARTS, "SA0"]):
                A.append([v[(c, t)] / v[(c, dec)] - 1 for c in PARTS])
                b.append(v[("SA0", t)] / v[("SA0", dec)] - 1)
        if len(A) < 4:
            continue
        A_, b_ = np.array(A), np.array(b)
        scale = np.abs(A_).mean() or 1.0
        rows_A, rows_b = [A_ / scale], [b_ / scale]
        rows_A.append(np.ones((1, len(PARTS))) * 10)  # sum-to-one constraint, heavily weighted
        rows_b.append(np.array([10.0]))
        if prev is not None:
            rows_A.append(np.eye(len(PARTS)) * SHRINK)
            rows_b.append(np.array(prev) * SHRINK)
        sol = lsq_linear(np.vstack(rows_A), np.concatenate(rows_b), bounds=(0, 1)).x
        sol = sol / sol.sum()
        fit = float(np.sqrt(np.mean((A_ @ sol - b_) ** 2)) * 100)
        prev = sol.tolist()
        rows += [
            {"year": y, "code": c, "weight": float(w), "fit_rmse": fit, "months": len(A)}
            for c, w in zip(PARTS, sol, strict=True)
        ]
    return pl.DataFrame(rows)


def build(out: Path = EXPORT) -> dict:
    cpi = latest_snapshot()
    w = derive_weights(cpi)
    idx = cpi.select("code", "date", "value")
    total = idx.filter(pl.col("code") == "SA0").select(pl.lit("US").alias("geo"), "date", "value")
    comp = idx.filter(pl.col("code").is_in(PARTS)).select(
        pl.lit("US").alias("geo"), pl.col("code").alias("coicop"), "date", "value"
    )
    weights = w.select(
        pl.lit("US").alias("geo"),
        pl.col("code").alias("coicop"),
        "year",
        (1000 * pl.col("weight")).alias("weight"),
    )
    c = contributions(comp, weights, total).filter(pl.col("date") >= date(2001, 1, 1))

    last = idx["date"].max()
    months = pl.date_range(date(2000, 1, 1), last, "1mo", eager=True).to_list()
    V = {(cd, d): x for cd, d, x in idx.iter_rows()}

    def yoy(code: str, d: date) -> float | None:
        a, b = V.get((code, d)), V.get((code, date(d.year - 1, d.month, 1)))
        return None if a is None or b is None else round(100 * (a / b - 1), 2)

    codes = ["SA0", *PARTS, *GROUPS, "SAH1", "SA0L2"]
    cm = sorted(set(c["date"].to_list()))
    cv = {(cd, d): x for _, cd, d, x in c.iter_rows()}
    residual = []
    for d in cm:
        y = yoy("SA0", d)
        parts = [cv.get((p, d)) for p in PARTS]
        residual.append(None if y is None or None in parts else round(y - sum(parts), 3))  # type: ignore[arg-type]
    missing = sorted({d.strftime("%Y-%m") for d in months if ("SA0", d) not in V})
    fit = w.group_by("year").agg(pl.col("fit_rmse").first(), pl.col("months").first()).sort("year")
    rec = [r for r in residual if r is not None]
    payload = {
        "source": "U.S. Bureau of Labor Statistics, CPI-U, U.S. city average, not seasonally adjusted (1982-84=100)",
        "latest_month": last.strftime("%Y-%m"),
        "missing_months": missing,
        "labels": {k: LABEL[k] for k in codes},
        "parts": PARTS,
        "groups": GROUPS,
        "months": [d.strftime("%Y-%m") for d in months],
        "yoy": {k: [yoy(k, d) for d in months] for k in codes},
        "weights": {
            str(y): {
                r["code"]: round(r["weight"], 4) for r in w.filter(pl.col("year") == y).iter_rows(named=True)
            }
            for y in sorted(w["year"].unique().to_list())
        },
        "contrib": {
            "months": [d.strftime("%Y-%m") for d in cm],
            "values": {
                p: [None if cv.get((p, d)) is None else round(cv[(p, d)], 3) for d in cm] for p in PARTS
            },
            "residual": residual,
        },
        "quality": {
            "max_abs_residual_pp": round(max(abs(x) for x in rec), 3) if rec else None,
            "p95_abs_residual_pp": round(float(np.quantile(np.abs(rec), 0.95)), 3) if rec else None,
            "fit_rmse_by_year": {str(r["year"]): round(r["fit_rmse"], 4) for r in fit.iter_rows(named=True)},
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "us.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False))
    lines = [
        "# M8 United States (BLS CPI-U) report (generated)",
        "",
        f"Source: {payload['source']}. Latest month {payload['latest_month']}. Months not published by BLS: {missing}.",
        "",
        "Derived December weights (relative importance, share of all items) for energy, food, core goods and core services, "
        "estimated from the December-linked index identity. Published relative importances are on bls.gov, which PriceLens "
        "cannot fetch automatically without sending a personal contact e-mail.",
        "",
        "| year | " + " | ".join(LABEL[p] for p in PARTS) + " | fit RMSE (x100) | months |",
        "|---|" + "---|" * (len(PARTS) + 2),
    ]
    for y, ws in payload["weights"].items():
        lines.append(
            f"| {y} | "
            + " | ".join(f"{100 * ws[p]:.1f}%" for p in PARTS)
            + f" | {payload['quality']['fit_rmse_by_year'][y]} | {fit.filter(pl.col('year') == int(y))['months'][0]} |"
        )
    lines += [
        "",
        f"Contributions computed with these weights add up to the published annual rate within p95 {payload['quality']['p95_abs_residual_pp']} pp "
        f"(max {payload['quality']['max_abs_residual_pp']} pp) since 2001.",
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "m8_us.md").write_text("\n".join(lines))
    return {"latest": payload["latest_month"], "missing": missing, **payload["quality"]}
