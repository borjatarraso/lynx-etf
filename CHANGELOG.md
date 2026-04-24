# Changelog

## 1.0.0 — 2026-04-24

**First release.**

ETF-specialist analysis tool, part of the Lince Investor Suite. Cloned
from the lynx-fundamental scaffold but rewritten with ETF-native data
models (`ETFProfile`, `ETFReport`, `CostMetrics`, `IncomeMetrics`,
`LiquidityMetrics`, `PerformanceMetrics`, `AllocationMetrics`,
`RiskProfile`, `Verdict`).

**Scope**

- Strictly ETFs. Stocks (`EQUITY`), mutual funds (`MUTUALFUND`),
  closed-end funds (`CLOSEDENDFUND`), raw indices (`INDEX`), and other
  quote-types are rejected at the resolver with a clear error.

**Features**

- Full four-mode support: console, interactive REPL, Textual TUI,
  Tkinter GUI.
- `--explain <metric>` and `--explain-all` for metric education.
- `--search <query>` for free-text ETF search.
- `--list-cache` / `--drop-cache <TICKER|ALL>` for cache management.
- Registered as a Suite plugin (`lynx_investor_suite.agents` group).

**Data model**

- `FundSizeTier` (Mega / Large / Mid / Small / Micro / Nano) classified
  by AUM.
- Seven section types: costs, income, liquidity, performance,
  allocation, risk, verdict.

**Tests**

- 81 pytest tests covering models, calculator, ticker resolution,
  display, CLI parsing, storage, relevance, explanations, analyzer
  serialisation, plugin registration.
