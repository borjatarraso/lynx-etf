"""ETF metric explanations — powers the ``--explain`` CLI output."""

from __future__ import annotations

from lynx_etf.models import MetricExplanation


EXPLANATIONS: dict[str, MetricExplanation] = {
    "expense_ratio": MetricExplanation(
        key="expense_ratio",
        full_name="Expense Ratio (TER)",
        description=(
            "Annual cost the fund charges as a percentage of assets. "
            "Deducted continuously from NAV — you never see the bill."
        ),
        why_used=(
            "The single strongest predictor of long-term ETF underperformance. "
            "Compounds against you every year you hold."
        ),
        formula="TER = Annual fund operating expenses / Average NAV",
        category="costs",
    ),
    "spread_bps": MetricExplanation(
        key="spread_bps",
        full_name="Bid-Ask Spread (bps)",
        description="The cost you pay to enter and exit the position on exchange.",
        why_used="Hidden cost for smaller / less-liquid ETFs.",
        formula="Spread = (Ask − Bid) / Mid × 10,000",
        category="costs",
    ),
    "dividend_yield": MetricExplanation(
        key="dividend_yield",
        full_name="Trailing Dividend Yield",
        description="Sum of the past 12 months of distributions divided by the current price.",
        why_used="Primary income signal for dividend-focused ETFs.",
        formula="Yield = Σ(trailing 12m distributions) / Price",
        category="income",
    ),
    "sec_yield_30d": MetricExplanation(
        key="sec_yield_30d",
        full_name="SEC 30-Day Yield",
        description="Standardised SEC yield — primary income metric for US bond ETFs.",
        why_used="Comparable across funds; forward-looking vs trailing yield.",
        formula="(Σ income − expenses) / (NAV × shares outstanding), annualised",
        category="income",
    ),
    "aum": MetricExplanation(
        key="aum",
        full_name="Assets Under Management",
        description="Total market value of assets held in the fund.",
        why_used=(
            "Below $250M → risk of closure. Below $50M → acute risk. "
            "Larger AUM generally = tighter spreads and lower ownership risk."
        ),
        formula="AUM = Σ(NAV × shares outstanding)",
        category="liquidity",
    ),
    "avg_volume": MetricExplanation(
        key="avg_volume",
        full_name="Average Daily Volume",
        description="Average shares traded per day.",
        why_used="Proxy for how quickly you can enter / exit without moving the price.",
        formula="Trailing average of daily share volume",
        category="liquidity",
    ),
    "fund_age_years": MetricExplanation(
        key="fund_age_years",
        full_name="Fund Age (years)",
        description="Years since the fund's inception.",
        why_used="Seasoned funds have longer track records. New funds are less proven.",
        formula="Today − Inception",
        category="liquidity",
    ),
    "return_1y": MetricExplanation(
        key="return_1y",
        full_name="Total Return — 1 Year",
        description="Total return (price + distributions) over the past 12 months.",
        why_used="Short-horizon momentum; noise-prone, never evaluate in isolation.",
        formula="(Price_today + reinvested distributions) / Price_1y − 1",
        category="performance",
    ),
    "return_5y": MetricExplanation(
        key="return_5y",
        full_name="Total Return — 5 Year CAGR",
        description="Compound annual growth rate over 5 years.",
        why_used="Long-enough window to smooth out short-term noise.",
        formula="(P_now / P_5y_ago) ^ (1/5) − 1",
        category="performance",
    ),
    "sharpe_3y": MetricExplanation(
        key="sharpe_3y",
        full_name="Sharpe Ratio (3Y)",
        description="Excess return per unit of total volatility.",
        why_used="Normalises return by risk — comparable across funds.",
        formula="(Annual return − Risk-free rate) / Annual volatility",
        category="performance",
    ),
    "sortino_3y": MetricExplanation(
        key="sortino_3y",
        full_name="Sortino Ratio (3Y)",
        description="Excess return per unit of downside volatility only.",
        why_used="Penalises painful drawdowns only, not upside volatility.",
        formula="(Annual return − Risk-free rate) / Downside deviation",
        category="performance",
    ),
    "top10_concentration": MetricExplanation(
        key="top10_concentration",
        full_name="Top-10 Concentration",
        description="Sum of weights of the 10 largest holdings.",
        why_used="High top-10 → exposure driven by a few names rather than a broad index.",
        formula="Σ(weight of 10 largest holdings)",
        category="allocation",
    ),
    "herfindahl_sector": MetricExplanation(
        key="herfindahl_sector",
        full_name="Sector HHI",
        description="Herfindahl–Hirschman Index over sector weights. 1/N is perfectly balanced.",
        why_used="Detects sector concentration — a diversified equity ETF should have low HHI.",
        formula="HHI = Σ(weight²)",
        category="allocation",
    ),
    "holdings_count": MetricExplanation(
        key="holdings_count",
        full_name="Number of Holdings",
        description="How many underlying positions the fund holds.",
        why_used="More positions generally means lower single-name risk.",
        formula="count(holdings)",
        category="allocation",
    ),
    "volatility_3y": MetricExplanation(
        key="volatility_3y",
        full_name="Annualised Volatility (3Y)",
        description="Standard deviation of daily log returns, scaled to one year.",
        why_used="Primary risk metric — lets you size positions responsibly.",
        formula="σ(log returns) × √252",
        category="risk",
    ),
    "max_drawdown_3y": MetricExplanation(
        key="max_drawdown_3y",
        full_name="Max Drawdown (3Y)",
        description="Largest peak-to-trough decline in the past 3 years.",
        why_used="Measures how painful the worst drawdown has been.",
        formula="min((P_t − P_peak) / P_peak) for t in window",
        category="risk",
    ),
    "beta_3y": MetricExplanation(
        key="beta_3y",
        full_name="Beta (3Y)",
        description="Sensitivity of returns vs the benchmark.",
        why_used="β ≈ 1 tracks the market; β > 1 amplifies; β < 1 dampens.",
        formula="Cov(R_fund, R_bench) / Var(R_bench)",
        category="risk",
    ),
    "tracking_error": MetricExplanation(
        key="tracking_error",
        full_name="Tracking Error",
        description="Annualised stdev of return differences vs benchmark.",
        why_used="Measures how closely the ETF follows its index. Lower = better tracking.",
        formula="σ(R_etf − R_bench) × √252",
        category="risk",
    ),
    "tracking_difference": MetricExplanation(
        key="tracking_difference",
        full_name="Tracking Difference",
        description="Annualised average return gap vs benchmark.",
        why_used="A TER-adjusted version of 'what did the index give vs what I got'.",
        formula="mean(R_etf − R_bench) × 252",
        category="risk",
    ),
}


def get_explanation(key: str):
    return EXPLANATIONS.get(key)


def list_keys() -> list[str]:
    return sorted(EXPLANATIONS.keys())


def by_category() -> dict[str, list]:
    buckets: dict[str, list] = {}
    for e in EXPLANATIONS.values():
        buckets.setdefault(e.category, []).append(e)
    for v in buckets.values():
        v.sort(key=lambda m: m.full_name)
    return buckets
