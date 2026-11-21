"""Forecast lab: targets, baselines and the no-lookahead guarantees."""

import math
from datetime import date, timedelta

import polars as pl
import pytest

import pricelens.forecast as fc
import pricelens.sources.extra as extra


def _panel(n_years=6):
    rows = []
    d = date(2010, 1, 1)
    for k in range(12 * n_years):
        # level with a seasonal bump every March and a steady trend
        lvl = 100 * math.log(100) + 0.2 * k + (1.0 if d.month == 3 else 0.0)
        rows.append(("EA", "TOTAL", d, lvl))
        d = fc.month_add(d, 1)
    return pl.DataFrame(rows, schema=["geo", "code", "date", "logi"], orient="row")


def _no_exog(panel):
    return (
        panel.select("geo", "date")
        .unique()
        .with_columns([pl.lit(None, dtype=pl.Float64).alias(c) for c in fc.EXOG])
    )


def test_targets_and_seasonal_baselines_hand_worked():
    p = _panel()
    ds = fc.build_dataset(p, _no_exog(p))
    row = ds.filter(pl.col("origin") == date(2014, 2, 1)).row(0, named=True)
    # y1 = log change Feb -> Mar 2014 = trend 0.2 + March bump 1.0
    assert row["y1"] == pytest.approx(1.2)
    # seasonal naive / mean over the same window in 2013, 2012, 2011 are identical here
    assert row["sn1"] == pytest.approx(1.2)
    assert row["sm1"] == pytest.approx(1.2)
    # base for the annual rate of Mar-2014 is Mar-2013
    assert row["base1"] == pytest.approx(p.filter(pl.col("date") == date(2013, 3, 1))["logi"][0])


def test_score_converts_to_annual_rate():
    p = _panel()
    ds = fc.build_dataset(p, _no_exog(p))
    preds = ds.filter(pl.col("origin") == date(2014, 2, 1)).select(
        "geo",
        "code",
        "origin",
        pl.lit(1).alias("h"),
        pl.col("y1").alias("pred"),
        pl.lit("perfect").alias("model"),
    )
    s = fc.score(preds, ds)
    expected = 100 * (math.exp(12 * 0.2 / 100) - 1)  # 12 months of 0.2 log-points trend
    assert s["yoy_true"][0] == pytest.approx(expected)
    assert s["err"][0] == pytest.approx(0.0)


def test_rolling_never_trains_on_unrealised_targets(monkeypatch):
    p = _panel()
    ds = fc.build_dataset(p, _no_exog(p))
    seen = []

    def fake_fit(kind, train, h, params):
        seen.append((h, train["origin"].max()))
        return fc.Fitted(kind, None)

    monkeypatch.setattr(fc, "fit", fake_fit)
    monkeypatch.setattr(fc, "predict", lambda f, df, h: df[f"sm{h}"].to_numpy())
    origins = [date(2014, 6, 1), date(2015, 1, 1)]
    fc.rolling("ridge", ds, origins, {})
    for (h, last_train), T in zip(seen, [origins[0]] * len(fc.H) + [origins[1]] * len(fc.H), strict=True):
        assert last_train <= fc.month_add(T, -h)


def test_exog_features_ignore_data_after_the_cutoff(monkeypatch):
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(400)]

    def brent_frame(spike: bool):
        return pl.DataFrame(
            {
                "date": days,
                "usd": [
                    500.0 if spike and d > date(2019, 6, fc.CUTOFF_DAY) else 60.0 + (d.month % 3)
                    for d in days
                ],
            }
        )

    fx = pl.DataFrame({"date": days, "usd_per_eur": [1.1] * len(days)})
    mondays = [d for d in days if d.weekday() == 0]
    oil = pl.DataFrame(
        {
            "geo": ["EA"] * len(mondays),
            "product": ["petrol"] * len(mondays),
            "date": mondays,
            "price": [1500.0 + d.month for d in mondays],
        }
    )
    monkeypatch.setattr(extra, "eurusd", lambda: fx)
    monkeypatch.setattr(extra, "oil_bulletin", lambda: oil)
    monkeypatch.setattr(extra, "brent", lambda: brent_frame(False))
    a = fc.exog_features().filter((pl.col("geo") == "EA") & (pl.col("date") == date(2019, 5, 1)))
    monkeypatch.setattr(extra, "brent", lambda: brent_frame(True))
    b = fc.exog_features().filter((pl.col("geo") == "EA") & (pl.col("date") == date(2019, 5, 1)))
    # a spike after 15 June must not reach the forecast for origin May, issued on 15 June ...
    for c in ("f_brent_1", "f_brent_0", "f_brent_12", "f_fx_1"):
        assert a[c][0] == pytest.approx(b[c][0])
    # ... but it must reach the forecast for origin June (issued 15 July), proving the test can fail
    a6 = fc.exog_features().filter((pl.col("geo") == "EA") & (pl.col("date") == date(2019, 6, 1)))
    monkeypatch.setattr(extra, "brent", lambda: brent_frame(False))
    b6 = fc.exog_features().filter((pl.col("geo") == "EA") & (pl.col("date") == date(2019, 6, 1)))
    assert a6["f_brent_1"][0] != pytest.approx(b6["f_brent_1"][0])


def test_pivot_columns_have_a_fixed_order_whatever_the_row_order():
    rows = pl.DataFrame(
        {
            "code": ["CP00"] * 3,
            "h": [1] * 3,
            "model": ["no_change", "ridge", "seasonal_mean"],
            "mae": [0.3, 0.1, 0.2],
        }
    )
    a = rows.pivot(on="model", index=["code", "h"], values="mae")
    b = rows.reverse().pivot(on="model", index=["code", "h"], values="mae")
    assert a.columns != b.columns  # pivot follows row order, which group_by does not fix
    order = ["code", "h", "ridge", "seasonal_mean", "no_change"]
    assert a.select(fc._ordered(a, order)).columns == order
    assert b.select(fc._ordered(b, order)).columns == order
    # preferred names that are missing are skipped; unexpected columns go last, sorted
    c = a.with_columns(pl.lit(0.0).alias("extra"))
    assert fc._ordered(c, ["code", "h", "ridge", "ridge", "missing"]) == [
        "code",
        "h",
        "ridge",
        "extra",
        "no_change",
        "seasonal_mean",
    ]
