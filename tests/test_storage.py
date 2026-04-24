"""Storage / caching tests."""

from __future__ import annotations

import pytest

from lynx_etf.core import storage


@pytest.fixture(autouse=True)
def _testing_mode():
    prev = storage.get_mode()
    storage.set_mode("testing")
    # Ensure clean test dir
    storage.drop_cache_all()
    yield
    storage.drop_cache_all()
    storage.set_mode(prev)


def test_set_mode_rejects_unknown():
    with pytest.raises(ValueError):
        storage.set_mode("weird")


def test_has_cache_false_in_testing_mode():
    assert not storage.has_cache("SPY")


def test_save_and_load_analysis_in_production():
    storage.set_mode("production")
    try:
        storage.drop_cache_ticker("TSTX")
        path = storage.save_analysis_report("TSTX", {
            "profile": {"ticker": "TSTX", "name": "Test ETF", "tier": "Nano Fund"},
            "fetched_at": "2026-04-24T12:00:00",
        })
        assert path.exists()
        cached = storage.load_cached_report("TSTX")
        assert cached is not None
        assert cached["profile"]["ticker"] == "TSTX"
        assert storage.has_cache("TSTX")
        assert storage.drop_cache_ticker("TSTX")
        assert not storage.has_cache("TSTX")
    finally:
        storage.set_mode("testing")


def test_list_cached_tickers_empty():
    assert storage.list_cached_tickers() == []
