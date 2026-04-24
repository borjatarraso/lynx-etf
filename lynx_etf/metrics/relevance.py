"""Per-tier relevance filter for ETF metrics."""

from __future__ import annotations

from lynx_etf.models import FundSizeTier, Relevance


_ALWAYS_CRITICAL = {"expense_ratio", "aum", "volatility_3y", "max_drawdown_3y"}
_SMALL_FUND_DIM = {"sharpe_3y", "sortino_3y", "tracking_error", "tracking_difference"}


def relevance_for(metric_key: str, tier: FundSizeTier) -> Relevance:
    if metric_key in _ALWAYS_CRITICAL:
        return Relevance.CRITICAL

    if tier in (FundSizeTier.NANO, FundSizeTier.MICRO):
        if metric_key in _SMALL_FUND_DIM:
            return Relevance.CONTEXTUAL
        if metric_key in {"avg_volume", "spread_bps", "fund_age_years"}:
            return Relevance.CRITICAL
        return Relevance.RELEVANT

    if tier in (FundSizeTier.MEGA, FundSizeTier.LARGE):
        if metric_key == "spread_bps":
            return Relevance.CONTEXTUAL
        return Relevance.RELEVANT

    return Relevance.RELEVANT


def is_critical(metric_key: str, tier: FundSizeTier) -> bool:
    return relevance_for(metric_key, tier) == Relevance.CRITICAL
