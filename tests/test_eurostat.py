from pathlib import Path

import polars as pl

from pricelens.sources.eurostat import (
    bulk_url,
    data_timestamp,
    dimensions,
    parse_codelists,
    parse_tsv,
    snapshot_dirname,
)

FIX = Path(__file__).parent / "fixtures"


def test_parse_tsv_long_format_values_and_flags():
    df = parse_tsv(FIX / "minr_small.tsv")
    assert df.columns == ["freq", "unit", "coicop18", "geo", "time", "value", "flag"]
    de = df.filter((pl.col("geo") == "DE") & (pl.col("unit") == "I25") & (pl.col("coicop18") == "TOTAL"))
    assert de.sort("time")["value"].to_list() == [99.8, 100.1, 100.5]
    assert de.sort("time")["flag"].to_list() == ["", "", "p"]


def test_parse_tsv_missing_and_confidential():
    df = parse_tsv(FIX / "minr_small.tsv")
    cp04 = df.filter(pl.col("coicop18") == "CP04").sort("time")
    # ': ' (plain missing) is dropped, ': c' (confidential) kept with null value, real value kept
    assert cp04["time"].to_list() == ["2025-12", "2026-01"]
    assert cp04["value"].to_list() == [None, 101.2]
    assert cp04["flag"].to_list() == ["c", ""]


def test_parse_tsv_negative_rates_and_estimated_flag():
    df = parse_tsv(FIX / "minr_small.tsv").filter(pl.col("unit") == "RCH_A").sort("time")
    assert df["value"].to_list() == [-0.4, 2.1, 2.3]
    assert df["flag"].to_list()[-1] == "e"


def test_parse_tsv_keep_filter():
    df = parse_tsv(FIX / "minr_small.tsv", keep={"geo": ["FR"]})
    assert set(df["geo"]) == {"FR"}
    assert df.height == 3


def test_structure_parsing():
    xml = FIX / "structure_small.xml"
    assert data_timestamp(xml.read_bytes()) == "2026-11-04T11:00:00+0100"
    assert dimensions(xml) == ["freq", "unit", "coicop18", "geo"]
    cl = parse_codelists(xml)
    assert cl["UNIT"]["I25"] == "Index, 2025=100"  # English label chosen over German
    assert cl["COICOP18"]["CP04"].startswith("Housing")


def test_snapshot_dirname_is_filesystem_safe():
    assert ":" not in snapshot_dirname("2026-11-04T11:00:00+0100")


def test_bulk_url_uses_compressed_tsv():
    assert bulk_url("PRC_HICP_IW").endswith("/data/PRC_HICP_IW?format=TSV&compressed=true")
