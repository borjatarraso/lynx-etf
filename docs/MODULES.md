# Module reference

Per-file responsibilities inside the [`lynx_etf/`](../lynx_etf/) package. This is
the detailed companion to the map in [`lynx_etf/CLAUDE.md`](../lynx_etf/CLAUDE.md)
and the dataflow in [`ARCHITECTURE.md`](../ARCHITECTURE.md).

## Entry / orchestration

- **`cli.py`** — `run_cli(argv)` parses arguments and dispatches sub-commands
  (analyze, search, cache list/drop, explain, UI launchers); `build_parser`
  builds the argparse parser with argcomplete support.
- **`interactive.py`** — `run_interactive` REPL; delegates to `cli.py`
  sub-command functions.
- **`__main__.py`** — `main()`, the `lynx-etf` console-script target.
- **`__init__.py`** — package metadata (`__version__`, `APP_NAME`, …),
  `get_logo_ascii()`, `get_about_text()`.

## Schema

- **`models.py`** — all dataclasses/enums (`ETFReport`, `ETFProfile`, metric
  sections, `Verdict`, `Holding`, `NewsArticle`, `MetricExplanation`,
  `FundSizeTier`, `Relevance`) plus backward-compat aliases. No internal imports.

## `core/` — data

- **`analyzer.py`** — pipeline orchestrator: `run_full_analysis`,
  `run_progressive_analysis`, and report ↔ dict serialisation.
- **`fetcher.py`** — yfinance access: info, profile, holdings, price &
  benchmark history, sector/country/asset breakdowns.
- **`ticker.py`** — `resolve_identifier`, `is_isin`, `search_etfs`, and the
  `NotAnETFError` scope guard.
- **`storage.py`** — cache + data-directory management; production/testing mode.
- **`news.py`** — fund news from yfinance + RSS, cached to disk.

## `metrics/` — computation

- **`calculator.py`** — `calc_*` section calculators + `build_verdict` and the
  statistical helpers (see [METRICS.md](METRICS.md)).
- **`explanations.py`** — `EXPLANATIONS` catalogue, `get_explanation`,
  `by_category` (powers `--explain`).
- **`relevance.py`** — `relevance_for` / `is_critical` per `FundSizeTier`.

## Presentation

- **`display.py`** — `render_full_report`, `render_about`, per-section
  renderers, and Rich formatting helpers.
- **`passive_checklist.py`** — `run_passive_checklist`, `summarize_status`
  (Boglehead-style rule-of-thumb checks).
- **`tips.py`** — `compose_tips`, `for_passive_investor`, `UNIVERSAL_TIPS`.

## UI

- **`gui/app.py`** — `run_gui` (Tkinter).
- **`tui/app.py`** — `run_tui` (Textual).
- **`tui/themes.py`** — house + Suite theme definitions, `register_all_themes`.

## Suite glue

- **`plugin.py`** — `register()` returns a `SectorAgent` for Suite discovery.
