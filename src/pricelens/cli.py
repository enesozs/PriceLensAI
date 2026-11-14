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


def cmd_fetch_extra(args: argparse.Namespace) -> None:
    from pricelens.sources.eurostat import fetch_dataset
    from pricelens.sources.extra import fetch_all

    for ds in ("PRC_HICP_FPD", "PRC_HICP_FP"):  # first releases (flash/final), Eurostat
        e = fetch_dataset(ds)
        print(f"{ds:16s} version={e.source_version} bytes={e.bytes:,}")
    for s in fetch_all():
        print(f"{s.source:12s} {s.name:28s} bytes={s.bytes:,} sha256={s.sha256[:12]}")


def cmd_forecast(args: argparse.Namespace) -> None:
    from pricelens.forecast import run

    meta = run()
    print(
        f"chosen model: {meta['chosen_model']}; latest origin {meta['latest_origin']}; wrote reports/m4_forecast.md"
    )


def cmd_audit(args: argparse.Namespace) -> None:
    from pricelens.audit import write_audit

    write_audit()
    print("wrote reports/m0_source_audit.md")


def cmd_curate(args: argparse.Namespace) -> None:
    from pricelens.curate import write_all

    for name, n in write_all().items():
        print(f"{name:14s} {n:>12,} rows")


def cmd_qa(args: argparse.Namespace) -> None:
    from pricelens.qa import run_qa

    ok = run_qa()
    print("wrote reports/m1_qa.md")
    if not ok:
        sys.exit("QA FAILED: see reports/m1_qa.md")


def cmd_export(args: argparse.Namespace) -> None:
    from pricelens.export import export

    sizes = export()
    print(f"exported {len(sizes)} files, {sum(sizes.values()) / 1e6:.2f} MB")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="pricelens")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download Eurostat bulk snapshots (skips versions already stored)")
    f.add_argument("datasets", nargs="*", help="dataset keys from configs/sources.yaml")
    f.set_defaults(func=cmd_fetch)
    x = sub.add_parser("fetch-extra", help="forecast-lab sources: first releases, Oil Bulletin, Brent, ECB")
    x.set_defaults(func=cmd_fetch_extra)
    fc = sub.add_parser(
        "forecast", help="rolling-origin backtest, benchmarks, live forecast -> reports/m4_forecast.md"
    )
    fc.set_defaults(func=cmd_forecast)
    a = sub.add_parser("audit", help="M0 source audit report from the latest snapshots")
    a.set_defaults(func=cmd_audit)
    c = sub.add_parser("curate", help="raw snapshots -> data/curated/*.parquet")
    c.set_defaults(func=cmd_curate)
    q = sub.add_parser("qa", help="data-contract checks + official-HICP reconstruction gate")
    q.set_defaults(func=cmd_qa)
    e = sub.add_parser("export", help="static JSON for the web app -> app/public/data")
    e.set_defaults(func=cmd_export)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
