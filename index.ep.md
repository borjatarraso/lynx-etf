---
ep_version: 1
project: lynx-etf
title: Lynx ETF
status: PAUSED
last_touched: 2026-06-15
last_touched_text: 15 June 2026
section: sub
category: investments
generated: 2026-08-15
ep_locked: false   # set true and this file is never regenerated
---

# Lynx ETF

> Analyze ETFs

🟠 **PAUSED** · last touched **15 June 2026** (last commit)

---

## What this is

**Exchange-Traded Fund analysis — costs, holdings, allocation, performance, risk.**

Part of the [Lince Investor Suite](https://github.com/borjatarraso/lynx-dashboard).

Strictly **ETFs only**. Stocks, mutual funds, closed-end funds, and index funds are rejected at the resolver level with a clear error. Use `lynx-fundamental` for stocks.

Every analysis produces a 0-100 scored verdict across five categories (Costs, Liquidity, Performance, Diversification, Risk) with strengths, risks, and a "suitable for" recommendation.

All four Suite modes are supported:

- **Console** (default) — one-shot Rich-rendered report
- **Interactive** (`-i`) — REPL prompt
- **TUI** (`-tui`) — Textual full-screen
- **GUI** (`-x`) — Tkinter window

Every mode honours the Lince Investor Suite themes (including the Bloomberg-dark `lynx-theme` default).

- **yfinance** — price history, fund info, holdings, allocation
- **yfinance Search** — ISIN → ticker resolution
- **Yahoo Finance + Google News RSS** — fund-level news

BSD-3-Clause. See `LICENSE`.

This project is part of the **Lince Investor Suite**, authored and signed by

**Borja Tarraso** &lt;[borja.tarraso@member.fsf.org](mailto:borja.tarraso@member.fsf.org)&gt; Licensed under BSD-3-Clause.

Every report and export emitted by Suite tools includes this same signature in its footer. The shipped logo PNGs additionally carry the author's signature via steganography for provenance — please do not replace or re-encode the logo files.

<!-- LYNX-EP-FOOTER:BEGIN -->

New here, or coming back after a while? Read [`index.ep.md`](index.ep.md) (or open [`index.ep.html`](index.ep.html) in a browser) — the standard card that answers what this is, where to look first, and how to run it, in the same shape for every project.

🟠 **PAUSED** · last touched **15 June 2026**

<img src="https://www.cortex-university.com/static/brand/lince-logo.png" alt="Lince" width="96" height="96" align="left" style="margin-right:16px" />

**Lynx ETF is proudly part of Lince.**

Part of the LINCE company · © All rights reserved

<!-- LYNX-EP-FOOTER:END -->

## Start here

- [`README.md`](README.md) — what the project is, in its own words
- [`CLAUDE.md`](CLAUDE.md) — working agreement for a session in this repo
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — module map and how the pieces fit

## Run it

```bash
cd ~/claude/lince-investor/lynx-etf
lynx-etf                              # console entry point
python3 -m lynx_etf                   # runnable package
```

## The rest of it

**Directories**

- `data/` — 3 entries
- `data_test/` — 0 entries
- `docs/` — 5 entries
- `img/` — 6 entries
- `lynx_etf/` — 15 entries
- `lynx_etf.egg-info/` — 6 entries
- `tests/` — 14 entries

**Other documentation**

- [`CHANGELOG.md`](CHANGELOG.md)
- [`DESIGN.md`](DESIGN.md)

**`docs/`** holds 5 files.

**Build / config**: `pyproject.toml`

---

## Ownership

<img src="https://www.cortex-university.com/static/brand/lince-logo.png" alt="Lince" width="96" height="96" align="left" style="margin-right:16px" />

**Lynx ETF is proudly part of Lince.**

| Company ID | Headquarters |
|---|---|
| 3015071-2 | Helsinki, Finland |

Part of the LINCE company · © All rights reserved


<sub>Standard entry-point card (`index.ep.md`, format v1) — generated 2026-08-15 by Lynx Factory. Regenerating overwrites this file unless `ep_locked: true`.</sub>
