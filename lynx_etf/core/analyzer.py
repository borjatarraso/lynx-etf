"""ETF analysis orchestrator.

Cache-first loading: if a previous analysis exists on disk, return it.
Use ``refresh=True`` to force a fresh pull from the network.

Progressive analysis: ``run_progressive_analysis`` accepts an
*on_progress* callback that is invoked after each stage completes so
that UIs can render sections as data becomes available.
"""

from __future__ import annotations

import dataclasses
from typing import Callable, Optional

from rich.console import Console

from lynx_etf.core.fetcher import (
    fetch_asset_class_breakdown,
    fetch_benchmark_history,
    fetch_country_breakdown,
    fetch_history,
    fetch_holdings,
    fetch_info,
    fetch_profile,
    fetch_sector_breakdown,
)
from lynx_etf.core.news import fetch_all_news
from lynx_etf.core.storage import (
    get_cache_age_hours,
    has_cache,
    load_cached_report,
    save_analysis_report,
)
from lynx_etf.core.ticker import NotAnETFError, resolve_identifier
from lynx_etf.metrics.calculator import (
    build_verdict,
    calc_allocation,
    calc_costs,
    calc_income,
    calc_liquidity,
    calc_performance,
    calc_risk,
)
from lynx_etf.models import (
    AllocationMetrics,
    CostMetrics,
    ETFProfile,
    ETFReport,
    FundSizeTier,
    Holding,
    IncomeMetrics,
    LiquidityMetrics,
    NewsArticle,
    PerformanceMetrics,
    RiskProfile,
    Verdict,
    classify_tier,
)


console = Console(stderr=True)

ProgressCallback = Callable[[str, ETFReport], None]


def run_full_analysis(
    identifier: str,
    download_news: bool = True,
    verbose: bool = False,
    refresh: bool = False,
) -> ETFReport:
    """Synchronous wrapper around :func:`run_progressive_analysis`."""
    return run_progressive_analysis(
        identifier=identifier,
        download_news=download_news,
        verbose=verbose,
        refresh=refresh,
        on_progress=None,
    )


def run_progressive_analysis(
    identifier: str,
    download_news: bool = True,
    verbose: bool = False,
    refresh: bool = False,
    on_progress: Optional[ProgressCallback] = None,
) -> ETFReport:
    """Run a progressive ETF analysis, notifying after each stage.

    Stages: ``profile``, ``costs``, ``income``, ``liquidity``,
    ``performance``, ``allocation``, ``risk``, ``verdict``, ``news``,
    ``complete``.
    """

    def _notify(stage: str, report: ETFReport) -> None:
        if on_progress is not None:
            on_progress(stage, report)

    # 1. Resolve (validates that it's an ETF) -----------------------------
    console.print(f"[bold cyan]Resolving identifier:[/] {identifier}")
    try:
        ticker, isin = resolve_identifier(identifier)
    except NotAnETFError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise

    console.print(
        f"[green]Ticker:[/] {ticker}"
        + (f"  [dim]ISIN: {isin}[/dim]" if isin else "")
    )

    # 2. Cache check -------------------------------------------------------
    if not refresh and has_cache(ticker):
        age = get_cache_age_hours(ticker)
        age_str = f"{age:.1f}h ago" if age is not None else "unknown age"
        console.print(f"[bold green]Using cached data[/] [dim](fetched {age_str})[/]")
        cached = load_cached_report(ticker)
        if cached:
            try:
                report = _dict_to_report(cached)
                if isin and report.profile.isin is None:
                    report.profile.isin = isin
                console.print("[dim]Use --refresh to force fresh data download.[/]")
                _notify("complete", report)
                return report
            except Exception as exc:
                console.print(f"[yellow]Cached data is corrupt ({exc}), re-fetching...[/]")

    # 3. Fresh fetch — profile --------------------------------------------
    if refresh:
        console.print("[yellow]Refreshing data from network...[/]")

    console.print("[cyan]Fetching ETF profile...[/]")
    info = fetch_info(ticker)
    profile = fetch_profile(ticker, info=info)
    profile.isin = isin
    if profile.aum is not None:
        profile.tier = classify_tier(profile.aum)

    console.print(
        f"[green]{profile.name}[/] — "
        f"{profile.category or 'N/A'} / {profile.asset_class or 'N/A'}"
        f"  [bold][{_tier_color(profile.tier)}]{profile.tier.value}[/]"
    )

    report = ETFReport(profile=profile)
    _notify("profile", report)

    tier = profile.tier

    # 4. Price history (shared across several calculators) ----------------
    console.print("[cyan]Fetching price history...[/]")
    hist = fetch_history(ticker, period="10y")

    # 5. Costs -------------------------------------------------------------
    report.costs = calc_costs(info, tier)
    _notify("costs", report)

    # 6. Income ------------------------------------------------------------
    report.income = calc_income(info, tier)
    _notify("income", report)

    # 7. Liquidity ---------------------------------------------------------
    report.liquidity = calc_liquidity(info, hist, tier)
    _notify("liquidity", report)

    # 8. Performance -------------------------------------------------------
    report.performance = calc_performance(info, hist, tier)
    _notify("performance", report)

    # 9. Allocation --------------------------------------------------------
    console.print("[cyan]Fetching holdings & allocation...[/]")
    holdings = fetch_holdings(ticker, info=info)
    sectors = fetch_sector_breakdown(ticker, info=info)
    countries = fetch_country_breakdown(ticker, info=info)
    currencies: list[tuple] = []
    asset_classes = fetch_asset_class_breakdown(ticker, info=info)
    report.holdings = holdings
    report.allocation = calc_allocation(info, holdings, sectors, countries, currencies, asset_classes)
    _notify("allocation", report)

    # 10. Risk (vs benchmark if available) --------------------------------
    benchmark_hist = None
    if profile.benchmark:
        console.print(f"[cyan]Fetching benchmark {profile.benchmark}...[/]")
        benchmark_hist = fetch_benchmark_history(profile.benchmark, period="5y")
    report.risk = calc_risk(info, hist, benchmark_hist, tier)
    _notify("risk", report)

    # 11. Verdict ---------------------------------------------------------
    report.verdict = build_verdict(
        profile,
        report.costs,
        report.income,
        report.liquidity,
        report.performance,
        report.allocation,
        report.risk,
    )
    _notify("verdict", report)

    # 12. News ------------------------------------------------------------
    if download_news:
        console.print("[cyan]Fetching news...[/]")
        try:
            report.news = fetch_all_news(ticker, profile.name) or []
            console.print(f"[green]Found {len(report.news)} articles[/]")
        except Exception as exc:
            console.print(f"[yellow]News fetch failed: {exc}[/]")
    _notify("news", report)

    # 13. Save ------------------------------------------------------------
    console.print("[cyan]Saving analysis...[/]")
    path = save_analysis_report(ticker, _report_to_dict(report))
    console.print(f"[bold green]Analysis saved to:[/] {path}")
    _notify("complete", report)

    return report


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _report_to_dict(report: ETFReport) -> dict:
    def _dc(obj):
        if obj is None:
            return None
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: _dc(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, list):
            return [_dc(i) for i in obj]
        if isinstance(obj, tuple):
            return list(obj)
        return obj
    return _dc(report)


def _dict_to_report(d: dict) -> ETFReport:
    profile_raw = d.get("profile", {}) or {}
    profile = _build_dc(ETFProfile, profile_raw)
    profile.tier = _parse_tier(profile_raw.get("tier", ""))

    def _maybe(cls, key):
        raw = d.get(key)
        if raw is None:
            return None
        return _build_dc(cls, raw)

    return ETFReport(
        profile=profile,
        costs=_maybe(CostMetrics, "costs"),
        income=_maybe(IncomeMetrics, "income"),
        liquidity=_maybe(LiquidityMetrics, "liquidity"),
        performance=_maybe(PerformanceMetrics, "performance"),
        allocation=_maybe(AllocationMetrics, "allocation"),
        risk=_maybe(RiskProfile, "risk"),
        verdict=_maybe(Verdict, "verdict"),
        holdings=[_build_dc(Holding, h) for h in (d.get("holdings") or [])],
        news=[_build_dc(NewsArticle, n) for n in (d.get("news") or [])],
        fetched_at=d.get("fetched_at", ""),
    )


def _build_dc(cls, data: dict):
    import dataclasses as dc
    if not isinstance(data, dict):
        return cls()
    field_names = {f.name for f in dc.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def _parse_tier(raw) -> FundSizeTier:
    if isinstance(raw, FundSizeTier):
        return raw
    raw_str = str(raw)
    for t in FundSizeTier:
        if t.value == raw_str or t.name == raw_str:
            return t
    return FundSizeTier.NANO


def _tier_color(tier: FundSizeTier) -> str:
    return {
        FundSizeTier.MEGA: "bold green",
        FundSizeTier.LARGE: "green",
        FundSizeTier.MID: "cyan",
        FundSizeTier.SMALL: "yellow",
        FundSizeTier.MICRO: "#ff8800",
        FundSizeTier.NANO: "bold red",
    }.get(tier, "white")
