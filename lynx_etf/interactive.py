"""Interactive REPL for lynx-etf."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from lynx_etf import APP_NAME, __version__
from lynx_etf.core.ticker import NotAnETFError


HELP_TEXT = """\
Commands:
  analyze <TICKER>        Run the full analysis pipeline
  search <QUERY>          Search ETFs matching free-text query
  explain <METRIC>        Explain a metric (e.g. expense_ratio)
  cache                   List cached ETFs
  drop <TICKER|ALL>       Drop cache for a ticker or all
  about                   Show about info
  help                    Show this help
  quit / exit             Leave the REPL
"""


def run_interactive(args=None) -> int:
    console = Console()
    console.print(
        Panel(
            f"[bold cyan]{APP_NAME}[/] v{__version__}\n"
            "Type 'help' for commands or 'quit' to exit.",
            border_style="cyan",
        )
    )

    while True:
        try:
            cmd = Prompt.ask("[bold cyan]lynx-etf[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return 0
        if not cmd:
            continue

        tokens = cmd.split(maxsplit=1)
        action = tokens[0].lower()
        arg = tokens[1] if len(tokens) > 1 else ""

        if action in ("quit", "exit", "q"):
            return 0
        if action in ("help", "h", "?"):
            console.print(HELP_TEXT)
            continue
        if action == "about":
            from lynx_etf.display import render_about
            render_about(console)
            continue
        if action == "cache":
            from lynx_etf.cli import _cmd_list_cache
            _cmd_list_cache()
            continue
        if action == "drop":
            if not arg:
                console.print("[yellow]Usage: drop <TICKER|ALL>[/]")
                continue
            from lynx_etf.cli import _cmd_drop_cache
            _cmd_drop_cache(arg)
            continue
        if action == "explain":
            if not arg:
                console.print("[yellow]Usage: explain <METRIC>[/]")
                continue
            from lynx_etf.cli import _cmd_explain
            _cmd_explain(arg)
            continue
        if action == "search":
            if not arg:
                console.print("[yellow]Usage: search <QUERY>[/]")
                continue
            from lynx_etf.cli import _cmd_search
            _cmd_search(arg)
            continue
        if action == "analyze" or action == "a":
            if not arg:
                console.print("[yellow]Usage: analyze <TICKER>[/]")
                continue
            _analyze(console, arg)
            continue

        # Bare ticker → analyze
        _analyze(console, cmd)


def _analyze(console: Console, identifier: str) -> None:
    from lynx_etf.core.analyzer import run_full_analysis
    from lynx_etf.display import render_full_report

    try:
        report = run_full_analysis(identifier=identifier)
    except NotAnETFError as exc:
        console.print(f"[bold red]{exc}[/]")
        return
    except ValueError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return
    render_full_report(console, report)
