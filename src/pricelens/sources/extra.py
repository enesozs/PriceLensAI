"""Forecast-lab sources and their licences:

* EU Weekly Oil Bulletin (European Commission): weekly consumer fuel prices by country.  CC BY 4.0.
* EIA Europe Brent spot price (RBRTE, daily, USD/bbl).                                   US public domain.
* ECB Data Portal: EUR/USD reference rate (EXR) and Eurosystem/ECB staff projections (MPD).
  Reused unmodified with "Source: ECB statistics".
"""

from __future__ import annotations

import io

import fastexcel
import polars as pl

from pricelens.sources.snapshot import Snapshot, fetch, latest

OIL_URL = (
    "https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
    "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"
)
BRENT_URL = "https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls"
EXR_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&detail=dataonly"
# ECB/Eurosystem staff projections, euro area, quarterly annual growth: headline + the four ECB aggregates
MPD_URL = "https://data-api.ecb.europa.eu/service/data/MPD/Q.U2.HIC+HEG+HIF+HNE+HSE.A..?format=csvdata&detail=dataonly"
MPD_ITEM = {"HIC": "TOTAL", "HEG": "NRG", "HIF": "FOOD", "HNE": "IGD_NNRG", "HSE": "SERV"}
EXERCISE_MONTH = {"W": 3, "G": 6, "S": 9, "A": 12}

# Oil Bulletin country prefix for each forecast geo (EU weighted average stands in for the euro area)
OIL_GEO = {"EA": "EU", "DE": "DE", "FR": "FR", "IT": "IT", "ES": "ES"}
OIL_PRODUCTS = {"euro95": "petrol", "diesel": "diesel", "heating_oil": "heating_oil"}


def fetch_all() -> list[Snapshot]:
    return [
        fetch("oil_bulletin", "prices_history.xlsx", OIL_URL, "ec-reuse-cc-by-4.0"),
        fetch("eia", "RBRTEd.xls", BRENT_URL, "us-public-domain"),
        fetch("ecb", "exr_usd_eur_daily.csv", EXR_URL, "ecb-escb-statistics-reuse"),
        fetch("ecb", "mpd_hicp_ea_quarterly.csv", MPD_URL, "ecb-escb-statistics-reuse"),
    ]


def oil_bulletin(geos: dict[str, str] = OIL_GEO) -> pl.DataFrame:
    """Weekly consumer prices with taxes, EUR per 1000 l: geo, product, date, price."""
    wb = fastexcel.read_excel(latest("oil_bulletin", "prices_history.xlsx").read_bytes())
    raw = wb.load_sheet_by_name("Prices with taxes", header_row=None).to_polars()
    header = raw.row(0)
    body = raw.slice(3)  # rows 1-2 are labels and units
    out = []
    for geo, cc in geos.items():
        for code, product in OIL_PRODUCTS.items():
            col = f"{cc}_price_with_tax_{code}"
            if col not in header:
                continue
            j = header.index(col)
            out.append(
                pl.DataFrame({"date": body.to_series(0), "price": body.to_series(j)})
                .with_columns(
                    date=pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False),
                    price=pl.col("price").cast(pl.Float64, strict=False),
                    geo=pl.lit(geo),
                    product=pl.lit(product),
                )
                .drop_nulls()
            )
    return pl.concat(out).unique(["geo", "product", "date"]).sort("geo", "product", "date")


def brent() -> pl.DataFrame:
    """Daily Brent spot, USD per barrel: date, usd."""
    wb = fastexcel.read_excel(latest("eia", "RBRTEd.xls").read_bytes())
    raw = wb.load_sheet_by_name("Data 1", header_row=None).to_polars().slice(3)
    return (
        raw.select(
            date=pl.col(raw.columns[0]).str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False),
            usd=pl.col(raw.columns[1]).cast(pl.Float64, strict=False),
        )
        .drop_nulls()
        .sort("date")
    )


def eurusd() -> pl.DataFrame:
    """Daily ECB reference rate, USD per EUR: date, usd_per_eur."""
    df = pl.read_csv(io.BytesIO(latest("ecb", "exr_usd_eur_daily.csv").read_bytes()), infer_schema=False)
    return (
        df.select(
            date=pl.col("TIME_PERIOD").str.to_date("%Y-%m-%d"),
            usd_per_eur=pl.col("OBS_VALUE").cast(pl.Float64, strict=False),
        )
        .drop_nulls()
        .sort("date")
    )


def staff_projections() -> pl.DataFrame:
    """Quarterly annual rates by exercise: exercise, ex_year, ex_month, code, quarter (YYYY-Qn), value."""
    df = pl.read_csv(io.BytesIO(latest("ecb", "mpd_hicp_ea_quarterly.csv").read_bytes()), infer_schema=False)
    df = df.filter(pl.col("PD_ORIGIN") == "0000").filter(pl.col("PD_SEAS_EX").str.contains(r"^[WGSA]\d\d$"))
    return (
        df.select(
            exercise=pl.col("PD_SEAS_EX"),
            ex_year=(2000 + pl.col("PD_SEAS_EX").str.slice(1, 2).cast(pl.Int32)),
            ex_month=pl.col("PD_SEAS_EX").str.slice(0, 1).replace_strict(EXERCISE_MONTH).cast(pl.Int32),
            code=pl.col("PD_ITEM").replace_strict(MPD_ITEM),
            quarter=pl.col("TIME_PERIOD"),
            value=pl.col("OBS_VALUE").cast(pl.Float64, strict=False),
        )
        .drop_nulls()
        .sort("exercise", "code", "quarter")
    )
