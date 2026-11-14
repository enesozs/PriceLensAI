"""Contributions of components to the annual rate of a December-linked chain index.

For month t in year y, with normalized weights w_{i,y} (sum 1) price-updated to Dec(y-1):

    I_t / I_{t-12} - 1 =  sum_i C_{i,t}
    C_{i,t} = 100 / I_{t-12} * [ I_{Dec(y-1)} * w_{i,y}   * (I_{i,t} / I_{i,Dec(y-1)} - 1)
                               + I_{Dec(y-2)} * w_{i,y-1} * (I_{i,Dec(y-1)} - I_{i,t-12}) / I_{i,Dec(y-2)} ]

The first term is the component's contribution since last December (this year's basket), the second the
contribution from t-12 to last December (last year's basket). The decomposition is exact for the
reconstructed index; against the *published* aggregate it leaves a small residual (rounding and, for a few
countries, compilation differences), which is reported, never hidden.
"""

from __future__ import annotations

import polars as pl


def contributions(comp: pl.DataFrame, weights: pl.DataFrame, total: pl.DataFrame) -> pl.DataFrame:
    """comp: geo, coicop, date, value; weights: geo, coicop, year, weight; total: geo, date, value.

    Returns geo, coicop, date, contribution_pp. Months lacking any input are dropped.
    """
    n_comp = comp["coicop"].n_unique()
    w = (
        weights.select("geo", "coicop", pl.col("year").cast(pl.Int32), "weight")
        .filter(pl.col("weight").is_not_null())
        .with_columns(n=pl.len().over("geo", "year"), s=pl.col("weight").sum().over("geo", "year"))
        .filter(pl.col("n") == n_comp)
        .with_columns(w=pl.col("weight") / pl.col("s"))
        .select("geo", "coicop", "year", "w")
    )
    c = comp.select("geo", "coicop", "date", pl.col("value").alias("i"))
    tot = total.select("geo", "date", pl.col("value").alias("tot"))
    df = c.with_columns(
        year=pl.col("date").dt.year().cast(pl.Int32),
        dec1=pl.date(pl.col("date").dt.year() - 1, 12, 1),
        dec2=pl.date(pl.col("date").dt.year() - 2, 12, 1),
        lag=pl.col("date").dt.offset_by("-12mo"),
    )

    def at(col: str, frame: pl.DataFrame, name: str, keys: list[str]) -> pl.DataFrame:
        return frame.rename({"date": col, frame.columns[-1]: name}).select(*keys, col, name)

    df = (
        df.join(at("dec1", c, "i_dec1", ["geo", "coicop"]), on=["geo", "coicop", "dec1"])
        .join(at("dec2", c, "i_dec2", ["geo", "coicop"]), on=["geo", "coicop", "dec2"])
        .join(at("lag", c, "i_lag", ["geo", "coicop"]), on=["geo", "coicop", "lag"])
        .join(at("dec1", tot, "t_dec1", ["geo"]), on=["geo", "dec1"])
        .join(at("dec2", tot, "t_dec2", ["geo"]), on=["geo", "dec2"])
        .join(at("lag", tot, "t_lag", ["geo"]), on=["geo", "lag"])
        .join(w, on=["geo", "coicop", "year"])
        .join(w.with_columns(pl.col("year") + 1).rename({"w": "w_prev"}), on=["geo", "coicop", "year"])
    )
    df = df.with_columns(
        contribution_pp=100
        / pl.col("t_lag")
        * (
            pl.col("t_dec1") * pl.col("w") * (pl.col("i") / pl.col("i_dec1") - 1)
            + pl.col("t_dec2") * pl.col("w_prev") * (pl.col("i_dec1") - pl.col("i_lag")) / pl.col("i_dec2")
        )
    )
    complete = df.group_by("geo", "date").agg(n=pl.len()).filter(pl.col("n") == n_comp).select("geo", "date")
    return (
        df.join(complete, on=["geo", "date"])
        .select("geo", "coicop", "date", "contribution_pp")
        .sort("geo", "date", "coicop")
    )
