"""Metric explanations catalogue tests."""

from __future__ import annotations

from lynx_etf.metrics.explanations import EXPLANATIONS, by_category, get_explanation, list_keys


def test_keys_are_consistent():
    for key, exp in EXPLANATIONS.items():
        assert exp.key == key
        assert exp.full_name
        assert exp.description
        assert exp.why_used
        assert exp.formula
        assert exp.category in {"costs", "income", "liquidity", "performance", "allocation", "risk"}


def test_get_explanation_known():
    e = get_explanation("expense_ratio")
    assert e is not None
    assert e.category == "costs"


def test_get_explanation_unknown():
    assert get_explanation("nope") is None


def test_list_keys_is_sorted():
    keys = list_keys()
    assert keys == sorted(keys)


def test_by_category_groups():
    buckets = by_category()
    assert "costs" in buckets
    assert "risk" in buckets
    for cat, items in buckets.items():
        assert items, f"category {cat} is empty"
