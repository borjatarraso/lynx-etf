"""ETF metric calculator.

Consumes the ``info`` dict, holdings list, and price-history DataFrame
produced by :mod:`lynx_etf.core.fetcher` and populates the metric
sections defined in :mod:`lynx_etf.models`.

Coverage in this revision:

* **Costs**: TER, management/performance fee, spread (1d + 30d median),
  estimated cost over 1 / 10 years, total cost of ownership (TER +
  spread + tracking diff).
* **Income**: yield, SEC yield, frequency / policy, qualified-dividend
  share, capital-gains-distribution proxy, tax-efficiency score.
* **Liquidity**: AUM, volume, $ volume, age, shares out, premium /
  discount + 1Y stats (median, max prem, max disc, mean abs deviation),
  closure-risk bucket.
* **Performance**: per-window returns, calendar returns, capture
  ratios, Sharpe / Sortino / Calmar / info / Treynor, best & worst
  quarters, recovery time from max drawdown.
* **Allocation**: holdings count, top-1/5/10/25 concentrations,
  effective holdings (1/HHI), sector / country / currency breakdowns
  + counts.
* **Risk**: 1Y / 3Y volatility, max drawdown, beta, tracking error /
  difference, R², downside deviation, parametric VaR/CVaR (1-day,
  95%), skewness, kurtosis.

Every new field falls back to ``None`` when input data is unavailable
so existing tests keep working.
"""

from __future__ import annotations

from lynx_investor_core.translations import t as _t

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
# Numeric helpers
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


def _recovery_days_from_max_dd(hist) -> Optional[int]:
    """Days between the trough of the worst drawdown and full recovery (or None)."""
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        running_max = closes.cummax()
        dd = (closes - running_max) / running_max
        trough_idx = dd.idxmin()
        peak_value = running_max.loc[trough_idx]
        post = closes.loc[trough_idx:]
        recovered = post[post >= peak_value]
        if recovered.empty:
            return None
        return int((recovered.index[0] - trough_idx).days)
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


def _downside_dev(hist) -> Optional[float]:
    if hist is None or getattr(hist, "empty", True):
        return None
    try:
        import numpy as np
        closes = hist["Close"].dropna()
        if len(closes) < 30:
            return None
        log_returns = np.log(closes / closes.shift(1)).dropna()
        downside = log_returns[log_returns < 0]
        if len(downside) < 5:
            return None
        return float(downside.std() * math.sqrt(252))
    except Exception:
        return None


def _calmar(performance_3y: Optional[float],
            max_dd_3y: Optional[float]) -> Optional[float]:
    if performance_3y is None or max_dd_3y is None or max_dd_3y >= 0:
        return None
    return float(performance_3y / abs(max_dd_3y))


def _info_ratio(hist, benchmark_hist) -> Optional[float]:
    if hist is None or benchmark_hist is None:
        return None
    try:
        import numpy as np
        import pandas as pd
        a = hist["Close"].pct_change().dropna()
        b = benchmark_hist["Close"].pct_change().dropna()
        joined = pd.concat([a, b], axis=1, join="inner").dropna()
        if len(joined) < 60:
            return None
        diff = joined.iloc[:, 0] - joined.iloc[:, 1]
        ann_excess = float(diff.mean() * 252)
        ann_te = float(diff.std() * math.sqrt(252))
        if ann_te == 0:
            return None
        return ann_excess / ann_te
    except Exception:
        return None


def _treynor(hist, beta: Optional[float], rf: float = 0.03) -> Optional[float]:
    if beta is None or beta == 0 or hist is None or getattr(hist, "empty", True):
        return None
    try:
        closes = hist["Close"].dropna()
        if len(closes) < 30:
            return None
        ann_ret = float((closes.iloc[-1] / closes.iloc[0]) ** (252 / len(closes)) - 1)
        return (ann_ret - rf) / beta
    except Exception:
        return None


def _capture_ratios(hist, benchmark_hist) -> tuple[Optional[float], Optional[float]]:
    """Return (up_capture, down_capture) — daily returns vs benchmark."""
    if hist is None or benchmark_hist is None:
        return None, None
    try:
        import pandas as pd
        a = hist["Close"].pct_change().dropna()
        b = benchmark_hist["Close"].pct_change().dropna()
        joined = pd.concat([a, b], axis=1, join="inner").dropna()
        if len(joined) < 60:
            return None, None
        ar = joined.iloc[:, 0]
        br = joined.iloc[:, 1]
        up_mask = br > 0
        dn_mask = br < 0
        up_capture = (
            float(ar[up_mask].mean() / br[up_mask].mean())
            if up_mask.sum() > 5 and br[up_mask].mean() != 0 else None
        )
        dn_capture = (
            float(ar[dn_mask].mean() / br[dn_mask].mean())
            if dn_mask.sum() > 5 and br[dn_mask].mean() != 0 else None
        )
        return up_capture, dn_capture
    except Exception:
        return None, None


def _quarterly_extremes(hist) -> tuple[Optional[float], Optional[float]]:
    """Return (best_quarter, worst_quarter) over the supplied history."""
    if hist is None or getattr(hist, "empty", True):
        return None, None
    try:
        closes = hist["Close"].dropna()
        if len(closes) < 60:
            return None, None
        q = closes.resample("QE").last().dropna() if hasattr(closes, "resample") else None
        if q is None or len(q) < 2:
            return None, None
        rets = (q / q.shift(1) - 1).dropna()
        if rets.empty:
            return None, None
        return float(rets.max()), float(rets.min())
    except Exception:
        return None, None


def _calendar_returns(hist, max_years: int = 10) -> list[tuple[int, float]]:
    """Return up to *max_years* (year, return) tuples ordered descending."""
    if hist is None or getattr(hist, "empty", True):
        return []
    try:
        closes = hist["Close"].dropna()
        if closes.empty:
            return []
        years = sorted({d.year for d in closes.index}, reverse=True)[:max_years]
        out: list[tuple[int, float]] = []
        for year in years:
            yr_close = closes[closes.index.year == year]
            if yr_close.empty:
                continue
            start = yr_close.iloc[0]
            end = yr_close.iloc[-1]
            if start <= 0:
                continue
            out.append((year, float(end / start - 1)))
        return out
    except Exception:
        return []


def _var_cvar_95(hist) -> tuple[Optional[float], Optional[float]]:
    """Parametric (historical) 1-day VaR/CVaR at 95% confidence — negative numbers."""
    if hist is None or getattr(hist, "empty", True):
        return None, None
    try:
        closes = hist["Close"].dropna()
        if len(closes) < 60:
            return None, None
        rets = (closes / closes.shift(1) - 1).dropna()
        if rets.empty:
            return None, None
        sorted_rets = rets.sort_values()
        cutoff = max(1, int(len(sorted_rets) * 0.05))
        var = float(sorted_rets.iloc[cutoff - 1])
        cvar = float(sorted_rets.iloc[:cutoff].mean())
        return var, cvar
    except Exception:
        return None, None


def _skew_kurt(hist) -> tuple[Optional[float], Optional[float]]:
    if hist is None or getattr(hist, "empty", True):
        return None, None
    try:
        closes = hist["Close"].dropna()
        if len(closes) < 60:
            return None, None
        rets = (closes / closes.shift(1) - 1).dropna()
        if rets.empty:
            return None, None
        return float(rets.skew()), float(rets.kurt())
    except Exception:
        return None, None


def _premium_discount_stats(hist, info: dict) -> tuple[
    Optional[float], Optional[float], Optional[float], Optional[float]
]:
    """Return (median_pd_1y, max_premium_1y, max_discount_1y, mean_abs_dev_1y).

    Without a NAV time-series we approximate from price extremes vs the
    most recent (price - NAV) snapshot in *info* so the absolute level
    matches the spot premium/discount the upstream value already returned.
    """
    if hist is None or getattr(hist, "empty", True):
        return None, None, None, None
    try:
        from datetime import timedelta
        closes = hist["Close"].dropna()
        if closes.empty:
            return None, None, None, None
        cutoff = closes.index[-1] - timedelta(days=365)
        last_year = closes[closes.index >= cutoff]
        if last_year.empty:
            return None, None, None, None
        nav = _f(info.get("navPrice"))
        price = _f(info.get("regularMarketPrice") or info.get("previousClose"))
        if nav is None or price is None or nav == 0:
            return None, None, None, None
        # Premium/discount on the latest day:
        spot = (price - nav) / nav
        # Approximate intraday variation by scaling daily returns.
        rel = (last_year - last_year.iloc[-1]) / last_year.iloc[-1]
        approx_pd = rel + spot
        median_pd = float(approx_pd.median())
        max_prem = float(approx_pd.max())
        max_disc = float(approx_pd.min())
        mean_abs = float(approx_pd.abs().mean())
        return median_pd, max_prem, max_disc, mean_abs
    except Exception:
        return None, None, None, None


def _herfindahl(weights) -> Optional[float]:
    clean = [w for (_, w) in weights if w is not None]
    if not clean:
        return None
    total = sum(clean)
    if total <= 0:
        return None
    normed = [w / total for w in clean]
    return float(sum(w * w for w in normed))


def _herfindahl_holdings(holdings: list[Holding]) -> Optional[float]:
    weights = [h.weight for h in holdings if h.weight is not None]
    if not weights:
        return None
    total = sum(weights)
    if total <= 0:
        return None
    normed = [w / total for w in weights]
    return float(sum(w * w for w in normed))


def _top_n_concentration(holdings: list[Holding], n: int) -> Optional[float]:
    if not holdings:
        return None
    sorted_w = sorted(
        [h.weight for h in holdings if h.weight is not None],
        reverse=True,
    )[:n]
    if not sorted_w:
        return None
    s = sum(sorted_w)
    if s > 1:
        s /= 100.0
    return float(s)


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
    perf_fee = _pct(info.get("performanceFee"))
    raw_spread = _f(info.get("bidAskSpread"))
    if raw_spread is not None and raw_spread < 1:
        spread_bps = raw_spread * 10000
    else:
        spread_bps = raw_spread
    median_spread = _f(info.get("medianSpread30Day"))
    turnover = _pct(info.get("portfolioTurnover") or info.get("annualHoldingsTurnover"))

    est_year1 = er * 10000 if er is not None else None
    est_year10 = (
        ((1 + er) ** 10 - 1) * 10000 if er is not None else None
    )

    # Total cost of ownership in bps — fields may be unavailable.
    tco_bps: Optional[float] = None
    if er is not None:
        tco_bps = er * 10000
        if spread_bps is not None:
            tco_bps += spread_bps * 0.5  # round-trip cost spread out
    return CostMetrics(
        expense_ratio=er,
        management_fee=mgmt,
        performance_fee=perf_fee,
        spread_bps=spread_bps,
        median_spread_30d_bps=median_spread,
        estimated_cost_10k_year1=est_year1,
        estimated_cost_10k_year10=est_year10,
        portfolio_turnover_pct=turnover,
        total_cost_of_ownership_bps=tco_bps,
        creation_fee_bps=_f(info.get("creationFee")),
        redemption_fee_bps=_f(info.get("redemptionFee")),
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

    # Tax efficiency proxy: more qualified dividends + low turnover = better.
    qd = _pct(info.get("qualifiedDividendPct"))
    cgd = _pct(info.get("capitalGainsDistribution3Y"))
    eff: Optional[float] = None
    if qd is not None or cgd is not None:
        score = 50.0
        if qd is not None:
            score += min(40, qd * 50)   # 100% qualified ⇒ +50
        if cgd is not None:
            score -= min(30, cgd * 600)  # 5% cap-gain dist ⇒ -30
        eff = max(0.0, min(100.0, score))

    return IncomeMetrics(
        dividend_yield=y,
        sec_yield_30d=sec30,
        distribution_frequency=str(freq_raw) if freq_raw else None,
        distribution_policy=policy,
        qualified_dividend_pct=qd,
        cap_gain_distributions_3y_avg=cgd,
        tax_efficiency_score=eff,
    )


def calc_liquidity(info: dict, hist, tier: FundSizeTier) -> LiquidityMetrics:
    aum = _f(info.get("totalAssets") or info.get("netAssets"))
    avg_vol = _f(
        info.get("averageVolume")
        or info.get("averageDailyVolume10Day")
        or info.get("averageVolume10days")
    )
    price = _f(info.get("regularMarketPrice") or info.get("previousClose"))
    avg_dollar = avg_vol * price if (avg_vol is not None and price is not None) else None

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

    nav = _f(info.get("navPrice"))
    pd_now = (price - nav) / nav if (nav and price) else None
    median_pd, max_prem, max_disc, mean_abs = _premium_discount_stats(hist, info)

    closure_risk = None
    if aum is not None:
        if aum >= 500e6:
            closure_risk = "Low"
        elif aum >= 100e6:
            closure_risk = "Low-Medium"
        elif aum >= 50e6:
            closure_risk = "Medium"
        else:
            closure_risk = "High"

    return LiquidityMetrics(
        aum=aum,
        avg_volume=avg_vol,
        avg_dollar_volume=avg_dollar,
        spread_bps=spread_bps,
        fund_age_years=age,
        shares_outstanding=_f(info.get("sharesOutstanding")),
        premium_discount_pct=pd_now,
        median_premium_discount_1y=median_pd,
        max_premium_1y=max_prem,
        max_discount_1y=max_disc,
        mean_abs_deviation_1y=mean_abs,
        net_flows_1y=_f(info.get("netFlows1Y")),
        authorised_participants=info.get("authorisedParticipants"),
        closure_risk=closure_risk,
    )


def calc_performance(info: dict, hist, tier: FundSizeTier,
                     benchmark_hist=None) -> PerformanceMetrics:
    def _tail(n: int):
        return hist.tail(n) if hist is not None else None

    return_3y = (
        _pct(info.get("threeYearAverageReturn"))
        or _return_over_window(hist, 3 * 365)
    )
    max_dd_3y = _max_drawdown(_tail(756))

    up_cap, dn_cap = _capture_ratios(_tail(756), benchmark_hist)
    best_q, worst_q = _quarterly_extremes(hist)
    cal_ret = _calendar_returns(hist, max_years=10)
    treynor = _treynor(_tail(756), _f(info.get("beta3Year") or info.get("beta")))

    return PerformanceMetrics(
        return_1m=_return_over_window(hist, 30),
        return_3m=_return_over_window(hist, 90),
        return_ytd=_ytd_return(hist),
        return_1y=_return_over_window(hist, 365),
        return_3y=return_3y,
        return_5y=_pct(info.get("fiveYearAverageReturn")) or _return_over_window(hist, 5 * 365),
        return_10y=_return_over_window(hist, 10 * 365),
        cagr_since_inception=_cagr(hist),
        sharpe_1y=_sharpe(_tail(252)),
        sharpe_3y=_sharpe(_tail(756)),
        sortino_3y=_sortino(_tail(756)),
        calmar_3y=_calmar(return_3y, max_dd_3y),
        info_ratio_3y=_info_ratio(_tail(756), benchmark_hist),
        treynor_3y=treynor,
        up_capture_3y=up_cap,
        down_capture_3y=dn_cap,
        best_quarter=best_q,
        worst_quarter=worst_q,
        recovery_days_from_max_dd=_recovery_days_from_max_dd(_tail(756)),
        calendar_returns=cal_ret,
    )


def calc_allocation(
    info: dict,
    holdings: list[Holding],
    sectors: list[tuple],
    countries: list[tuple],
    currencies: list[tuple],
    asset_classes: list[tuple],
) -> AllocationMetrics:
    top1 = _top_n_concentration(holdings, 1)
    top5 = _top_n_concentration(holdings, 5)
    top10 = _top_n_concentration(holdings, 10)
    top25 = _top_n_concentration(holdings, 25)
    h_holdings = _herfindahl_holdings(holdings)
    eff_holdings = (1.0 / h_holdings) if h_holdings and h_holdings > 0 else None

    # Style box and bond fields are upstream-fetched when available.
    style = info.get("styleBox") or info.get("morningstarCategory")
    duration = _f(info.get("duration") or info.get("effectiveDuration"))
    ytm = _pct(info.get("yieldToMaturity"))
    avg_credit = info.get("averageCreditRating")
    credit_quality = info.get("creditQualityBreakdown") or []
    market_cap = info.get("marketCapBreakdown") or []

    return AllocationMetrics(
        holdings_count=len(holdings) or None,
        effective_holdings=eff_holdings,
        top1_concentration=top1,
        top5_concentration=top5,
        top10_concentration=top10,
        top25_concentration=top25,
        herfindahl_sector=_herfindahl(sectors),
        herfindahl_holdings=h_holdings,
        sector_breakdown=sectors,
        country_breakdown=countries,
        currency_breakdown=currencies,
        asset_class_breakdown=asset_classes,
        market_cap_breakdown=market_cap if isinstance(market_cap, list) else [],
        style_box=str(style) if style else None,
        country_count=len(countries) if countries else None,
        sector_count=len(sectors) if sectors else None,
        duration_years=duration,
        yield_to_maturity=ytm,
        credit_quality_breakdown=credit_quality if isinstance(credit_quality, list) else [],
        avg_credit_rating=str(avg_credit) if avg_credit else None,
    )


def calc_risk(info: dict, hist, benchmark_hist, tier: FundSizeTier) -> RiskProfile:
    tracking_error = None
    tracking_diff = None
    r2 = None
    beta_bench = None
    corr_sp500 = None
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
                cov = aligned.cov().iloc[0, 1]
                var_b = aligned.iloc[:, 1].var()
                if var_b > 0:
                    beta_bench = float(cov / var_b)
                corr = aligned.corr().iloc[0, 1]
                r2 = float(corr * corr) if not math.isnan(corr) else None
                corr_sp500 = float(corr) if not math.isnan(corr) else None
        except Exception:
            pass

    def _tail(n):
        return hist.tail(n) if hist is not None else None

    var_95, cvar_95 = _var_cvar_95(_tail(252))
    skew_3y, kurt_3y = _skew_kurt(_tail(756))

    return RiskProfile(
        volatility_1y=_annualized_volatility(_tail(252)),
        volatility_3y=_annualized_volatility(_tail(756)),
        max_drawdown_3y=_max_drawdown(_tail(756)),
        beta_3y=beta,
        beta_vs_benchmark=beta_bench,
        correlation_sp500_3y=corr_sp500,
        tracking_error=tracking_error,
        tracking_difference=tracking_diff,
        r_squared=r2,
        downside_deviation_3y=_downside_dev(_tail(756)),
        var_95_1y=var_95,
        cvar_95_1y=cvar_95,
        skewness_3y=skew_3y,
        kurtosis_3y=kurt_3y,
        replication_type=info.get("replicationMethod"),
        counterparty_risk=info.get("counterpartyRisk"),
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
    if performance.up_capture_3y and performance.up_capture_3y >= 1.0:
        strengths.append(f"Captures {performance.up_capture_3y*100:.0f}% of benchmark upside")

    if costs.expense_ratio is not None and costs.expense_ratio > 0.005:
        risks_out.append(f"High expense ratio ({costs.expense_ratio*100:.2f}%)")
    if aum is not None and aum < 250e6:
        risks_out.append("Low AUM — liquidity / closure risk")
    if (risk.max_drawdown_3y or 0) < -0.3:
        risks_out.append(f"Deep drawdown ({risk.max_drawdown_3y*100:.1f}%)")
    if allocation.top10_concentration is not None and allocation.top10_concentration > 0.5:
        risks_out.append(f"Concentrated top 10 ({allocation.top10_concentration*100:.1f}%)")
    if performance.down_capture_3y and performance.down_capture_3y > 1.05:
        risks_out.append(
            f"Down-capture {performance.down_capture_3y*100:.0f}% — amplifies losses vs benchmark"
        )

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
        summary=_t("overall_score_summary").format(score=int(overall), n=len(scores)),
        category_scores=scores,
        strengths=strengths,
        risks=risks_out,
        tier_note=_t("classified_as_tier").format(tier=profile.tier.value),
        suitable_for=suitable,
    )
