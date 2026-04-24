"""Textual TUI for lynx-etf.

Compact dashboard: input an ETF ticker, press Enter, see every panel
rendered in the main viewport. Suite theme switching via ``t``.
"""

from __future__ import annotations

from rich.console import Console

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from lynx_etf import APP_NAME, __version__
from lynx_etf.core.ticker import NotAnETFError


class LynxETFApp(App):
    CSS = """
    #ticker-bar { height: 3; padding: 0 1; }
    #output { padding: 1 2; height: 1fr; }
    Input { width: 30%; }
    """

    BINDINGS = [
        ("ctrl+l", "clear", "Clear"),
        ("t", "cycle_theme", "Theme"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, initial_ticker: str | None = None) -> None:
        super().__init__()
        self._initial_ticker = initial_ticker
        self._theme_names: list[str] = []
        self._theme_idx = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="ticker-bar"):
            yield Static("[bold cyan]ETF Ticker:[/]")
            yield Input(placeholder="e.g. SPY, QQQ, VTI", id="ticker")
        with VerticalScroll(id="output"):
            yield Static(
                f"[bold cyan]{APP_NAME} v{__version__}[/]\n"
                "Enter an ETF ticker or ISIN and press Enter.",
                id="body",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"{APP_NAME} v{__version__}"
        try:
            from lynx_investor_core.themes import register_suite_themes, SUITE_THEME_NAMES
            register_suite_themes(self)
            self._theme_names = list(SUITE_THEME_NAMES)
            if "lynx-theme" in self._theme_names:
                self.theme = "lynx-theme"
                self._theme_idx = self._theme_names.index("lynx-theme")
        except Exception:
            pass

        if self._initial_ticker:
            inp = self.query_one("#ticker", Input)
            inp.value = self._initial_ticker
            self.call_later(self._run_analysis, self._initial_ticker)
        self.query_one("#ticker", Input).focus()

    def action_clear(self) -> None:
        self.query_one("#body", Static).update("[dim]Cleared.[/]")

    def action_cycle_theme(self) -> None:
        if not self._theme_names:
            return
        self._theme_idx = (self._theme_idx + 1) % len(self._theme_names)
        name = self._theme_names[self._theme_idx]
        try:
            self.theme = name
            self.notify(f"Theme: {name}", timeout=2)
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        ticker = (event.value or "").strip()
        if not ticker:
            return
        await self._run_analysis(ticker)

    async def _run_analysis(self, ticker: str) -> None:
        body = self.query_one("#body", Static)
        body.update(f"[cyan]Analysing {ticker}...[/]")

        def _do():
            from lynx_etf.core.analyzer import run_full_analysis
            from lynx_etf.display import render_full_report
            console = Console(record=True, width=120)
            try:
                report = run_full_analysis(identifier=ticker)
            except NotAnETFError as exc:
                return f"[bold red]{exc}[/]"
            except ValueError as exc:
                return f"[bold red]Error:[/] {exc}"
            render_full_report(console, report)
            return console.export_text(clear=True, styles=True)

        text = await self.run_worker(_do, thread=True).wait()
        # Rich export includes ANSI; Static does not re-interpret ANSI but
        # rich markup is OK. Use plain text but render as Rich renderable.
        from rich.text import Text
        body.update(Text.from_ansi(text))


def run_tui(initial_ticker: str | None = None) -> int:
    app = LynxETFApp(initial_ticker=initial_ticker)
    app.run()
    return 0
