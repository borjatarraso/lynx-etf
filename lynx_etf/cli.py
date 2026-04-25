"""Command-line interface for lynx-etf.

Mirrors the flag vocabulary of ``lynx-fundamental`` (``-p``/``-t``,
``-i``/``-tui``/``-x``/``-s``, ``--list-cache`` / ``--drop-cache``,
``--export``/``--output``, ``--about``/``--version``) so users can move
between the Suite tools without relearning the CLI.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from lynx_etf import (
    APP_NAME,
    SUITE_LABEL,
    __author__,
    __author_email__,
    __license__,
    __version__,
    __year__,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticker_completer(prefix, **kw):
    """Dynamic argcomplete completer that returns cached tickers."""
    try:
        from lynx_etf.core.storage import list_cached_tickers
        items = list_cached_tickers() or []
        return [t["ticker"] for t in items if t["ticker"].startswith(prefix.upper())]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lynx-etf",
        description=(
            "Lynx ETF — Exchange-Traded Fund analysis.\n"
            "Fetch, calculate, and display fund-specific metrics for any ETF\n"
            "by ticker or ISIN. Stocks, mutual funds, and index funds are\n"
            "rejected at the resolver level.\n\n"
            "One of --production-mode (-p) or --testing-mode (-t) is required\n"
            "for analysis (defaults to production for one-shot commands)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  lynx-etf -p SPY                      Production analysis (uses cache)\n"
            "  lynx-etf -p QQQ --refresh             Force fresh data download\n"
            "  lynx-etf -t VTI                       Testing analysis (fresh, isolated)\n"
            "  lynx-etf -p IE00B4L5Y983              Analyze by ISIN\n"
            "  lynx-etf -p -s 'world equity'         Search ETFs matching query\n"
            "  lynx-etf -p --list-cache              Show cached ETFs\n"
            "  lynx-etf -p --drop-cache SPY          Remove cached data for SPY\n"
            "  lynx-etf -p --drop-cache ALL          Remove all cached data\n"
            "  lynx-etf -p -i                        Interactive REPL\n"
            "  lynx-etf -p -tui                      Textual UI\n"
            "  lynx-etf -p -x                        Graphical UI\n"
            "  lynx-etf -p -x SPY                    Graphical UI with pre-filled ticker\n"
            "  lynx-etf -p SPY --export html         Export report to HTML\n"
            "  lynx-etf --explain expense_ratio      Explain a metric\n"
            "  lynx-etf --about                      Show developer & license info\n"
        ),
    )

    # --- Execution mode (one required for analysis; --about/--explain bypass) ---
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "-p", "--production-mode",
        action="store_const", const="production", dest="run_mode",
        help="Production mode: use data/ for persistent cache and storage",
    )
    run_mode.add_argument(
        "-t", "--testing-mode",
        action="store_const", const="testing", dest="run_mode",
        help="Testing mode: use data_test/ (isolated, always fresh)",
    )

    ident_arg = parser.add_argument(
        "identifier",
        nargs="?",
        help="ETF ticker (e.g. SPY) or ISIN (e.g. IE00B4L5Y983)",
    )
    ident_arg.completer = _ticker_completer

    # --- Interface mode ---
    ui_mode = parser.add_mutually_exclusive_group()
    ui_mode.add_argument(
        "-i", "--interactive-mode",
        action="store_true", dest="interactive",
        help="Launch the interactive REPL",
    )
    ui_mode.add_argument(
        "-tui", "--tui-mode", "--textual-ui",
        action="store_true", dest="tui",
        help="Launch the Textual terminal UI",
    )
    ui_mode.add_argument(
        "-x", "--graphical-mode", "--gui",
        action="store_true", dest="gui",
        help="Launch the Tkinter graphical UI",
    )
    ui_mode.add_argument(
        "-s", "--search",
        metavar="QUERY",
        help="Search ETFs matching a free-text query and exit",
    )

    # --- Data / cache options ---
    parser.add_argument(
        "--refresh", action="store_true",
        help="Force fresh data download (production mode only)",
    )
    parser.add_argument(
        "--no-news", action="store_true",
        help="Skip news fetching",
    )
    parser.add_argument(
        "--no-reports", action="store_true",
        help="Skip fetching ancillary fund reports",
    )

    parser.add_argument(
        "--list-cache", action="store_true",
        help="List all cached ETFs and exit",
    )
    parser.add_argument(
        "--drop-cache", metavar="TICKER",
        help="Remove cached data for TICKER, or ALL to clear everything",
    )

    # --- Learn ---
    parser.add_argument(
        "--explain", metavar="METRIC",
        help="Explain a metric and exit (e.g. expense_ratio)",
    )
    parser.add_argument(
        "--explain-all", action="store_true",
        help="Print all metric explanations and exit",
    )

    # --- Export ---
    parser.add_argument(
        "--export", choices=["txt", "html", "pdf"], metavar="FORMAT",
        help="Export report to file (txt, html, or pdf)",
    )
    parser.add_argument(
        "--output", metavar="PATH",
        help="Output file path for export (default: auto-generated in data dir)",
    )

    # --- Info ---
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output during analysis",
    )
    parser.add_argument(
        "--about", action="store_true",
        help="Show about, author, and license info and exit",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}  |  {SUITE_LABEL}  ({__year__}) by {__author__}",
    )

    # Shared --language flag (us / es / it / de / fr / fa).
    try:
        from lynx_investor_core.translations import add_language_argument
        add_language_argument(parser)
    except ImportError:
        pass

    return parser


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------

def run_cli(argv: Optional[list] = None) -> int:
    parser = build_parser()
    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args(argv)
    try:
        from lynx_investor_core.translations import apply_args as _apply_lang
        _apply_lang(args)
    except ImportError:
        pass

    from rich.console import Console
    from lynx_investor_core.translations import t as _t
    errc = Console(stderr=True)

    # Standalone commands that don't need a run mode --------------------------
    if args.about:
        _print_about()
        return 0
    if args.explain:
        return _cmd_explain(args.explain)
    if args.explain_all:
        return _cmd_explain_all()

    # Default to production for friendlier one-shot UX -----------------------
    if args.run_mode is None:
        args.run_mode = "production"

    from lynx_etf.core.storage import set_mode
    set_mode(args.run_mode)

    mode_label = (
        f"[bold green]{_t('mode_production', default='PRODUCTION')}[/]"
        if args.run_mode == "production"
        else f"[bold yellow]{_t('mode_testing', default='TESTING')}[/]"
    )
    errc.print(f"Mode: {mode_label}")

    # Cache commands ---------------------------------------------------------
    if args.list_cache:
        return _cmd_list_cache()
    if args.drop_cache:
        return _cmd_drop_cache(args.drop_cache)

    # Search -----------------------------------------------------------------
    if args.search:
        return _cmd_search(args.search)

    # UI dispatch ------------------------------------------------------------
    if args.gui:
        from lynx_etf.gui.app import run_gui
        return run_gui(args)

    if args.tui:
        from lynx_etf.tui.app import run_tui
        return run_tui(initial_ticker=args.identifier)

    if args.interactive:
        from lynx_etf.interactive import run_interactive
        return run_interactive(args)

    # Console mode — need an identifier --------------------------------------
    if not args.identifier:
        parser.print_help()
        return 1

    return _cmd_analyze(args)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _cmd_analyze(args) -> int:
    from rich.console import Console
    from lynx_etf.core.analyzer import run_full_analysis
    from lynx_etf.core.ticker import NotAnETFError
    from lynx_etf.display import render_full_report

    console = Console()
    errc = Console(stderr=True)
    try:
        report = run_full_analysis(
            identifier=args.identifier,
            download_news=not args.no_news,
            refresh=args.refresh,
        )
    except NotAnETFError as exc:
        errc.print(f"[bold red]Error:[/] {exc}")
        return 2
    except ValueError as exc:
        errc.print(f"[bold red]Error:[/] {exc}")
        return 2
    except (ConnectionError, TimeoutError, OSError) as exc:
        errc.print(f"[bold red]Network error:[/] {exc}")
        errc.print("[dim]Check your internet connection and try again.[/]")
        return 1

    render_full_report(console, report)

    if args.export:
        path = _do_export(report, args.export, args.output)
        if path:
            errc.print(f"[bold green]{_t('exported_to')}[/] {path}")
    return 0


def _do_export(report, fmt: str, output: str | None) -> str | None:
    """Best-effort export. Falls back to writing the rendered text.

    Mirrors lynx-fundamental's ``--export`` flow: txt always works, html
    wraps the text in a <pre>, pdf uses weasyprint when available.
    """
    import io as _io
    import os
    from pathlib import Path
    from rich.console import Console
    from lynx_etf.display import render_full_report
    from lynx_investor_core.author_footer import text_footer, html_footer

    buf = _io.StringIO()
    render_full_report(Console(file=buf, width=120, force_terminal=False), report)
    text = buf.getvalue() + text_footer(SUITE_LABEL)

    ticker = report.profile.ticker if hasattr(report, "profile") else "etf"
    if output:
        path = Path(output)
    else:
        path = Path(os.getcwd()) / f"lynx-etf-{ticker.lower()}.{fmt}"

    if fmt == "txt":
        path.write_text(text, encoding="utf-8")
        return str(path)
    if fmt == "html":
        html = (
            f"<html><head><meta charset='utf-8'>"
            f"<title>{APP_NAME} — {ticker}</title>"
            f"<style>body{{background:#1e1e2e;color:#cdd6f4;"
            f"font-family:monospace;padding:18px}}pre{{white-space:pre-wrap}}</style>"
            f"</head><body><pre>{text}</pre>"
            f"{html_footer(SUITE_LABEL)}"
            f"</body></html>"
        )
        path.write_text(html, encoding="utf-8")
        return str(path)
    if fmt == "pdf":
        try:
            from weasyprint import HTML  # type: ignore
            html = (
                f"<html><body><pre style='font-family:monospace;'>{text}</pre>"
                f"{html_footer(SUITE_LABEL)}"
                f"</body></html>"
            )
            HTML(string=html).write_pdf(str(path))
            return str(path)
        except ImportError:
            from rich.console import Console as _C
            _C(stderr=True).print(
                "[yellow]PDF export requires the optional 'weasyprint' "
                "dependency. Install lynx-etf[pdf] to enable it.[/]"
            )
            return None
    return None


def _cmd_search(query: str) -> int:
    from rich.console import Console
    from rich.table import Table
    from rich.box import ROUNDED
    from lynx_etf.core.ticker import search_etfs

    console = Console()
    results = search_etfs(query)
    if not results:
        console.print(f"[yellow]No ETFs matching '{query}'[/]")
        return 1
    t = Table(box=ROUNDED, title=f"ETFs matching '{query}'",
              show_header=True, header_style="bold")
    t.add_column("Symbol", style="bold cyan")
    t.add_column("Name")
    t.add_column("Exchange")
    t.add_column("Currency")
    for r in results:
        t.add_row(r["symbol"], r["name"], r["exchange"], r["currency"])
    console.print(t)
    return 0


def _cmd_list_cache() -> int:
    from rich.console import Console
    from rich.table import Table
    from rich.box import ROUNDED
    from lynx_etf.core.storage import get_mode, list_cached_tickers

    console = Console()
    items = list_cached_tickers()
    if not items:
        console.print(f"[yellow]No cached ETFs in {get_mode()} mode[/]")
        return 0
    t = Table(box=ROUNDED, title=f"Cached ETFs ({get_mode()})",
              show_header=True, header_style="bold")
    t.add_column("Ticker", style="bold cyan")
    t.add_column("Name")
    t.add_column("Tier")
    t.add_column("Age", justify="right")
    t.add_column("Files", justify="right")
    t.add_column("Size", justify="right")
    for i in items:
        age = i.get("age_hours")
        if age is not None:
            if age < 1:
                age_str = f"{age * 60:.0f}m"
            elif age < 24:
                age_str = f"{age:.1f}h"
            else:
                age_str = f"{age / 24:.1f}d"
        else:
            age_str = "?"
        t.add_row(
            i["ticker"],
            i.get("name", ""),
            i.get("tier", ""),
            age_str,
            str(i.get("files", 0)),
            f"{i.get('size_mb', 0):.1f}MB",
        )
    console.print(t)
    console.print(f"[dim]Total: {len(items)} ETF(s) cached[/]")
    return 0


def _cmd_drop_cache(target: str) -> int:
    from rich.console import Console
    from lynx_etf.core.storage import drop_cache_all, drop_cache_ticker, get_mode

    console = Console()
    label = f"({get_mode()} mode)"
    if target.upper() == "ALL":
        count = drop_cache_all()
        console.print(f"[bold green]Removed all cached data {label} ({count} ETFs).[/]")
        return 0
    if drop_cache_ticker(target.upper()):
        console.print(f"[bold green]Removed cached data for {target.upper()} {label}.[/]")
        return 0
    console.print(f"[yellow]No cached data found for '{target.upper()}' {label}.[/]")
    return 1


def _cmd_explain(key: str) -> int:
    from rich.console import Console
    from rich.panel import Panel
    from lynx_etf.metrics.explanations import get_explanation

    console = Console()
    exp = get_explanation(key)
    if not exp:
        console.print(f"[yellow]No explanation found for '{key}'.[/]")
        console.print("[dim]Use --explain-all to list every metric.[/]")
        return 1

    body = (
        f"[bold]{exp.full_name}[/] [dim]({exp.category})[/]\n\n"
        f"{exp.description}\n\n"
        f"[bold cyan]Why use it:[/] {exp.why_used}\n"
        f"[bold cyan]Formula:[/]   [bold]{exp.formula}[/]"
    )
    console.print(Panel(body, title=f"Metric: {exp.key}", border_style="cyan"))
    return 0


def _cmd_explain_all() -> int:
    from rich.console import Console
    from rich.table import Table
    from rich.box import ROUNDED
    from lynx_etf.metrics.explanations import by_category

    console = Console()
    for cat, items in sorted(by_category().items()):
        t = Table(box=ROUNDED, title=cat.title(), show_header=True, header_style="bold")
        t.add_column("Key", style="bold cyan")
        t.add_column("Name")
        t.add_column("Why")
        for e in items:
            t.add_row(e.key, e.full_name, e.why_used)
        console.print(t)
    console.print(
        "[dim]Use --explain <key> for a detailed single-metric panel.[/]"
    )
    return 0


def _print_about() -> None:
    from rich.console import Console
    from lynx_etf.display import render_about
    render_about(Console())


if __name__ == "__main__":
    sys.exit(run_cli())
