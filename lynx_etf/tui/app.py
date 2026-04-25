"""Textual TUI for lynx-etf.

Mirrors the look-and-feel of ``lynx.tui.app``: house ``lynx-dark`` /
``lynx-light`` themes plus the full Suite gallery, About modal with the
shared logo, mode-aware footer, and ``t`` to cycle themes.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, Static

from lynx_investor_core.translations import t as _t

from lynx_etf import (
    APP_NAME,
    SUITE_LABEL,
    __version__,
    get_about_text,
    get_logo_ascii,
)
from lynx_etf.core.ticker import NotAnETFError
from lynx_etf.tui.themes import THEME_NAMES, register_all_themes


# ---------------------------------------------------------------------------
# About modal
# ---------------------------------------------------------------------------

class AboutModal(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss_modal", _t("tui_close"))]

    DEFAULT_CSS = """
    AboutModal {
        align: center middle;
    }
    #about-dialog {
        width: 80%;
        height: 80%;
        max-width: 110;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    #about-title {
        text-align: center;
        padding: 1 0;
    }
    #about-scroll {
        height: 1fr;
        padding: 0 1;
    }
    #about-hint {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        about = get_about_text()
        logo = get_logo_ascii()
        logo_block = f"[green]{logo}[/]\n\n" if logo else ""
        with Vertical(id="about-dialog"):
            yield Label(f"[bold blue]{about['name']}[/]", id="about-title")
            yield VerticalScroll(
                Static(
                    f"{logo_block}"
                    f"[bold blue]{about['name']} v{about['version']}[/]\n"
                    f"[dim]Part of {about['suite']} v{about['suite_version']}[/]\n"
                    f"[dim]Released {about['year']}[/]\n\n"
                    f"[bold]Developed by:[/] {about['author']}\n"
                    f"[bold]Contact:[/]      {about['email']}\n"
                    f"[bold]License:[/]      {about['license']}\n\n"
                    f"{about['description']}\n\n"
                    f"[bold cyan]BSD 3-Clause License[/]\n"
                    f"[dim]{about['license_text']}[/]",
                    id="about-content",
                ),
                id="about-scroll",
            )
            yield Label("[dim]Press Escape to close[/]", id="about-hint")

    def action_dismiss_modal(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class LynxETFApp(App):
    CSS = """
    Screen {
        background: $background;
    }
    #ticker-bar {
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    #ticker-bar > Static {
        padding: 1 1 0 1;
        color: $accent;
    }
    #output {
        padding: 1 2;
        height: 1fr;
    }
    Input {
        width: 30%;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear", _t("tui_clear")),
        Binding("a", "about", _t("btn_about")),
        Binding("t", "cycle_theme", _t("tui_theme")),
        Binding("q", "quit", _t("btn_quit")),
    ]

    def __init__(self, initial_ticker: str | None = None) -> None:
        super().__init__()
        self._initial_ticker = initial_ticker
        self._theme_idx = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="ticker-bar"):
            yield Static(f"[bold]{_t('tui_etf_ticker_label')}[/]")
            yield Input(placeholder=_t("tui_ticker_placeholder"), id="ticker")
        with VerticalScroll(id="output"):
            yield Static(
                f"[bold blue]{APP_NAME} v{__version__}[/]\n"
                f"[dim]{SUITE_LABEL}[/]\n\n"
                f"{_t('tui_intro_etf')}\n"
                "[dim]Stocks, mutual funds and index funds are rejected at the resolver level.[/]\n\n"
                f"[dim]{_t('tui_keys_help')}[/]",
                id="body",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"{APP_NAME} v{__version__}"
        self.sub_title = SUITE_LABEL

        try:
            register_all_themes(self)
        except Exception:
            pass

        # Default to the house dark theme; fall back to whatever Textual ships.
        for preferred in ("lynx-dark", "lynx-theme", "textual-dark"):
            try:
                self.theme = preferred
                if preferred in THEME_NAMES:
                    self._theme_idx = THEME_NAMES.index(preferred)
                break
            except Exception:
                continue

        if self._initial_ticker:
            inp = self.query_one("#ticker", Input)
            inp.value = self._initial_ticker
            self.call_later(self._run_analysis, self._initial_ticker)
        self.query_one("#ticker", Input).focus()

    def action_clear(self) -> None:
        self.query_one("#body", Static).update("[dim]Cleared.[/]")

    def action_about(self) -> None:
        self.push_screen(AboutModal())

    def action_cycle_theme(self) -> None:
        if not THEME_NAMES:
            return
        self._theme_idx = (self._theme_idx + 1) % len(THEME_NAMES)
        name = THEME_NAMES[self._theme_idx]
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
        body.update(Text.from_ansi(text))


def run_tui(initial_ticker: str | None = None) -> int:
    app = LynxETFApp(initial_ticker=initial_ticker)
    app.run()
    return 0


# Back-compat alias mirroring lynx-fundamental's class name.
DashboardApp = LynxETFApp
