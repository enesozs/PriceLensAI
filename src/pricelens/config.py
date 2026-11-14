"""Project paths and source configuration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
CURATED = DATA / "curated"
REPORTS = ROOT / "reports"
EXPORT = ROOT / "app" / "public" / "data"


@dataclass(frozen=True)
class Dataset:
    key: str
    id: str
    grain: tuple[str, ...]


@cache
def sources() -> dict[str, Any]:
    with open(ROOT / "configs" / "sources.yaml") as f:
        return yaml.safe_load(f)


def eurostat_dataset(key: str) -> Dataset:
    d = sources()["eurostat"]["datasets"][key]
    return Dataset(key=key, id=d["id"], grain=tuple(d["grain"]))


def warehouse_geos() -> list[str]:
    g = sources()["geos"]
    return list(g["aggregates"]) + list(g["countries"])


def countries() -> list[str]:
    return list(sources()["geos"]["countries"])


def forecast_geos() -> list[str]:
    return list(sources()["forecast_geos"])


def hicp_units() -> list[str]:
    return list(sources()["hicp_units"])
