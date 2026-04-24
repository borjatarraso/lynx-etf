"""CLI argument parsing and plumbing tests."""

from __future__ import annotations

import io

from rich.console import Console

from lynx_etf.cli import build_parser, _cmd_explain


class TestBuildParser:
    def test_help_contains_etf(self):
        parser = build_parser()
        help_text = parser.format_help()
        assert "lynx-etf" in help_text
        assert "ETF" in help_text or "Exchange-Traded" in help_text

    def test_parses_production_mode(self):
        args = build_parser().parse_args(["-p", "SPY"])
        assert args.run_mode == "production"
        assert args.identifier == "SPY"

    def test_parses_testing_mode(self):
        args = build_parser().parse_args(["-t", "QQQ"])
        assert args.run_mode == "testing"
        assert args.identifier == "QQQ"

    def test_mutually_exclusive_run_mode(self):
        import pytest
        with pytest.raises(SystemExit):
            build_parser().parse_args(["-p", "-t", "SPY"])

    def test_interactive_flag(self):
        args = build_parser().parse_args(["-p", "-i"])
        assert args.interactive

    def test_gui_flag(self):
        args = build_parser().parse_args(["-p", "-x"])
        assert args.gui

    def test_tui_flag(self):
        args = build_parser().parse_args(["-p", "-tui"])
        assert args.tui

    def test_search(self):
        args = build_parser().parse_args(["-p", "-s", "world equity"])
        assert args.search == "world equity"

    def test_explain(self):
        args = build_parser().parse_args(["--explain", "expense_ratio"])
        assert args.explain == "expense_ratio"


class TestExplain:
    def test_known_metric(self):
        # Just exercise the code path; it prints to stdout.
        rc = _cmd_explain("expense_ratio")
        assert rc == 0

    def test_unknown_metric(self):
        rc = _cmd_explain("nope_not_real")
        assert rc == 1
