# CLAUDE.md — `lynx_etf` package

Scoped guidance for the application package. For project-wide commands and
conventions see the [root CLAUDE.md](../CLAUDE.md); for the dataflow picture see
[ARCHITECTURE.md](../ARCHITECTURE.md).

## Responsibility

Everything that turns an ETF identifier (ticker or ISIN) into a scored,
rendered analysis. Organised in layers; each loose top-level module and each
sub-package owns one slice.

## Internal module map

| Area | Files | Owns |
|------|-------|------|
| **Entry / orchestration** | `cli.py`, `interactive.py`, `__main__.py` | Argument parsing, sub-command dispatch, the REPL. |
| **Schema** | `models.py` | All dataclasses/enums passed between layers. No logic, no imports from siblings. |
| **Data (`core/`)** | `analyzer.py`, `fetcher.py`, `ticker.py`, `storage.py`, `news.py` | Identifier resolution, yfinance fetching, cache persistence, news, and the analysis pipeline. |
| **Metrics (`metrics/`)** | `calculator.py`, `explanations.py`, `relevance.py` | Pure computation of metric sections + the verdict; metric explanations; per-tier relevance. |
| **Presentation** | `display.py`, `passive_checklist.py`, `tips.py` | Rich console rendering, Boglehead-style checklist, educational tips. |
| **UI (`gui/`, `tui/`)** | `gui/app.py`, `tui/app.py`, `tui/themes.py` | Tkinter GUI and Textual TUI front-ends. |
| **Suite glue** | `plugin.py`, `__init__.py` | Plugin registration + package metadata / About text. |

Sub-package `__init__.py` files are intentionally empty — import members by
their full path (`from lynx_etf.core.analyzer import run_full_analysis`), not
via package re-exports.

## Public interface (the stable contract)

- **CLI:** `cli.run_cli(argv=None) -> int`; `__main__.main()` (console script).
- **Plugin:** `plugin.register()` (entry point `lynx_investor_suite.agents.etf`).
- **Programmatic:** `core.analyzer.run_full_analysis(identifier, download_news=True, refresh=False) -> ETFReport`
  and `core.analyzer.run_progressive_analysis(...)`.
- **Resolution:** `core.ticker.resolve_identifier`, `search_etfs`, `NotAnETFError`.
- **Metrics:** `metrics.calculator.calc_*` + `build_verdict`; `metrics.explanations.get_explanation` / `by_category`.
- **Rendering:** `display.render_full_report(console, report)`, `display.render_about(console)`.
- Package metadata: `__version__`, `APP_NAME`, `get_about_text()`, `get_logo_ascii()`.

## Module-local conventions

- **Dependency direction is one-way:** UI/entry → presentation → metrics →
  core → `models`. `models.py` imports nothing from the package; don't add
  cycles. `metrics/` and `core/` must not import from `display.py`, `gui/`, or
  `tui/`.
- **`analyzer.py` is the only orchestrator.** Front-ends (`cli`, `interactive`,
  `gui`, `tui`) call `run_full_analysis` / `run_progressive_analysis`; they
  don't call `fetcher`/`calculator` directly.
- **Cache-first:** analysis reads from cache unless `refresh=True`. Cache
  read/write lives only in `core/storage.py`; route all persistence through it
  and respect production (`data/`) vs testing (`data_test/`) mode.
- **`interactive.py` reuses `cli.py` sub-commands** (`_cmd_search`,
  `_cmd_explain`, …) — extend the CLI command and the REPL inherits it.
- **New metrics:** add the field to the relevant dataclass in `models.py`,
  compute it in `metrics/calculator.py`, add an entry to
  `metrics/explanations.py`, then render it in `display.py`.
- **User-facing text → `t()`** (`lynx_investor_core.translations`); never
  hardcode English in report/UI strings.
