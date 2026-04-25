"""Data models for Lynx ETF Analysis.

Scope: Exchange-Traded Funds only. Non-ETF instruments (stocks, mutual
funds, closed-end funds, index mutual funds) are rejected at the
resolver level and never reach these models.

The model surface intentionally over-collects: every field important to
a passive ETF investor — replication method, UCITS status, securities
lending policy, premium/discount stats over time, calendar-year
returns, up/down capture ratios, ESG / SFDR classification, tail-risk
(VaR/CVaR), bond-specific fields (duration, YTM, credit quality), and
a structured passive-investor checklist — has a typed slot here even
when the upstream data source can't (yet) populate it. Defaults are
``None`` / empty so existing call sites and tests keep working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Fund size tier classification (based on AUM)
# ---------------------------------------------------------------------------

class FundSizeTier(str, Enum):
    """AUM-based fund classification.

    Each tier has distinct analytical implications:
      MEGA       — >$50B: ample liquidity, tight spreads, flagship funds
      LARGE      — $10B–$50B: excellent liquidity
      MID        — $1B–$10B: good liquidity
      SMALL      — $250M–$1B: acceptable; watch spread
      MICRO      — $50M–$250M: liquidity risk; potential closure
      NANO       — <$50M: high closure risk
    """
    MEGA = "Mega Fund"
    LARGE = "Large Fund"
    MID = "Mid Fund"
    SMALL = "Small Fund"
    MICRO = "Micro Fund"
    NANO = "Nano Fund"


def classify_tier(aum: Optional[float]) -> FundSizeTier:
    """Classify an ETF by assets under management (USD)."""
    if aum is None or aum <= 0:
        return FundSizeTier.NANO
    if aum >= 50_000_000_000:
        return FundSizeTier.MEGA
    if aum >= 10_000_000_000:
        return FundSizeTier.LARGE
    if aum >= 1_000_000_000:
        return FundSizeTier.MID
    if aum >= 250_000_000:
        return FundSizeTier.SMALL
    if aum >= 50_000_000:
        return FundSizeTier.MICRO
    return FundSizeTier.NANO


# Keep the old name as an alias so shared code (and some tests importing
# from lynx_investor_core) that references CompanyTier keeps working.
CompanyTier = FundSizeTier


class Relevance(str, Enum):
    CRITICAL = "critical"
    RELEVANT = "relevant"
    CONTEXTUAL = "contextual"
    IRRELEVANT = "irrelevant"


# ---------------------------------------------------------------------------
# ETF profile
# ---------------------------------------------------------------------------

@dataclass
class ETFProfile:
    ticker: str
    name: str
    isin: Optional[str] = None
    category: Optional[str] = None       # e.g. "Large Blend", "Emerging Markets"
    asset_class: Optional[str] = None    # Equity, Fixed Income, Commodity, Multi-Asset
    fund_family: Optional[str] = None    # Vanguard, iShares, SPDR...
    domicile: Optional[str] = None       # US, IE, LU...
    inception_date: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    aum: Optional[float] = None          # Assets under management (USD)
    description: Optional[str] = None
    website: Optional[str] = None
    benchmark: Optional[str] = None
    replication: Optional[str] = None    # Physical, Synthetic, Sampling
    distribution_policy: Optional[str] = None  # Distributing, Accumulating
    tier: FundSizeTier = FundSizeTier.NANO

    # ── Structure / regulatory (matters a lot for passive investors) ─────
    regulatory_type: Optional[str] = None        # ETF, ETN, ETC, ETP
    ucits: Optional[bool] = None                  # UCITS-compliant (EU retail-eligible)
    kiid_prr_risk_rating: Optional[int] = None    # 1..7 SRRI (for UCITS docs)
    securities_lending: Optional[bool] = None     # Does fund lend securities?
    lending_revenue_split: Optional[float] = None # Share returned to investors (0..1)
    leverage_factor: Optional[float] = None       # 1.0 plain, 2.0 leveraged, -1.0 inverse
    currency_hedged: Optional[bool] = None
    hedged_to: Optional[str] = None               # Hedged target currency
    swap_counterparties: list = field(default_factory=list)  # for synthetic ETFs

    # ── Index quality ────────────────────────────────────────────────────
    index_provider: Optional[str] = None          # S&P, MSCI, FTSE, Bloomberg…
    index_name: Optional[str] = None
    index_constituents: Optional[int] = None      # # of names in the index
    rebalancing_frequency: Optional[str] = None   # Quarterly, Semi-annual, Annual
    free_float_adjusted: Optional[bool] = None
    index_licensing_disclosed: Optional[bool] = None


# Alias so downstream shared code that imports CompanyProfile finds the
# ETF type. This preserves wire compatibility with the Suite core.
CompanyProfile = ETFProfile


# ---------------------------------------------------------------------------
# Metric sections — ETF-specific
# ---------------------------------------------------------------------------

@dataclass
class CostMetrics:
    """Fees and full cost-of-ownership."""
    expense_ratio: Optional[float] = None     # TER, as decimal (0.0003 = 3 bps)
    management_fee: Optional[float] = None
    performance_fee: Optional[float] = None
    spread_bps: Optional[float] = None        # Bid-ask spread (basis points)
    median_spread_30d_bps: Optional[float] = None
    estimated_cost_10k_year1: Optional[float] = None  # $ for $10k held 1y
    estimated_cost_10k_year10: Optional[float] = None  # $ over 10y
    portfolio_turnover_pct: Optional[float] = None     # Annual turnover
    total_cost_of_ownership_bps: Optional[float] = None  # TER + spread + tracking diff
    creation_fee_bps: Optional[float] = None    # Authorised-participant cost
    redemption_fee_bps: Optional[float] = None


@dataclass
class IncomeMetrics:
    """Dividend, distribution, and tax-flavour signals."""
    dividend_yield: Optional[float] = None    # trailing, as decimal
    sec_yield_30d: Optional[float] = None
    distribution_frequency: Optional[str] = None  # Quarterly, Monthly, Annual
    distribution_policy: Optional[str] = None     # Distributing, Accumulating
    yoy_distribution_change: Optional[float] = None
    qualified_dividend_pct: Optional[float] = None     # for US tax efficiency
    cap_gain_distributions_3y_avg: Optional[float] = None  # taxable in US
    tax_efficiency_score: Optional[float] = None      # 0..100, higher = better


@dataclass
class LiquidityMetrics:
    """Size, trading activity, premium/discount, and stability."""
    aum: Optional[float] = None
    avg_volume: Optional[float] = None
    avg_dollar_volume: Optional[float] = None
    spread_bps: Optional[float] = None
    fund_age_years: Optional[float] = None
    shares_outstanding: Optional[float] = None
    premium_discount_pct: Optional[float] = None
    median_premium_discount_1y: Optional[float] = None
    max_premium_1y: Optional[float] = None
    max_discount_1y: Optional[float] = None
    mean_abs_deviation_1y: Optional[float] = None     # avg |premium/discount|
    net_flows_1y: Optional[float] = None              # USD created - redeemed
    authorised_participants: Optional[int] = None     # AP count, when published
    closure_risk: Optional[str] = None                # Low / Medium / High


@dataclass
class PerformanceMetrics:
    """Return history, capture ratios, and risk-adjusted returns."""
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_ytd: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    return_10y: Optional[float] = None
    cagr_since_inception: Optional[float] = None
    sharpe_1y: Optional[float] = None
    sharpe_3y: Optional[float] = None
    sortino_3y: Optional[float] = None
    calmar_3y: Optional[float] = None
    info_ratio_3y: Optional[float] = None
    treynor_3y: Optional[float] = None
    up_capture_3y: Optional[float] = None             # vs benchmark
    down_capture_3y: Optional[float] = None
    best_quarter: Optional[float] = None
    worst_quarter: Optional[float] = None
    recovery_days_from_max_dd: Optional[int] = None
    calendar_returns: list = field(default_factory=list)  # [(year, ret)]


@dataclass
class AllocationMetrics:
    """Sector/geo/currency composition + bond-specific allocation."""
    holdings_count: Optional[int] = None
    effective_holdings: Optional[float] = None        # 1 / Σw²
    top1_concentration: Optional[float] = None
    top5_concentration: Optional[float] = None
    top10_concentration: Optional[float] = None
    top25_concentration: Optional[float] = None
    herfindahl_sector: Optional[float] = None         # Σ(weight²) by sector
    herfindahl_holdings: Optional[float] = None       # Σ(weight²) at holding level
    sector_breakdown: list = field(default_factory=list)     # [(sector, weight)]
    country_breakdown: list = field(default_factory=list)    # [(country, weight)]
    currency_breakdown: list = field(default_factory=list)   # [(currency, weight)]
    asset_class_breakdown: list = field(default_factory=list)  # [(class, weight)]
    market_cap_breakdown: list = field(default_factory=list)   # large/mid/small
    style_box: Optional[str] = None                    # Large Value, Mid Blend...
    country_count: Optional[int] = None
    sector_count: Optional[int] = None
    # ── Bond-specific (optional; unused for equity ETFs) ────────────────
    duration_years: Optional[float] = None
    yield_to_maturity: Optional[float] = None
    credit_quality_breakdown: list = field(default_factory=list)  # [(rating, w)]
    avg_credit_rating: Optional[str] = None


@dataclass
class RiskProfile:
    """Volatility, drawdown, tail risk, and tracking-quality signals."""
    volatility_1y: Optional[float] = None
    volatility_3y: Optional[float] = None
    max_drawdown_3y: Optional[float] = None
    beta_3y: Optional[float] = None
    beta_vs_benchmark: Optional[float] = None
    correlation_sp500_3y: Optional[float] = None
    tracking_error: Optional[float] = None
    tracking_difference: Optional[float] = None       # ETF return – benchmark return
    r_squared: Optional[float] = None
    downside_deviation_3y: Optional[float] = None
    var_95_1y: Optional[float] = None                 # parametric VaR (1-day, 95%)
    cvar_95_1y: Optional[float] = None                # Expected Shortfall
    skewness_3y: Optional[float] = None
    kurtosis_3y: Optional[float] = None
    replication_type: Optional[str] = None
    counterparty_risk: Optional[str] = None           # Synthetic ETFs


@dataclass
class ESGProfile:
    """Sustainability metadata for ETFs that disclose it."""
    score: Optional[float] = None                     # 0..100
    sfdr_article: Optional[int] = None                # 6 / 8 / 9
    sustainability_rating: Optional[str] = None       # e.g. "5 globes" (Morningstar)
    carbon_intensity: Optional[float] = None          # tCO₂e / $M revenue
    controversy_score: Optional[float] = None
    exclusions: list = field(default_factory=list)    # ["Tobacco", "Weapons"]


@dataclass
class Verdict:
    """Overall assessment of the ETF."""
    overall_score: float = 0.0                # 0-100
    verdict: str = ""                          # Strong Buy / Buy / Hold / Caution / Avoid
    summary: str = ""
    category_scores: dict = field(default_factory=dict)
    strengths: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    tier_note: str = ""
    suitable_for: list = field(default_factory=list)  # e.g. "Core long-term", "Income"


@dataclass
class PassiveCheck:
    """One pass/warn/fail line in the passive-investor checklist."""
    label: str                                  # e.g. "TER under 10 bps"
    status: str = "warn"                        # "pass" / "warn" / "fail" / "info"
    message: str = ""                           # Human-readable explanation
    rule_of_thumb: str = ""                     # The threshold itself ("TER ≤ 0.10%")


@dataclass
class Holding:
    """A single holding line."""
    symbol: Optional[str] = None
    name: Optional[str] = None
    weight: Optional[float] = None            # 0..1
    sector: Optional[str] = None
    country: Optional[str] = None


@dataclass
class NewsArticle:
    title: str
    url: str
    published: Optional[str] = None
    source: Optional[str] = None
    summary: Optional[str] = None
    local_path: Optional[str] = None


@dataclass
class MetricExplanation:
    """Explanation of an ETF metric."""
    key: str
    full_name: str
    description: str
    why_used: str
    formula: str
    category: str  # costs, income, liquidity, performance, allocation, risk


@dataclass
class ETFReport:
    """Complete ETF analysis."""
    profile: ETFProfile
    costs: Optional[CostMetrics] = None
    income: Optional[IncomeMetrics] = None
    liquidity: Optional[LiquidityMetrics] = None
    performance: Optional[PerformanceMetrics] = None
    allocation: Optional[AllocationMetrics] = None
    risk: Optional[RiskProfile] = None
    esg: Optional[ESGProfile] = None
    verdict: Optional[Verdict] = None
    holdings: list = field(default_factory=list)
    news: list = field(default_factory=list)
    passive_checklist: list = field(default_factory=list)  # list[PassiveCheck]
    tips: list = field(default_factory=list)               # list[str]
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Wire-compat alias — legacy code and cached JSON may reference this name.
AnalysisReport = ETFReport
