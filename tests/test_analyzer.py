"""Analyzer orchestration tests (network-free)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lynx_etf.core import analyzer
from lynx_etf.core.ticker import NotAnETFError
from lynx_etf.models import ETFProfile, ETFReport, FundSizeTier


@pytest.fixture(autouse=True)
def _testing_mode():
    from lynx_etf.core import storage
    prev = storage.get_mode()
    storage.set_mode("testing")
    yield
    storage.set_mode(prev)


class TestSerialization:
    def test_roundtrip(self):
        from lynx_etf.models import CostMetrics, Holding, Verdict
        p = ETFProfile(ticker="SPY", name="SPDR S&P 500", aum=500e9,
                       tier=FundSizeTier.MEGA)
        r = ETFReport(profile=p,
                      costs=CostMetrics(expense_ratio=0.0009),
                      holdings=[Holding(symbol="AAPL", weight=0.07)],
                      verdict=Verdict(overall_score=85, verdict="Buy"))
        d = analyzer._report_to_dict(r)
        r2 = analyzer._dict_to_report(d)
        assert r2.profile.ticker == "SPY"
        assert r2.profile.tier == FundSizeTier.MEGA
        assert r2.costs.expense_ratio == 0.0009
        assert len(r2.holdings) == 1
        assert r2.holdings[0].symbol == "AAPL"
        assert r2.verdict.verdict == "Buy"

    def test_parse_tier_by_value(self):
        assert analyzer._parse_tier("Mega Fund") == FundSizeTier.MEGA
        assert analyzer._parse_tier("Nano Fund") == FundSizeTier.NANO
        assert analyzer._parse_tier("Unknown") == FundSizeTier.NANO


class TestResolveRejectsNonETF:
    def test_stock_raises(self):
        from unittest.mock import MagicMock
        fake = MagicMock()
        fake.info = {"quoteType": "EQUITY"}
        with patch("yfinance.Ticker", return_value=fake):
            with pytest.raises(NotAnETFError):
                analyzer.run_full_analysis("AAPL")
