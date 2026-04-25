"""Pin the i18n language to English for the whole test run.

Display tests assert on English literals (e.g. "Top Holdings"), so any
language preference persisted to ``~/.config/lynx/language.json`` from
manual smoke tests must not leak in.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _pin_english_language():
    from lynx_investor_core.translations import set_language
    set_language("en")
    yield
