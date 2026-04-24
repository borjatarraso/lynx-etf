"""Ticker resolution and ETF scope enforcement tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lynx_etf.core.ticker import (
    NotAnETFError,
    is_isin,
    resolve_identifier,
    search_etfs,
)


class TestIsIsin:
    def test_valid_isin_formats(self):
        assert is_isin("IE00B4L5Y983")
        assert is_isin("US78462F1030")
        assert is_isin("us78462f1030")  # lowercased

    def test_invalid(self):
        assert not is_isin("SPY")
        assert not is_isin("")
        assert not is_isin("IE00B4L5Y98")  # too short


class TestResolveIdentifier:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            resolve_identifier("")

    def test_etf_ticker_accepted(self):
        fake = MagicMock()
        fake.info = {"quoteType": "ETF", "isin": "US78462F1030"}
        with patch("yfinance.Ticker", return_value=fake):
            ticker, isin = resolve_identifier("SPY")
        assert ticker == "SPY"
        assert isin == "US78462F1030"

    def test_stock_rejected(self):
        fake = MagicMock()
        fake.info = {"quoteType": "EQUITY"}
        with patch("yfinance.Ticker", return_value=fake):
            with pytest.raises(NotAnETFError) as ei:
                resolve_identifier("AAPL")
        assert "stock" in str(ei.value).lower()

    def test_mutual_fund_rejected(self):
        fake = MagicMock()
        fake.info = {"quoteType": "MUTUALFUND"}
        with patch("yfinance.Ticker", return_value=fake):
            with pytest.raises(NotAnETFError) as ei:
                resolve_identifier("VTSAX")
        assert "mutual" in str(ei.value).lower()

    def test_index_rejected(self):
        fake = MagicMock()
        fake.info = {"quoteType": "INDEX"}
        with patch("yfinance.Ticker", return_value=fake):
            with pytest.raises(NotAnETFError) as ei:
                resolve_identifier("^GSPC")
        assert "index" in str(ei.value).lower()


class TestSearchEtfs:
    def test_returns_empty_on_failure(self):
        with patch("yfinance.Search", side_effect=Exception("boom")):
            assert search_etfs("anything") == []

    def test_filters_non_etf_quotes(self):
        fake = MagicMock()
        fake.quotes = [
            {"symbol": "AAPL", "shortname": "Apple", "quoteType": "EQUITY"},
            {"symbol": "SPY", "shortname": "SPDR S&P 500", "quoteType": "ETF",
             "exchange": "NYSEARCA", "currency": "USD"},
            {"symbol": "VTSAX", "shortname": "Vanguard TSM", "quoteType": "MUTUALFUND"},
        ]
        with patch("yfinance.Search", return_value=fake):
            results = search_etfs("market", limit=5)
        assert len(results) == 1
        assert results[0]["symbol"] == "SPY"
