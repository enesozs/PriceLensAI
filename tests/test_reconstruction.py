"""Hand-worked fixtures for the chain-linked aggregation (src/pricelens/reconstruction.py)."""

from datetime import date

import polars as pl
import pytest

from pricelens.reconstruction import chain_links, reconstruct, yoy_gaps


def _idx(rows):
    return pl.DataFrame(rows, schema=["geo", "coicop", "date", "value"], orient="row")


def _w(rows):
    return pl.DataFrame(rows, schema=["geo", "coicop", "year", "weight"], orient="row")


def test_link_hand_calculation():
    # Dec-2024: A=100, B=100. Jan-2025: A=102, B=99. Weights 2025: A=600, B=400 (per 1000).
    # L = 0.6*1.02 + 0.4*0.99 = 0.612 + 0.396 = 1.008
    idx = _idx(
        [
            ("X", "A", date(2024, 12, 1), 100.0),
            ("X", "B", date(2024, 12, 1), 100.0),
            ("X", "A", date(2025, 1, 1), 102.0),
            ("X", "B", date(2025, 1, 1), 99.0),
        ]
    )
    w = _w([("X", "A", 2025, 600.0), ("X", "B", 2025, 400.0)])
    links = chain_links(idx, w, n_components=2)
    assert links.height == 1
    assert links["link"][0] == pytest.approx(1.008)


def test_link_uses_december_of_previous_year_and_same_year_weights():
    # Different Dec bases per component: A Dec=50 -> Jan 55 (+10%), B Dec=200 -> Jan 200 (0%).
    # Weights 2025: 250/750 -> L = 0.25*1.1 + 0.75*1.0 = 1.025. Weights of 2024 must be ignored.
    idx = _idx(
        [
            ("X", "A", date(2024, 12, 1), 50.0),
            ("X", "B", date(2024, 12, 1), 200.0),
            ("X", "A", date(2025, 1, 1), 55.0),
            ("X", "B", date(2025, 1, 1), 200.0),
        ]
    )
    w = _w(
        [("X", "A", 2024, 900.0), ("X", "B", 2024, 100.0), ("X", "A", 2025, 250.0), ("X", "B", 2025, 750.0)]
    )
    assert chain_links(idx, w, 2)["link"][0] == pytest.approx(1.025)


def test_missing_component_month_is_dropped():
    idx = _idx(
        [
            ("X", "A", date(2024, 12, 1), 100.0),
            ("X", "B", date(2024, 12, 1), 100.0),
            ("X", "A", date(2025, 1, 1), 101.0),
        ]
    )
    w = _w([("X", "A", 2025, 500.0), ("X", "B", 2025, 500.0)])
    assert chain_links(idx, w, 2).height == 0


def test_anchored_and_chained_reconstruction_two_years():
    # Two components, constant 50/50 weights; A rises 10% per year (Dec to Dec), B flat.
    # Dec links: 2025 = 0.5*1.1 + 0.5*1.0 = 1.05; 2026 = 0.5*(121/110) + 0.5 = 1.05
    rows = []
    for y, a in [(2024, 100.0), (2025, 110.0), (2026, 121.0)]:
        rows += [("X", "A", date(y, 12, 1), a), ("X", "B", date(y, 12, 1), 100.0)]
    idx = _idx(rows)
    w = _w([("X", c, y, 500.0) for c in "AB" for y in (2025, 2026)])
    published = pl.DataFrame(
        {
            "geo": ["X"] * 3,
            "date": [date(2024, 12, 1), date(2025, 12, 1), date(2026, 12, 1)],
            "value": [100.0, 105.0, 110.25],
        }
    )
    rec = reconstruct(chain_links(idx, w, 2), published)
    assert rec["anchored"].to_list() == pytest.approx([105.0, 110.25])
    assert rec["chained"].to_list() == pytest.approx([105.0, 110.25])
    g = yoy_gaps(rec)
    assert g["yoy_rec"][0] == pytest.approx(5.0)
    assert g["gap_pp"][0] == pytest.approx(0.0)
