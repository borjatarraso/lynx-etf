"""About / metadata sanity tests."""

from __future__ import annotations

from lynx_etf import (
    APP_NAME,
    SUITE_LABEL,
    __author__,
    __author_email__,
    __license__,
    __version__,
    __year__,
    get_about_text,
)


def test_version_is_semver_like():
    assert __version__.count(".") >= 2
    parts = __version__.split(".")
    assert all(p.isdigit() for p in parts[:2])


def test_metadata_values():
    assert __author__ == "Borja Tarraso"
    assert __author_email__ == "borja.tarraso@member.fsf.org"
    assert __license__ == "BSD-3-Clause"
    assert __year__ == "2026"
    assert APP_NAME == "Lynx ETF Analysis"


def test_suite_label_mentions_suite_version():
    assert SUITE_LABEL.startswith("Lince Investor Suite")


def test_about_text_has_keys():
    t = get_about_text()
    for key in (
        "name", "suite", "suite_version", "version",
        "author", "license", "license_text", "description",
    ):
        assert key in t, f"missing key: {key}"
    assert "ETF" in t["description"] or "Exchange-Traded" in t["description"]
    assert "stocks" in t["description"].lower() or "mutual" in t["description"].lower()
