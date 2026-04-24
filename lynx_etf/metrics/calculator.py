"""ETF metric calculator.

Consumes the ``info`` dict, holdings list, and price-history DataFrame
produced by :mod:`lynx_etf.core.fetcher` and populates the metric
sections defined in :mod:`lynx_etf.models`.
"""

from __future__ import annotations

import math
from typing import Optional

from lynx_etf.models import (
    AllocationMetrics,
    CostMetrics,
    FundSizeTier,
    Holding,
    IncomeMetrics,
    LiquidityMetrics,
    PerformanceMetrics,
    RiskProfile,
    Verdict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _pct(v) -> Optional[float]:
    """Coerce to decimal fraction (treats > 1 as percentage value)."""
    f = _f(v)
    if f is None:
        return None
    return f / 100.0 if abs(f) > 1 else f


def _annualized_volatility(hist) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        import numpy as np
        closes = hist["Close"].dropna()
        if len(closes) < 20:
            return None
        log_returns = np.log(closes / closes.shift(1)).dropna()
        return float(log_returns.std() * math.sqrt(252))
    except Exception:
        return None


def _max_drawdown(hist) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        running_max = closes.cummax()
        drawdown = (closes - running_max) / running_max
        return float(drawdown.min())
    except Exception:
        return None


def _cagr(hist) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        years = (closes.index[-1] - closes.index[0]).days / 365.25
        if years <= 0:
            return None
        return float((closes.iloc[-1] / closes.iloc[0]) ** (1 / years) - 1)
    except Exception:
        return None


def _return_over_window(hist, days: int) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        from datetime import timedelta
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        cutoff = closes.index[-1] - timedelta(days=days)
        eligible = closes[closes.index <= cutoff]
        if eligible.empty:
            return None
        start = eligible.iloc[-1]
        end = closes.iloc[-1]
        return float(end / start - 1)
    except Exception:
        return None


def _ytd_return(hist) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        last = closes.index[-1]
        try:
            year_start = last.replace(month=1, day=1)
        except Exception:
            return None
        eligible = closes[closes.index >= year_start]
        if eligible.empty:
            return None
        return float(closes.iloc[-1] / eligible.iloc[0] - 1)
    except Exception:
        return None


def _sharpe(hist, rf: float = 0.03) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        import numpy as np
        closes = hist["Close"].dropna()
        if len(closes) < 30:
            return None
        log_returns = np.log(closes / closes.shift(1)).dropna()
        ann_return = log_returns.mean() * 252
        ann_vol = log_returns.std() * math.sqrt(252)
        if ann_vol == 0:
            return None
        return float((ann_return - rf) / ann_vol)
    except Exception:
        return None


def _sortino(hist, rf: float = 0.03) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        import numpy as np
        closes = hist["Close"].dropna()
        if len(closes) < 30:
            return None
        log_returns = np.log(closes / closes.shift(1)).dropna()
        downside = log_returns[log_returns < 0]
        if len(downside) == 0:
            return None
        ann_return = log_returns.mean() * 252
        ann_down = downside.std() * math.sqrt(252)
        if ann_down == 0:
            return None
        return float((ann_return - rf) / ann_down)
    except Exception:
        return None


def _herfindahl(weights) -> Optional[float]:
    clean = [w for (_, w) in weights if w is not None]
    if not clean:
        return None
    total = sum(clean)
    if total <= 0:
        return None
    normed = [w / total for w in clean]
    return float(sum(w * w for w in normed))


# ---------------------------------------------------------------------------
# Per-section calculators
# ---------------------------------------------------------------------------

def calc_costs(info: dict, tier: FundSizeTier) -> CostMetrics:
    er = _pct(
        info.get("annualReportExpenseRatio")
        or info.get("netExpenseRatio")
        or info.get("expenseRatio")
    )
    mgmt = _pct(info.get("managementFee"))
    spread = _f(info.get("bidAskSpread"))
    if spread is not None and spread < 1:
        spread_bps = spread * 10000
    else:
        spread_bps = spread
    est_cost = er * 10000 if er is not None else None
    return CostMetrics(
        expense_ratio=er,
        management_fee=mgmt,
        spread_bps=spread_bps,
        estimated_cost_10k_year1=est_cost,
    )


def calc_income(info: dict, tier: FundSizeTier) -> IncomeMetrics:
    y = _pct(
        info.get("yield")
        or info.get("dividendYield")
        or info.get("trailingAnnualDividendYield")
    )
    sec30 = _pct(info.get("secYield") or info.get("secYield30Day"))
    freq_raw = info.get("distributionFrequency") or info.get("payoutFrequency")
    policy = info.get("distributionPolicy")
    return IncomeMetrics(
        dividend_yield=y,
        sec_yield_30d=sec30,
        distribution_frequency=str(freq_raw) if freq_raw else None,
        distribution_policy=policy,
    )


def calc_liquidity(info: dict, hist, tier: FundSizeTier) -> LiquidityMetrics:
    aum = _f(info.get("totalAssets") or info.get("netAssets"))
    avg_vol = _f(
        info.get("averageVolume")
        or info.get("averageDailyVolume10Day")
        or info.get("averageVolume10days")
    )
    price = _f(info.get("regularMarketPrice") or info.get("previousClose"))
    avg_dollar = None
    if avg_vol is not None and price is not None:
        avg_dollar = avg_vol * price

    spread = _f(info.get("bidAskSpread"))
    if spread is not None and price and spread < 1:
        spread_bps = (spread / price) * 10000
    elif spread is not None:
        spread_bps = spread
    else:
        spread_bps = None

    age = None
    inception = info.get("fundInceptionDate")
    if inception:
        try:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(float(inception), tz=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).days / 365.25
        except Exception:
            pass

    premium_discount = None
    nav = _f(info.get("navPrice"))
    if nav and price:
        premium_discount = (price - nav) / nav

    return LiquidityMetrics(
        aum=aum,
        avg_volume=avg_vol,
        avg_dollar_volume=avg_dollar,
        spread_bps=spread_bps,
        fund_age_years=age,
        shares_outstanding=_f(info.get("sharesOutstanding")),
        premium_discount_pct=premium_discount,
    )


def calc_performance(info: dict, hist, tier: FundSizeTier) -> PerformanceMetrics:
    def _tail(n: int):
        return hist.tail(n) if hist is not None else None

    return PerformanceMetrics(
        return_1m=_return_over_window(hist, 30),
        return_3m=_return_over_window(hist, 90),
        return_ytd=_ytd_return(hist),
        return_1y=_return_over_window(hist, 365),
        return_3y=_pct(info.get("threeYearAverageReturn")) or _return_over_window(hist, 3 * 365),
        return_5y=_pct(info.get("fiveYearAverageReturn")) or _return_over_window(hist, 5 * 365),
        return_10y=_return_over_window(hist, 10 * 365),
        cagr_since_inception=_cagr(hist),
        sharpe_1y=_sharpe(_tail(252)),
        sharpe_3y=_sharpe(_tail(756)),
        sortino_3y=_sortino(_tail(756)),
    )


def calc_allocation(
    info: dict,
    holdings: list[Holding],
    sectors: list[tuple],
    countries: list[tuple],
    currencies: list[tuple],
    asset_classes: list[tuple],
) -> AllocationMetrics:
    top10 = None
    if holdings:
        top_sorted = sorted(holdings, key=lambda h: h.weight or 0, reverse=True)[:10]
        weights = [h.weight for h in top_sorted if h.weight is not None]
        if weights:
            s = sum(weights)
            if s > 1:
                s = s / 100.0
            top10 = s

    return AllocationMetrics(
        holdings_count=len(holdings) or None,
        top10_concentration=top10,
        herfindahl_sector=_herfindahl(sectors),
        sector_breakdown=sectors,
        country_breakdown=countries,
        currency_breakdown=currencies,
        asset_class_breakdown=asset_classes,
        country_count=len(countries) if countries else None,
        sector_count=len(sectors) if sectors else None,
    )


def calc_risk(info: dict, hist, benchmark_hist, tier: FundSizeTier) -> RiskProfile:
    tracking_error = None
    tracking_diff = None
    r2 = None
    beta = _f(info.get("beta3Year") or info.get("beta"))

    if hist is not None and benchmark_hist is not None:
        try:
            import pandas as pd
            a = hist["Close"].pct_change().dropna()
            b = benchmark_hist["Close"].pct_change().dropna()
            aligned = pd.concat([a, b], axis=1, join="inner").dropna()
            if len(aligned) >= 30:
                diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
                tracking_error = float(diff.std() * math.sqrt(252))
                tracking_diff = float(
                    (aligned.iloc[:, 0].mean() - aligned.iloc[:, 1].mean()) * 252
                )
                corr = aligned.corr().iloc[0, 1]
                r2 = float(corr * corr) if not math.isnan(corr) else None
        except Exception:
            pass

    def _tail(n):
        return hist.tail(n) if hist is not None else None

    return RiskProfile(
        volatility_1y=_annualized_volatility(_tail(252)),
        volatility_3y=_annualized_volatility(_tail(756)),
        max_drawdown_3y=_max_drawdown(_tail(756)),
        beta_3y=beta,
        tracking_error=tracking_error,
        tracking_difference=tracking_diff,
        r_squared=r2,
        downside_deviation_3y=None,
        replication_type=None,
        counterparty_risk=None,
    )


# ---------------------------------------------------------------------------
# Verdict synthesis
# ---------------------------------------------------------------------------

def build_verdict(
    profile,
    costs: CostMetrics,
    income: IncomeMetrics,
    liquidity: LiquidityMetrics,
    performance: PerformanceMetrics,
    allocation: AllocationMetrics,
    risk: RiskProfile,
) -> Verdict:
    """Heuristic 0-100 scoring across 5 categories."""
    scores: dict[str, float] = {}

    if costs.expense_ratio is not None:
        scores["Costs"] = max(0.0, 100.0 - (costs.expense_ratio * 10000))
    else:
        scores["Costs"] = 50.0

    aum = liquidity.aum or profile.aum
    if aum is None:
        scores["Liquidity"] = 50.0
    elif aum >= 50e9:
        scores["Liquidity"] = 100.0
    elif aum >= 10e9:
        scores["Liquidity"] = 85.0
    elif aum >= 1e9:
        scores["Liquidity"] = 70.0
    elif aum >= 250e6:
        scores["Liquidity"] = 50.0
    elif aum >= 50e6:
        scores["Liquidity"] = 30.0
    else:
        scores["Liquidity"] = 15.0

    perf_bits = [r for r in [performance.return_3y, performance.return_5y] if r is not None]
    if perf_bits:
        avg = sum(perf_bits) / len(perf_bits)
        scores["Performance"] = max(0.0, min(100.0, 50 + avg * 500))
    else:
        scores["Performance"] = 50.0

    if allocation.herfindahl_sector is not None or allocation.holdings_count:
        div = 0.0
        if allocation.herfindahl_sector is not None:
            div += max(0.0, 60 - allocation.herfindahl_sector * 300)
        if allocation.holdings_count is not None:
            div += min(40.0, allocation.holdings_count / 25)
        scores["Diversification"] = min(100.0, div)
    else:
        scores["Diversification"] = 50.0

    r = 50.0
    if risk.volatility_3y is not None:
        r = max(0.0, 100 - risk.volatility_3y * 400)
    if risk.max_drawdown_3y is not None:
        r = min(r, 100 + risk.max_drawdown_3y * 120)
    scores["Risk"] = max(0.0, min(100.0, r))

    overall = sum(scores.values()) / len(scores)
    if overall >= 80:
        verdict = "Strong Buy"
    elif overall >= 65:
        verdict = "Buy"
    elif overall >= 50:
        verdict = "Hold"
    elif overall >= 35:
        verdict = "Caution"
    else:
        verdict = "Avoid"

    strengths: list[str] = []
    risks_out: list[str] = []
    if costs.expense_ratio is not None and costs.expense_ratio < 0.002:
        strengths.append(f"Low fees ({costs.expense_ratio*100:.2f}%)")
    if (liquidity.aum or 0) >= 10e9:
        strengths.append(f"Deep liquidity (AUM ${(liquidity.aum or 0)/1e9:.1f}B)")
    if (performance.return_5y or 0) > 0.08:
        strengths.append(f"Strong 5Y return ({performance.return_5y*100:.1f}%)")
    if allocation.holdings_count and allocation.holdings_count >= 100:
        strengths.append(f"Broadly diversified ({allocation.holdings_count} holdings)")

    if costs.expense_ratio is not None and costs.expense_ratio > 0.005:
        risks_out.append(f"High expense ratio ({costs.expense_ratio*100:.2f}%)")
    if aum is not None and aum < 250e6:
        risks_out.append("Low AUM — liquidity / closure risk")
    if (risk.max_drawdown_3y or 0) < -0.3:
        risks_out.append(f"Deep drawdown ({risk.max_drawdown_3y*100:.1f}%)")
    if allocation.top10_concentration is not None and allocation.top10_concentration > 0.5:
        risks_out.append(f"Concentrated top 10 ({allocation.top10_concentration*100:.1f}%)")

    suitable = []
    if scores["Liquidity"] >= 70 and scores["Diversification"] >= 60:
        suitable.append("Core long-term holding")
    if (income.dividend_yield or 0) > 0.03:
        suitable.append("Income-oriented investors")
    if scores["Risk"] >= 65:
        suitable.append("Lower-volatility allocations")

    return Verdict(
        overall_score=overall,
        verdict=verdict,
        summary=f"Overall score {overall:.0f}/100 across {len(scores)} categories.",
        category_scores=scores,
        strengths=strengths,
        risks=risks_out,
        tier_note=f"Classified as {profile.tier.value} by AUM.",
        suitable_for=suitable,
    )
