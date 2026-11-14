"""Generic immutable snapshots for non-SDMX sources (file downloads keyed by retrieval date + content hash)."""

from __future__ import annotations

import hashlib
import json
import ssl
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import certifi

from pricelens.config import RAW

USER_AGENT = "pricelens-research-pipeline/0.1"


@dataclass
class Snapshot:
    source: str
    name: str
    url: str
    retrieved_at: str
    path: str
    sha256: str
    bytes: int
    licence: str


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:  # noqa: S310 - fixed https URLs
        return r.read()


def fetch(source: str, name: str, url: str, licence: str, raw_dir: Path = RAW) -> Snapshot:
    """Download `url` into raw/<source>/<date>/<name> unless an identical file already exists for the source."""
    payload = get(url)
    digest = hashlib.sha256(payload).hexdigest()
    base = raw_dir / source
    for meta in sorted(base.glob("*/manifest.json")):
        m = json.loads(meta.read_text())
        if m["name"] == name and m["sha256"] == digest:
            return Snapshot(**m)
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    snap = base / day
    snap.mkdir(parents=True, exist_ok=True)
    (snap / name).write_bytes(payload)
    s = Snapshot(
        source=source,
        name=name,
        url=url,
        retrieved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        path=str((snap / name).relative_to(raw_dir.parent.parent)),
        sha256=digest,
        bytes=len(payload),
        licence=licence,
    )
    (snap / "manifest.json").write_text(json.dumps(asdict(s), indent=2))
    with open(raw_dir / "manifest.jsonl", "a") as f:
        f.write(json.dumps(asdict(s)) + "\n")
    return s


def latest(source: str, name: str, raw_dir: Path = RAW) -> Path:
    files = sorted((raw_dir / source).glob(f"*/{name}"))
    if not files:
        raise FileNotFoundError(f"no snapshot of {source}/{name}; run `pricelens fetch-extra`")
    return files[-1]
