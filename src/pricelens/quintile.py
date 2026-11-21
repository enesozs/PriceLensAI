"""Income-quintile inflation: HICP division indices weighted with HBS expenditure structures.

For each usable geo and HBS wave, quintile shares (ECOICOP ver.2 divisions, imputed rent removed) are
price-updated to every December and chained exactly like the HICP (see src/pricelens/reconstruction.py). Output type is
`hbs_quintile_basket`: a group-average basket, not an official statistic and not any real household.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl

from pricelens.basket import price_updated_shares
from pricelens.config import CURATED, EXPORT
from pricelens.contrib import contributions
from pricelens.curate import DIVISIONS
from pricelens.reconstruction import chain_links

QUINTILES = ["QU1", "QU2", "QU3", "QU4", "QU5"]
WAVES = [2015, 2020]
HBS_SUM_TOL = 6.0
START = date(2001, 1, 1)
CONTRIB_MONTHS = 36


def usable_waves(hbs: pl.DataFrame) -> pl.DataFrame:
    """geo, wave pairs whose bridge is complete and whose HBS division total is 1000 ± rounding."""
    return (
        hbs.group_by("geo", "wave")
        .agg(
            missing=pl.col("missing_codes").str.join(""),
            dev=(pl.col("hbs_total_per_1000") - 1000).abs().max(),
            minshare=pl.col("share").min(),
        )
        .filter((pl.col("missing") == "") & (pl.col("dev") <= HBS_SUM_TOL) & (pl.col("minshare") >= 0))
        .select("geo", "wave")
    )


def chain_levels(links: pl.DataFrame) -> pl.DataFrame:
    """links (key, date, link) -> key, date, level anchored at 100 in the December before the first link."""
    df = links.with_columns(year=pl.col("date").dt.year()).sort("key", "date")
    dec = (
        df.filter(pl.col("date").dt.month() == 12)
        .select("key", "year", pl.col("link").alias("dec_link"))
        .sort("key", "year")
        .with_columns(dec_level=100 * pl.col("dec_link").cum_prod().over("key"))
        .select("key", (pl.col("year") + 1).alias("year"), pl.col("dec_level").alias("prev_dec"))
    )
    first = df.group_by("key").agg(first_year=pl.col("year").min())
    df = df.join(dec, on=["key", "year"], how="left").join(first, on="key")
    df = df.with_columns(
        prev_dec=pl.when(pl.col("year") == pl.col("first_year")).then(100.0).otherwise(pl.col("prev_dec"))
    ).with_columns(level=pl.col("prev_dec") * pl.col("link"))
    return df.select("key", "date", "level").drop_nulls()


def quintile_indices() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    index = pl.read_parquet(CURATED / "hicp_index.parquet")
    hbs = pl.read_parquet(CURATED / "hbs_quintile.parquet")
    ok = usable_waves(hbs)
    div = index.filter(
        (pl.col("unit") == "I25") & pl.col("coicop").is_in(DIVISIONS) & pl.col("value").is_not_null()
    ).select("geo", "coicop", "date", "value")
    levels, contribs = [], []
    for wave in WAVES:
        geos = ok.filter(pl.col("wave") == wave)["geo"].to_list()
        sh = hbs.filter((pl.col("wave") == wave) & pl.col("geo").is_in(geos)).select(
            "geo", "quintile", "division", "share"
        )
        w = price_updated_shares(div.filter(pl.col("geo").is_in(geos)), sh, wave)
        w = w.with_columns(key=pl.concat_str("geo", pl.lit("|"), "quintile")).filter(
            pl.col("year") >= START.year
        )
        d = (
            div.filter(pl.col("geo").is_in(geos))
            .join(pl.DataFrame({"quintile": QUINTILES}), how="cross")
            .with_columns(key=pl.concat_str("geo", pl.lit("|"), "quintile"))
        )
        links = chain_links(
            d.select(pl.col("key").alias("geo"), "coicop", "date", "value"),
            w.select(pl.col("key").alias("geo"), "coicop", "year", "weight"),
            n_components=len(DIVISIONS),
        ).rename({"geo": "key"})
        lv = chain_levels(links).with_columns(wave=pl.lit(wave))
        levels.append(lv)
        last = lv["date"].max()
        recent = d.filter(pl.col("date") >= pl.lit(last).dt.offset_by(f"-{CONTRIB_MONTHS + 24}mo"))
        c = contributions(
            recent.select(pl.col("key").alias("geo"), "coicop", "date", "value"),
            w.select(pl.col("key").alias("geo"), "coicop", "year", "weight"),
            lv.select(pl.col("key").alias("geo"), "date", pl.col("level").alias("value")),
        ).with_columns(wave=pl.lit(wave))
        contribs.append(c.rename({"geo": "key"}))
    lv = pl.concat(levels).with_columns(
        geo=pl.col("key").str.split("|").list.first(), quintile=pl.col("key").str.split("|").list.last()
    )
    lag = lv.select(
        "key", "wave", pl.col("date").dt.offset_by("12mo").alias("date"), pl.col("level").alias("l12")
    )
    lv = lv.join(lag, on=["key", "wave", "date"], how="left").with_columns(
        yoy=100 * (pl.col("level") / pl.col("l12") - 1)
    )
    ct = pl.concat(contribs).with_columns(
        geo=pl.col("key").str.split("|").list.first(), quintile=pl.col("key").str.split("|").list.last()
    )
    return lv, ct, ok


def export_quintiles(out: Path = EXPORT) -> dict[str, int]:
    lv, ct, ok = quintile_indices()
    hbs = pl.read_parquet(CURATED / "hbs_quintile.parquet")
    sizes: dict[str, int] = {}
    summary = []
    last = lv["date"].max()
    months = pl.date_range(START, last, "1mo", eager=True).to_list()
    for geo in sorted(ok["geo"].unique().to_list()):
        g = lv.filter(pl.col("geo") == geo)
        waves = sorted(ok.filter(pl.col("geo") == geo)["wave"].to_list())
        yoy: dict[str, dict[str, list]] = {}
        contrib: dict[str, dict[str, dict[str, list]]] = {}
        shares: dict[str, dict[str, dict[str, float]]] = {}
        imputed: dict[str, dict[str, float | None]] = {}
        c_months = sorted(ct.filter(pl.col("geo") == geo)["date"].unique().to_list())[-CONTRIB_MONTHS:]
        for wave in waves:
            gw = g.filter(pl.col("wave") == wave)
            yoy[str(wave)] = {}
            for q in QUINTILES:
                m = dict(gw.filter(pl.col("quintile") == q).select("date", "yoy").iter_rows())
                yoy[str(wave)][q] = [None if m.get(d) is None else round(m[d], 3) for d in months]
            cw = ct.filter((pl.col("geo") == geo) & (pl.col("wave") == wave) & pl.col("date").is_in(c_months))
            contrib[str(wave)] = {
                q: {
                    dv: [
                        None if v is None else round(v, 3)
                        for v in (
                            dict(
                                cw.filter((pl.col("quintile") == q) & (pl.col("coicop") == dv))
                                .select("date", "contribution_pp")
                                .iter_rows()
                            ).get(d)
                            for d in c_months
                        )
                    ]
                    for dv in DIVISIONS
                }
                for q in QUINTILES
            }
            hw = hbs.filter((pl.col("geo") == geo) & (pl.col("wave") == wave))
            shares[str(wave)] = {
                q: {
                    r["division"]: round(r["share"], 5)
                    for r in hw.filter(pl.col("quintile") == q).iter_rows(named=True)
                }
                for q in QUINTILES
            }
            imputed[str(wave)] = {
                q: hw.filter(pl.col("quintile") == q)["imputed_rent_per_1000"].first() for q in QUINTILES
            }
            y1 = yoy[str(wave)]["QU1"][-1]
            y5 = yoy[str(wave)]["QU5"][-1]
            k = len(months) - 1
            while (y1 is None or y5 is None) and k > 0:  # latest month with all divisions
                k -= 1
                y1, y5 = yoy[str(wave)]["QU1"][k], yoy[str(wave)]["QU5"][k]
            summary.append(
                {
                    "geo": geo,
                    "wave": wave,
                    "month": months[k].strftime("%Y-%m"),
                    "q1": y1,
                    "q5": y5,
                    "gap": None if y1 is None or y5 is None else round(y1 - y5, 3),
                }
            )
        payload = {
            "geo": geo,
            "waves": waves,
            "months": [d.strftime("%Y-%m") for d in months],
            "yoy": yoy,
            "contrib": {"months": [d.strftime("%Y-%m") for d in c_months], "values": contrib},
            "shares": shares,
            "imputed_rent_per_1000": imputed,
        }
        p = out / "quintiles" / f"{geo}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, separators=(",", ":"), allow_nan=False)
        p.write_text(text)
        sizes[f"quintiles/{geo}.json"] = len(text)
    text = json.dumps({"latest": summary}, separators=(",", ":"), allow_nan=False)
    (out / "quintiles" / "summary.json").write_text(text)
    sizes["quintiles/summary.json"] = len(text)
    return sizes
