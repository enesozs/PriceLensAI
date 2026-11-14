"""M8: derived December weights must recover the true weights of a December-linked index."""

import math
from datetime import date

import polars as pl
import pytest

import pricelens.forecast as fc
from pricelens.us import PARTS, derive_weights


def test_derive_weights_recovers_true_weights():
    true = {2025: [0.07, 0.14, 0.20, 0.59], 2026: [0.06, 0.13, 0.21, 0.60]}
    months = [fc.month_add(date(2024, 12, 1), k) for k in range(25)]
    paths = {
        "SA0E": lambda k: 100 * math.exp(0.03 * math.sin(k / 2.0) + 0.002 * k),
        "SAF1": lambda k: 100 * math.exp(0.0025 * k),
        "SACL1E": lambda k: 100 * math.exp(-0.001 * k + 0.004 * (k % 3)),
        "SASLE": lambda k: 100 * math.exp(0.0035 * k),
    }
    rows = [(c, d, f(k)) for c, f in paths.items() for k, d in enumerate(months)]
    lv = {(c, d): x for c, d, x in rows}
    tot = {months[0]: 100.0}
    for d in months[1:]:
        dec = date(d.year - 1, 12, 1)
        tot[d] = tot[dec] * sum(
            w * lv[(c, d)] / lv[(c, dec)] for c, w in zip(PARTS, true[d.year], strict=True)
        )
    rows += [("SA0", d, x) for d, x in tot.items()]
    cpi = pl.DataFrame(rows, schema=["code", "date", "value"], orient="row")
    w = derive_weights(cpi)
    for y, ws in true.items():
        got = w.filter(pl.col("year") == y).sort(
            pl.col("code").replace({c: str(i) for i, c in enumerate(PARTS)})
        )
        assert got["weight"].to_list() == pytest.approx(ws, abs=0.01)
