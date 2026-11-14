"""M6 experiments on top of the M4 Forecast Lab. Every adoption decision uses validation origins (2012-2019) only;
test scores (2020+) are reported, never used to choose.

1. Ablations: which inputs carry the pooled ridge model's gain over the seasonal floor?
2. Hierarchical headline: the headline forecast rebuilt bottom-up from the four component forecasts with the
   official chain formula and weights, vs the direct headline forecast (and their average).
3. Adaptive intervals: chosen inside the forecast pipeline (forecast.add_intervals); summarised here.

Writes reports/m6_advanced.md and app/public/data/advanced.json.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

import pricelens.forecast as fc
from pricelens.config import CURATED, EXPORT, REPORTS

COMPONENTS = ["NRG", "FOOD", "IGD_NNRG", "SERV"]
MATERIALITY = 0.05  # minimum relative validation gain for adopting added complexity
OWN = ["sd0", "sd1", "sd2", "sd_3m", "sd_6m", "sd_12m", "yoy0"]
ABLATIONS = {
    "full": (),
    "no oil, fuel or FX": tuple(fc.EXOG),
    "no pump prices (Oil Bulletin)": ("f_fuel_1", "f_fuel_0", "f_heat_1", "f_heat_0"),
    "no Brent or FX": ("f_brent_1", "f_brent_0", "f_brent_12", "f_fx_1", "f_fx_12"),
    "no own price momentum": tuple(OWN),
}


def _split(df: pl.DataFrame) -> pl.Expr:
    return pl.when(pl.col("origin") <= fc.VALID[1]).then(pl.lit("validation")).otherwise(pl.lit("test"))


def ablations(ds: pl.DataFrame, version: dict, alpha: float) -> pl.DataFrame:
    origins = sorted(o for o in ds["origin"].unique().to_list() if fc.VALID[0] <= o)
    rows = []
    for name, excl in ABLATIONS.items():
        params = {"alpha": alpha, "exclude": list(excl)}
        p = fc.cached(
            f"abl-{name.replace(' ', '_')}",
            {**version, "p": params, "from": str(origins[0])},
            lambda params=params: fc.rolling("ridge", ds, origins, params),
        ).with_columns(model=pl.lit(name))
        s = fc.score(p, ds).filter(pl.col("err").is_not_null() & pl.col("h").is_in([1, 3]))
        rows.append(
            s.with_columns(
                split=_split(s),
                group=pl.when(pl.col("code") == "NRG")
                .then(pl.lit("energy"))
                .otherwise(pl.lit("other series")),
            )
            .group_by("model", "split", "h", "group")
            .agg(mae=pl.col("err").abs().mean())
        )
    return pl.concat(rows)


def bottom_up(S: pl.DataFrame, panel: pl.DataFrame, chosen: str) -> pl.DataFrame:
    """Headline annual rate from component forecasts via the December-linked chain (see src/pricelens/reconstruction.py).

    Weights: the latest year whose item weights were published before the issue date (weights for year y appear
    with the January release, so origin months >= February may use year y; earlier origins use y-1).
    """
    w = pl.read_parquet(CURATED / "hicp_weights.parquet").filter(pl.col("coicop").is_in(COMPONENTS))
    W = {
        (g, c, y): v
        for g, c, y, v in w.select("geo", "coicop", "year", "weight_per_1000").iter_rows()
        if v is not None
    }
    L = {
        (g, c, d): float(np.exp(v / 100))
        for g, c, d, v in panel.select("geo", "code", "date", "logi").iter_rows()
    }
    pr = S.filter(pl.col("model") == chosen)
    P = {(g, c, o, h): v for g, c, o, h, v in pr.select("geo", "code", "origin", "h", "pred").iter_rows()}
    out = []
    for geo, T in pr.select("geo", "origin").unique().iter_rows():
        out += _bottom_up_one(geo, T, W, L, P)
    bu = pl.DataFrame(out)
    direct = pr.filter(pl.col("code") == "TOTAL").select("geo", "origin", "h", "yoy_pred", "yoy_true")
    return direct.join(bu, on=["geo", "origin", "h"], how="inner").with_columns(
        yoy_avg=(pl.col("yoy_pred") + pl.col("yoy_bu")) / 2
    )


def _bottom_up_one(geo: str, T: date, W: dict, L: dict, P: dict) -> list[dict]:
    """Bottom-up headline annual rates for one geo and origin T, h = 1..6."""
    out: list[dict] = []
    wy = T.year if T.month >= 2 else T.year - 1

    def lvl(c: str, d: date) -> float | None:
        if d <= T:
            return L.get((geo, c, d))
        k = (d.year - T.year) * 12 + d.month - T.month
        base, p = L.get((geo, c, T)), P.get((geo, c, T, k))
        return None if base is None or p is None else base * float(np.exp(p / 100))

    def total(d: date) -> float | None:
        if d <= T:
            return L.get((geo, "TOTAL", d))
        dec = date(d.year - 1, 12, 1)
        tdec = total(dec)
        ws = {c: W.get((geo, c, min(wy, d.year))) for c in COMPONENTS}
        if tdec is None or any(v is None for v in ws.values()):
            return None
        s = sum(ws.values())
        acc = 0.0
        for c in COMPONENTS:
            a, b = lvl(c, d), lvl(c, dec)
            if a is None or b is None:
                return None
            acc += ws[c] / s * a / b
        return tdec * acc

    for h in fc.H:
        d = fc.month_add(T, h)
        t, prev = total(d), L.get((geo, "TOTAL", fc.month_add(d, -12)))
        if t is not None and prev is not None:
            out.append({"geo": geo, "origin": T, "h": h, "yoy_bu": 100 * (t / prev - 1)})
    return out


def run(out: Path = EXPORT) -> dict:
    panel, full = fc.load_panel()
    exog = fc.exog_features()
    ds = fc.build_dataset(panel, exog)
    version = fc.data_version(full, ds, exog)
    meta = json.loads((CURATED / "forecast_meta.json").read_text())
    S = pl.read_parquet(CURATED / "forecast_backtest.parquet")
    alt = pl.read_parquet(CURATED / "forecast_backtest_alt_intervals.parquet")
    chosen = meta["chosen_model"]

    # 1. ablations
    ab = ablations(ds, version, meta["best_params"]["ridge"]["alpha"])
    floor = (
        fc.score(
            fc.baselines(ds, sorted(ds["origin"].unique().to_list())).filter(
                pl.col("model") == "seasonal_mean"
            ),
            ds,
        )
        .filter(pl.col("err").is_not_null() & pl.col("h").is_in([1, 3]) & (pl.col("origin") >= fc.VALID[0]))
        .with_columns(
            split=pl.when(pl.col("origin") <= fc.VALID[1])
            .then(pl.lit("validation"))
            .otherwise(pl.lit("test")),
            group=pl.when(pl.col("code") == "NRG").then(pl.lit("energy")).otherwise(pl.lit("other series")),
        )
        .group_by("split", "h", "group")
        .agg(floor=pl.col("err").abs().mean())
    )
    ab_tab = (
        ab.join(floor, on=["split", "h", "group"])
        .with_columns(gain_vs_floor_pct=100 * (1 - pl.col("mae") / pl.col("floor")))
        .sort("split", "h", "group", "mae")
    )

    # 2. hierarchical headline
    bu = bottom_up(S, panel, chosen).drop_nulls(["yoy_true"])
    bu_tab = (
        bu.with_columns(split=_split(bu))
        .filter(pl.col("h").is_in([1, 3]))
        .group_by("split", "h")
        .agg(
            direct=(pl.col("yoy_pred") - pl.col("yoy_true")).abs().mean(),
            bottom_up=(pl.col("yoy_bu") - pl.col("yoy_true")).abs().mean(),
            average=(pl.col("yoy_avg") - pl.col("yoy_true")).abs().mean(),
            n=pl.len(),
        )
        .sort("split", "h")
    )
    val = bu.filter(
        (pl.col("origin") >= fc.VALID[0]) & (pl.col("origin") <= fc.VALID[1]) & pl.col("h").is_in([1, 3])
    )
    hier_val = {
        k: float(val.select((pl.col(c) - pl.col("yoy_true")).abs().mean()).item())
        for k, c in (("direct", "yoy_pred"), ("bottom_up", "yoy_bu"), ("average", "yoy_avg"))
    }
    # Materiality rule: a structural change is adopted only if it improves
    # the validation MAE by at least MATERIALITY; smaller gains are within noise and not worth the complexity.
    best_alt = min(("bottom_up", "average"), key=hier_val.get)
    gain = 1 - hier_val[best_alt] / hier_val["direct"]
    hier_choice = best_alt if gain >= MATERIALITY else "direct"

    # 3. intervals: chosen vs alternative, by period
    def cov(df: pl.DataFrame, label: str) -> pl.DataFrame:
        d = df.filter(
            (pl.col("model") == chosen)
            & pl.col("lo80").is_not_null()
            & pl.col("err").is_not_null()
            & pl.col("h").is_in([1, 3])
        )
        return (
            d.with_columns(
                period=fc.regime(),
                inside=(pl.col("yoy_true") >= pl.col("lo80")) & (pl.col("yoy_true") <= pl.col("hi80")),
                score=fc.interval_score(d),
            )
            .group_by("period", "h")
            .agg(coverage80=pl.col("inside").mean(), winkler=pl.col("score").mean())
            .with_columns(method=pl.lit(label))
        )

    other = "adaptive" if meta["interval_method"] == "static" else "static"
    iv = pl.concat([cov(S, meta["interval_method"]), cov(alt, other)]).sort("h", "period", "method")

    lines = [
        "# M6 advanced forecasting report (generated)",
        "",
        "All choices on validation origins 2012–2019; test = origins 2020+ (reported only). Errors are annual-rate MAE in pp.",
        "",
        "## 1. Ablations of the pooled ridge model",
        "",
        "Gain vs the 3-year seasonal-mean floor, by input family removed.",
        "",
        fc._md(ab_tab),
        "",
        "## 2. Hierarchical headline",
        "",
        f"Validation MAE (h=1,3): {json.dumps({k: round(v, 4) for k, v in hier_val.items()})}. Best alternative "
        f"`{best_alt}` gains {100 * gain:.1f}% vs the direct forecast; materiality threshold {100 * MATERIALITY:.0f}% → "
        f"adopted: **{hier_choice}**.",
        "",
        fc._md(bu_tab),
        "",
        "## 3. Intervals",
        "",
        f"Chosen on validation inside `pricelens forecast`: **{meta['interval_method']}** "
        f"(validation Winkler {json.dumps(meta['interval_validation_winkler'])}).",
        "",
        fc._md(iv),
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "m6_advanced.md").write_text("\n".join(lines))

    r3 = lambda x: None if x is None else round(float(x), 3)  # noqa: E731
    payload = {
        "ablations": [
            {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
            for r in ab_tab.iter_rows(named=True)
        ],
        "hierarchy": {
            "validation": {k: r3(v) for k, v in hier_val.items()},
            "adopted": hier_choice,
            "best_alternative": best_alt,
            "gain": r3(gain),
            "materiality": MATERIALITY,
            "table": [
                {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
                for r in bu_tab.iter_rows(named=True)
            ],
        },
        "intervals": {
            "chosen": meta["interval_method"],
            "validation_winkler": meta["interval_validation_winkler"],
            "table": [
                {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
                for r in iv.iter_rows(named=True)
            ],
        },
    }
    (out / "advanced.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False))
    return {"hierarchy": hier_choice, "intervals": meta["interval_method"]}
