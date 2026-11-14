"""M4 Forecast Laboratory: rolling-origin forecasts of HICP aggregates with honest benchmarks.

Information set (no lookahead)
------------------------------
A forecast with origin T (the latest month with a full HICP release) is issued on day CUTOFF_DAY of month T+1,
after the full release of T (around mid-month) and before the flash estimate of T+1 (end of month T+1).
It may use: HICP up to T; Oil Bulletin weekly prices dated up to CUTOFF_DAY-2 of T+1 (publication lag);
Brent and EUR/USD daily up to CUTOFF_DAY of T+1. Market prices are public in real time; the EIA file is used
as their archive. HICP is rarely revised, so the current vintage is used for history (disclosed:
pseudo-real-time).

Targets and scoring
-------------------
y_{s,T,h} = 100 * log(I_{s,T+h} / I_{s,T}) for h = 1..6; forecasts are converted to the annual rate of T+h
(using the observed I_{T+h-12}) and scored in percentage points. Validation origins (all tuning): 2012-01 to
2019-12. Test origins: 2020-01 onward, never used for any choice.
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import polars as pl

from pricelens.config import CURATED, EXPORT, REPORTS, forecast_geos

CODES = ["TOTAL", "NRG", "FOOD", "IGD_NNRG", "SERV"]
H = [1, 2, 3, 4, 5, 6]
CUTOFF_DAY = 15
OIL_PUBLICATION_LAG_DAYS = 2
VALID = (date(2012, 1, 1), date(2019, 12, 1))
TEST_FROM = date(2020, 1, 1)
BACKTEST_FROM = date(2010, 1, 1)  # 2010-2011 origins only warm up the interval calibration
INTERVAL_WINDOW = 60  # realised errors used for empirical intervals
SEED = 7
GBM_THREADS = 2


# ------------------------------------------------------------------------------------------------ data


def month_add(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    return date(d.year + y, m + 1, 1)


def load_panel() -> tuple[pl.DataFrame, date]:
    """geo, code, date, logi (100*log I25) for the forecast scope, full releases only."""
    idx = pl.read_parquet(CURATED / "hicp_index.parquet").filter(
        (pl.col("unit") == "I25")
        & pl.col("geo").is_in(forecast_geos())
        & pl.col("coicop").is_in(CODES)
        & pl.col("value").is_not_null()
    )
    full = idx.filter((pl.col("geo") == "EA") & (pl.col("level") == "division"))["date"].max()
    if full is None:  # divisions are not in this filtered frame; recompute from the full table
        allidx = pl.read_parquet(CURATED / "hicp_index.parquet")
        full = allidx.filter(
            (pl.col("unit") == "I25") & (pl.col("geo") == "EA") & (pl.col("level") == "division")
        )["date"].max()
    panel = idx.filter(pl.col("date") <= full).select(
        "geo", pl.col("coicop").alias("code"), "date", (100 * pl.col("value").log()).alias("logi")
    )
    return panel.sort("geo", "code", "date"), full


def exog_features() -> pl.DataFrame:
    """Monthly as-of features keyed by origin month T (information up to CUTOFF_DAY of T+1)."""
    from pricelens.sources.extra import brent, eurusd, oil_bulletin

    fx = eurusd()
    b = (
        brent()
        .join(fx, on="date", how="left")
        .sort("date")
        .with_columns(pl.col("usd_per_eur").forward_fill())
    )
    b = b.with_columns(eur=pl.col("usd") / pl.col("usd_per_eur")).drop_nulls("eur")
    b = b.with_columns(month=pl.col("date").dt.truncate("1mo"), day=pl.col("date").dt.day())
    fx = fx.with_columns(month=pl.col("date").dt.truncate("1mo"), day=pl.col("date").dt.day())
    full_b = b.group_by("month").agg(brent=pl.col("eur").mean())
    early_b = b.filter(pl.col("day") <= CUTOFF_DAY).group_by("month").agg(brent_early=pl.col("eur").mean())
    full_fx = fx.group_by("month").agg(fx=pl.col("usd_per_eur").mean())
    early_fx = (
        fx.filter(pl.col("day") <= CUTOFF_DAY).group_by("month").agg(fx_early=pl.col("usd_per_eur").mean())
    )
    m = (
        full_b.join(early_b, on="month", how="full", coalesce=True)
        .join(full_fx, on="month", how="full", coalesce=True)
        .join(early_fx, on="month", how="full", coalesce=True)
        .sort("month")
    )
    # origin T: month T complete; T+1 known up to the cutoff
    g = m.with_columns(
        f_brent_1=pl.col("brent_early").shift(-1).log() - pl.col("brent").log(),
        f_brent_0=pl.col("brent").log() - pl.col("brent").shift(1).log(),
        f_brent_12=pl.col("brent").log() - pl.col("brent").shift(12).log(),
        f_fx_1=pl.col("fx_early").shift(-1).log() - pl.col("fx").log(),
        f_fx_12=pl.col("fx").log() - pl.col("fx").shift(12).log(),
    ).select(pl.col("month").alias("date"), "f_brent_1", "f_brent_0", "f_brent_12", "f_fx_1", "f_fx_12")

    oil = oil_bulletin().with_columns(month=pl.col("date").dt.truncate("1mo"), day=pl.col("date").dt.day())
    oil = oil.with_columns(
        product=pl.when(pl.col("product") == "heating_oil").then(pl.lit("heat")).otherwise(pl.lit("motor"))
    )
    fm = oil.group_by("geo", "product", "month").agg(p=pl.col("price").mean())
    fe = (
        oil.filter(pl.col("day") <= CUTOFF_DAY - OIL_PUBLICATION_LAG_DAYS)
        .group_by("geo", "product", "month")
        .agg(pe=pl.col("price").mean())
    )
    f = fm.join(fe, on=["geo", "product", "month"], how="full", coalesce=True).sort("geo", "product", "month")
    f = f.with_columns(
        one=pl.col("pe").shift(-1).over("geo", "product").log() - pl.col("p").log(),
        zero=pl.col("p").log() - pl.col("p").shift(1).over("geo", "product").log(),
    )
    fw = f.pivot(on="product", index=["geo", "month"], values=["one", "zero"])
    names = {
        "one_motor": "f_fuel_1",
        "zero_motor": "f_fuel_0",
        "one_heat": "f_heat_1",
        "zero_heat": "f_heat_0",
    }
    fw = fw.with_columns([pl.lit(None, dtype=pl.Float64).alias(c) for c in names if c not in fw.columns])
    fw = fw.rename(names)
    fw = fw.rename({"month": "date"})
    geos = pl.DataFrame({"geo": forecast_geos()})
    out = geos.join(g, how="cross").join(fw, on=["geo", "date"], how="left")
    return out.with_columns([pl.col(c) * 100 for c in out.columns if c.startswith("f_")])


EXOG = [
    "f_brent_1",
    "f_brent_0",
    "f_brent_12",
    "f_fx_1",
    "f_fx_12",
    "f_fuel_1",
    "f_fuel_0",
    "f_heat_1",
    "f_heat_0",
]


def build_dataset(panel: pl.DataFrame, exog: pl.DataFrame) -> pl.DataFrame:
    """One row per (geo, code, origin T): features known at the issue date + targets y_h and seasonal baselines."""
    p = panel.sort("geo", "code", "date")
    grp = ["geo", "code"]
    p = p.with_columns(d=pl.col("logi").diff().over(grp))
    p = p.with_columns(
        sd=pl.col("d") - (pl.col("d").shift(12) + pl.col("d").shift(24) + pl.col("d").shift(36)).over(grp) / 3
    )
    feats = [
        pl.col("sd").alias("sd0"),
        pl.col("sd").shift(1).over(grp).alias("sd1"),
        pl.col("sd").shift(2).over(grp).alias("sd2"),
        (pl.col("sd").rolling_sum(3).over(grp)).alias("sd_3m"),
        (pl.col("sd").rolling_sum(6).over(grp)).alias("sd_6m"),
        (pl.col("sd").rolling_sum(12).over(grp)).alias("sd_12m"),
        (pl.col("logi") - pl.col("logi").shift(12).over(grp)).alias("yoy0"),
    ]
    p = p.with_columns(feats)
    tgt = []
    for h in H:
        fut = pl.col("logi").shift(-h).over(grp)
        tgt += [
            (fut - pl.col("logi")).alias(f"y{h}"),
            # seasonal baselines: same window in previous years
            (pl.col("logi").shift(12 - h).over(grp) - pl.col("logi").shift(12).over(grp)).alias(f"sn{h}"),
            (
                sum(
                    (pl.col("logi").shift(12 * k - h).over(grp) - pl.col("logi").shift(12 * k).over(grp))
                    for k in (1, 2, 3)
                )
                / 3
            ).alias(f"sm{h}"),
            # level 12 months before the target month (known at origin for h <= 12)
            pl.col("logi").shift(12 - h).over(grp).alias(f"base{h}"),
        ]
    p = p.with_columns(tgt)
    p = p.join(exog, on=["geo", "date"], how="left")
    return p.rename({"date": "origin"}).filter(pl.col("sm6").is_not_null())


# ------------------------------------------------------------------------------------------------ models


def design(df: pl.DataFrame, h: int) -> tuple[np.ndarray, list[str]]:
    """Feature matrix for the pooled linear model: own dynamics + exog x series-type interactions + calendar."""
    cols, mats = [], []
    base = ["sd0", "sd1", "sd2", "sd_3m", "sd_6m", "sd_12m", "yoy0"]
    target_month = (pl.col("origin").dt.month() + h - 1) % 12
    X = df.with_columns(
        cal_s=(2 * math.pi * target_month / 12).sin(),
        cal_c=(2 * math.pi * target_month / 12).cos(),
    )
    for c in CODES:
        isc = (X["code"] == c).cast(pl.Float64).to_numpy()
        mats.append(isc[:, None])
        cols.append(f"is_{c}")
        for f in base + EXOG + ["cal_s", "cal_c"]:
            v = X[f].fill_null(0.0).to_numpy()
            mats.append((v * isc)[:, None])
            cols.append(f"{f}|{c}")
    for g in forecast_geos():
        mats.append((X["geo"] == g).cast(pl.Float64).to_numpy()[:, None])
        cols.append(f"geo_{g}")
    return np.hstack(mats), cols


def lgbm_matrix(df: pl.DataFrame, h: int) -> np.ndarray:
    target_month = ((df["origin"].dt.month() + h - 1) % 12).to_numpy()
    code = np.array([CODES.index(c) for c in df["code"]])
    geo = np.array([forecast_geos().index(g) for g in df["geo"]])
    num = df.select(["sd0", "sd1", "sd2", "sd_3m", "sd_6m", "sd_12m", "yoy0", *EXOG]).to_numpy().astype(float)
    return np.column_stack([num, code, geo, target_month])


@dataclass
class Fitted:
    kind: str
    obj: object
    mu: np.ndarray | None = None
    sd: np.ndarray | None = None


def fit(kind: str, train: pl.DataFrame, h: int, params: dict) -> Fitted:
    y = (train[f"y{h}"] - train[f"sm{h}"]).to_numpy()  # learn the deviation from the seasonal mean
    if kind == "ridge":
        from sklearn.linear_model import Ridge

        X, _ = design(train, h)
        mu, sd = X.mean(0), X.std(0)
        sd[sd == 0] = 1
        m = Ridge(alpha=params["alpha"]).fit((X - mu) / sd, y)
        return Fitted(kind, m, mu, sd)
    if kind == "gbm":
        # scikit-learn's histogram gradient boosting (LightGBM-style); LightGBM itself needs a system OpenMP library

        from threadpoolctl import threadpool_limits

        X = lgbm_matrix(train, h)
        n = X.shape[1]
        with threadpool_limits(limits=GBM_THREADS):  # default OpenMP threading oversubscribes (~3x slower)
            m = _hgb(params, n, X, y)
        return Fitted(kind, m)
    raise ValueError(kind)


def _hgb(params: dict, n: int, X: np.ndarray, y: np.ndarray):
    from sklearn.ensemble import HistGradientBoostingRegressor

    return HistGradientBoostingRegressor(
        max_iter=params["max_iter"],
        learning_rate=params["learning_rate"],
        max_leaf_nodes=params["max_leaf_nodes"],
        min_samples_leaf=params["min_samples_leaf"],
        l2_regularization=1.0,
        categorical_features=[n - 3, n - 2],
        random_state=SEED,
    ).fit(X, y)


def predict(f: Fitted, df: pl.DataFrame, h: int) -> np.ndarray:
    if f.kind == "gbm":
        from threadpoolctl import threadpool_limits

        with threadpool_limits(limits=GBM_THREADS):
            return df[f"sm{h}"].to_numpy() + f.obj.predict(lgbm_matrix(df, h))  # type: ignore[attr-defined]
    sm = df[f"sm{h}"].to_numpy()
    if f.kind == "ridge":
        X, _ = design(df, h)
        return sm + f.obj.predict((X - f.mu) / f.sd)  # type: ignore[attr-defined]
    return sm + f.obj.predict(lgbm_matrix(df, h))  # type: ignore[attr-defined]


def sarima_forecasts(panel: pl.DataFrame, origins: list[date]) -> pl.DataFrame:
    """Per-series SARIMA(1,0,0)(1,0,0)12 with constant on monthly log changes, 10-year rolling window,
    parameters refit every January and re-filtered (not refit) for the other origins of the year."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    rows = []
    for (geo, code), g in panel.group_by("geo", "code"):
        g = g.sort("date")
        d = np.diff(g["logi"].to_numpy())
        dates = g["date"].to_list()[1:]
        res = None
        for T in origins:
            if T not in dates:
                continue
            i = dates.index(T)
            window = d[max(0, i - 119) : i + 1]
            if res is None or T.month == 1:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = SARIMAX(window, order=(1, 0, 0), seasonal_order=(1, 0, 0, 12), trend="c").fit(
                        disp=False
                    )
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = res.apply(window)
            fc = np.cumsum(res.forecast(max(H)))
            for h in H:
                rows.append({"geo": geo, "code": code, "origin": T, "h": h, "pred": float(fc[h - 1])})
    return pl.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ backtest

RIDGE_GRID = [{"alpha": a} for a in (1.0, 10.0, 100.0, 1000.0)]
GBM_GRID = [
    {"max_iter": 200, "learning_rate": 0.03, "max_leaf_nodes": 7, "min_samples_leaf": 40},
    {"max_iter": 400, "learning_rate": 0.03, "max_leaf_nodes": 15, "min_samples_leaf": 40},
    {"max_iter": 300, "learning_rate": 0.05, "max_leaf_nodes": 7, "min_samples_leaf": 80},
]


def rolling(kind: str, ds: pl.DataFrame, origins: list[date], params: dict) -> pl.DataFrame:
    """Expanding-window rolling origin; models refit every January (and at the first origin)."""
    out = []
    fitted: dict[int, Fitted] = {}
    for T in origins:
        test = ds.filter(pl.col("origin") == T)
        if test.height == 0:
            continue
        for h in H:
            if h not in fitted or T.month == 1 or origins[0] == T:
                train = ds.filter((pl.col("origin") <= month_add(T, -h)) & pl.col(f"y{h}").is_not_null())
                fitted[h] = fit(kind, train, h, params)
            out.append(
                test.select("geo", "code", "origin").with_columns(
                    h=pl.lit(h), pred=pl.Series(predict(fitted[h], test, h))
                )
            )
    return pl.concat(out)


def baselines(ds: pl.DataFrame, origins: list[date]) -> pl.DataFrame:
    rows = []
    sub = ds.filter(pl.col("origin").is_in(origins))
    for h in H:
        for name, expr in [
            ("no_change", pl.lit(0.0)),
            ("seasonal_naive", pl.col(f"sn{h}")),
            ("seasonal_mean", pl.col(f"sm{h}")),
        ]:
            rows.append(
                sub.select(
                    "geo",
                    "code",
                    "origin",
                    pl.lit(h).alias("h"),
                    expr.alias("pred"),
                    pl.lit(name).alias("model"),
                )
            )
    return pl.concat(rows)


def score(preds: pl.DataFrame, ds: pl.DataFrame) -> pl.DataFrame:
    """Attach actuals and convert to annual rates of the target month (pp)."""
    long = pl.concat(
        [
            ds.select(
                "geo",
                "code",
                "origin",
                pl.lit(h).alias("h"),
                pl.col(f"y{h}").alias("y"),
                pl.col(f"base{h}").alias("base"),
                "logi",
            )
            for h in H
        ]
    )
    df = preds.join(long, on=["geo", "code", "origin", "h"], how="left")
    to_rate = lambda lg: 100 * ((pl.col("logi") + lg - pl.col("base")) / 100).exp() - 100  # noqa: E731
    return df.with_columns(
        target=pl.col("origin").dt.offset_by(pl.format("{}mo", pl.col("h"))),
        yoy_pred=to_rate(pl.col("pred")),
        yoy_true=pl.when(pl.col("y").is_not_null()).then(to_rate(pl.col("y"))),
    ).with_columns(err=pl.col("yoy_pred") - pl.col("yoy_true"))


def add_intervals(sc: pl.DataFrame) -> pl.DataFrame:
    """Empirical intervals from each model's own realised errors (target month <= origin, last INTERVAL_WINDOW)."""
    out = []
    for _key, g in sc.group_by("model", "geo", "code", "h"):
        g = g.sort("origin")
        origins = g["origin"].to_list()
        targets = g["target"].to_list()
        errs = g["err"].to_list()
        q = {k: [] for k in ("lo80", "hi80", "lo95", "hi95")}
        for i, T in enumerate(origins):
            past = [e for t, e in zip(targets[:i], errs[:i], strict=True) if t <= T and e is not None][
                -INTERVAL_WINDOW:
            ]
            if len(past) < 24:
                for k in q:
                    q[k].append(None)
                continue
            a = np.array(past)
            q["lo80"].append(float(np.quantile(a, 0.1)))
            q["hi80"].append(float(np.quantile(a, 0.9)))
            q["lo95"].append(float(np.quantile(a, 0.025)))
            q["hi95"].append(float(np.quantile(a, 0.975)))
        out.append(
            g.with_columns(
                # interval for the true value = prediction - error quantiles
                lo80=pl.col("yoy_pred") - pl.Series(q["hi80"], dtype=pl.Float64),
                hi80=pl.col("yoy_pred") - pl.Series(q["lo80"], dtype=pl.Float64),
                lo95=pl.col("yoy_pred") - pl.Series(q["hi95"], dtype=pl.Float64),
                hi95=pl.col("yoy_pred") - pl.Series(q["lo95"], dtype=pl.Float64),
            )
        )
    return pl.concat(out)


def mae(df: pl.DataFrame) -> float:
    return float(df["err"].abs().mean())  # type: ignore[arg-type]


def regime(col: str = "target") -> pl.Expr:
    t = pl.col(col)
    return (
        pl.when(t < pl.date(2020, 1, 1))
        .then(pl.lit("2012-19 (validation)"))
        .when(t < pl.date(2022, 1, 1))
        .then(pl.lit("2020-21 pandemic"))
        .when(t < pl.date(2024, 1, 1))
        .then(pl.lit("2022-23 energy shock"))
        .when(t < pl.date(2026, 1, 1))
        .then(pl.lit("2024-25 normalisation"))
        .otherwise(pl.lit("2026 shock"))
    )


# ------------------------------------------------------------------------------------------------ benchmarks


def flash_benchmark() -> pl.DataFrame:
    """First published flash annual rates: geo, code, target (date), flash."""
    from pricelens.sources.eurostat import latest_snapshot, parse_tsv

    out = []
    for ds, code_col, total in (("PRC_HICP_FP", "coicop", "CP00"), ("PRC_HICP_FPD", "coicop18", "TOTAL")):
        snap = latest_snapshot(ds)
        df = parse_tsv(
            snap / "data.tsv.gz",
            keep={
                "unit": ["RCH_A"],
                "release": ["FLS"],
                "geo": forecast_geos(),
                code_col: [total, *CODES[1:]],
            },
        )
        out.append(
            df.select(
                "geo",
                pl.col(code_col).replace({total: "TOTAL"}).alias("code"),
                pl.col("time").str.to_date("%Y-%m").alias("target"),
                pl.col("value").alias("flash"),
            ).drop_nulls()
        )
    fp = pl.concat(out)
    return fp.unique(["geo", "code", "target"], keep="last")


def staff_benchmark(levels: pl.DataFrame, preds: pl.DataFrame, model: str) -> pl.DataFrame:
    """Quarterly annual rates: ECB/Eurosystem staff projections vs our model, euro area.

    Exercise in month m (Mar/Jun/Sep/Dec) of year y -> our origin T = m-2 (its full HICP release is out by
    mid m-1, before the staff data cut-off). Q0 = quarter containing m (months m-2..m, i.e. T and h=1,2);
    Q1 = next quarter (h=3,4,5). ECB projections usually include the flash for m-1 as well: an information edge
    for the ECB, disclosed.
    """
    from pricelens.sources.extra import staff_projections

    sp = staff_projections()
    lv = levels.filter(pl.col("geo") == "EA").select("code", "date", "logi")
    lvd = {(c, d): v for c, d, v in lv.iter_rows()}
    pr = preds.filter((pl.col("model") == model) & (pl.col("geo") == "EA"))
    prd = {(c, o, h): p for c, o, h, p in pr.select("code", "origin", "h", "pred").iter_rows()}
    rows = []
    for ex, y, m in sp.select("exercise", "ex_year", "ex_month").unique().iter_rows():
        T = date(y, m - 2, 1)
        for qi, months in (
            (0, [month_add(T, k) for k in (0, 1, 2)]),
            (1, [month_add(T, k) for k in (3, 4, 5)]),
        ):
            qlabel = f"{months[0].year}-Q{(months[0].month - 1) // 3 + 1}"
            for c in CODES:
                prev = [lvd.get((c, month_add(d, -12))) for d in months]
                true = [lvd.get((c, d)) for d in months]
                ours = []
                for d in months:
                    k = (d.year - T.year) * 12 + d.month - T.month
                    if k == 0:
                        ours.append(lvd.get((c, T)))
                    else:
                        p = prd.get((c, T, k))
                        ours.append(None if p is None or lvd.get((c, T)) is None else lvd[(c, T)] + p)
                ecb = sp.filter(
                    (pl.col("exercise") == ex) & (pl.col("code") == c) & (pl.col("quarter") == qlabel)
                )["value"]
                if None in prev or None in true or None in ours or ecb.len() == 0:
                    continue
                den = sum(math.exp(v / 100) for v in prev)

                def qr(a: list, den: float = den) -> float:
                    return 100 * (sum(math.exp(v / 100) for v in a) / den - 1)

                rows.append(
                    {
                        "exercise": ex,
                        "origin": T,
                        "horizon": f"Q{qi}",
                        "quarter": qlabel,
                        "code": c,
                        "actual": qr(true),
                        "ours": qr(ours),
                        "ecb": float(ecb[0]),
                    }
                )
    return pl.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ run


def cached(name: str, key: dict, compute) -> pl.DataFrame:
    """Cache expensive rolling predictions under data/curated/forecast_cache, keyed by settings + data version."""
    import hashlib
    import time

    d = CURATED / "forecast_cache"
    d.mkdir(parents=True, exist_ok=True)
    k = hashlib.sha256(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:16]
    f = d / f"{name}-{k}.parquet"
    if f.exists():
        return pl.read_parquet(f)
    t0 = time.time()
    df = compute().with_columns(pl.col("h").cast(pl.Int64))
    df.write_parquet(f)
    print(f"  {name}: {df.height:,} predictions in {time.time() - t0:.0f}s")
    return df


def run(out_dir: Path = CURATED) -> dict:
    panel, full = load_panel()
    exog = exog_features()
    ds = build_dataset(panel, exog)
    version = {
        "latest": str(full),
        "rows": ds.height,
        "exog_sum": float(exog.select(pl.sum_horizontal(pl.col("^f_.*$").fill_null(0).sum())).item()),
        "h": H,
        "cutoff": CUTOFF_DAY,
    }
    all_origins = sorted(o for o in ds["origin"].unique().to_list() if o >= BACKTEST_FROM)
    valid_origins = [o for o in all_origins if VALID[0] <= o <= VALID[1]]

    # ---- tuning on validation origins only (h=1 and h=3 annual-rate MAE)
    def val_mae(kind: str, params: dict) -> float:
        p = cached(
            f"val-{kind}", {**version, "params": params}, lambda: rolling(kind, ds, valid_origins, params)
        ).with_columns(model=pl.lit(kind))
        s = score(p, ds).filter(pl.col("h").is_in([1, 3]) & pl.col("err").is_not_null())
        return mae(s)

    tuning = {
        "ridge": [(p, val_mae("ridge", p)) for p in RIDGE_GRID],
        "gbm": [(p, val_mae("gbm", p)) for p in GBM_GRID],
    }
    best = {k: min(v, key=lambda x: x[1])[0] for k, v in tuning.items()}

    # ---- full rolling backtest with the chosen settings
    preds = [
        cached(
            "ridge", {**version, "p": best["ridge"]}, lambda: rolling("ridge", ds, all_origins, best["ridge"])
        ).with_columns(model=pl.lit("ridge")),
        cached(
            "gbm", {**version, "p": best["gbm"]}, lambda: rolling("gbm", ds, all_origins, best["gbm"])
        ).with_columns(model=pl.lit("gbm")),
        cached("sarima", version, lambda: sarima_forecasts(panel, all_origins)).with_columns(
            model=pl.lit("sarima")
        ),
        baselines(ds, all_origins),
    ]
    P = pl.concat(
        [
            p.select(
                "geo", "code", "origin", pl.col("h").cast(pl.Int64), pl.col("pred").cast(pl.Float64), "model"
            )
            for p in preds
        ]
    )
    ens = (
        P.filter(pl.col("model").is_in(["ridge", "gbm"]))
        .group_by("geo", "code", "origin", "h")
        .agg(pred=pl.col("pred").mean())
        .with_columns(model=pl.lit("ensemble"))
        .select(P.columns)
    )
    P = pl.concat([P, ens])
    S = add_intervals(score(P, ds))

    # ---- model selection on validation only
    v = S.filter(
        (pl.col("origin") >= VALID[0])
        & (pl.col("origin") <= VALID[1])
        & pl.col("h").is_in([1, 3])
        & pl.col("err").is_not_null()
    )
    val_table = v.group_by("model").agg(mae=pl.col("err").abs().mean()).sort("mae")
    chosen = val_table.filter(~pl.col("model").is_in(["no_change", "seasonal_naive", "seasonal_mean"]))[
        "model"
    ][0]

    S.write_parquet(out_dir / "forecast_backtest.parquet")
    flash = flash_benchmark()
    staff = staff_benchmark(panel, P, chosen)
    staff.write_parquet(out_dir / "forecast_staff_benchmark.parquet")

    # ---- live forecast from the latest full month (issued as of CUTOFF_DAY of the next month)
    live = S.filter((pl.col("origin") == full) & (pl.col("model") == chosen))
    meta = {
        "chosen_model": chosen,
        "tuning": {k: [{"params": p, "val_mae": round(m, 4)} for p, m in v_] for k, v_ in tuning.items()},
        "best_params": best,
        "latest_origin": full.isoformat(),
        "issued_as_of": date(month_add(full, 1).year, month_add(full, 1).month, CUTOFF_DAY).isoformat(),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / "forecast_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    report(S, val_table, chosen, flash, staff, meta)
    export(S, chosen, flash, staff, meta, live, panel)
    return meta


# ------------------------------------------------------------------------------------------------ report + export


def _md(df: pl.DataFrame) -> str:
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for row in df.iter_rows():
        lines.append(
            "| "
            + " | ".join("" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v)) for v in row)
            + " |"
        )
    return "\n".join(lines)


MODEL_LABEL = {
    "no_change": "No change (floor)",
    "seasonal_naive": "Seasonal naïve (floor)",
    "seasonal_mean": "Seasonal mean, 3 years (floor)",
    "sarima": "SARIMA per series",
    "ridge": "Ridge, pooled",
    "gbm": "Gradient boosting, pooled",
    "ensemble": "Ridge + gradient boosting average",
}


def summary_tables(
    S: pl.DataFrame, flash: pl.DataFrame, staff: pl.DataFrame, chosen: str
) -> dict[str, pl.DataFrame]:
    test = S.filter((pl.col("origin") >= TEST_FROM) & pl.col("err").is_not_null())
    by_model = (
        test.filter(pl.col("h").is_in([1, 3]))
        .group_by("model", "h")
        .agg(mae=pl.col("err").abs().mean(), rmse=(pl.col("err") ** 2).mean().sqrt(), n=pl.len())
        .sort("h", "mae")
    )
    by_code = (
        test.filter(pl.col("h").is_in([1, 3]) & pl.col("model").is_in([chosen, "seasonal_mean", "no_change"]))
        .group_by("code", "h", "model")
        .agg(mae=pl.col("err").abs().mean())
        .pivot(on="model", index=["code", "h"], values="mae")
        .sort("h", "code")
    )
    by_regime = (
        S.filter(
            pl.col("h").is_in([1, 3])
            & pl.col("err").is_not_null()
            & pl.col("model").is_in([chosen, "seasonal_mean"])
        )
        .with_columns(period=regime())
        .group_by("period", "h", "model")
        .agg(mae=pl.col("err").abs().mean())
        .pivot(on="model", index=["period", "h"], values="mae")
        .sort("h", "period")
    )
    cov = (
        test.filter(pl.col("model") == chosen)
        .filter(pl.col("lo80").is_not_null())
        .with_columns(
            in80=(pl.col("yoy_true") >= pl.col("lo80")) & (pl.col("yoy_true") <= pl.col("hi80")),
            in95=(pl.col("yoy_true") >= pl.col("lo95")) & (pl.col("yoy_true") <= pl.col("hi95")),
            w80=pl.col("hi80") - pl.col("lo80"),
            period=regime(),
        )
        .group_by("h", "period")
        .agg(
            cov80=pl.col("in80").mean(),
            cov95=pl.col("in95").mean(),
            width80=pl.col("w80").median(),
            n=pl.len(),
        )
        .sort("h", "period")
    )
    fl = (
        S.filter((pl.col("model") == chosen) & (pl.col("h") == 1) & pl.col("err").is_not_null())
        .join(flash, on=["geo", "code", "target"], how="inner")
        .with_columns(flash_err=pl.col("flash") - pl.col("yoy_true"))
    )
    flash_tab = (
        fl.group_by("code")
        .agg(
            n=pl.len(),
            ours_mae=pl.col("err").abs().mean(),
            flash_mae=pl.col("flash_err").abs().mean(),
            from_=pl.col("target").min().dt.strftime("%Y-%m"),
        )
        .sort("code")
    )
    st = staff.filter(pl.col("origin") >= TEST_FROM)
    staff_tab = (
        st.group_by("horizon", "code")
        .agg(
            n=pl.len(),
            ours_mae=(pl.col("ours") - pl.col("actual")).abs().mean(),
            ecb_mae=(pl.col("ecb") - pl.col("actual")).abs().mean(),
        )
        .sort("horizon", "code")
    )
    return {
        "by_model": by_model,
        "by_code": by_code,
        "by_regime": by_regime,
        "coverage": cov,
        "flash": flash_tab,
        "staff": staff_tab,
        "flash_rows": fl,
    }


def report(
    S: pl.DataFrame,
    val_table: pl.DataFrame,
    chosen: str,
    flash: pl.DataFrame,
    staff: pl.DataFrame,
    meta: dict,
) -> None:
    t = summary_tables(S, flash, staff, chosen)
    lines = [
        "# M4 Forecast Laboratory report (generated)",
        "",
        f"Generated {meta['generated_at']} by `uv run pricelens forecast`. Latest origin {meta['latest_origin']}, issued as of "
        f"{meta['issued_as_of']}. Scores are annual-rate errors of the target month, in percentage points, over the euro area, "
        "DE, FR, IT and ES × headline, energy, food, non-energy industrial goods and services.",
        "",
        "## Model selection (validation origins 2012–2019 only; h = 1 and 3)",
        "",
        _md(val_table.with_columns(pl.col("model").replace(MODEL_LABEL))),
        "",
        f"Chosen model: **{MODEL_LABEL[chosen]}**. Tuning grids: {json.dumps(meta['tuning'])}",
        "",
        "## Test period (origins 2020-01 onward, untouched during tuning)",
        "",
        _md(t["by_model"].with_columns(pl.col("model").replace(MODEL_LABEL))),
        "",
        "### By series type",
        "",
        _md(t["by_code"]),
        "",
        "### By period (validation and test)",
        "",
        _md(t["by_regime"]),
        "",
        "### Interval calibration (empirical intervals from the model's own past errors)",
        "",
        _md(t["coverage"]),
        "",
        "## Benchmarks",
        "",
        "### Eurostat flash estimate (h = 1)",
        "",
        "The flash for month T+1 is published at the end of T+1, about two weeks after our forecast is issued, with "
        "most of the month's prices. It is the bar to beat, not a floor. Flash rates have 1 decimal.",
        "",
        _md(t["flash"].rename({"from_": "from"})),
        "",
        "### ECB/Eurosystem staff projections (quarterly annual rate, euro area, test exercises)",
        "",
        "Q0 = quarter of the projection exercise (we know its first month), Q1 = next quarter. Staff projections "
        "typically also use the flash for the month before publication: an information edge for the ECB.",
        "",
        _md(t["staff"]),
        "",
    ]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "m4_forecast.md").write_text("\n".join(lines))


def export(
    S: pl.DataFrame,
    chosen: str,
    flash: pl.DataFrame,
    staff: pl.DataFrame,
    meta: dict,
    live: pl.DataFrame,
    panel: pl.DataFrame,
    out: Path = EXPORT,
) -> None:
    t = summary_tables(S, flash, staff, chosen)
    r3 = lambda x: None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 3)  # noqa: E731
    series = {}
    for (geo, code), g in S.filter((pl.col("model") == chosen) & pl.col("h").is_in([1, 3])).group_by(
        "geo", "code"
    ):
        g = g.sort("target")
        series[f"{geo}|{code}"] = {
            str(h): {
                "target": [d.strftime("%Y-%m") for d in g.filter(pl.col("h") == h)["target"]],
                "pred": [r3(x) for x in g.filter(pl.col("h") == h)["yoy_pred"]],
                "lo80": [r3(x) for x in g.filter(pl.col("h") == h)["lo80"]],
                "hi80": [r3(x) for x in g.filter(pl.col("h") == h)["hi80"]],
                "true": [r3(x) for x in g.filter(pl.col("h") == h)["yoy_true"]],
            }
            for h in (1, 3)
        }
    fl = t["flash_rows"]
    payload = {
        "meta": {
            **meta,
            "chosen_label": MODEL_LABEL[chosen],
            "test_from": TEST_FROM.isoformat()[:7],
            "valid": [VALID[0].isoformat()[:7], VALID[1].isoformat()[:7]],
        },
        "labels": MODEL_LABEL,
        "by_model": [
            {**r, "mae": r3(r["mae"]), "rmse": r3(r["rmse"])} for r in t["by_model"].iter_rows(named=True)
        ],
        "by_regime": [
            {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
            for r in t["by_regime"].iter_rows(named=True)
        ],
        "coverage": [
            {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
            for r in t["coverage"].iter_rows(named=True)
        ],
        "flash": [
            {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
            for r in t["flash"].iter_rows(named=True)
        ],
        "flash_rows": {
            f"{geo}|{code}": {
                "target": [d.strftime("%Y-%m") for d in g.sort("target")["target"]],
                "ours": [r3(x) for x in g.sort("target")["yoy_pred"]],
                "flash": [r3(x) for x in g.sort("target")["flash"]],
                "true": [r3(x) for x in g.sort("target")["yoy_true"]],
            }
            for (geo, code), g in fl.group_by("geo", "code")
        },
        "staff": [
            {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
            for r in t["staff"].iter_rows(named=True)
        ],
        "series": series,
        "live": [
            {
                "geo": r["geo"],
                "code": r["code"],
                "h": r["h"],
                "target": r["target"].strftime("%Y-%m"),
                "pred": r3(r["yoy_pred"]),
                "lo80": r3(r["lo80"]),
                "hi80": r3(r["hi80"]),
                "lo95": r3(r["lo95"]),
                "hi95": r3(r["hi95"]),
            }
            for r in live.sort("geo", "code", "h").iter_rows(named=True)
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "forecast.json").write_text(
        json.dumps(payload, separators=(",", ":"), allow_nan=False, default=str)
    )
