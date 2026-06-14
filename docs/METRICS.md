# Metrics reference

What the analysis computes and where. Each section is a dataclass in
`lynx_etf/models.py`, produced by a `calc_*` function in
`lynx_etf/metrics/calculator.py`, and explained (for `--explain`) in
`lynx_etf/metrics/explanations.py`.

| Section | Dataclass | Calculator | Examples |
|---------|-----------|-----------|----------|
| Costs | `CostMetrics` | `calc_costs` | expense ratio (TER), management fee, bid-ask spread, est. $/yr per $10k |
| Income | `IncomeMetrics` | `calc_income` | trailing dividend yield, SEC 30-day yield, distribution frequency & policy |
| Size & liquidity | `LiquidityMetrics` | `calc_liquidity` | AUM, avg daily volume, avg daily $ volume, fund age, premium/discount |
| Performance | `PerformanceMetrics` | `calc_performance` | 1M–10Y returns, CAGR, Sharpe (1Y/3Y), Sortino (3Y) |
| Allocation | `AllocationMetrics` | `calc_allocation` | holdings count, top-10 concentration, Herfindahl, sector/country breakdown |
| Risk | `RiskProfile` | `calc_risk` | volatility (1Y/3Y), max drawdown (3Y), beta, tracking error/difference, R² |
| Verdict | `Verdict` | `build_verdict` | 0–100 across Costs, Liquidity, Performance, Diversification, Risk |

Top holdings (`Holding`) and news (`NewsArticle`) round out the `ETFReport`.

## Supporting computation

`calculator.py` also implements the time-series and concentration maths behind
the sections, including (private helpers): annualised volatility, max drawdown,
CAGR, Sharpe / Sortino / Calmar / information / Treynor ratios, up/down capture,
calendar & quarterly returns, VaR/CVaR (95%), skew/kurtosis, premium-discount
stats, Herfindahl index, and top-N concentration.

## Relevance by fund size

`metrics/relevance.py` classifies each metric as critical / relevant /
contextual / irrelevant for a given `FundSizeTier`, so front-ends can prioritise
what to surface for mega-cap vs micro-cap funds.

## Explanations (`--explain`)

`metrics/explanations.py` holds the `EXPLANATIONS` catalogue keyed by metric.
`get_explanation(key)` returns one entry; `by_category()` groups them. This
powers `lynx-etf --explain <metric>` and `--explain-all`.
