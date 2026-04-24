"""Relevance filter tests."""

from __future__ import annotations

from lynx_etf.metrics.relevance import is_critical, relevance_for
from lynx_etf.models import FundSizeTier, Relevance


def test_always_critical_metrics():
    for tier in FundSizeTier:
        assert is_critical("expense_ratio", tier)
        assert is_critical("aum", tier)


def test_small_funds_see_spread_as_critical():
    assert is_critical("spread_bps", FundSizeTier.MICRO)
    assert is_critical("avg_volume", FundSizeTier.NANO)


def test_mega_funds_downgrade_spread():
    assert relevance_for("spread_bps", FundSizeTier.MEGA) == Relevance.CONTEXTUAL


def test_small_funds_downgrade_sharpe():
    assert relevance_for("sharpe_3y", FundSizeTier.MICRO) == Relevance.CONTEXTUAL
