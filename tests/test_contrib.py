"""Contributions must add up exactly to the annual rate of a chain index built from the same inputs."""

from datetime import date

import polars as pl
import pytest

from pricelens.contrib import contributions


def _months(y0: int, y1: int):
    return [date(y, m, 1) for y in range(y0, y1 + 1) for m in range(1, 13)]


def test_contributions_sum_to_annual_rate_with_changing_weights():
    months = _months(2023, 2025)
    # component paths: A grows 1%/month, B falls 0.2%/month
    a = {d: 100 * 1.01**k for k, d in enumerate(months)}
    b = {d: 100 * 0.998**k for k, d in enumerate(months)}
    weights = {2023: (0.5, 0.5), 2024: (0.7, 0.3), 2025: (0.4, 0.6)}
    # build the official chain index exactly as the HICP does
    tot: dict[date, float] = {}
    for d in months:
        if d.year == 2023:
            tot[d] = 100.0  # first year: only needed as an anchor level for Dec-2023
            continue
        dec = date(d.year - 1, 12, 1)
        wa, wb = weights[d.year]
        tot[d] = tot[dec] * (wa * a[d] / a[dec] + wb * b[d] / b[dec])
    comp = pl.DataFrame(
        [("X", "A", d, a[d]) for d in months] + [("X", "B", d, b[d]) for d in months],
        schema=["geo", "coicop", "date", "value"],
        orient="row",
    )
    w = pl.DataFrame(
        [("X", "A", y, 1000 * wa) for y, (wa, _) in weights.items()]
        + [("X", "B", y, 1000 * wb) for y, (_, wb) in weights.items()],
        schema=["geo", "coicop", "year", "weight"],
        orient="row",
    )
    total = pl.DataFrame({"geo": ["X"] * len(tot), "date": list(tot), "value": list(tot.values())})
    c = contributions(comp, w, total)
    # 2025 months have both terms (2025 basket since Dec-2024, 2024 basket Dec-2023..Dec-2024)
    for d in [date(2025, 3, 1), date(2025, 12, 1)]:
        s = c.filter(pl.col("date") == d)["contribution_pp"].sum()
        yoy = (tot[d] / tot[date(d.year - 1, d.month, 1)] - 1) * 100
        assert s == pytest.approx(yoy, abs=1e-10)
    # December: only the current-basket term is non-zero, and component A dominates
    dec = c.filter(pl.col("date") == date(2025, 12, 1)).sort("coicop")["contribution_pp"].to_list()
    assert dec[0] > 0 > dec[1]
