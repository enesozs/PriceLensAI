"""Official-HICP reconstruction (quality gate).

The HICP is an annually chain-linked Laspeyres-type index. For month t in year y, with weights w_{i,y}
price-updated to December of y-1 (as published in PRC_HICP_IW):

    L_t      = sum_i w_{i,y} * I_{i,t} / I_{i,Dec(y-1)}   /  sum_i w_{i,y}
    I_t      = I_{Dec(y-1)} * L_t

Two variants are produced:
* anchored: I_{Dec(y-1)} is the *published* all-items December value. Each year is reconstructed
  independently, so errors do not accumulate; this isolates the aggregation error of one year.
* chained:  I_{Dec(y-1)} is the *reconstructed* December value, anchored once at the first December.
  This shows long-run drift from rounding of the published sub-indices and weights.
"""

from __future__ import annotations

import polars as pl


def chain_links(div_index: pl.DataFrame, weights: pl.DataFrame, n_components: int) -> pl.DataFrame:
    """Monthly links L_t per geo from component indices and annual weights.

    div_index: geo, coicop, date, value   (component index levels, any common reference period)
    weights:   geo, coicop, year, weight  (weights for year y, price-updated to Dec y-1)
    Returns geo, date, link, n (components used). Only months with all `n_components` present are kept.
    """
    idx = div_index.select("geo", "coicop", "date", "value").with_columns(
        year=pl.col("date").dt.year(),
        link_date=pl.date(pl.col("date").dt.year() - 1, 12, 1),
    )
    dec = idx.select("geo", "coicop", pl.col("date").alias("link_date"), pl.col("value").alias("dec_value"))
    w = weights.select("geo", "coicop", pl.col("year").cast(pl.Int32), "weight")
    j = (
        idx.with_columns(pl.col("year").cast(pl.Int32))
        .join(dec, on=["geo", "coicop", "link_date"], how="inner")
        .join(w, on=["geo", "coicop", "year"], how="inner")
        .filter(pl.col("value").is_not_null() & pl.col("dec_value").is_not_null() & (pl.col("weight") > 0))
    )
    links = (
        j.group_by("geo", "date")
        .agg(
            link=(pl.col("weight") * pl.col("value") / pl.col("dec_value")).sum() / pl.col("weight").sum(),
            n=pl.len(),
        )
        .filter(pl.col("n") == n_components)
        .sort("geo", "date")
    )
    return links


def price_update_weights(div_index: pl.DataFrame, weights: pl.DataFrame) -> pl.DataFrame:
    """Diagnostic variant: treat weights as valued at average prices of y-1 and price-update them to Dec(y-1).

    w*_{i,y} = w_{i,y} * I_{i,Dec(y-1)} / mean_{m in y-1}(I_{i,m})
    Used to test whether a country's published weights are *not* already price-updated.
    """
    idx = div_index.with_columns(year=pl.col("date").dt.year())
    avg = (
        idx.group_by("geo", "coicop", "year")
        .agg(avg=pl.col("value").mean(), n=pl.len())
        .filter(pl.col("n") == 12)
    )
    dec = idx.filter(pl.col("date").dt.month() == 12).select(
        "geo", "coicop", "year", pl.col("value").alias("dec")
    )
    f = avg.join(dec, on=["geo", "coicop", "year"]).select(
        "geo",
        "coicop",
        (pl.col("year") + 1).cast(pl.Int32).alias("year"),
        (pl.col("dec") / pl.col("avg")).alias("pu"),
    )
    return (
        weights.with_columns(pl.col("year").cast(pl.Int32))
        .join(f, on=["geo", "coicop", "year"], how="inner")
        .with_columns(weight=pl.col("weight") * pl.col("pu"))
        .drop("pu")
    )


def reconstruct(links: pl.DataFrame, published: pl.DataFrame) -> pl.DataFrame:
    """Anchored and chained reconstruction of the aggregate index.

    published: geo, date, value (published aggregate index, same reference period as components)
    Returns geo, date, published, anchored, chained.
    """
    pub = published.select("geo", "date", pl.col("value").alias("published"))
    df = links.with_columns(link_date=pl.date(pl.col("date").dt.year() - 1, 12, 1)).join(
        pub.rename({"date": "link_date", "published": "pub_dec"}), on=["geo", "link_date"], how="left"
    )
    df = df.join(pub, on=["geo", "date"], how="left").with_columns(
        anchored=pl.col("pub_dec") * pl.col("link")
    )

    # chained: cumulative product of December links within contiguous runs, anchored at the first December
    dec_links = (
        df.filter(pl.col("date").dt.month() == 12)
        .select("geo", pl.col("date").dt.year().alias("year"), pl.col("link").alias("dec_link"))
        .sort("geo", "year")
    )
    first_anchor = (
        df.group_by("geo")
        .agg(first_link_date=pl.col("link_date").min())
        .join(
            pub.rename({"date": "first_link_date", "published": "anchor"}),
            on=["geo", "first_link_date"],
            how="left",
        )
    )
    dec_chain = (
        dec_links.join(first_anchor, on="geo", how="left")
        .with_columns(level=pl.col("anchor") * pl.col("dec_link").cum_prod().over("geo"))
        .select("geo", (pl.col("year") + 1).alias("year"), pl.col("level").alias("chain_dec_prev"))
    )
    df = (
        df.with_columns(year=pl.col("date").dt.year())
        .join(dec_chain, on=["geo", "year"], how="left")
        .join(first_anchor.select("geo", "first_link_date", "anchor"), on="geo", how="left")
        .with_columns(
            chain_dec_prev=pl.when(pl.col("link_date") == pl.col("first_link_date"))
            .then(pl.col("anchor"))
            .otherwise(pl.col("chain_dec_prev"))
        )
        .with_columns(chained=pl.col("chain_dec_prev") * pl.col("link"))
    )
    return df.select("geo", "date", "published", "anchored", "chained", "link").sort("geo", "date")


def yoy_gaps(rec: pl.DataFrame, published_rate: pl.DataFrame | None = None) -> pl.DataFrame:
    """Annual rates of the anchored reconstruction vs the published index (and published RCH_A if given)."""
    lag = rec.select(
        "geo",
        pl.col("date").dt.offset_by("12mo").alias("date"),
        pl.col("anchored").alias("anchored_l12"),
        pl.col("published").alias("published_l12"),
    )
    df = rec.join(lag, on=["geo", "date"], how="inner").with_columns(
        yoy_rec=(pl.col("anchored") / pl.col("anchored_l12") - 1) * 100,
        yoy_pub=(pl.col("published") / pl.col("published_l12") - 1) * 100,
    )
    if published_rate is not None:
        df = df.join(
            published_rate.select("geo", "date", pl.col("value").alias("rch_a")),
            on=["geo", "date"],
            how="left",
        )
    return df.with_columns(
        gap_pp=(pl.col("yoy_rec") - pl.col("yoy_pub")),
        level_gap_pct=(pl.col("anchored") / pl.col("published") - 1) * 100,
        chain_drift_pct=(pl.col("chained") / pl.col("published") - 1) * 100,
    )
