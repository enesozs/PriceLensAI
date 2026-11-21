"""Basket indices: Python reference implementation (the browser implementation in app/src/lib/basket.ts
is tested against the same fixtures) and income-quintile baskets from HBS structures.

Fixed-base (Laspeyres-type):
    I_t = 100 * sum_i w_i * I_{i,t} / I_{i,b}
Chained annual (as in src/pricelens/reconstruction.py), shares w_{i,y} applied to December-linked links:
    L_t = sum_i w_{i,y} * I_{i,t} / I_{i,Dec(y-1)},  I_t = I_{Dec(y-1)} * L_t
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import polars as pl

Series = Mapping[str, Sequence[float | None]]


def normalize(amounts: Mapping[str, float]) -> dict[str, float]:
    """Amounts or shares -> shares summing to 1. Rejects negative values and an all-zero basket."""
    if any(v < 0 or math.isnan(v) for v in amounts.values()):
        raise ValueError("weights must be non-negative numbers")
    s = sum(amounts.values())
    if s <= 0:
        raise ValueError("the basket is empty")
    return {k: v / s for k, v in amounts.items()}


def fixed_base(index: Series, shares: Mapping[str, float], base: int) -> list[float | None]:
    n = len(next(iter(index.values())))
    out: list[float | None] = []
    for t in range(n):
        acc = 0.0
        for c, w in shares.items():
            if w == 0:
                continue
            it, ib = index[c][t], index[c][base]
            if it is None or ib is None:
                acc = math.nan
                break
            acc += w * it / ib
        out.append(None if math.isnan(acc) else 100 * acc)
    return out


def chained(
    index: Series, months: Sequence[str], shares_by_year: Mapping[int, Mapping[str, float]], base: int
) -> list[float | None]:
    """December-linked chain with (possibly year-specific) shares; anchored at 100 in the base month.

    The base month must be a December (the chain's natural anchor) or the result is rebased to it.
    """
    n = len(months)
    level: list[float | None] = [None] * n
    dec_level: dict[int, float] = {}
    first_dec = next((t for t in range(n) if months[t].endswith("-12")), None)
    if first_dec is None:
        return level
    dec_level[int(months[first_dec][:4])] = 100.0
    level[first_dec] = 100.0
    for t in range(first_dec + 1, n):
        y = int(months[t][:4])
        prev_dec_year = y - 1
        if prev_dec_year not in dec_level:
            continue
        dec_idx = months.index(f"{prev_dec_year}-12")
        sh = shares_by_year.get(y)
        if sh is None:
            continue
        acc = 0.0
        ok = True
        for c, w in sh.items():
            if w == 0:
                continue
            it, idec = index[c][t], index[c][dec_idx]
            if it is None or idec is None:
                ok = False
                break
            acc += w * it / idec
        if not ok:
            continue
        level[t] = dec_level[prev_dec_year] * acc
        if months[t].endswith("-12"):
            dec_level[y] = level[t]
    b = level[base]
    if b is None:
        return [None] * n
    return [None if v is None else 100 * v / b for v in level]


def yoy(levels: Sequence[float | None]) -> list[float | None]:
    return [
        None
        if t < 12 or levels[t] is None or levels[t - 12] is None
        else 100 * (levels[t] / levels[t - 12] - 1)  # type: ignore[operator]
        for t in range(len(levels))
    ]


def contrib_since_base(index: Series, shares: Mapping[str, float], base: int, t: int) -> dict[str, float]:
    """Fixed-base contributions to cumulative change since the base month, in index points (= % since base)."""
    return {c: 100 * w * (index[c][t] / index[c][base] - 1) for c, w in shares.items() if w}  # type: ignore[operator]


# ------------------------------------------------------------------------------------------------ quintiles


def price_updated_shares(div_index: pl.DataFrame, shares: pl.DataFrame, wave: int) -> pl.DataFrame:
    """HBS shares (valued at average prices of the wave year) -> weights for each chain year y, price-updated to
    December of y-1:  w_{i,y} ∝ s_i * I_{i,Dec(y-1)} / mean_{m in wave}(I_{i,m}), normalized to sum 1.

    div_index: geo, coicop, date, value. shares: geo, quintile, division, share (one wave).
    Returns geo, quintile, coicop, year, weight (sums to 1 per geo-quintile-year).
    """
    idx = div_index.with_columns(year=pl.col("date").dt.year())
    avg = (
        idx.filter(pl.col("year") == wave)
        .group_by("geo", "coicop")
        .agg(avg=pl.col("value").mean(), n=pl.len())
        .filter(pl.col("n") == 12)
        .drop("n")
    )
    dec = idx.filter(pl.col("date").dt.month() == 12).select(
        "geo", "coicop", (pl.col("year") + 1).cast(pl.Int32).alias("year"), pl.col("value").alias("dec")
    )
    w = (
        shares.rename({"division": "coicop"})
        .join(avg, on=["geo", "coicop"])
        .join(dec, on=["geo", "coicop"])
        .with_columns(raw=pl.col("share") * pl.col("dec") / pl.col("avg"))
        .with_columns(weight=pl.col("raw") / pl.col("raw").sum().over("geo", "quintile", "year"))
        .select("geo", "quintile", "coicop", "year", "weight")
    )
    return w
