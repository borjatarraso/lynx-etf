"""ETF ticker resolution and validation.

Scope guard: only ETFs are accepted. Stocks (EQUITY), mutual funds
(MUTUALFUND), closed-end funds (CLOSEDENDFUND), and raw indices
(INDEX) are rejected with a clear error.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


class NotAnETFError(ValueError):
    """Raised when the resolved instrument is not an ETF."""


_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")

_ETF_QUOTE_TYPES = {"ETF"}
_REJECTED_QUOTE_TYPES = {
    "EQUITY": "stock",
    "MUTUALFUND": "mutual fund",
    "CLOSEDENDFUND": "closed-end fund",
    "INDEX": "index",
    "CURRENCY": "currency",
    "CRYPTOCURRENCY": "cryptocurrency",
    "FUTURE": "futures contract",
    "OPTION": "option",
}


def is_isin(identifier: str) -> bool:
    return bool(_ISIN_RE.match((identifier or "").strip().upper()))


def resolve_identifier(identifier: str) -> Tuple[str, Optional[str]]:
    """Resolve a raw identifier to (ticker, isin_or_None).

    Rejects non-ETF instruments by raising :class:`NotAnETFError`.
    """
    raw = (identifier or "").strip().upper()
    if not raw:
        raise ValueError("Empty identifier")

    isin: Optional[str] = None
    ticker: str = raw

    if is_isin(raw):
        isin = raw
        resolved = _ticker_from_isin(raw)
        if not resolved:
            raise ValueError(f"Could not resolve ISIN {raw} to a ticker")
        ticker = resolved

    try:
        import yfinance as yf
    except ImportError:
        return ticker, isin

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return ticker, isin

    quote_type = str(info.get("quoteType", "")).upper()
    if quote_type and quote_type not in _ETF_QUOTE_TYPES:
        kind = _REJECTED_QUOTE_TYPES.get(quote_type, quote_type.lower())
        raise NotAnETFError(
            f"'{ticker}' is a {kind}, not an ETF. "
            f"lynx-etf only analyses Exchange-Traded Funds. "
            f"Use lynx-fundamental for stocks."
        )

    if isin is None:
        fetched = info.get("isin") or None
        if fetched and is_isin(str(fetched).upper()):
            isin = str(fetched).upper()

    return ticker, isin


def _ticker_from_isin(isin: str) -> Optional[str]:
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        search = yf.Search(isin, max_results=5)
        quotes = getattr(search, "quotes", None) or []
    except Exception:
        return None
    for q in quotes:
        qt = str(q.get("quoteType", "")).upper()
        if qt == "ETF":
            symbol = q.get("symbol") or q.get("ticker")
            if symbol:
                return str(symbol).upper()
    return None


def search_etfs(query: str, limit: int = 10) -> list[dict]:
    """Search ETFs matching free-text query; returns list of dicts."""
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        search = yf.Search(query, max_results=limit * 3)
        quotes = getattr(search, "quotes", None) or []
    except Exception:
        return []
    out: list[dict] = []
    for q in quotes:
        qt = str(q.get("quoteType", "")).upper()
        if qt != "ETF":
            continue
        out.append({
            "symbol": q.get("symbol") or q.get("ticker") or "",
            "name": q.get("shortname") or q.get("longname") or "",
            "exchange": q.get("exchange") or "",
            "currency": q.get("currency") or "",
        })
        if len(out) >= limit:
            break
    return out
