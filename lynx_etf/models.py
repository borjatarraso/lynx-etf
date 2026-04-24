"""Data models for Lynx ETF Analysis.

Scope: Exchange-Traded Funds only. Non-ETF instruments (stocks, mutual
funds, closed-end funds, index mutual funds) are rejected at the
resolver level and never reach these models.
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


# Alias so downstream shared code that imports CompanyProfile finds the
# ETF type. This preserves wire compatibility with the Suite core.
CompanyProfile = ETFProfile


# ---------------------------------------------------------------------------
# Metric sections — ETF-specific
# ---------------------------------------------------------------------------

@dataclass
class CostMetrics:
    """Fees and cost structure."""
    expense_ratio: Optional[float] = None     # TER, as decimal (0.0003 = 3 bps)
    management_fee: Optional[float] = None
    spread_bps: Optional[float] = None        # Bid-ask spread (basis points)
    estimated_cost_10k_year1: Optional[float] = None  # $ for $10k held 1y


@dataclass
class IncomeMetrics:
    """Dividend and distribution analysis."""
    dividend_yield: Optional[float] = None    # trailing, as decimal
    sec_yield_30d: Optional[float] = None
    distribution_frequency: Optional[str] = None  # Quarterly, Monthly, Annual
    distribution_policy: Optional[str] = None     # Distributing, Accumulating
    yoy_distribution_change: Optional[float] = None


@dataclass
class LiquidityMetrics:
    """Size, trading activity, and stability."""
    aum: Optional[float] = None
    avg_volume: Optional[float] = None
    avg_dollar_volume: Optional[float] = None
    spread_bps: Optional[float] = None
    fund_age_years: Optional[float] = None
    shares_outstanding: Optional[float] = None
    premium_discount_pct: Optional[float] = None


@dataclass
class PerformanceMetrics:
    """Return history and risk-adjusted returns."""
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


@dataclass
class AllocationMetrics:
    """Sector/geo/currency composition."""
    holdings_count: Optional[int] = None
    top10_concentration: Optional[float] = None       # % weight of top 10
    herfindahl_sector: Optional[float] = None          # Sum(weight^2)
    sector_breakdown: list = field(default_factory=list)     # [(sector, weight)]
    country_breakdown: list = field(default_factory=list)    # [(country, weight)]
    currency_breakdown: list = field(default_factory=list)   # [(currency, weight)]
    asset_class_breakdown: list = field(default_factory=list)  # [(class, weight)]
    country_count: Optional[int] = None
    sector_count: Optional[int] = None


@dataclass
class RiskProfile:
    """Volatility and risk signals (replaces moat)."""
    volatility_1y: Optional[float] = None
    volatility_3y: Optional[float] = None
    max_drawdown_3y: Optional[float] = None
    beta_3y: Optional[float] = None
    tracking_error: Optional[float] = None
    tracking_difference: Optional[float] = None       # ETF return – benchmark return
    r_squared: Optional[float] = None
    downside_deviation_3y: Optional[float] = None
    replication_type: Optional[str] = None
    counterparty_risk: Optional[str] = None           # for synthetic ETFs


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
    verdict: Optional[Verdict] = None
    holdings: list = field(default_factory=list)
    news: list = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Wire-compat alias — legacy code and cached JSON may reference this name.
AnalysisReport = ETFReport
