# Architecture

A one-page tour of how `lynx-etf` is put together. Code lives in the
[`lynx_etf/`](lynx_etf/) package; this document describes how its parts relate.
For per-area detail see [`lynx_etf/CLAUDE.md`](lynx_etf/CLAUDE.md).

## Layers

The package is split into layers with a one-way dependency direction:

```
            ┌──────────────────────────────────────────────┐
 entry  →   │  cli.py · interactive.py · __main__.py        │
            └───────────────┬──────────────────────────────┘
                            │ launches
            ┌───────────────┴──────────────────────────────┐
 UI     →   │  gui/app.py   tui/app.py (+ tui/themes.py)    │
            └───────────────┬──────────────────────────────┘
                            │ calls run_full_analysis()
 data   →   ┌───────────────┴──────────────────────────────┐
            │  core/analyzer.py  ── orchestrator            │
            │     ├─ core/ticker.py    resolve + ETF guard  │
            │     ├─ core/fetcher.py   yfinance fetch        │
            │     ├─ core/news.py      news fetch/cache      │
            │     └─ core/storage.py   cache (data/ vs test) │
            └───────────────┬──────────────────────────────┘
                            │ raw data
 metrics →  ┌───────────────┴──────────────────────────────┐
            │  metrics/calculator.py  calc_* + build_verdict│
            │  metrics/explanations.py  metric reference     │
            │  metrics/relevance.py     per-tier relevance   │
            └───────────────┬──────────────────────────────┘
                            │ ETFReport (dataclasses)
 present →  ┌───────────────┴──────────────────────────────┐
            │  display.py · passive_checklist.py · tips.py  │
            └──────────────────────────────────────────────┘

 schema  →  models.py  — dataclasses shared by every layer (imports nothing)
```

`models.py` is the spine: every layer exchanges the dataclasses defined there
(`ETFReport`, `ETFProfile`, `CostMetrics`, `Verdict`, …). It has no internal
dependencies, so it can be read first to understand the whole shape.

## Dataflow (one analysis)

1. **Resolve** — `core/ticker.resolve_identifier` turns a ticker/ISIN into a
   canonical ticker and confirms it is an ETF (else `NotAnETFError`).
2. **Cache check** — `core/analyzer.run_full_analysis` asks `core/storage`
   whether a fresh cached report exists; if so it deserialises and returns it
   (unless `refresh=True`).
3. **Fetch** — on a miss, `core/fetcher` pulls info, profile, holdings, price
   history, benchmark history, and sector/country/asset breakdowns from
   yfinance; `core/news` pulls fund news.
4. **Compute** — `metrics/calculator.calc_costs/income/liquidity/performance/
   allocation/risk` build the metric dataclasses, then `build_verdict` scores
   five categories into a 0–100 `Verdict`.
5. **Enrich** — `passive_checklist.run_passive_checklist` and `tips.compose_tips`
   attach rule-of-thumb checks and educational tips.
6. **Persist** — the assembled `ETFReport` is cached via `core/storage`.
7. **Render** — `display.render_full_report` (console), or the GUI/TUI, present
   it. `--explain` instead reads `metrics/explanations`.

`run_progressive_analysis` performs the same pipeline with an `on_progress`
callback so the GUI/TUI can update incrementally.

## Entry points

- **Console script** `lynx-etf` → `lynx_etf.__main__:main` → `cli.run_cli`.
- **Module** `python -m lynx_etf` → same path.
- **Root wrapper** `lynx-etf.py` → `cli.run_cli` (for running from a checkout).
- **Suite plugin** `lynx_investor_suite.agents.etf` → `plugin.register`, so the
  broader Lince Investor Suite can discover this agent.

## External dependencies

- **`lynx-investor-core`** — Suite shared code: identifier resolver,
  `translations.t()` (i18n), themes, plugin base classes, debounce helpers.
- **`yfinance`** — prices, fund info, holdings, allocation, ISIN→ticker search.
- **`feedparser` / `beautifulsoup4` / `requests`** — fund news (Yahoo + RSS).
- **`pandas` / `numpy`** — time-series and concentration maths in `metrics/`.
- **`rich`** — console rendering; **`textual`** — TUI; **`tkinter`** — GUI.
- **`weasyprint`** (optional, `pdf` extra) — PDF export.

## Caching model

Two isolated cache roots keep real and test data apart: `data/` (production,
selected by the `-p` flag) and `data_test/` (default). All reads/writes go
through `core/storage.py`. Details in [`docs/CACHING.md`](docs/CACHING.md).
