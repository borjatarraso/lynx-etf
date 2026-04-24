"""Command-line interface for lynx-etf."""

from __future__ import annotations

import argparse
import sys

from lynx_etf import (
    APP_NAME,
    SUITE_LABEL,
    __author__,
    __author_email__,
    __license__,
    __version__,
    __year__,
)


def _ticker_completer(prefix, **kw):
    try:
        from lynx_etf.core.storage import list_cached_tickers
        items = list_cached_tickers() or []
        return [t["ticker"] for t in items if t["ticker"].startswith(prefix.upper())]
    except Exception:
        return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lynx-etf",
        description=(
            "Lynx ETF — Exchange-Traded Fund analysis.\n"
            "Fetch, calculate, and display fund-specific metrics for any ETF\n"
            "by ticker or ISIN. Stocks, mutual funds, and index funds are\n"
            "rejected at the resolver level.\n\n"
            "One of --production-mode (-p) or --testing-mode (-t) is required."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  lynx-etf -p SPY                     Production analysis (uses cache)\n"
            "  lynx-etf -p QQQ --refresh            Force fresh data download\n"
            "  lynx-etf -t VTI                      Testing analysis (fresh, isolated)\n"
            "  lynx-etf -p IE00B4L5Y983             Analyze by ISIN (IWDA equivalent)\n"
            "  lynx-etf -p -s 'world equity'        Search ETFs matching query\n"
            "  lynx-etf -p --list-cache             Show cached tickers\n"
            "  lynx-etf -p --drop-cache SPY         Remove cached data for SPY\n"
            "  lynx-etf -p --drop-cache ALL         Remove all cached data\n"
            "  lynx-etf -p -i                       Interactive mode\n"
            "  lynx-etf -p -tui                     Textual UI\n"
            "  lynx-etf -p -x                       Graphical UI\n"
            "  lynx-etf -p -x SPY                   Graphical UI with pre-filled ticker\n"
            "  lynx-etf --explain expense_ratio     Explain a metric\n"
        ),
    )

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

    ui_mode = parser.add_mutually_exclusive_group()
    ui_mode.add_argument("-i", "--interactive-mode", action="store_true", dest="interactive",
                         help="Launch the interactive REPL")
    ui_mode.add_argument("-tui", "--tui-mode", action="store_true", dest="tui",
                         help="Launch the Textual terminal UI")
    ui_mode.add_argument("-x", "--graphical-mode", action="store_true", dest="gui",
                         help="Launch the Tkinter graphical UI")
    ui_mode.add_argument("-s", "--search", metavar="QUERY",
                         help="Search ETFs matching a free-text query and exit")

    parser.add_argument("--refresh", action="store_true",
                        help="Force fresh network fetch (production mode only)")
    parser.add_argument("--no-news", action="store_true",
                        help="Skip news download")

    parser.add_argument("--list-cache", action="store_true",
                        help="List cached ETFs and exit")
    parser.add_argument("--drop-cache", metavar="TICKER_OR_ALL",
                        help="Remove cached data for a ticker or 'ALL'")

    parser.add_argument("--explain", metavar="METRIC",
                        help="Explain a metric and exit (e.g. expense_ratio)")
    parser.add_argument("--explain-all", action="store_true",
                        help="Print all metric explanations and exit")

    parser.add_argument("--about", action="store_true", help="Show about info and exit")
    parser.add_argument("--version", action="version",
                        version=f"{APP_NAME} v{__version__}  ({SUITE_LABEL})")

    return parser


def run_cli(argv=None) -> int:
    try:
        import argcomplete
        # Completion must be wired before we know whether the user needed
        # a run-mode flag, so we build the parser unconditionally.
    except ImportError:
        argcomplete = None  # noqa: F841

    parser = build_parser()

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args(argv)

    if args.about:
        _print_about()
        return 0

    if args.explain:
        return _cmd_explain(args.explain)
    if args.explain_all:
        return _cmd_explain_all()

    # Remaining commands need a run_mode
    if args.run_mode is None:
        # Default to production for a friendlier UX on one-shot commands.
        args.run_mode = "production"

    from lynx_etf.core.storage import set_mode
    set_mode(args.run_mode)

    if args.list_cache:
        return _cmd_list_cache()
    if args.drop_cache:
        return _cmd_drop_cache(args.drop_cache)

    if args.search:
        return _cmd_search(args.search)

    if args.gui:
        from lynx_etf.gui.app import run_gui
        return run_gui(initial_ticker=args.identifier)

    if args.tui:
        from lynx_etf.tui.app import run_tui
        return run_tui(initial_ticker=args.identifier)

    if args.interactive:
        from lynx_etf.interactive import run_interactive
        return run_interactive(args)

    # Console mode — need an identifier
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
    try:
        report = run_full_analysis(
            identifier=args.identifier,
            download_news=not args.no_news,
            refresh=args.refresh,
        )
    except NotAnETFError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return 2
    except ValueError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return 2

    render_full_report(console, report)
    return 0


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
    t = Table(box=ROUNDED, title=f"ETFs matching '{query}'", show_header=True, header_style="bold")
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
    t = Table(box=ROUNDED, title=f"Cached ETFs ({get_mode()})", show_header=True, header_style="bold")
    t.add_column("Ticker", style="bold cyan")
    t.add_column("Name")
    t.add_column("Tier")
    t.add_column("Age (h)", justify="right")
    t.add_column("Files", justify="right")
    t.add_column("Size (MB)", justify="right")
    for i in items:
        t.add_row(
            i["ticker"],
            i.get("name", ""),
            i.get("tier", ""),
            str(i.get("age_hours", "")),
            str(i.get("files", "")),
            str(i.get("size_mb", "")),
        )
    console.print(t)
    return 0


def _cmd_drop_cache(target: str) -> int:
    from rich.console import Console
    from lynx_etf.core.storage import drop_cache_all, drop_cache_ticker, get_mode

    console = Console()
    if target.upper() == "ALL":
        count = drop_cache_all()
        console.print(f"[green]Removed {count} ticker(s) from {get_mode()} cache[/]")
        return 0
    ok = drop_cache_ticker(target.upper())
    if ok:
        console.print(f"[green]Removed cache for {target.upper()}[/]")
        return 0
    console.print(f"[yellow]No cache found for {target.upper()}[/]")
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
        f"[bold]Why use it:[/] {exp.why_used}\n"
        f"[bold]Formula:[/] {exp.formula}"
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
    return 0


def _print_about():
    from rich.console import Console
    from lynx_etf.display import render_about
    render_about(Console())


if __name__ == "__main__":
    sys.exit(run_cli())
