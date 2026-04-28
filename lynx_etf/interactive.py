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

from lynx_investor_core.translations import t as _t

from lynx_etf import APP_NAME, SUITE_LABEL, __version__
from lynx_etf.core.ticker import NotAnETFError


console = Console()


def _banner() -> str:
    return (
        f"\n[bold blue]  {_t('banner_lynx_etf_analysis')}[/]\n"
        f"[dim]    {_t('tagline_costs_holdings')}[/]\n"
    )


def _menu() -> str:
    return (
        f"\n[bold cyan]{_t('menu_analysis')}[/]\n"
        f"  [bold]analyze[/] <TICKER|ISIN>           {_t('cmd_analyze_desc')}\n"
        f"  [bold]refresh[/] <TICKER|ISIN>           {_t('cmd_refresh_desc')}\n"
        f"  [bold]search[/] <query>                  {_t('cmd_search_etf_desc')}\n"
        f"\n[bold cyan]{_t('menu_cache')}[/]\n"
        f"  [bold]cache[/]                           {_t('cmd_cache_etf_desc')}\n"
        f"  [bold]drop-cache[/] <TICKER>             {_t('cmd_drop_cache_etf_desc')}\n"
        f"  [bold]drop-cache all[/]                  {_t('cmd_drop_cache_all_desc')}\n"
        f"\n[bold cyan]{_t('menu_learn')}[/]\n"
        f"  [bold]explain[/] <metric>                {_t('cmd_explain_desc')}\n"
        f"  [bold]explain-all[/]                     {_t('cmd_explain_all_desc')}\n"
        f"\n[bold cyan]{_t('menu_other')}[/]\n"
        f"  [bold]about[/]                           {_t('cmd_about_desc')}\n"
        f"  [bold]help[/]                            {_t('cmd_help_desc')}\n"
        f"  [bold]quit[/]                            {_t('cmd_quit_desc')}\n"
    )


def run_interactive(args=None) -> int:
    """Run the interactive prompt loop."""
    from lynx_etf.core.storage import get_mode, is_testing

    console.print(_banner())

    if is_testing():
        console.print(Panel(
            f"[bold yellow]{_t('testing_mode')}[/]\n"
            "Data is stored in [bold]data_test/[/] — production data is never touched.\n"
            "All fetches are fresh (cache is not used).",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            f"[bold green]{_t('production_mode')}[/]\n"
            "Data is stored in [bold]data/[/] — cached analyses are reused automatically.\n"
            "Use [bold]refresh[/] to force a fresh download.",
            border_style="green",
        ))

    console.print(Panel(_menu(), border_style="cyan", title=f"[bold]{_t('interactive_mode_title')}[/]"))

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
            console.print(f"\n[dim]{_t('goodbye')}[/]")
            return 0

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            console.print(f"[dim]{_t('goodbye')}[/]")
            return 0

        if cmd in ("help", "h", "?"):
            console.print(_menu())
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
                    target = Prompt.ask(f"[bold]{_t('ticker_to_drop_prompt')}[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print(f"[dim]{_t('cancelled')}[/]")
                    continue
            if not target:
                console.print(f"[red]{_t('no_ticker_provided')}[/]")
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
                    arg = Prompt.ask(f"[bold]{_t('search_query_prompt')}[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print(f"[dim]{_t('cancelled')}[/]")
                    continue
            if not arg:
                console.print(f"[red]{_t('no_query_provided')}[/]")
                continue
            from lynx_etf.cli import _cmd_search
            _cmd_search(arg)
            continue

        if cmd in ("analyze", "a", "refresh"):
            force = (cmd == "refresh") or is_testing()
            target = arg
            if not target:
                try:
                    target = Prompt.ask(f"[bold]{_t('enter_etf_id_prompt')}[/]")
                except (EOFError, KeyboardInterrupt):
                    console.print(f"[dim]{_t('cancelled')}[/]")
                    continue
            if not target:
                console.print(f"[red]{_t('no_identifier_provided')}[/]")
                continue
            _analyze(target, refresh=force)
            continue

        # Bare token → try as ticker
        console.print(f"[dim]{_t('unknown_command_trying').format(cmd=cmd)}[/]")
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
        console.print(f"[dim]{_t('analysis_cancelled')}[/]")
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
