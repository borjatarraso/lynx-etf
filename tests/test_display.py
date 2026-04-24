"""Display rendering smoke tests."""

from __future__ import annotations

import io

from rich.console import Console

from lynx_etf.display import (
    fmt_bps,
    fmt_int,
    fmt_money,
    fmt_pct,
    fmt_years,
    render_about,
    render_full_report,
)
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
)


class TestFormatters:
    def test_fmt_pct(self):
        assert fmt_pct(None) == "—"
        assert fmt_pct(0.0123) == "1.23%"
        assert fmt_pct(0.1, 0) == "10%"

    def test_fmt_money(self):
        assert fmt_money(None) == "—"
        assert fmt_money(1.2e12) == "$1.20T"
        assert fmt_money(5.4e9) == "$5.40B"
        assert fmt_money(7.1e6) == "$7.10M"
        assert fmt_money(999) == "$999.00"

    def test_fmt_bps(self):
        assert fmt_bps(None) == "—"
        assert fmt_bps(3.4) == "3.4 bps"

    def test_fmt_int(self):
        assert fmt_int(None) == "—"
        assert fmt_int(1234567) == "1,234,567"

    def test_fmt_years(self):
        assert fmt_years(None) == "—"
        assert fmt_years(10.7) == "10.7 yr"


def _make_report() -> ETFReport:
    return ETFReport(
        profile=ETFProfile(
            ticker="SPY", name="SPDR S&P 500", aum=500e9,
            tier=FundSizeTier.MEGA, isin="US78462F1030",
            category="Large Blend", asset_class="Equity",
            fund_family="State Street",
        ),
        costs=CostMetrics(expense_ratio=0.0009, spread_bps=0.3),
        income=IncomeMetrics(dividend_yield=0.013),
        liquidity=LiquidityMetrics(aum=500e9, avg_volume=7e7, fund_age_years=33),
        performance=PerformanceMetrics(return_1y=0.21, return_5y=0.12, sharpe_3y=0.8),
        allocation=AllocationMetrics(holdings_count=500, top10_concentration=0.32,
                                     herfindahl_sector=0.15,
                                     sector_breakdown=[("Technology", 0.28)],
                                     country_breakdown=[("US", 1.0)],
                                     country_count=1, sector_count=11),
        risk=RiskProfile(volatility_3y=0.16, max_drawdown_3y=-0.25, beta_3y=1.0),
        verdict=Verdict(overall_score=85, verdict="Strong Buy",
                        category_scores={"Costs": 91, "Liquidity": 100}),
        holdings=[Holding(symbol="AAPL", name="Apple", weight=0.07)],
    )


class TestRenderFullReport:
    def test_renders_all_sections(self):
        buf = io.StringIO()
        console = Console(file=buf, width=120, force_terminal=False)
        render_full_report(console, _make_report())
        out = buf.getvalue()
        assert "SPY" in out
        assert "SPDR S&P 500" in out
        assert "Strong Buy" in out
        assert "Costs" in out
        assert "Holdings" in out or "Top" in out

    def test_handles_missing_sections(self):
        r = ETFReport(profile=ETFProfile(ticker="X", name="X"))
        buf = io.StringIO()
        console = Console(file=buf, width=80, force_terminal=False)
        render_full_report(console, r)
        out = buf.getvalue()
        assert "X" in out  # header renders
        assert "Caution" not in out  # no verdict means no verdict panel


class TestRenderAbout:
    def test_renders(self):
        buf = io.StringIO()
        console = Console(file=buf, width=120, force_terminal=False)
        render_about(console)
        out = buf.getvalue()
        assert "Lynx ETF Analysis" in out
        assert "ETFs only" in out or "ETF" in out
