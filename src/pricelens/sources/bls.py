"""U.S. Bureau of Labor Statistics CPI (US public domain, citation requested).

Uses the keyless public API v1 (25 queries/day, 25 series and 10 years per query). The bls.gov website and flat
files refuse automated clients that do not send a personal contact e-mail, which PriceLens does not send;
relative-importance weights are therefore derived from the index identity (see pricelens.us).
CPI-U, U.S. city average, not seasonally adjusted (`CUUR0000…`), index 1982-84=100.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

import certifi
import polars as pl

from pricelens.config import RAW

API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
LICENCE = "us-public-domain"
SERIES = {
    "SA0": "All items",
    "SA0E": "Energy",
    "SAF1": "Food",
    "SACL1E": "Commodities less food and energy commodities",
    "SASLE": "Services less energy services",
    "SAF": "Food and beverages",
    "SAH": "Housing",
    "SAA": "Apparel",
    "SAT": "Transportation",
    "SAM": "Medical care",
    "SAR": "Recreation",
    "SAE": "Education and communication",
    "SAG": "Other goods and services",
    "SAH1": "Shelter",
    "SA0L2": "All items less shelter",
}
FIRST_YEAR = 1997


def _post(payload: dict) -> bytes:
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "pricelens-research-pipeline/0.1"},
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:  # noqa: S310 - fixed https URL
        return r.read()


def fetch(raw_dir: Path = RAW) -> list[dict]:
    """One snapshot per 10-year block; at most 3 API queries per run (BLS v1 allows 25 per day)."""
    today = datetime.now(UTC)
    snap = raw_dir / "bls" / today.strftime("%Y-%m-%d")
    snap.mkdir(parents=True, exist_ok=True)
    out = []
    for start in range(FIRST_YEAR, today.year + 1, 10):
        end = min(start + 9, today.year)
        key = hashlib.sha256(",".join(SERIES).encode()).hexdigest()[:8]
        path = snap / f"cpi_{start}_{end}_{key}.json"
        if not path.exists():
            body = _post(
                {"seriesid": [f"CUUR0000{s}" for s in SERIES], "startyear": str(start), "endyear": str(end)}
            )
            msg = json.loads(body)
            if msg.get("status") != "REQUEST_SUCCEEDED":
                raise RuntimeError(f"BLS API: {msg.get('status')} {msg.get('message')}")
            path.write_bytes(body)
            entry = {
                "source": "bls",
                "name": path.name,
                "url": API,
                "request": {"years": [start, end], "series": list(SERIES)},
                "retrieved_at": today.isoformat(timespec="seconds"),
                "path": str(path.relative_to(raw_dir.parent.parent)),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "licence": LICENCE,
            }
            with open(raw_dir / "manifest.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")
        out.append({"block": f"{start}-{end}", "path": str(path)})
    return out


def parse_responses(paths: list[Path]) -> pl.DataFrame:
    rows = []
    for p in paths:
        for s in json.loads(p.read_text())["Results"]["series"]:
            code = s["seriesID"].removeprefix("CUUR0000")
            for d in s["data"]:
                if not d["period"].startswith("M") or d["period"] == "M13" or d["value"] in ("-", ""):
                    continue
                rows.append(
                    {
                        "code": code,
                        "date": date(int(d["year"]), int(d["period"][1:]), 1),
                        "value": float(d["value"]),
                        "preliminary": any(
                            "reliminary" in (f.get("text") or "") for f in d.get("footnotes", [])
                        ),
                    }
                )
    return pl.DataFrame(rows).unique(["code", "date"], keep="last").sort("code", "date")


def latest_snapshot(raw_dir: Path = RAW) -> pl.DataFrame:
    snaps = sorted((raw_dir / "bls").glob("*/cpi_*.json"))
    if not snaps:
        raise FileNotFoundError("no BLS snapshot; run `pricelens fetch-extra`")
    key = hashlib.sha256(",".join(SERIES).encode()).hexdigest()[:8]
    files = sorted((raw_dir / "bls").glob(f"*/cpi_*_{key}.json"))
    if not files:
        raise FileNotFoundError("no BLS snapshot for the current series list; run `pricelens fetch-extra`")
    latest_day = files[-1].parent
    return parse_responses(sorted(latest_day.glob(f"cpi_*_{key}.json")))
