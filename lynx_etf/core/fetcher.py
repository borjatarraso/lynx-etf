"""ETF data fetching via yfinance."""

from __future__ import annotations

from typing import Optional

from lynx_etf.models import ETFProfile, Holding, classify_tier


def fetch_info(ticker: str) -> dict:
    """Fetch yfinance Ticker.info as a plain dict (best-effort)."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    try:
        return dict(yf.Ticker(ticker).info or {})
    except Exception:
        return {}


def fetch_profile(ticker: str, info: Optional[dict] = None) -> ETFProfile:
    """Build an :class:`ETFProfile` from yfinance info."""
    info = info if info is not None else fetch_info(ticker)

    name = (
        info.get("longName")
        or info.get("shortName")
        or info.get("name")
        or ticker
    )
    aum = _coerce_float(info.get("totalAssets") or info.get("netAssets"))
    inception_ts = info.get("fundInceptionDate")
    inception_date = _epoch_to_iso(inception_ts)

    profile = ETFProfile(
        ticker=ticker,
        name=str(name),
        category=info.get("category"),
        asset_class=info.get("legalType") or _infer_asset_class(info),
        fund_family=info.get("fundFamily"),
        domicile=info.get("domicile") or info.get("region") or info.get("country"),
        inception_date=inception_date,
        exchange=info.get("exchange") or info.get("fullExchangeName"),
        currency=info.get("currency"),
        aum=aum,
        description=info.get("longBusinessSummary") or info.get("description"),
        website=info.get("website"),
        benchmark=info.get("benchmark") or info.get("trackingIndex"),
        replication=_infer_replication(info),
        distribution_policy=_infer_distribution_policy(info),
    )
    profile.tier = classify_tier(aum)
    return profile


def fetch_history(ticker: str, period: str = "10y"):
    """Fetch price history as a pandas DataFrame (or None)."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if hist is None or hist.empty:
            return None
        return hist
    except Exception:
        return None


def fetch_holdings(ticker: str, info: Optional[dict] = None) -> list[Holding]:
    """Return the ETF's top holdings as a list of :class:`Holding`."""
    info = info if info is not None else fetch_info(ticker)
    raw = info.get("holdings") or info.get("topHoldings")
    if isinstance(raw, dict):
        raw = raw.get("holdings") or raw.get("topHoldings") or []
    if not raw:
        return []

    out: list[Holding] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        weight = _coerce_float(
            row.get("holdingPercent")
            or row.get("weight")
            or row.get("percent")
        )
        if weight is not None and weight > 1:
            weight = weight / 100.0
        out.append(Holding(
            symbol=row.get("symbol") or row.get("ticker"),
            name=row.get("holdingName") or row.get("name"),
            weight=weight,
            sector=row.get("sector"),
            country=row.get("country"),
        ))
    return out


def fetch_sector_breakdown(ticker: str, info: Optional[dict] = None) -> list[tuple]:
    info = info if info is not None else fetch_info(ticker)
    raw = info.get("sectorWeightings") or info.get("sector_weightings")
    return _normalise_breakdown(raw)


def fetch_country_breakdown(ticker: str, info: Optional[dict] = None) -> list[tuple]:
    info = info if info is not None else fetch_info(ticker)
    raw = (
        info.get("countryWeightings")
        or info.get("country_weightings")
        or info.get("geoWeightings")
    )
    return _normalise_breakdown(raw)


def fetch_asset_class_breakdown(ticker: str, info: Optional[dict] = None) -> list[tuple]:
    info = info if info is not None else fetch_info(ticker)
    raw = info.get("bondHoldings") or info.get("assetClassWeightings")
    return _normalise_breakdown(raw)


def fetch_benchmark_history(benchmark_ticker: str, period: str = "5y"):
    return fetch_history(benchmark_ticker, period=period)


# Internal helpers ------------------------------------------------------------

def _coerce_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _epoch_to_iso(v) -> Optional[str]:
    if v is None:
        return None
    try:
        from datetime import datetime, timezone
        secs = float(v)
        return datetime.fromtimestamp(secs, tz=timezone.utc).date().isoformat()
    except Exception:
        return None


def _infer_asset_class(info: dict) -> Optional[str]:
    cat = (info.get("category") or "").lower()
    if any(k in cat for k in ["bond", "treasury", "fixed income", "credit"]):
        return "Fixed Income"
    if any(k in cat for k in ["commodity", "gold", "silver", "oil"]):
        return "Commodity"
    if any(k in cat for k in ["allocation", "multi-asset", "target"]):
        return "Multi-Asset"
    if any(k in cat for k in ["equity", "stock", "blend", "value", "growth"]):
        return "Equity"
    return None


def _infer_replication(info: dict) -> Optional[str]:
    name = (info.get("longName") or info.get("shortName") or "").lower()
    if "swap" in name or "synthetic" in name:
        return "Synthetic"
    if "sampling" in name:
        return "Sampling"
    return None


def _infer_distribution_policy(info: dict) -> Optional[str]:
    name = (info.get("longName") or info.get("shortName") or "").lower()
    if any(k in name for k in [" acc", " accumulating", " accumulation"]):
        return "Accumulating"
    if " dist" in name or " distributing" in name:
        return "Distributing"
    if info.get("dividendYield") or info.get("trailingAnnualDividendYield"):
        return "Distributing"
    return None


def _normalise_breakdown(raw) -> list[tuple]:
    out: list[tuple] = []
    if not raw:
        return out

    if isinstance(raw, dict):
        for k, v in raw.items():
            w = _coerce_float(v)
            if w is None:
                continue
            if w > 1:
                w = w / 100.0
            out.append((str(k).replace("_", " ").title(), w))
    elif isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict):
                if "name" in row or "sector" in row:
                    label = row.get("name") or row.get("sector") or ""
                    w = _coerce_float(row.get("weight") or row.get("percent"))
                    if w is not None and w > 1:
                        w = w / 100.0
                    if label and w is not None:
                        out.append((str(label), w))
                else:
                    for k, v in row.items():
                        w = _coerce_float(v)
                        if w is None:
                            continue
                        if w > 1:
                            w = w / 100.0
                        out.append((str(k).replace("_", " ").title(), w))
    out.sort(key=lambda kv: kv[1] or 0, reverse=True)
    return out
