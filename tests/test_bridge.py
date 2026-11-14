"""HBS COICOP 1999 -> ECOICOP ver.2 bridge (configs/hbs_to_ecoicop2.csv)."""

import pytest

from pricelens.curate import DIVISIONS, bridge_quintile, load_bridge, parse_split


def _base_vals():
    # 12 HBS divisions summing to 1000 per mille
    vals = {
        "CP01": 150.0,
        "CP02": 30.0,
        "CP03": 50.0,
        "CP04": 300.0,
        "CP05": 60.0,
        "CP06": 40.0,
        "CP07": 120.0,
        "CP08": 30.0,
        "CP09": 90.0,
        "CP10": 10.0,
        "CP11": 60.0,
        "CP12": 60.0,
    }
    vals.update(
        {
            "CP042": 100.0,  # imputed rent inside CP04
            "CP081": 5.0,  # postal -> CP07
            "CP0911": 8.0,  # AV equipment -> CP08
            "CP0912": 2.0,  # photographic stays in CP09
            "CP0913": 10.0,  # IT equipment -> CP08
            "CP0914": 4.0,  # split
            "CP0915": 2.0,  # split
            "CP125": 20.0,  # insurance -> CP12
            "CP126": 5.0,  # financial -> CP12
        }
    )
    return vals


def _br():
    return list(load_bridge().iter_rows(named=True))


SPLITS = {"CP0914": {"CP08": 0.25, "CP09": 0.75}, "CP0915": {"CP08": 0.5, "CP09": 0.5}}


def test_bridge_hand_calculation():
    acc, missing, method = bridge_quintile(_base_vals(), _br(), SPLITS, None)
    assert missing == [] and method == "bridge"
    assert acc["CP04"] == pytest.approx(200.0)  # 300 - 100 imputed rent
    assert acc["CP07"] == pytest.approx(125.0)  # 120 + 5 postal
    # CP08 = 30 - 5 postal + 8 + 10 + 0.25*4 + 0.5*2 = 45
    assert acc["CP08"] == pytest.approx(45.0)
    # CP09 = 90 - 8 - 10 - 1 - 1 = 70
    assert acc["CP09"] == pytest.approx(70.0)
    assert acc["CP12"] == pytest.approx(25.0)  # insurance + financial
    assert acc["CP13"] == pytest.approx(35.0)  # 60 - 25
    assert sum(acc.values()) == pytest.approx(900.0)  # 1000 minus imputed rent
    assert set(acc) == set(DIVISIONS)


def test_missing_imputed_rent_is_reported():
    vals = _base_vals()
    del vals["CP042"]
    _, missing, _ = bridge_quintile(vals, _br(), SPLITS, None)
    assert "CP042" in missing


def test_cp091_fallback_when_children_missing():
    vals = _base_vals()
    for c in ("CP0911", "CP0912", "CP0913", "CP0914", "CP0915"):
        del vals[c]
    vals["CP091"] = 26.0
    acc, missing, method = bridge_quintile(vals, _br(), SPLITS, {"CP08": 0.8, "CP09": 0.2})
    assert method == "bridge+cp091_fallback" and missing == []
    assert acc["CP08"] == pytest.approx(30 - 5 + 0.8 * 26)
    assert acc["CP09"] == pytest.approx(90 - 0.8 * 26)


def test_parse_split():
    assert parse_split("CP08:CP0815|CP09:CP0952,CP0941") == {"CP08": ["CP0815"], "CP09": ["CP0952", "CP0941"]}
