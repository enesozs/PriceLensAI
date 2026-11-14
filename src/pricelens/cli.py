"""PriceLens command line: `uv run pricelens <command>`."""

from __future__ import annotations

import argparse
import sys

from pricelens.config import eurostat_dataset


def cmd_fetch(args: argparse.Namespace) -> None:
    from pricelens.sources.eurostat import fetch_dataset

    keys = args.datasets or ["hicp_monthly", "hicp_weights", "hbs_quintile"]
    for key in keys:
        ds = eurostat_dataset(key)
        e = fetch_dataset(ds.id)
        print(f"{ds.id:16s} version={e.source_version} bytes={e.bytes:,} sha256={e.sha256[:12]}")


def cmd_audit(args: argparse.Namespace) -> None:
    from pricelens.audit import write_audit

    write_audit()
    print("wrote reports/m0_source_audit.md")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="pricelens")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download Eurostat bulk snapshots (skips versions already stored)")
    f.add_argument("datasets", nargs="*", help="dataset keys from configs/sources.yaml")
    f.set_defaults(func=cmd_fetch)
    a = sub.add_parser("audit", help="M0 source audit report from the latest snapshots")
    a.set_defaults(func=cmd_audit)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
