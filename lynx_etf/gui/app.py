"""Tkinter GUI for lynx-etf.

Compact but fully functional:
 - Entry field for ticker / ISIN
 - Analyse button that runs the full pipeline in a worker thread
 - Scrollable result pane with every section rendered as plain text
 - Themes menu driven by lynx_investor_core.gui_themes
 - About dialog
"""

from __future__ import annotations

import io
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from lynx_etf import APP_NAME, SUITE_LABEL, __author__, __version__, __year__


def run_gui(initial_ticker: str | None = None) -> int:
    root = tk.Tk()
    root.title(f"{APP_NAME} v{__version__}")
    root.geometry("1100x750")

    try:
        from lynx_investor_core.gui_themes import apply_theme, ThemeCycler
        cycler = ThemeCycler(root, start="lynx-theme")
    except Exception:
        cycler = None
        apply_theme = None  # type: ignore[assignment]

    state = {"busy": False, "q": queue.Queue()}

    # ── Menu ────────────────────────────────────────────────────────────
    menubar = tk.Menu(root)

    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="About", command=lambda: _about_dialog(root))
    file_menu.add_separator()
    file_menu.add_command(label="Quit", command=root.quit, accelerator="Ctrl+Q")
    menubar.add_cascade(label="File", menu=file_menu)

    theme_menu = tk.Menu(menubar, tearoff=0)
    if cycler:
        try:
            from lynx_investor_core.gui_themes import SUITE_GUI_THEMES
            for name in SUITE_GUI_THEMES:
                theme_menu.add_command(
                    label=name,
                    command=lambda n=name: cycler.set(n) if hasattr(cycler, "set") else None,
                )
        except Exception:
            pass
    menubar.add_cascade(label="Themes", menu=theme_menu)
    root.config(menu=menubar)

    # ── Top bar ─────────────────────────────────────────────────────────
    top = ttk.Frame(root, padding=8)
    top.pack(fill=tk.X)

    ttk.Label(top, text="ETF Ticker or ISIN:").pack(side=tk.LEFT, padx=(0, 8))
    ticker_var = tk.StringVar(value=initial_ticker or "")
    ticker_entry = ttk.Entry(top, textvariable=ticker_var, width=30)
    ticker_entry.pack(side=tk.LEFT, padx=(0, 8))

    analyze_btn = ttk.Button(top, text="Analyse")
    analyze_btn.pack(side=tk.LEFT)

    status_var = tk.StringVar(value="Ready.")
    ttk.Label(top, textvariable=status_var, foreground="#888").pack(side=tk.LEFT, padx=12)

    # ── Output pane ─────────────────────────────────────────────────────
    out = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 10))
    out.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
    out.configure(state=tk.DISABLED)

    def _write(text: str) -> None:
        out.configure(state=tk.NORMAL)
        out.delete("1.0", tk.END)
        out.insert(tk.END, text)
        out.configure(state=tk.DISABLED)

    # ── Analysis driver ────────────────────────────────────────────────
    def _analyze():
        ticker = ticker_var.get().strip()
        if not ticker:
            return
        if state["busy"]:
            return
        state["busy"] = True
        analyze_btn.state(["disabled"])
        status_var.set(f"Analysing {ticker}...")

        def _worker():
            try:
                from rich.console import Console
                from lynx_etf.core.analyzer import run_full_analysis
                from lynx_etf.core.ticker import NotAnETFError
                from lynx_etf.display import render_full_report

                buf = io.StringIO()
                console = Console(file=buf, width=120, force_terminal=False)
                try:
                    report = run_full_analysis(identifier=ticker)
                except NotAnETFError as exc:
                    state["q"].put(("error", f"{exc}"))
                    return
                except ValueError as exc:
                    state["q"].put(("error", f"{exc}"))
                    return

                render_full_report(console, report)
                state["q"].put(("ok", buf.getvalue()))
            except Exception as exc:  # noqa: BLE001
                state["q"].put(("error", f"{type(exc).__name__}: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _drain_queue():
        try:
            while True:
                kind, payload = state["q"].get_nowait()
                if kind == "ok":
                    _write(payload)
                    status_var.set("Done.")
                else:
                    _write(f"Error:\n\n{payload}")
                    status_var.set("Error.")
                state["busy"] = False
                analyze_btn.state(["!disabled"])
        except queue.Empty:
            pass
        root.after(120, _drain_queue)

    analyze_btn.configure(command=_analyze)
    ticker_entry.bind("<Return>", lambda e: _analyze())
    root.bind_all("<Control-q>", lambda e: root.quit())

    if initial_ticker:
        root.after(200, _analyze)

    root.after(120, _drain_queue)
    ticker_entry.focus_set()
    root.mainloop()
    return 0


def _about_dialog(root: tk.Tk) -> None:
    messagebox.showinfo(
        "About",
        f"{APP_NAME} v{__version__}\n"
        f"{SUITE_LABEL}\n\n"
        "Exchange-Traded Fund analysis — costs, holdings, allocation, "
        "performance, risk.\n\n"
        f"© {__year__} {__author__}\n"
        "BSD-3-Clause",
        parent=root,
    )
