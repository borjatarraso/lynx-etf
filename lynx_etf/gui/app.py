"""Tkinter graphical user interface for Lynx ETF Analysis.

Mirrors the visual identity of ``lynx-fundamental``: Catppuccin Mocha
palette, splash screen, themed buttons, themed scrolled output, About
dialog with the shared PNG / ASCII logo, and Suite-wide theme cycling
via ``lynx_investor_core.gui_themes``.
"""

from __future__ import annotations

import io
import os
import platform as _plat
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from lynx_investor_core.translations import t as _t

from lynx_etf import (
    APP_NAME,
    SUITE_LABEL,
    SUITE_NAME,
    SUITE_VERSION,
    __author__,
    __author_email__,
    __license__,
    __version__,
    __year__,
    get_about_text,
    get_logo_ascii,
)

# ---------------------------------------------------------------------------
# Colour palette (Catppuccin Mocha) — matches lynx-fundamental.
# ---------------------------------------------------------------------------
BG = "#1e1e2e"
BG_SURFACE = "#232336"
BG_CARD = "#2a2a3d"
BG_INPUT = "#313147"
BG_HOVER = "#3b3b54"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
FG_SUBTLE = "#585b70"
ACCENT = "#89b4fa"
ACCENT_DIM = "#5a7ec2"
LAVENDER = "#b4befe"
BORDER = "#45475a"
BORDER_LIGHT = "#585b70"
BTN_BG = "#89b4fa"
BTN_FG = "#1e1e2e"
BTN_ACTIVE = "#74c7ec"
BTN_SECONDARY_BG = "#45475a"
BTN_SECONDARY_FG = "#cdd6f4"
BTN_DANGER_BG = "#f38ba8"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
ORANGE = "#fab387"
TEAL = "#94e2d5"
MAUVE = "#cba6f7"
SKY = "#89dceb"

# Unicode glyphs
DIAMOND = "\u25c6"
BULLET = "\u2022"
CHART = "\u2587"

# Fonts
if _plat.system() == "Windows":
    _FAMILY = "Segoe UI"
    _MONO = "Consolas"
elif _plat.system() == "Darwin":
    _FAMILY = "Helvetica"
    _MONO = "Menlo"
else:
    _FAMILY = "Noto Sans"
    _MONO = "Noto Sans Mono"

FONT = (_FAMILY, 11)
FONT_BOLD = (_FAMILY, 11, "bold")
FONT_SMALL = (_FAMILY, 10)
FONT_TITLE = (_FAMILY, 22, "bold")
FONT_SUBTITLE = (_FAMILY, 12)
FONT_SECTION = (_FAMILY, 13, "bold")
FONT_MONO = (_MONO, 10)
FONT_SPLASH_TITLE = (_FAMILY, 36, "bold")
FONT_SPLASH_SUB = (_FAMILY, 14)
FONT_SPLASH_VER = (_FAMILY, 11)
FONT_BTN = (_FAMILY, 10, "bold")

# Image paths
_IMG_DIR = Path(__file__).resolve().parent.parent.parent / "img"
_LOGO_SM = _IMG_DIR / "logo_sm_quarter_green.png"
_LOGO_MD = _IMG_DIR / "logo_sm_green.png"


# ---------------------------------------------------------------------------
# Splash screen
# ---------------------------------------------------------------------------

class SplashScreen:
    """Animated splash shown at startup. Mirrors lynx-fundamental's splash."""

    def __init__(self, root: tk.Tk, on_done) -> None:
        self.root = root
        self.on_done = on_done
        self.frame = tk.Frame(root, bg=BG)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.frame.lift()

        center = tk.Frame(self.frame, bg=BG)
        center.place(relx=0.5, rely=0.4, anchor=tk.CENTER)

        logo_text = f"{DIAMOND}  {DIAMOND}  {DIAMOND}"
        tk.Label(center, text=logo_text, font=(_FAMILY, 28),
                 bg=BG, fg=ACCENT).pack(pady=(0, 12))

        tk.Label(center, text="LYNX", font=FONT_SPLASH_TITLE,
                 bg=BG, fg=FG).pack(pady=(0, 2))

        tk.Label(center, text=_t("hero_subtitle_etf"), font=FONT_SPLASH_SUB,
                 bg=BG, fg=ACCENT).pack(pady=(0, 20))

        tk.Label(center,
                 text=_t("tagline_costs_holdings_amp"),
                 font=FONT_SMALL, bg=BG, fg=FG_DIM).pack(pady=(0, 30))

        tk.Label(
            center,
            text=f"v{__version__}  {BULLET}  {__year__}  {BULLET}  {__author__}",
            font=FONT_SPLASH_VER, bg=BG, fg=FG_SUBTLE,
        ).pack(pady=(0, 4))

        tk.Label(center, text=SUITE_LABEL,
                 font=FONT_SPLASH_VER, bg=BG, fg=FG_SUBTLE).pack(pady=(0, 40))

        self.bar_frame = tk.Frame(center, bg=BORDER, height=3, width=260)
        self.bar_frame.pack(pady=(0, 8))
        self.bar_frame.pack_propagate(False)
        self.bar_fill = tk.Frame(self.bar_frame, bg=ACCENT, height=3, width=0)
        self.bar_fill.place(x=0, y=0, relheight=1)

        self.loading = tk.Label(center, text=_t("loading"), font=FONT_SMALL,
                                bg=BG, fg=FG_DIM)
        self.loading.pack()

        self._progress = 0
        self._animate()

    def _animate(self) -> None:
        self._progress = min(100, self._progress + 8)
        self.bar_fill.place(x=0, y=0, relheight=1,
                            width=int(260 * self._progress / 100))
        if self._progress >= 100:
            self.root.after(200, self._fade_out)
        else:
            self.root.after(35, self._animate)

    def _fade_out(self) -> None:
        try:
            self.frame.destroy()
        except tk.TclError:
            pass
        if self.on_done:
            self.on_done()


# ---------------------------------------------------------------------------
# Style application
# ---------------------------------------------------------------------------

def _apply_style(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Lock active/pressed states so buttons never go white-on-white.
    style.configure(
        "Lynx.TButton",
        background=BTN_BG, foreground=BTN_FG,
        font=FONT_BTN, borderwidth=0, padding=(12, 6),
        relief="flat",
    )
    style.map(
        "Lynx.TButton",
        background=[("active", BTN_ACTIVE), ("pressed", BTN_ACTIVE)],
        foreground=[("active", BTN_FG), ("pressed", BTN_FG)],
    )
    style.configure(
        "Subtle.TButton",
        background=BTN_SECONDARY_BG, foreground=BTN_SECONDARY_FG,
        font=FONT_BTN, borderwidth=0, padding=(10, 5),
        relief="flat",
    )
    style.map(
        "Subtle.TButton",
        background=[("active", BORDER_LIGHT), ("pressed", BORDER_LIGHT)],
        foreground=[("active", FG), ("pressed", FG)],
    )
    style.configure("Lynx.TEntry",
                    fieldbackground=BG_INPUT, background=BG_INPUT,
                    foreground=FG, insertcolor=FG, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, padding=4)
    style.configure("Lynx.TFrame", background=BG)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Surface.TFrame", background=BG_SURFACE)
    style.configure("Lynx.TLabel", background=BG, foreground=FG, font=FONT)
    style.configure("Card.TLabel", background=BG_CARD, foreground=FG, font=FONT)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
    style.configure("Sub.TLabel", background=BG, foreground=ACCENT, font=FONT_SUBTITLE)
    style.configure("Dim.TLabel", background=BG, foreground=FG_DIM, font=FONT_SMALL)

    # Root + Tk options
    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox*Background", BG_INPUT)
    root.option_add("*TCombobox*Listbox*Foreground", FG)
    return style


# ---------------------------------------------------------------------------
# Main GUI
# ---------------------------------------------------------------------------

def run_gui(args=None, *, initial_ticker: str | None = None) -> int:
    """Launch the Tkinter GUI for Lynx ETF.

    *args* is the parsed argparse namespace from the CLI (so we can read
    ``--no-news`` / ``--refresh`` / pre-filled identifier).  *initial_ticker*
    is a back-compat shim used by older test fixtures.
    """
    if initial_ticker is None and args is not None:
        initial_ticker = getattr(args, "identifier", None)

    root = tk.Tk()
    root.title(f"{APP_NAME} v{__version__}")
    root.geometry("1100x750")
    root.minsize(900, 600)

    _apply_style(root)

    # Suite theme cycler — keeps ETF in lockstep with the rest of the Suite.
    try:
        from lynx_investor_core.gui_themes import ThemeCycler, SUITE_GUI_THEMES, apply_theme
        # Register user-saved lynx_theme JSON themes (~/.config/lynx-theme)
        try:
            from lynx_theme.storage import register_user_themes as _reg_user_themes
            _reg_user_themes()
        except Exception:
            pass
        cycler = ThemeCycler(root, start="lynx-theme")
        try:
            apply_theme(root, theme="lynx-theme")
        except Exception:
            pass
    except Exception:
        cycler = None
        SUITE_GUI_THEMES = []
        apply_theme = None  # type: ignore[assignment]

    state = {"busy": False, "q": queue.Queue(), "report": None}

    # ── Menu ────────────────────────────────────────────────────────────
    menubar = tk.Menu(root, bg=BG_SURFACE, fg=FG, activebackground=ACCENT,
                      activeforeground=BTN_FG, tearoff=0)
    file_menu = tk.Menu(menubar, tearoff=0, bg=BG_SURFACE, fg=FG,
                        activebackground=ACCENT, activeforeground=BTN_FG)
    file_menu.add_command(label=_t("btn_about"), command=lambda: _show_about_dialog(root))
    file_menu.add_separator()
    file_menu.add_command(label=_t("btn_quit"), command=root.quit, accelerator="Ctrl+Q")
    menubar.add_cascade(label=_t("menu_file"), menu=file_menu)

    theme_menu = tk.Menu(menubar, tearoff=0, bg=BG_SURFACE, fg=FG,
                         activebackground=ACCENT, activeforeground=BTN_FG)
    if cycler is not None:
        for name in (SUITE_GUI_THEMES or []):
            theme_menu.add_command(
                label=name,
                command=lambda n=name: cycler.set(n) if hasattr(cycler, "set") else None,
            )
    menubar.add_cascade(label=_t("menu_themes"), menu=theme_menu)
    root.config(menu=menubar)

    # ── Hero ────────────────────────────────────────────────────────────
    hero = ttk.Frame(root, style="Lynx.TFrame", padding=(16, 14, 16, 8))
    hero.pack(fill=tk.X)

    logo_img = None
    if _LOGO_SM.exists():
        try:
            logo_img = tk.PhotoImage(file=str(_LOGO_SM))
            logo_lbl = tk.Label(hero, image=logo_img, bg=BG, borderwidth=0)
            logo_lbl.image = logo_img  # keep ref
            logo_lbl.pack(side=tk.LEFT, padx=(0, 14))
        except tk.TclError:
            logo_img = None

    titles = ttk.Frame(hero, style="Lynx.TFrame")
    titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Label(titles, text="Lynx ETF", style="Title.TLabel").pack(anchor=tk.W)
    ttk.Label(titles, text=_t("hero_subtitle_etf"),
              style="Sub.TLabel").pack(anchor=tk.W)
    ttk.Label(titles,
              text=f"v{__version__}  {BULLET}  {SUITE_LABEL}",
              style="Dim.TLabel").pack(anchor=tk.W, pady=(2, 0))

    quit_btn = ttk.Button(hero, text=_t("btn_quit"), style="Subtle.TButton",
                          command=root.quit)
    quit_btn.pack(side=tk.RIGHT, padx=(8, 0))

    # ── Search bar ──────────────────────────────────────────────────────
    bar = ttk.Frame(root, style="Lynx.TFrame", padding=(16, 4, 16, 8))
    bar.pack(fill=tk.X)

    ttk.Label(bar, text=f"{_t('ticker_or_isin')}:", style="Lynx.TLabel").pack(
        side=tk.LEFT, padx=(0, 8))

    ticker_var = tk.StringVar(value=initial_ticker or "")
    entry = ttk.Entry(bar, textvariable=ticker_var, width=28,
                      style="Lynx.TEntry", font=FONT)
    entry.pack(side=tk.LEFT, padx=(0, 8))

    analyze_btn = ttk.Button(bar, text=_t("btn_analyse"), style="Lynx.TButton")
    analyze_btn.pack(side=tk.LEFT, padx=(0, 4))

    refresh_btn = ttk.Button(bar, text=_t("btn_refresh"), style="Subtle.TButton")
    refresh_btn.pack(side=tk.LEFT, padx=(0, 4))

    export_btn = ttk.Button(bar, text=_t("btn_export"), style="Subtle.TButton")
    export_btn.pack(side=tk.LEFT, padx=(0, 12))

    status_var = tk.StringVar(value=_t("ready_"))
    status_lbl = tk.Label(bar, textvariable=status_var, bg=BG, fg=FG_DIM,
                          font=FONT_SMALL)
    status_lbl.pack(side=tk.LEFT, padx=(8, 0))

    # ── Output ──────────────────────────────────────────────────────────
    out_wrap = tk.Frame(root, bg=BG)
    out_wrap.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

    out = tk.Text(out_wrap, wrap=tk.WORD, font=FONT_MONO,
                  bg=BG_CARD, fg=FG, insertbackground=FG,
                  selectbackground=ACCENT, selectforeground=BTN_FG,
                  borderwidth=0, padx=14, pady=10)
    sb = ttk.Scrollbar(out_wrap, orient=tk.VERTICAL, command=out.yview)
    out.configure(yscrollcommand=sb.set, state=tk.DISABLED)
    out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)

    # Tag styling so rich-rendered ANSI / markup colours degrade gracefully.
    out.tag_configure("ok", foreground=GREEN)
    out.tag_configure("err", foreground=RED)
    out.tag_configure("dim", foreground=FG_DIM)
    out.tag_configure("accent", foreground=ACCENT)

    welcome = (
        f"{APP_NAME} v{__version__}\n"
        f"{SUITE_LABEL}\n\n"
        f"{_t('welcome_etf_panel')}\n"
    )

    def _write(text: str, tag: str | None = None) -> None:
        out.configure(state=tk.NORMAL)
        out.delete("1.0", tk.END)
        if tag:
            out.insert(tk.END, text, tag)
        else:
            out.insert(tk.END, text)
        out.configure(state=tk.DISABLED)

    _write(welcome, "dim")

    # ── Analysis driver ────────────────────────────────────────────────
    def _start(refresh: bool = False) -> None:
        ticker = ticker_var.get().strip()
        if not ticker or state["busy"]:
            return
        state["busy"] = True
        analyze_btn.state(["disabled"])
        refresh_btn.state(["disabled"])
        status_var.set(_t("status_analysing").format(ticker=ticker))
        status_lbl.configure(fg=ACCENT)

        no_news = bool(getattr(args, "no_news", False))

        def _worker():
            try:
                from rich.console import Console
                from lynx_etf.core.analyzer import run_full_analysis
                from lynx_etf.core.ticker import NotAnETFError
                from lynx_etf.display import render_full_report

                buf = io.StringIO()
                console = Console(file=buf, width=120, force_terminal=False)
                try:
                    report = run_full_analysis(
                        identifier=ticker,
                        download_news=not no_news,
                        refresh=refresh,
                    )
                except NotAnETFError as exc:
                    state["q"].put(("error", str(exc)))
                    return
                except ValueError as exc:
                    state["q"].put(("error", str(exc)))
                    return

                render_full_report(console, report)
                state["q"].put(("ok", buf.getvalue(), report))
            except Exception as exc:  # noqa: BLE001
                state["q"].put(("error", f"{type(exc).__name__}: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _drain():
        try:
            while True:
                payload = state["q"].get_nowait()
                kind = payload[0]
                if kind == "ok":
                    text = payload[1]
                    state["report"] = payload[2] if len(payload) > 2 else None
                    _write(text)
                    status_var.set(_t("status_done"))
                    status_lbl.configure(fg=GREEN)
                else:
                    _write(f"{_t('status_error_label')}\n\n{payload[1]}", "err")
                    status_var.set(_t("status_error_short"))
                    status_lbl.configure(fg=RED)
                state["busy"] = False
                analyze_btn.state(["!disabled"])
                refresh_btn.state(["!disabled"])
        except queue.Empty:
            pass
        root.after(120, _drain)

    def _export():
        report = state.get("report")
        if not report:
            messagebox.showinfo(_t("btn_export"), _t("export_run_first"), parent=root)
            return
        path = filedialog.asksaveasfilename(
            parent=root,
            title=_t("dialog_export_etf_title"),
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("HTML", "*.html"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            from rich.console import Console
            from lynx_etf.display import render_full_report
            buf = io.StringIO()
            console = Console(file=buf, width=120, force_terminal=False)
            render_full_report(console, report)
            text = buf.getvalue()
            ext = os.path.splitext(path)[1].lower()
            if ext in (".html", ".htm"):
                text = (
                    f"<html><head><meta charset='utf-8'>"
                    f"<title>{APP_NAME} — {report.profile.ticker}</title></head>"
                    f"<body style='background:{BG};color:{FG};font-family:monospace;'>"
                    f"<pre>{text}</pre></body></html>"
                )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            messagebox.showinfo(_t("btn_export"),
                                _t("export_saved_to_path").format(path=path),
                                parent=root)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(_t("btn_export"),
                                 _t("export_failed").format(err=exc),
                                 parent=root)

    analyze_btn.configure(command=lambda: _start(refresh=False))
    refresh_btn.configure(command=lambda: _start(refresh=True))
    export_btn.configure(command=_export)
    entry.bind("<Return>", lambda _e: _start(False))
    root.bind_all("<Control-q>", lambda _e: root.quit())
    root.bind_all("<Control-r>", lambda _e: _start(True))

    # ── Splash ──────────────────────────────────────────────────────────
    def _after_splash():
        entry.focus_set()
        if initial_ticker:
            root.after(150, lambda: _start(False))

    if os.environ.get("LYNX_NO_SPLASH") == "1":
        _after_splash()
    else:
        SplashScreen(root, on_done=_after_splash)

    root.after(120, _drain)
    # Bottom-right language toggle (US/ES/IT/DE/FR/FA).
    try:
        from lynx_investor_core.lang_widget import mount_tk_language_button
        mount_tk_language_button(root)
    except ImportError:
        pass

    root.mainloop()
    return 0


# ---------------------------------------------------------------------------
# About dialog
# ---------------------------------------------------------------------------

def _show_about_dialog(parent: tk.Tk) -> None:
    win = tk.Toplevel(parent)
    win.title(f"{_t('dialog_about_title')} — {APP_NAME}")
    win.configure(bg=BG)
    win.transient(parent)
    win.geometry("680x540")

    about = get_about_text()
    logo_ascii = get_logo_ascii()

    logo_img = None
    if _LOGO_MD.exists():
        try:
            logo_img = tk.PhotoImage(file=str(_LOGO_MD))
            tk.Label(win, image=logo_img, bg=BG, borderwidth=0).pack(pady=(18, 6))
        except tk.TclError:
            logo_img = None

    if not logo_img and logo_ascii:
        tk.Label(win, text=logo_ascii, font=(_MONO, 9),
                 bg=BG, fg=GREEN, justify=tk.LEFT).pack(pady=(18, 6))

    tk.Label(win, text=f"{about['name']} v{about['version']}",
             font=(_FAMILY, 16, "bold"), bg=BG, fg=ACCENT).pack(pady=(6, 0))
    tk.Label(win, text=_t("part_of_suite").format(suite=about['suite']) + f" v{about['suite_version']}",
             font=FONT_SMALL, bg=BG, fg=FG_DIM).pack()
    tk.Label(win, text=_t("released_year").format(year=about['year']),
             font=FONT_SMALL, bg=BG, fg=FG_DIM).pack(pady=(0, 12))

    info = tk.Frame(win, bg=BG)
    info.pack(padx=24, pady=4, fill=tk.X)
    tk.Label(info, text=_t("developed_by_label"),
             font=FONT_BOLD, bg=BG, fg=FG, anchor=tk.W).grid(row=0, column=0, sticky=tk.W)
    tk.Label(info, text=about['author'],
             font=FONT, bg=BG, fg=FG, anchor=tk.W).grid(row=0, column=1, sticky=tk.W, padx=(8, 0))
    tk.Label(info, text=_t("contact_label"),
             font=FONT_BOLD, bg=BG, fg=FG, anchor=tk.W).grid(row=1, column=0, sticky=tk.W)
    tk.Label(info, text=about['email'],
             font=FONT, bg=BG, fg=FG, anchor=tk.W).grid(row=1, column=1, sticky=tk.W, padx=(8, 0))
    tk.Label(info, text=_t("license_label"),
             font=FONT_BOLD, bg=BG, fg=FG, anchor=tk.W).grid(row=2, column=0, sticky=tk.W)
    tk.Label(info, text=about['license'],
             font=FONT, bg=BG, fg=FG, anchor=tk.W).grid(row=2, column=1, sticky=tk.W, padx=(8, 0))

    desc = tk.Label(win, text=about['description'], font=FONT_SMALL,
                    bg=BG, fg=FG_DIM, wraplength=620, justify=tk.LEFT)
    desc.pack(padx=24, pady=(14, 8), fill=tk.X)

    btn = ttk.Button(win, text=_t("close"), style="Lynx.TButton",
                     command=win.destroy)
    btn.pack(pady=(8, 18))

    if logo_img:
        win._logo_ref = logo_img  # keep alive
    win.bind("<Escape>", lambda _e: win.destroy())
    win.focus_set()


# Back-compat for older callers that imported the private name.
_about_dialog = _show_about_dialog
