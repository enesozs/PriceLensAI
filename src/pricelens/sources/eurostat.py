"""Eurostat SDMX 2.1 bulk connector.

Downloads whole-dataset bulk files (TSV, gzip) plus their SDMX structure, stores them as immutable
snapshots keyed by Eurostat's own data timestamp, and parses the wide TSV into a long table.

Bulk files are used instead of filtered queries because Eurostat queues large filtered requests
asynchronously, while the pre-generated bulk files download synchronously and are small
(PRC_HICP_MINR is about 34 MB compressed).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import certifi
import polars as pl

from pricelens.config import RAW, sources

NS = {
    "s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
USER_AGENT = "pricelens-research-pipeline/0.1"


def base_url() -> str:
    return sources()["eurostat"]["base_url"]


def bulk_url(dataset_id: str) -> str:
    return f"{base_url()}/data/{dataset_id}?format=TSV&compressed=true"


def structure_url(dataset_id: str) -> str:
    return f"{base_url()}/dataflow/ESTAT/{dataset_id}/latest?references=descendants&detail=referencepartial"


# --------------------------------------------------------------------------------------------- download


@dataclass
class ManifestEntry:
    source: str
    dataset_id: str
    source_version: str  # Eurostat DISSEMINATION_TIMESTAMP_DATA
    url: str
    structure_url: str
    retrieved_at: str
    path: str
    structure_path: str
    sha256: str
    bytes: int
    licence: str


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context(cafile=certifi.where())  # uv's standalone Python has no system CAs
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:  # noqa: S310 - fixed https URLs
        return r.read()


def data_timestamp(structure_xml: bytes) -> str:
    """Eurostat's DISSEMINATION_TIMESTAMP_DATA annotation: the version of the data in the dataflow."""
    root = ET.fromstring(structure_xml)
    for ann in root.iter(f"{{{NS['c']}}}Annotation"):
        typ = ann.find("c:AnnotationType", NS)
        if typ is not None and typ.text == "DISSEMINATION_TIMESTAMP_DATA":
            title = ann.find("c:AnnotationTitle", NS)
            if title is not None and title.text:
                return title.text
    raise ValueError("structure has no DISSEMINATION_TIMESTAMP_DATA annotation")


def snapshot_dirname(ts: str) -> str:
    """'2026-11-04T11:00:00+0100' -> '2026-11-04T110000+0100' (filesystem-safe)."""
    return ts.replace(":", "")


def fetch_dataset(dataset_id: str, raw_dir: Path = RAW) -> ManifestEntry:
    """Download structure + bulk data into raw/eurostat/<ID>/<version>/ unless that version exists."""
    s_url, d_url = structure_url(dataset_id), bulk_url(dataset_id)
    structure = _get(s_url)
    version = data_timestamp(structure)
    snap = raw_dir / "eurostat" / dataset_id / snapshot_dirname(version)
    data_path, struct_path = snap / "data.tsv.gz", snap / "structure.xml"
    entry_path = snap / "manifest.json"
    if entry_path.exists() and data_path.exists():
        return ManifestEntry(**json.loads(entry_path.read_text()))
    snap.mkdir(parents=True, exist_ok=True)
    payload = _get(d_url)
    with gzip.open(io.BytesIO(payload)) as g:  # integrity check: must be valid gzip TSV
        head = g.readline().decode()
    if "\\TIME_PERIOD" not in head:
        raise ValueError(f"{dataset_id}: unexpected bulk payload header {head[:120]!r}")
    struct_path.write_bytes(structure)
    data_path.write_bytes(payload)
    entry = ManifestEntry(
        source="eurostat",
        dataset_id=dataset_id,
        source_version=version,
        url=d_url,
        structure_url=s_url,
        retrieved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        path=str(data_path.relative_to(raw_dir.parent.parent)),
        structure_path=str(struct_path.relative_to(raw_dir.parent.parent)),
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
        licence=sources()["eurostat"]["licence"],
    )
    entry_path.write_text(json.dumps(asdict(entry), indent=2))
    with open(raw_dir / "manifest.jsonl", "a") as f:
        f.write(json.dumps(asdict(entry)) + "\n")
    return entry


def latest_snapshot(dataset_id: str, raw_dir: Path = RAW) -> Path:
    base = raw_dir / "eurostat" / dataset_id
    snaps = sorted(p for p in base.glob("*") if (p / "data.tsv.gz").exists())
    if not snaps:
        raise FileNotFoundError(f"no snapshot for {dataset_id}; run `pricelens fetch`")
    return snaps[-1]


# --------------------------------------------------------------------------------------------- parse


def parse_tsv(path: Path, keep: dict[str, list[str]] | None = None) -> pl.DataFrame:
    """Parse a Eurostat bulk TSV(.gz) into long format.

    Returns columns: <dimension columns...>, time (str), value (f64, null when missing), flag (str).
    Rows that are entirely missing (':' without a flag) are dropped.
    `keep` filters dimension values before the wide->long reshape to bound memory.
    """
    df = pl.read_csv(path, separator="\t", infer_schema=False, quote_char=None)
    first = df.columns[0]
    dims = first.split("\\")[0].split(",")
    df = df.rename({c: c.strip() for c in df.columns[1:]})
    df = df.with_columns(pl.col(first).str.split(",").list.to_struct(fields=dims).alias("_k")).unnest("_k")
    df = df.drop(first)
    for dim, values in (keep or {}).items():
        df = df.filter(pl.col(dim).is_in(values))
    times = [c for c in df.columns if c not in dims]
    long = df.unpivot(index=dims, on=times, variable_name="time", value_name="cell")
    cell = pl.col("cell").str.strip_chars()
    long = long.with_columns(
        value=pl.when(cell.str.starts_with(":"))
        .then(None)
        .otherwise(cell.str.extract(r"^([-0-9.eE+]+)", 1))
        .cast(pl.Float64),
        flag=cell.str.extract(r"([a-z]+)$", 1).fill_null(""),
    ).drop("cell")
    return long.filter(pl.col("value").is_not_null() | (pl.col("flag") != ""))


def parse_codelists(structure_xml: Path | bytes) -> dict[str, dict[str, str]]:
    """Return {codelist_id: {code: english_label}} from an SDMX structure message."""
    raw = structure_xml.read_bytes() if isinstance(structure_xml, Path) else structure_xml
    root = ET.fromstring(raw)
    out: dict[str, dict[str, str]] = {}
    for cl in root.iter(f"{{{NS['s']}}}Codelist"):
        codes: dict[str, str] = {}
        for c in cl.findall("s:Code", NS):
            names = [n.text or "" for n in c.findall("c:Name", NS) if n.get(XML_LANG) == "en"]
            codes[c.get("id", "")] = names[0] if names else ""
        out[cl.get("id", "")] = codes
    return out


def dimensions(structure_xml: Path | bytes) -> list[str]:
    raw = structure_xml.read_bytes() if isinstance(structure_xml, Path) else structure_xml
    root = ET.fromstring(raw)
    dims = sorted(root.iter(f"{{{NS['s']}}}Dimension"), key=lambda d: int(d.get("position", "0")))
    return [d.get("id", "") for d in dims]
