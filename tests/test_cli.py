"""The full refresh must run every step that produces site data, in dependency order."""

import argparse

import pricelens.cli as cli


def test_all_runs_every_step_in_order(monkeypatch, capsys):
    calls: list[str] = []
    names = ["fetch", "fetch_extra", "curate", "qa", "forecast", "advanced", "us", "export"]
    for n in names:
        monkeypatch.setattr(cli, f"cmd_{n}", lambda args, n=n: calls.append(n))
    cli.cmd_all(argparse.Namespace())
    assert calls == names
