# CLAUDE.md — lynx-etf

Project-level guidance for agents working in this repo. Keep it terse;
deeper detail lives in the linked files.

## Purpose

**Lynx ETF** analyses Exchange-Traded Funds — costs, income, size/liquidity,
performance, allocation, holdings, and risk — and emits a 0–100 scored
verdict. It is part of the **Lince Investor Suite** and depends on the shared
`lynx-investor-core` package.

Scope is **ETFs only**. Stocks, mutual funds, closed-end funds, and index
funds are rejected at the resolver level (`NotAnETFError`). See
[`lynx_etf/core/ticker.py`](lynx_etf/core/ticker.py).

## Top-level layout

| Path | What it is |
|------|------------|
| `lynx_etf/` | The Python package — all application code. See [`lynx_etf/CLAUDE.md`](lynx_etf/CLAUDE.md). |
| `tests/` | Pytest suite (one `test_*.py` per area). |
| `docs/` | Reference pages — see [`docs/`](docs/). |
| `img/` | Logos (ASCII + PNG). Do not re-encode the PNGs (see README). |
| `lynx-etf.py` | Thin root wrapper → `lynx_etf.cli:run_cli()`. |
| `pyproject.toml` | Packaging, deps, console-script and Suite plugin entry points. |
| `ARCHITECTURE.md` | How the internal modules fit together + dataflow. |
| `DESIGN.md` | Design decisions and why they are the way they are. |

The package is internally modularised into `core/`, `metrics/`, `gui/`, `tui/`
plus a thin orchestration/presentation layer of loose modules. The full map is
in [`lynx_etf/CLAUDE.md`](lynx_etf/CLAUDE.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Build / test / run

```bash
pip install -e .                 # install (editable), pulls lynx-investor-core
pytest                           # run the suite (config in pyproject.toml)
pytest tests/test_calculator.py  # run one file

lynx-etf -p SPY                  # console analysis (cache-first)
lynx-etf -p QQQ --refresh        # force fresh data
lynx-etf -p -i                   # interactive REPL
lynx-etf -p -tui                 # Textual TUI
lynx-etf -p -x                   # Tkinter GUI
lynx-etf --explain expense_ratio # explain a metric
python -m lynx_etf -p SPY        # equivalent module entry point
```

The `-p` flag selects production mode (real `data/` cache); without it the
tools use the isolated `data_test/` cache. See [`docs/CACHING.md`](docs/CACHING.md).

## Conventions for agents

- **Don't change behaviour or rename public functions** unless explicitly
  asked — the CLI flags, console-script, and the `lynx_investor_suite.agents`
  plugin entry point are a stable contract.
- **`lynx_etf/models.py` is the schema.** Every layer passes the dataclasses
  defined there; don't invent parallel data shapes.
- **Layer discipline:** data → metrics → presentation → UI. Rendering
  (`display.py`, `gui/`, `tui/`) must stay logic-free; calculation lives in
  `metrics/`; fetching/caching in `core/`. See [`ARCHITECTURE.md`](ARCHITECTURE.md).
- **i18n:** user-facing strings go through `t()` from
  `lynx_investor_core.translations` — don't hardcode English in new UI/report
  text.
- **Tests are cache-isolated** via `conftest.py`; never point tests at the
  production `data/` directory.
- Author/signature footer and the steganographically-signed logos are
  intentional — leave them intact.

## External dependencies

`lynx-investor-core` (Suite shared code: resolver, translations, themes,
plugins), `yfinance` (data), `rich`/`textual` (console/TUI), `tkinter` (GUI),
`pandas`/`numpy` (metrics), `feedparser`/`beautifulsoup4`/`requests` (news).
