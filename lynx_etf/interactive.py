"""Interactive prompt mode for lynx-etf.

Mirrors the visual layout of ``lynx.interactive`` (banner, mode panel,
mode-coloured prompt, command menu) so a user moving between Suite tools
gets a consistent experience. The command set is the ETF-shaped
counterpart: ``analyze`` / ``refresh`` / ``search`` / ``cache`` /
``drop-cache`` / ``explain`` / ``explain-all`` / ``about`` / ``help`` /
``quit``.
"""

from __future__ import annotations

try:
    import readline as _readline  # noqa: F401 — arrow-key history
except ImportError:
    pass  # not available on Windows

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from lynx_etf import APP_NAME, SUITE_LABEL, __version__
from lynx_etf.core.ticker import NotAnETFError


console = Console()


BANNER = """
[bold blue]  L Y N X   ETF Analysis[/]
[dim]    Costs · Holdings · Performance · Risk[/]
"""


MENU = """
[bold cyan]Analysis:[/]
  [bold]analyze[/] <TICKER|ISIN>           Analyze (uses cache in production mode)
  [bold]refresh[/] <TICKER|ISIN>           Force fresh data download
  [bold]search[/] <query>                  Search ETFs by free-text

[bold cyan]Cache:[/]
  [bold]cache[/]                           List cached ETFs
  [bold]drop-cache[/] <TICKER>             Remove cached data for an ETF
  [bold]drop-cache all[/]                  Remove all cached data

[bold cyan]Learn:[/]
  [bold]explain[/] <metric>                Explain a metric (e.g. expense_ratio)
  [bold]explain-all[/]                     List every metric explanation

[bold cyan]Other:[/]
  [bold]about[/]                           Show about, author, and license
  [bold]help[/]                            Show this menu
  [bold]quit[/]                            Exit
"""


def run_interactive(args=None) -> int:
    """Run the interactive prompt loop."""
    from lynx_etf.core.storage import get_mode, is_testing

    console.print(BANNER)

    if is_testing():
        console.print(Panel(
            "[bold yellow]TESTING MODE[/]\n"
            "Data is stored in [bold]data_test/[/] — production data is never touched.\n"
            "All fetches are fresh (cache is not used).",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            "[bold green]PRODUCTION MODE[/]\n"
            "Data is stored in [bold]data/[/] — cached analyses are reused automatically.\n"
            "Use [bold]refresh[/] to force a fresh download.",
            border_style="green",
        ))

    console.print(Panel(MENU, border_style="cyan", title="[bold]Interactive Mode[/]"))

    while True:
        prompt_color = "yellow" if is_testing() else "cyan"
        prompt_suffix = " [test]" if is_testing() else ""
        try:
            console.print(
                f"\n[bold {prompt_color}]lynx-etf{prompt_suffix}[/] ",
                end="",
            )
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            return 0

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/]")
            return 0

        if cmd in ("help", "h", "?"):
            console.print(MENU)
            continue

        if cmd == "about":
            _show_about()
            continue

        if cmd == "cache":
            _show_cache()
            continue

        if cmd == "drop-cache":
            target = arg
            if not target:
                try:
                    target = Prompt.ask("[bold]Ticker to drop (or 'all')[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                    continue
            if not target:
                console.print("[red]No ticker provided.[/]")
                continue
            from lynx_etf.cli import _cmd_drop_cache
            _cmd_drop_cache(target)
            continue

        if cmd == "explain":
            if not arg:
                console.print("[yellow]Usage: explain <metric_key>[/]")
                console.print("[dim]Use 'explain-all' to list every metric.[/]")
                continue
            from lynx_etf.cli import _cmd_explain
            _cmd_explain(arg)
            continue

        if cmd == "explain-all":
            from lynx_etf.cli import _cmd_explain_all
            _cmd_explain_all()
            continue

        if cmd == "search":
            if not arg:
                try:
                    arg = Prompt.ask("[bold]Search query[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                    continue
            if not arg:
                console.print("[red]No query provided.[/]")
                continue
            from lynx_etf.cli import _cmd_search
            _cmd_search(arg)
            continue

        if cmd in ("analyze", "a", "refresh"):
            force = (cmd == "refresh") or is_testing()
            target = arg
            if not target:
                try:
                    target = Prompt.ask("[bold]Enter ETF ticker or ISIN[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                    continue
            if not target:
                console.print("[red]No identifier provided.[/]")
                continue
            _analyze(target, refresh=force)
            continue

        # Bare token → try as ticker
        console.print(f"[dim]Unknown command '{cmd}'. Trying as ticker...[/]")
        _analyze(raw, refresh=is_testing())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze(identifier: str, *, refresh: bool = False) -> None:
    from lynx_etf.core.analyzer import run_full_analysis
    from lynx_etf.display import render_full_report

    try:
        report = run_full_analysis(identifier=identifier, refresh=refresh)
    except NotAnETFError as exc:
        console.print(f"[bold red]{exc}[/]")
        return
    except ValueError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return
    except (ConnectionError, TimeoutError, OSError) as exc:
        console.print(f"[bold red]Network error:[/] {exc}")
        console.print("[dim]Check your connection and try again.[/]")
        return
    except KeyboardInterrupt:
        console.print("[dim]Analysis cancelled.[/]")
        return

    render_full_report(console, report)


def _show_cache() -> None:
    from lynx_etf.core.storage import list_cached_tickers, get_mode

    items = list_cached_tickers()
    if not items:
        console.print(f"[yellow]No cached data ({get_mode()} mode).[/]")
        return
    t = Table(title=f"Cached ETFs ({get_mode()})", border_style="cyan")
    t.add_column("Ticker", style="bold cyan")
    t.add_column("Name")
    t.add_column("Tier")
    t.add_column("Age", justify="right")
    t.add_column("Files", justify="right")
    t.add_column("Size", justify="right")
    for info in items:
        age = info.get("age_hours")
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
            info["ticker"],
            info.get("name", ""),
            info.get("tier", ""),
            age_str,
            str(info.get("files", 0)),
            f"{info.get('size_mb', 0):.1f}MB",
        )
    console.print(t)


def _show_about() -> None:
    from lynx_etf import get_about_text, get_logo_ascii

    about = get_about_text()
    logo = get_logo_ascii()
    console.print()
    if logo:
        console.print(Panel(f"[green]{logo}[/]", border_style="green"))
    console.print(Panel(
        f"[bold blue]{about['name']} v{about['version']}[/]\n"
        f"[dim]Part of {about['suite']} v{about['suite_version']}[/]\n"
        f"[dim]Released {about['year']}[/]\n\n"
        f"[bold]Developed by:[/] {about['author']}\n"
        f"[bold]Contact:[/]      {about['email']}\n"
        f"[bold]License:[/]      {about['license']}\n\n"
        f"[dim]{about['description']}[/]",
        title="[bold]About[/]",
        border_style="blue",
    ))
    console.print(Panel(
        about["license_text"],
        title="[bold]BSD 3-Clause License[/]",
        border_style="dim",
    ))
