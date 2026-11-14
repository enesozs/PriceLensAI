"""Basket formulas against the hand-worked fixture shared with the browser implementation."""

import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from pricelens.basket import chained, contrib_since_base, fixed_base, normalize, price_updated_shares, yoy

CASE = json.loads((Path(__file__).parent / "fixtures" / "basket_cases.json").read_text())
MONTHS = CASE["months"]


def _at(levels, month):
    return levels[MONTHS.index(month)]


def test_fixed_base_hand_worked():
    lv = fixed_base(CASE["index"], CASE["shares"], MONTHS.index(CASE["base"]))
    for m, v in CASE["expected"]["fixed"].items():
        if not m.startswith("_"):
            assert _at(lv, m) == pytest.approx(v)


def test_chained_hand_worked():
    shares = {2025: CASE["shares"], 2026: CASE["shares"]}
    lv = chained(CASE["index"], MONTHS, shares, MONTHS.index(CASE["base"]))
    for m, v in CASE["expected"]["chained"].items():
        if not m.startswith("_"):
            assert _at(lv, m) == pytest.approx(v)


def test_yoy_hand_worked():
    lf = fixed_base(CASE["index"], CASE["shares"], 0)
    lc = chained(CASE["index"], MONTHS, {2025: CASE["shares"], 2026: CASE["shares"]}, 0)
    assert yoy(lf)[13] == pytest.approx(CASE["expected"]["yoy_2026_01"]["fixed"])
    assert yoy(lc)[13] == pytest.approx(CASE["expected"]["yoy_2026_01"]["chained"])


def test_contributions_sum_to_cumulative_change():
    c = contrib_since_base(CASE["index"], CASE["shares"], 0, 13)
    exp = CASE["expected"]["contrib_since_base_2026_01"]
    for k in "ABC":
        assert c[k] == pytest.approx(exp[k])
    assert sum(c.values()) == pytest.approx(CASE["expected"]["fixed"]["2026-01"] - 100)


def test_normalize_rejects_invalid():
    assert normalize({"a": 300, "b": 100}) == {"a": 0.75, "b": 0.25}
    with pytest.raises(ValueError):
        normalize({"a": -1, "b": 2})
    with pytest.raises(ValueError):
        normalize({"a": 0, "b": 0})


def test_missing_component_gives_missing_level_not_zero():
    idx = {"A": [100, None, 110], "B": [100, 100, 100]}
    lv = fixed_base(idx, {"A": 0.5, "B": 0.5}, 0)
    assert lv[1] is None and lv[2] == pytest.approx(105)


def test_price_updated_shares_hand_worked():
    # Wave 2020: A is 100 in Jan-Nov and 110 in Dec (2020 average 100.83); B is flat at 100.
    # Shares .5/.5 are valued at 2020 average prices; for 2021 they are price-updated to Dec-2020:
    # raw A = .5 * 110/100.83, raw B = .5 * 100/100, then normalized.
    rows = []
    for m in range(1, 13):
        rows += [
            ("X", "A", date(2020, m, 1), 110.0 if m == 12 else 100.0),
            ("X", "B", date(2020, m, 1), 100.0),
        ]
    idx = pl.DataFrame(rows, schema=["geo", "coicop", "date", "value"], orient="row")
    avg_a = idx.filter(pl.col("coicop") == "A")["value"].mean()
    shares = pl.DataFrame(
        {"geo": ["X", "X"], "quintile": ["QU1", "QU1"], "division": ["A", "B"], "share": [0.5, 0.5]}
    )
    w = price_updated_shares(idx, shares, 2020).filter(pl.col("year") == 2021).sort("coicop")
    ra, rb = 0.5 * 110 / avg_a, 0.5 * 100 / 100
    assert w["weight"].to_list() == pytest.approx([ra / (ra + rb), rb / (ra + rb)])
