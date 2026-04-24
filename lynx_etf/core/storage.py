"""Local data storage management.

Two isolated data directories:
  - Production: data/       (cache-enabled, persistent)
  - Testing:    data_test/  (always fresh, disposable)

Call set_mode("testing") before any data operations to redirect all
reads and writes to the test directory.  Production data is never
touched when running in testing mode.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Global mode (production | testing)
# ---------------------------------------------------------------------------

_MODE: str = "production"
_DATA_DIR_NAMES = {
    "production": "data",
    "testing": "data_test",
}


def set_mode(mode: str) -> None:
    """Set the global storage mode: 'production' or 'testing'."""
    global _MODE
    if mode not in _DATA_DIR_NAMES:
        raise ValueError(f"Unknown mode '{mode}'. Use 'production' or 'testing'.")
    _MODE = mode


def get_mode() -> str:
    """Return the current storage mode."""
    return _MODE


def is_testing() -> bool:
    return _MODE == "testing"


# ---------------------------------------------------------------------------
# Path helpers — all routed through the current mode
# ---------------------------------------------------------------------------

def get_data_root() -> Path:
    """Return the data directory for the current mode, creating it if needed."""
    dir_name = _DATA_DIR_NAMES[_MODE]
    root = Path(__file__).resolve().parent.parent.parent / dir_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_company_dir(ticker: str) -> Path:
    d = get_data_root() / ticker.upper()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_reports_dir(ticker: str) -> Path:
    d = get_company_dir(ticker) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_news_dir(ticker: str) -> Path:
    d = get_company_dir(ticker) / "news"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_financials_dir(ticker: str) -> Path:
    d = get_company_dir(ticker) / "financials"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def save_json(path: Path, data: Any) -> Path:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: Path, text: str) -> Path:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def save_binary(path: Path, content: bytes) -> Path:
    with open(path, "wb") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Analysis report persistence
# ---------------------------------------------------------------------------

def save_analysis_report(ticker: str, report_dict: dict) -> Path:
    """Save a full analysis report as JSON with timestamp."""
    d = get_company_dir(ticker)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = d / f"analysis_{ts}.json"
    save_json(path, report_dict)

    latest = d / "analysis_latest.json"
    save_json(latest, report_dict)
    return path


def load_cached_report(ticker: str) -> Optional[dict]:
    """Load the most recent cached analysis for a ticker, or None.

    Always returns None in testing mode (testing never reads cache).
    """
    if is_testing():
        return None
    latest = get_company_dir(ticker) / "analysis_latest.json"
    if latest.exists():
        try:
            return load_json(latest)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def get_cache_age_hours(ticker: str) -> Optional[float]:
    """Return how many hours old the cached analysis is, or None if no cache."""
    latest = get_company_dir(ticker) / "analysis_latest.json"
    if not latest.exists():
        return None
    try:
        data = load_json(latest)
        fetched = data.get("fetched_at")
        if fetched:
            ts = datetime.fromisoformat(fetched)
            now = datetime.now(ts.tzinfo)
            delta = (now - ts).total_seconds() / 3600
            return max(delta, 0)
    except Exception:
        pass
    try:
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        now = datetime.now()
        delta = (now - mtime).total_seconds() / 3600
        return max(delta, 0)
    except Exception:
        return None


def has_cache(ticker: str) -> bool:
    """Check if a cached analysis exists for a ticker.

    Always returns False in testing mode.
    """
    if is_testing():
        return False
    latest = get_company_dir(ticker) / "analysis_latest.json"
    return latest.exists()


def list_saved_analyses(ticker: str) -> list[Path]:
    d = get_company_dir(ticker)
    return sorted(d.glob("analysis_*.json"), reverse=True)


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def drop_cache_ticker(ticker: str) -> bool:
    """Remove all cached data for a single ticker. Returns True if removed."""
    d = get_data_root() / ticker.upper()
    if d.exists() and d.is_dir():
        shutil.rmtree(d)
        return True
    return False


def drop_cache_all() -> int:
    """Remove all cached data. Returns the number of ticker directories removed."""
    root = get_data_root()
    count = 0
    for d in root.iterdir():
        if d.is_dir():
            shutil.rmtree(d)
            count += 1
    return count


def list_cached_tickers() -> list[dict]:
    """List all tickers that have cached data, with metadata."""
    root = get_data_root()
    if not root.exists():
        return []
    tickers = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        latest = d / "analysis_latest.json"
        info: dict = {"ticker": d.name, "path": str(d)}
        if latest.exists():
            try:
                data = load_json(latest)
                profile = data.get("profile", {})
                info["name"] = profile.get("name", "")
                info["tier"] = profile.get("tier", "")
                info["fetched_at"] = data.get("fetched_at", "")
                age = get_cache_age_hours(d.name)
                info["age_hours"] = round(age, 1) if age is not None else None
            except Exception:
                pass
        info["files"] = sum(1 for _ in d.rglob("*") if _.is_file())
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        info["size_mb"] = round(size / (1024 * 1024), 2)
        tickers.append(info)
    return tickers
