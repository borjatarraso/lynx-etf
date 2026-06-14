# Caching & storage

All persistence goes through `lynx_etf/core/storage.py`. Nothing else in the
codebase reads or writes the cache directly.

## Two isolated roots

| Mode | Directory | Selected by |
|------|-----------|-------------|
| Production | `data/` | `set_mode("production")` / the `-p` CLI flag |
| Testing | `data_test/` | default; `set_mode("testing")` |

Keeping them separate means tests and ad-hoc runs never overwrite real cached
analyses. The test suite is pinned to the testing root via `tests/conftest.py`.

## Cache-first analysis

`core/analyzer.run_full_analysis(identifier, refresh=False)`:

1. resolve the identifier (`core/ticker`),
2. if a cached report exists and `refresh` is `False`, load and return it,
3. otherwise fetch → compute → enrich → **save** → return.

`refresh=True` (CLI `--refresh`) forces a fresh fetch and re-cache.

## Storage API (selected)

- `set_mode(mode)` / `get_mode()` / `is_testing()` — choose/inspect the root.
- `has_cache(ticker)`, `load_cached_report(ticker)`, `save_analysis_report(ticker, report)`.
- `get_cache_age_hours(ticker)`, `list_cached_tickers()`.
- `drop_cache_ticker(ticker)`, `drop_cache_all()` — invalidation (CLI `cache` / `drop-cache`).
- `save_json` / `load_json` / `save_text` and the `get_*_dir()` path helpers.

Reports are serialised to/from plain dicts by `core/analyzer._report_to_dict`
and `_dict_to_report`, so the on-disk format tracks the `models.py` dataclasses.
