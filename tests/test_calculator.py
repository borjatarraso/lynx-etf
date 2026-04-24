"""Tests for the ETF metrics calculator."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lynx_etf.metrics.calculator import (
    _herfindahl,
    _pct,
    build_verdict,
    calc_allocation,
    calc_costs,
    calc_income,
    calc_liquidity,
    calc_performance,
    calc_risk,
)
from lynx_etf.models import ETFProfile, FundSizeTier, Holding


class TestCoercions:
    def test_pct_passthrough_when_decimal(self):
        assert _pct(0.003) == pytest.approx(0.003)

    def test_pct_converts_when_percentage(self):
        assert _pct(1.5) == pytest.approx(0.015)

    def test_pct_none(self):
        assert _pct(None) is None

    def test_pct_junk(self):
        assert _pct("foo") is None


class TestHerfindahl:
    def test_empty(self):
        assert _herfindahl([]) is None

    def test_equal_weights(self):
        # 5 sectors each at 20% → HHI = 0.2 (reciprocal of count).
        hhi = _herfindahl([("A", 0.2), ("B", 0.2), ("C", 0.2), ("D", 0.2), ("E", 0.2)])
        assert hhi == pytest.approx(0.2, rel=1e-6)

    def test_concentrated(self):
        # All in one sector → HHI = 1.
        hhi = _herfindahl([("A", 1.0)])
        assert hhi == pytest.approx(1.0)


class TestCalcCosts:
    def test_reads_expense_ratio_raw_decimal(self):
        out = calc_costs({"expenseRatio": 0.0003}, FundSizeTier.MEGA)
        assert out.expense_ratio == pytest.approx(0.0003)

    def test_reads_expense_ratio_as_percentage(self):
        # Some fund feeds report 0.03 meaning 3% (0.03 is ≤1 so we keep it).
        # But if the feed reports 3 meaning 3%, we should scale down.
        out = calc_costs({"expenseRatio": 3.0}, FundSizeTier.MEGA)
        assert out.expense_ratio == pytest.approx(0.03)

    def test_spread_conversion_from_decimal(self):
        out = calc_costs({"bidAskSpread": 0.0005}, FundSizeTier.MEGA)
        assert out.spread_bps == pytest.approx(5.0)

    def test_none_values(self):
        out = calc_costs({}, FundSizeTier.NANO)
        assert out.expense_ratio is None
        assert out.management_fee is None


class TestCalcIncome:
    def test_yield_from_dividendYield(self):
        out = calc_income({"dividendYield": 1.5}, FundSizeTier.MEGA)
        assert out.dividend_yield == pytest.approx(0.015)

    def test_distribution_fields(self):
        out = calc_income(
            {"distributionFrequency": "Quarterly", "distributionPolicy": "Distributing"},
            FundSizeTier.MEGA,
        )
        assert out.distribution_frequency == "Quarterly"
        assert out.distribution_policy == "Distributing"


class TestCalcLiquidity:
    def test_aum_and_dollar_volume(self):
        out = calc_liquidity(
            {"totalAssets": 500e9, "averageVolume": 8e7, "regularMarketPrice": 500},
            None, FundSizeTier.MEGA,
        )
        assert out.aum == 500e9
        assert out.avg_dollar_volume == pytest.approx(8e7 * 500)

    def test_spread_bps_when_decimal(self):
        out = calc_liquidity(
            {"bidAskSpread": 0.0005, "regularMarketPrice": 500},
            None, FundSizeTier.MEGA,
        )
        assert out.spread_bps is not None
        assert out.spread_bps == pytest.approx((0.0005 / 500) * 10000)


class TestCalcPerformance:
    def test_no_history_returns_none_for_windows(self):
        out = calc_performance({}, None, FundSizeTier.MEGA)
        assert out.return_1y is None
        assert out.cagr_since_inception is None

    def test_return_windows_with_history(self):
        idx = pd.date_range(end="2026-01-01", periods=400, freq="D")
        series = pd.Series([100 + i * 0.1 for i in range(len(idx))], index=idx)
        hist = pd.DataFrame({"Close": series})
        out = calc_performance({}, hist, FundSizeTier.MEGA)
        assert out.return_1y is not None
        assert out.cagr_since_inception is not None
        assert out.return_1y > 0  # rising series


class TestCalcAllocation:
    def test_holdings_count(self):
        holdings = [Holding(symbol="A", weight=0.1), Holding(symbol="B", weight=0.05)]
        out = calc_allocation({}, holdings, [], [], [], [])
        assert out.holdings_count == 2

    def test_top10_concentration(self):
        holdings = [Holding(symbol=f"T{i}", weight=0.05) for i in range(20)]
        out = calc_allocation({}, holdings, [], [], [], [])
        assert out.top10_concentration == pytest.approx(0.5)

    def test_sector_hhi(self):
        out = calc_allocation(
            {}, [],
            [("Technology", 0.4), ("Financials", 0.3), ("Healthcare", 0.3)],
            [], [], [],
        )
        assert out.herfindahl_sector == pytest.approx(0.34, abs=0.01)


class TestCalcRisk:
    def test_beta_from_info(self):
        out = calc_risk({"beta": 1.1}, None, None, FundSizeTier.MEGA)
        assert out.beta_3y == 1.1

    def test_vol_none_without_history(self):
        out = calc_risk({}, None, None, FundSizeTier.MEGA)
        assert out.volatility_1y is None
        assert out.tracking_error is None


class TestBuildVerdict:
    def test_all_empty_sections_mid_score(self):
        from lynx_etf.models import (
            CostMetrics, IncomeMetrics, LiquidityMetrics, PerformanceMetrics,
            AllocationMetrics, RiskProfile,
        )
        p = ETFProfile(ticker="X", name="X", tier=FundSizeTier.NANO)
        v = build_verdict(
            p, CostMetrics(), IncomeMetrics(), LiquidityMetrics(),
            PerformanceMetrics(), AllocationMetrics(), RiskProfile(),
        )
        assert 30 <= v.overall_score <= 70
        assert v.verdict in {"Strong Buy", "Buy", "Hold", "Caution", "Avoid"}

    def test_low_fee_high_aum_scores_well(self):
        from lynx_etf.models import (
            CostMetrics, IncomeMetrics, LiquidityMetrics, PerformanceMetrics,
            AllocationMetrics, RiskProfile,
        )
        p = ETFProfile(ticker="VTI", name="Vanguard Total", aum=300e9,
                       tier=FundSizeTier.MEGA)
        v = build_verdict(
            p,
            CostMetrics(expense_ratio=0.0003),
            IncomeMetrics(dividend_yield=0.015),
            LiquidityMetrics(aum=300e9),
            PerformanceMetrics(return_3y=0.1, return_5y=0.12),
            AllocationMetrics(holdings_count=3700, herfindahl_sector=0.12, top10_concentration=0.25),
            RiskProfile(volatility_3y=0.16, max_drawdown_3y=-0.2),
        )
        assert v.overall_score >= 65, v.category_scores
        assert v.verdict in {"Buy", "Strong Buy"}
