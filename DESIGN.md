# Design notes

Why `lynx-etf` is built the way it is. These describe decisions visible in the
code today — not a roadmap. For the structural picture see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## ETF-only scope, enforced early

The tool deliberately refuses anything that is not an ETF. Resolution happens
up front in `core/ticker.py`, which raises `NotAnETFError` for stocks, mutual
funds, closed-end funds, and index funds. Keeping the guard at the resolver
means every downstream layer can assume it is working with an ETF and the
metric set stays coherent (TER, premium/discount, tracking error, replication,
etc. only make sense for funds). Stocks are handled by the sibling
`lynx-fundamental` tool.

## Cache-first, with production/test isolation

Network calls to yfinance are slow and rate-limited, so analysis is
cache-first: `core/analyzer.run_full_analysis` returns a stored report unless
`refresh=True`. Two cache roots are kept strictly separate — `data/`
(production, chosen with `-p`) and `data_test/` (default) — so tests and
experiments never pollute real cached analyses. All persistence is funnelled
through `core/storage.py` (mode flag + path helpers), which is the single place
that knows where bytes live.

## Immutable dataclass schema as the spine

`models.py` defines every structure passed between layers as a dataclass/enum
and imports nothing from the rest of the package. This makes the report shape
the contract: fetcher/calculator produce these types, presentation consumes
them, and there is one obvious place to add a field. Backward-compatibility
aliases (`CompanyTier`, `CompanyProfile`, `AnalysisReport`) are kept so older
Suite call-sites keep working.

## Strict layering: data → metrics → presentation → UI

Fetching/caching (`core/`), computation (`metrics/`), and rendering
(`display.py`, `gui/`, `tui/`) are separated and depend only downward. The
calculation layer is pure (numbers in, dataclasses out) and never touches
Rich/Tkinter/Textual; the rendering layer carries no business logic. This keeps
metrics testable in isolation and lets the four front-ends share one pipeline.

## One orchestrator, many front-ends

The four modes — console, interactive REPL, Textual TUI, Tkinter GUI — are thin
front-ends over a single entry: `core/analyzer.run_full_analysis` (or
`run_progressive_analysis` with a progress callback). The REPL further reuses
the CLI's sub-command functions, so a feature added to the CLI surfaces in
interactive mode automatically. See [`docs/MODES.md`](docs/MODES.md).

## Suite integration and i18n

`lynx-etf` is a member of the Lince Investor Suite. It registers as an agent via
`plugin.register` (entry point `lynx_investor_suite.agents.etf`) and pulls
shared behaviour from `lynx-investor-core`: the identifier resolver, theme
gallery, and the `t()` translation function. User-facing strings route through
`t()` so the whole Suite can be localised consistently rather than each tool
hardcoding English.

## Education alongside numbers

Beyond raw metrics, the tool ships a passive-investor checklist
(`passive_checklist.py`, Boglehead-style rules of thumb), educational tips
(`tips.py`), and per-metric explanations (`metrics/explanations.py`, powering
`--explain`). These are kept as separate modules so the analytical core stays
free of prose and the guidance can evolve independently.
