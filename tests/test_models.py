"""Tests for ETF data models."""

from __future__ import annotations

import pytest

from lynx_etf.models import (
    AllocationMetrics,
    CostMetrics,
    ETFProfile,
    ETFReport,
    FundSizeTier,
    Holding,
    IncomeMetrics,
    LiquidityMetrics,
    PerformanceMetrics,
    RiskProfile,
    Verdict,
    classify_tier,
)


class TestClassifyTier:
    def test_none_is_nano(self):
        assert classify_tier(None) == FundSizeTier.NANO

    def test_zero_is_nano(self):
        assert classify_tier(0) == FundSizeTier.NANO

    def test_thresholds(self):
        assert classify_tier(50e9) == FundSizeTier.MEGA
        assert classify_tier(100e9) == FundSizeTier.MEGA
        assert classify_tier(10e9) == FundSizeTier.LARGE
        assert classify_tier(1e9) == FundSizeTier.MID
        assert classify_tier(250e6) == FundSizeTier.SMALL
        assert classify_tier(50e6) == FundSizeTier.MICRO
        assert classify_tier(10e6) == FundSizeTier.NANO


class TestETFProfile:
    def test_minimum_fields(self):
        p = ETFProfile(ticker="SPY", name="SPDR S&P 500 ETF")
        assert p.ticker == "SPY"
        assert p.tier == FundSizeTier.NANO  # default until set

    def test_full_fields(self):
        p = ETFProfile(
            ticker="IWDA.AS", name="iShares Core MSCI World",
            isin="IE00B4L5Y983", domicile="IE",
            aum=70e9, tier=FundSizeTier.MEGA,
        )
        assert p.isin == "IE00B4L5Y983"
        assert p.domicile == "IE"


class TestETFReportStructure:
    def test_empty_report(self):
        p = ETFProfile(ticker="VTI", name="Vanguard Total Stock Market")
        r = ETFReport(profile=p)
        assert r.profile.ticker == "VTI"
        assert r.costs is None
        assert r.holdings == []
        assert r.news == []
        assert r.fetched_at != ""

    def test_report_with_all_sections(self):
        p = ETFProfile(ticker="VTI", name="Vanguard Total Stock Market")
        r = ETFReport(
            profile=p,
            costs=CostMetrics(expense_ratio=0.0003),
            income=IncomeMetrics(dividend_yield=0.015),
            liquidity=LiquidityMetrics(aum=300e9),
            performance=PerformanceMetrics(return_1y=0.2),
            allocation=AllocationMetrics(holdings_count=3700),
            risk=RiskProfile(volatility_3y=0.16),
            verdict=Verdict(overall_score=90, verdict="Strong Buy"),
            holdings=[Holding(symbol="AAPL", weight=0.06)],
        )
        assert r.costs.expense_ratio == 0.0003
        assert r.allocation.holdings_count == 3700
        assert r.verdict.verdict == "Strong Buy"
