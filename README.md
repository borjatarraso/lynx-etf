# Lynx ETF

**Exchange-Traded Fund analysis — costs, holdings, allocation, performance, risk.**

Part of the [Lince Investor Suite](https://github.com/borjatarraso/lynx-dashboard).

## Scope

Strictly **ETFs only**. Stocks, mutual funds, closed-end funds, and index
funds are rejected at the resolver level with a clear error. Use
`lynx-fundamental` for stocks.

## Install

```bash
pip install -e .
```

## Quickstart

```bash
lynx-etf -p SPY                     # Production analysis (uses cache)
lynx-etf -p QQQ --refresh            # Force fresh data
lynx-etf -p IE00B4L5Y983             # Analyze by ISIN (IWDA UCITS)
lynx-etf -p -s "world equity"        # Search for ETFs
lynx-etf -p -i                       # Interactive REPL
lynx-etf -p -tui                     # Textual TUI
lynx-etf -p -x                       # Tkinter GUI
lynx-etf --explain expense_ratio     # Explain a metric
```

## What it measures

| Section | Metrics |
|---------|---------|
| **Costs** | Expense ratio (TER), management fee, bid-ask spread, est. $ cost / $10k / yr |
| **Income** | Trailing dividend yield, SEC 30-day yield, distribution frequency, distribution policy (accumulating / distributing) |
| **Size & Liquidity** | AUM, avg daily volume, avg daily $ volume, fund age, shares outstanding, premium/discount |
| **Performance** | 1M / 3M / YTD / 1Y / 3Y / 5Y / 10Y returns, CAGR since inception, Sharpe (1Y / 3Y), Sortino (3Y) |
| **Allocation** | Holdings count, top-10 concentration, Herfindahl (sector), sector & country breakdown |
| **Top Holdings** | Top 15 positions by weight |
| **Risk** | Volatility (1Y / 3Y), max drawdown (3Y), beta (3Y), tracking error vs benchmark, tracking difference, R² |

## Verdict

Every analysis produces a 0-100 scored verdict across five categories
(Costs, Liquidity, Performance, Diversification, Risk) with strengths,
risks, and a "suitable for" recommendation.

## Modes

All four Suite modes are supported:

- **Console** (default) — one-shot Rich-rendered report
- **Interactive** (`-i`) — REPL prompt
- **TUI** (`-tui`) — Textual full-screen
- **GUI** (`-x`) — Tkinter window

Every mode honours the Lince Investor Suite themes (including the
Bloomberg-dark `lynx-theme` default).

## Data sources

- **yfinance** — price history, fund info, holdings, allocation
- **yfinance Search** — ISIN → ticker resolution
- **Yahoo Finance + Google News RSS** — fund-level news

## License

BSD-3-Clause. See `LICENSE`.

---

## Author and signature

This project is part of the **Lince Investor Suite**, authored and signed by

> **Borja Tarraso** &lt;[borja.tarraso@member.fsf.org](mailto:borja.tarraso@member.fsf.org)&gt;
> Licensed under BSD-3-Clause.

Every report and export emitted by Suite tools includes this same
signature in its footer. The shipped logo PNGs additionally carry the
author's signature via steganography for provenance — please do not
replace or re-encode the logo files.
