"""The bottom-up headline must equal the official chain aggregation when component forecasts are perfect."""

import math
from datetime import date

import pytest

import pricelens.forecast as fc
from pricelens.advanced import COMPONENTS, _bottom_up_one


def test_bottom_up_is_exact_with_perfect_component_forecasts():
    geo = "X"
    months = [fc.month_add(date(2023, 12, 1), k) for k in range(31)]  # Dec-2023 .. Jun-2026
    growth = {"NRG": 0.012, "FOOD": 0.004, "IGD_NNRG": 0.001, "SERV": 0.003}
    w = {"NRG": 100.0, "FOOD": 200.0, "IGD_NNRG": 250.0, "SERV": 450.0}  # same weights every year
    L = {}
    for c in COMPONENTS:
        for k, d in enumerate(months):
            L[(geo, c, d)] = 100 * math.exp(growth[c] * k + (0.02 if d.month == 7 else 0.0))
    # official headline built with the December-linked chain
    for d in months:
        if d == months[0]:
            L[(geo, "TOTAL", d)] = 100.0
            continue
        dec = date(d.year - 1, 12, 1)
        s = sum(w.values())
        L[(geo, "TOTAL", d)] = L[(geo, "TOTAL", dec)] * sum(
            w[c] / s * L[(geo, c, d)] / L[(geo, c, dec)] for c in COMPONENTS
        )
    W = {(geo, c, y): w[c] for c in COMPONENTS for y in (2024, 2025, 2026)}
    T = date(2025, 10, 1)  # forecasts cross the year boundary (h = 3..6 land in 2026)
    P = {
        (geo, c, T, h): 100 * math.log(L[(geo, c, fc.month_add(T, h))] / L[(geo, c, T)])
        for c in COMPONENTS
        for h in fc.H
    }
    rows = _bottom_up_one(geo, T, W, L, P)
    assert [r["h"] for r in rows] == fc.H
    for r in rows:
        d = fc.month_add(T, r["h"])
        true = 100 * (L[(geo, "TOTAL", d)] / L[(geo, "TOTAL", fc.month_add(d, -12))] - 1)
        assert r["yoy_bu"] == pytest.approx(true, abs=1e-9)
