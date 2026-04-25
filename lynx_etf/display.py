"""Rich console display for ETF analysis reports.

Mirrors the visual structure of ``lynx.display`` (lynx-fundamental):

* A header `Panel` with white-on-blue title text.
* A separate tier banner `Panel` whose border colour reflects fund size.
* The fund profile in a `Panel(table, border_style="cyan")`.
* Section tables use `show_lines=True` and a section-specific border
  colour (yellow / green / cyan / magenta / bold yellow / red) — the
  same hue vocabulary the rest of the Suite uses.
* The verdict is rendered as a coloured `Panel`, followed by a
  ``Category Scores`` table and a side-by-side strengths / risks table —
  the exact pattern lynx-fundamental uses for its conclusion section.
"""

from __future__ import annotations
from lynx_investor_core.translations import t as _t  # i18n helper

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lynx_etf import APP_NAME, SUITE_LABEL, __version__
from lynx_etf.models import ETFReport, FundSizeTier


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def fmt_pct(v: Optional[float], decimals: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v*100:.{decimals}f}%"


def fmt_bps(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.1f} bps"


def fmt_num(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:,.{digits}f}"


def fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e12:
        return f"${v/1e12:.2f}T"
    if a >= 1e9:
        return f"${v/1e9:.2f}B"
    if a >= 1e6:
        return f"${v/1e6:.2f}M"
    if a >= 1e3:
        return f"${v/1e3:.2f}K"
    return f"${v:.2f}"


def fmt_int(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def fmt_years(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.1f} yr"


def _fmt_score(score: Optional[float]) -> str:
    if score is None:
        return "[dim]N/A[/]"
    if score >= 80:
        return f"[bold green]{score:.1f}/100[/]"
    if score >= 65:
        return f"[green]{score:.1f}/100[/]"
    if score >= 50:
        return f"[cyan]{score:.1f}/100[/]"
    if score >= 35:
        return f"[yellow]{score:.1f}/100[/]"
    return f"[bold red]{score:.1f}/100[/]"


def verdict_style(verdict: str) -> str:
    return {
        "Strong Buy": "bold green",
        "Buy": "green",
        "Hold": "cyan",
        "Caution": "yellow",
        "Avoid": "bold red",
    }.get(verdict, "white")


def tier_style(tier: FundSizeTier) -> str:
    return {
        FundSizeTier.MEGA: "bold green",
        FundSizeTier.LARGE: "green",
        FundSizeTier.MID: "cyan",
        FundSizeTier.SMALL: "yellow",
        FundSizeTier.MICRO: "#ff8800",
        FundSizeTier.NANO: "bold red",
    }.get(tier, "white")


def _tier_label(tier: FundSizeTier) -> str:
    return {
        FundSizeTier.MEGA:  "MEGA AUM — Flagship-scale liquidity & cost basis",
        FundSizeTier.LARGE: "LARGE AUM — Highly liquid, mainstream allocation",
        FundSizeTier.MID:   "MID AUM — Stable but watch spreads in stress",
        FundSizeTier.SMALL: "SMALL AUM — Niche / younger fund, tighter due diligence",
        FundSizeTier.MICRO: "MICRO AUM — Closure / liquidity risk material",
        FundSizeTier.NANO:  "NANO AUM — Speculative; closure risk high",
    }.get(tier, "UNKNOWN")


def _colored_er(er: Optional[float]) -> Text:
    if er is None:
        return Text("—")
    value = f"{er*100:.3f}%"
    if er < 0.001:
        return Text(value, style="bold green")
    if er < 0.002:
        return Text(value, style="green")
    if er < 0.005:
        return Text(value, style="cyan")
    if er < 0.01:
        return Text(value, style="yellow")
    return Text(value, style="bold red")


def _colored_return(r: Optional[float]) -> Text:
    if r is None:
        return Text("—")
    sign = "+" if r >= 0 else ""
    value = f"{sign}{r*100:.2f}%"
    return Text(value, style="green" if r >= 0 else "red")


# ---------------------------------------------------------------------------
# Header & profile
# ---------------------------------------------------------------------------

def render_header(console: Console, report: ETFReport) -> None:
    """Header banner + tier banner, mirroring lynx-fundamental's _display_header."""
    p = report.profile

    # Title bar — white-on-blue, with ticker accent
    header = Text()
    header.append(f"  {p.name or p.ticker}", style="bold white on blue")
    header.append(f"  ({p.ticker})", style="bold cyan on blue")
    if p.isin:
        header.append(f"  ISIN: {p.isin}", style="dim on blue")
    console.print(Panel(
        header,
        title="[bold]LYNX ETF Analysis[/]",
        border_style="blue",
    ))

    # Tier banner
    tc = tier_style(p.tier)
    console.print(Panel(
        f"[{tc}]{_tier_label(p.tier)}[/]\n"
        f"[dim]Section colours follow the Suite vocabulary: "
        f"costs=yellow, income=green, liquidity=cyan, "
        f"performance=magenta, allocation=bold yellow, risk=red.[/]",
        border_style=tc,
        title=f"[{tc}]{p.tier.value}[/]",
    ))

    # Profile card
    profile_table = Table(show_header=False, box=None, padding=(0, 2))
    profile_table.add_column("Key", style="bold")
    profile_table.add_column(_t("value"))
    profile_table.add_row(_t("name"), p.name or "[dim]N/A[/]")
    profile_table.add_row(_t("family"), p.fund_family or "[dim]N/A[/]")
    profile_table.add_row(_t("category"), p.category or "[dim]N/A[/]")
    profile_table.add_row(_t("asset_class"), p.asset_class or "[dim]N/A[/]")
    profile_table.add_row(_t("domicile"), p.domicile or "[dim]N/A[/]")
    profile_table.add_row(_t("inception"), p.inception_date or "[dim]N/A[/]")
    profile_table.add_row(_t("benchmark"), p.benchmark or "[dim]N/A[/]")
    profile_table.add_row(_t("distribution"), p.distribution_policy or "[dim]N/A[/]")
    profile_table.add_row(_t("aum"), fmt_money(p.aum))
    profile_table.add_row(_t("size_tier"), f"[{tc}]{p.tier.value}[/]")
    console.print(Panel(
        profile_table,
        title=f"[bold]{_t('fund_profile')}[/]",
        border_style="cyan",
    ))


# ---------------------------------------------------------------------------
# Section tables — section colours match lynx-fundamental's vocabulary
# ---------------------------------------------------------------------------

def render_costs(console: Console, report: ETFReport) -> None:
    c = report.costs
    if not c:
        return
    t = Table(title=_t("costs"), show_lines=True, border_style="yellow")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=18)
    t.add_column(_t("assessment"), min_width=28)

    er = c.expense_ratio
    if er is None:
        er_assess = "[dim]N/A[/]"
    elif er < 0.001:
        er_assess = "[bold green]Industry-leading[/]"
    elif er < 0.002:
        er_assess = "[green]Very low — institutional-tier[/]"
    elif er < 0.005:
        er_assess = "[cyan]Low — competitive[/]"
    elif er < 0.01:
        er_assess = "[yellow]Average[/]"
    else:
        er_assess = "[bold red]High — drag on long-term return[/]"
    t.add_row("Expense Ratio (TER)", _colored_er(er), er_assess)

    t.add_row("Management Fee", fmt_pct(c.management_fee, 3), "")
    t.add_row("Bid-Ask Spread", fmt_bps(c.spread_bps),
              "[dim]Round-trip cost on top of TER[/]" if c.spread_bps else "")
    if c.estimated_cost_10k_year1 is not None:
        t.add_row("Est. yr-1 cost on $10k",
                  f"${c.estimated_cost_10k_year1:.2f}", "")
    console.print(t)


def render_income(console: Console, report: ETFReport) -> None:
    i = report.income
    if not i:
        return
    t = Table(title=_t("income"), show_lines=True, border_style="green")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=18)
    t.add_column(_t("assessment"), min_width=28)

    def _yield_assess(y):
        if y is None:
            return "[dim]N/A[/]"
        if y >= 0.04:
            return "[bold green]High income[/]"
        if y >= 0.02:
            return "[green]Solid income[/]"
        if y >= 0.005:
            return "[cyan]Modest[/]"
        return "[dim]Low / accumulating[/]"

    t.add_row("Dividend Yield (TTM)", fmt_pct(i.dividend_yield),
              _yield_assess(i.dividend_yield))
    t.add_row("SEC 30-day Yield", fmt_pct(i.sec_yield_30d),
              _yield_assess(i.sec_yield_30d))
    t.add_row("Distribution Frequency",
              i.distribution_frequency or "[dim]N/A[/]", "")
    t.add_row("Distribution Policy",
              i.distribution_policy or "[dim]N/A[/]", "")
    console.print(t)


def render_liquidity(console: Console, report: ETFReport) -> None:
    l = report.liquidity
    if not l:
        return
    t = Table(title=_t("liquidity"), show_lines=True, border_style="cyan")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=18)
    t.add_column(_t("assessment"), min_width=28)

    aum_assess = "[dim]N/A[/]"
    if l.aum is not None:
        if l.aum >= 50e9:
            aum_assess = "[bold green]Mega scale[/]"
        elif l.aum >= 10e9:
            aum_assess = "[green]Large, mainstream[/]"
        elif l.aum >= 1e9:
            aum_assess = "[cyan]Mid-tier — solid liquidity[/]"
        elif l.aum >= 100e6:
            aum_assess = "[yellow]Small — watch spreads[/]"
        else:
            aum_assess = "[bold red]Micro / closure risk[/]"
    t.add_row(_t("aum"), fmt_money(l.aum), aum_assess)

    t.add_row("Avg Daily Volume", fmt_int(l.avg_volume), "")
    t.add_row("Avg Daily $ Volume", fmt_money(l.avg_dollar_volume), "")
    t.add_row("Bid-Ask Spread", fmt_bps(l.spread_bps), "")
    t.add_row("Fund Age", fmt_years(l.fund_age_years),
              "[green]Track record established[/]"
              if (l.fund_age_years or 0) >= 5 else "[yellow]Younger fund[/]")
    t.add_row("Shares Outstanding", fmt_int(l.shares_outstanding), "")
    if l.premium_discount_pct is not None:
        pd = l.premium_discount_pct
        pd_assess = "[green]Trading near NAV[/]" if abs(pd) < 0.001 else "[yellow]Persistent gap to NAV[/]"
        t.add_row("Premium / Discount", fmt_pct(pd, 3), pd_assess)
    console.print(t)


def render_performance(console: Console, report: ETFReport) -> None:
    p = report.performance
    if not p:
        return

    # Returns table — magenta border like lynx-fundamental's growth section
    t = Table(title=_t("performance"),
              show_lines=True, border_style="magenta")
    t.add_column("Window", style="bold", min_width=22)
    t.add_column("Return", justify="right", min_width=18)
    t.add_column("Notes", min_width=28)
    rows = [
        ("1M",  p.return_1m, ""),
        ("3M",  p.return_3m, ""),
        ("YTD", p.return_ytd, ""),
        ("1Y",  p.return_1y, ""),
        ("3Y CAGR", p.return_3y, ""),
        ("5Y CAGR", p.return_5y, "[dim]Long-run trend[/]"),
        ("10Y CAGR", p.return_10y, "[dim]Cycle-spanning[/]"),
        ("Since Inception CAGR", p.cagr_since_inception, ""),
    ]
    for label, val, note in rows:
        t.add_row(label, _colored_return(val), note)
    console.print(t)

    # Risk-adjusted returns — cyan border to flag separate concept
    t2 = Table(title=f"{_t('performance')} — {_t('score')}",
               show_lines=True, border_style="cyan")
    t2.add_column(_t("metric"), style="bold", min_width=22)
    t2.add_column(_t("value"), justify="right", min_width=18)
    t2.add_column(_t("assessment"), min_width=28)

    def _sharpe_assess(s):
        if s is None:
            return "[dim]N/A[/]"
        if s >= 1.5:
            return "[bold green]Excellent[/]"
        if s >= 1.0:
            return "[green]Strong[/]"
        if s >= 0.5:
            return "[cyan]Acceptable[/]"
        if s >= 0:
            return "[yellow]Weak[/]"
        return "[bold red]Negative[/]"

    t2.add_row("Sharpe (1Y)", fmt_num(p.sharpe_1y), _sharpe_assess(p.sharpe_1y))
    t2.add_row("Sharpe (3Y)", fmt_num(p.sharpe_3y), _sharpe_assess(p.sharpe_3y))
    t2.add_row("Sortino (3Y)", fmt_num(p.sortino_3y),
               _sharpe_assess(p.sortino_3y))
    console.print(t2)


def render_allocation(console: Console, report: ETFReport) -> None:
    a = report.allocation
    if not a:
        return

    # Diversification overview — bold yellow like the moat panel
    t = Table(title=_t("diversification"),
              show_lines=True, border_style="bold yellow")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=18)
    t.add_column(_t("assessment"), min_width=28)

    def _conc_assess(c):
        if c is None:
            return "[dim]N/A[/]"
        if c >= 0.5:
            return "[bold red]Highly concentrated[/]"
        if c >= 0.35:
            return "[yellow]Concentrated[/]"
        if c >= 0.20:
            return "[cyan]Moderate[/]"
        return "[green]Well-diversified[/]"

    t.add_row("Holdings Count", fmt_int(a.holdings_count), "")
    t.add_row("Top 10 Concentration", fmt_pct(a.top10_concentration),
              _conc_assess(a.top10_concentration))
    t.add_row("Sector HHI", fmt_num(a.herfindahl_sector, 3),
              "[dim]Lower = more even sector mix[/]"
              if a.herfindahl_sector is not None else "")
    t.add_row("Sector Count", fmt_int(a.sector_count), "")
    t.add_row("Country Count", fmt_int(a.country_count), "")
    console.print(t)

    if a.sector_breakdown:
        st = Table(title="Sector Breakdown",
                   show_lines=True, border_style="blue")
        st.add_column("Sector", style="bold", min_width=22)
        st.add_column("Weight", justify="right", min_width=12)
        for sector, weight in a.sector_breakdown[:12]:
            st.add_row(str(sector), fmt_pct(weight))
        console.print(st)

    if a.country_breakdown:
        ct = Table(title="Country Breakdown",
                   show_lines=True, border_style="blue")
        ct.add_column("Country", style="bold", min_width=22)
        ct.add_column("Weight", justify="right", min_width=12)
        for country, weight in a.country_breakdown[:10]:
            ct.add_row(str(country), fmt_pct(weight))
        console.print(ct)


def render_holdings(console: Console, report: ETFReport) -> None:
    if not report.holdings:
        return
    n = min(len(report.holdings), 15)
    t = Table(title=f"Top {n} Holdings",
              show_lines=True, border_style="cyan")
    t.add_column("#", justify="right", min_width=3)
    t.add_column("Symbol", style="bold cyan")
    t.add_column("Name", min_width=24)
    t.add_column("Weight", justify="right", min_width=10)
    ordered = sorted(report.holdings, key=lambda h: h.weight or 0, reverse=True)[:15]
    for i, h in enumerate(ordered, 1):
        t.add_row(str(i), h.symbol or "[dim]—[/]",
                  h.name or "[dim]—[/]", fmt_pct(h.weight))
    console.print(t)


def render_risk(console: Console, report: ETFReport) -> None:
    r = report.risk
    if not r:
        return
    t = Table(title=_t("risk"),
              show_lines=True, border_style="red")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=18)
    t.add_column(_t("assessment"), min_width=28)

    def _vol_assess(v):
        if v is None:
            return "[dim]N/A[/]"
        if v < 0.10:
            return "[green]Low volatility[/]"
        if v < 0.18:
            return "[cyan]Equity-like[/]"
        if v < 0.30:
            return "[yellow]Elevated[/]"
        return "[bold red]High[/]"

    def _drawdown_assess(dd):
        if dd is None:
            return "[dim]N/A[/]"
        if dd > -0.10:
            return "[green]Mild[/]"
        if dd > -0.20:
            return "[cyan]Typical equity[/]"
        if dd > -0.40:
            return "[yellow]Severe[/]"
        return "[bold red]Crash-tier[/]"

    t.add_row("Volatility (1Y)", fmt_pct(r.volatility_1y), _vol_assess(r.volatility_1y))
    t.add_row("Volatility (3Y)", fmt_pct(r.volatility_3y), _vol_assess(r.volatility_3y))
    t.add_row("Max Drawdown (3Y)", fmt_pct(r.max_drawdown_3y),
              _drawdown_assess(r.max_drawdown_3y))
    t.add_row("Beta (3Y)", fmt_num(r.beta_3y),
              "[dim]Sensitivity to benchmark[/]" if r.beta_3y is not None else "")
    t.add_row("Tracking Error", fmt_pct(r.tracking_error),
              "[dim]Annualised σ of return gap[/]" if r.tracking_error is not None else "")
    t.add_row("Tracking Difference", fmt_pct(r.tracking_difference),
              "[dim]TER-adjusted return gap[/]" if r.tracking_difference is not None else "")
    t.add_row("R²", fmt_num(r.r_squared, 3),
              "[dim]Explained variance vs benchmark[/]" if r.r_squared is not None else "")
    console.print(t)


# ---------------------------------------------------------------------------
# Verdict — mirrors lynx-fundamental's _display_conclusion
# ---------------------------------------------------------------------------

def render_verdict(console: Console, report: ETFReport) -> None:
    v = report.verdict
    if not v:
        return
    style = verdict_style(v.verdict)

    # Verdict panel
    summary = getattr(v, "summary", None) or ""
    tier_note = getattr(v, "tier_note", None) or ""
    body = (
        f"[{style}]{v.verdict}[/]  —  Score: {_fmt_score(v.overall_score)}\n\n"
        f"{summary}\n\n"
        f"[dim]{tier_note}[/]"
    ).strip()
    console.print(Panel(
        body,
        title=f"[bold]{_t('verdict')}[/]",
        border_style=style,
    ))

    # Category breakdown
    if v.category_scores:
        t = Table(title="Category Scores",
                  show_lines=True, border_style="cyan")
        t.add_column(_t("category"), style="bold", min_width=18)
        t.add_column("Score", justify="right", min_width=12)
        t.add_column("Bar", min_width=24)
        for cat, score in v.category_scores.items():
            try:
                s = float(score)
            except (TypeError, ValueError):
                s = 0.0
            bar_len = max(0, min(20, int(round(s / 5))))
            bar = "█" * bar_len + "·" * (20 - bar_len)
            t.add_row(str(cat).title(), _fmt_score(s),
                      f"[{_score_color_token(s)}]{bar}[/]")
        console.print(t)

    # Strengths & Risks side by side
    strengths = getattr(v, "strengths", None) or []
    risks = getattr(v, "risks", None) or []
    if strengths or risks:
        sr = Table(show_header=True, border_style="green")
        sr.add_column("Strengths", style="green", ratio=1)
        sr.add_column("Risks", style="red", ratio=1)
        max_len = max(len(strengths), len(risks))
        for i in range(max_len):
            s = strengths[i] if i < len(strengths) else ""
            r = risks[i] if i < len(risks) else ""
            sr.add_row(str(s), str(r))
        console.print(sr)

    # Suitable-for footer
    suitable = getattr(v, "suitable_for", None) or []
    if suitable:
        console.print(
            f"[dim]Suitable for:[/] [cyan]{', '.join(suitable)}[/]"
        )


def _score_color_token(s: float) -> str:
    if s >= 80:
        return "bold green"
    if s >= 65:
        return "green"
    if s >= 50:
        return "cyan"
    if s >= 35:
        return "yellow"
    return "red"


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def render_news(console: Console, report: ETFReport, limit: int = 5) -> None:
    if not report.news:
        return
    t = Table(title=f"News (latest {min(limit, len(report.news))})",
              show_lines=True, border_style="cyan")
    t.add_column("Date", style="bold", min_width=12)
    t.add_column("Source", min_width=14)
    t.add_column("Title", min_width=40)
    for n in report.news[:limit]:
        t.add_row(n.published or "[dim]—[/]",
                  n.source or "[dim]—[/]",
                  n.title or "[dim]—[/]")
    console.print(t)


# ---------------------------------------------------------------------------
# Structure / regulatory section
# ---------------------------------------------------------------------------

def render_structure(console: Console, report: ETFReport) -> None:
    """Replication, UCITS, securities lending, hedging, leverage, index quality."""
    p = report.profile
    rows = []

    def _row(label: str, value, note: str = ""):
        rows.append((label, value if value not in (None, "") else "[dim]N/A[/]", note))

    rows_added_by_helper = lambda: bool(rows)

    _row("Regulatory Type", p.regulatory_type or "ETF",
         "[dim]ETN/ETC carry issuer credit risk[/]")
    if p.ucits is not None:
        _row("UCITS", "Yes" if p.ucits else "No",
             "[green]EU retail-eligible[/]" if p.ucits else "[yellow]Not EU-passportable[/]")
    if p.kiid_prr_risk_rating is not None:
        _row("KIID Risk (1-7)", str(p.kiid_prr_risk_rating),
             "[dim]Lower = less volatile (UCITS SRRI)[/]")

    rep = (p.replication or "").lower()
    if p.replication:
        if "synthetic" in rep or "swap" in rep:
            note = "[yellow]Counterparty risk — verify swap collateralisation[/]"
        elif "sample" in rep:
            note = "[dim]Acceptable for very large or illiquid indices[/]"
        else:
            note = "[green]Direct ownership of the underlying basket[/]"
        _row("Replication", p.replication, note)

    if p.swap_counterparties:
        _row("Swap Counterparties", ", ".join(p.swap_counterparties),
             "[dim]Disclosed in prospectus[/]")

    if p.securities_lending is not None:
        if p.securities_lending:
            split = p.lending_revenue_split
            label = (
                f"Yes ({split*100:.0f}% of revenue to investors)"
                if split is not None else "Yes"
            )
            if split is not None and split >= 0.85:
                lend_note = "[green]Investor-aligned split[/]"
            elif split is not None and split >= 0.65:
                lend_note = "[yellow]Average split[/]"
            elif split is not None:
                lend_note = "[red]Issuer keeps the bulk[/]"
            else:
                lend_note = "[dim]Split not disclosed[/]"
            _row("Securities Lending", label, lend_note)
        else:
            _row("Securities Lending", "No",
                 "[green]No counterparty risk from lending[/]")

    if p.leverage_factor is not None:
        if abs(p.leverage_factor - 1.0) < 0.01:
            _row("Leverage Factor", "1.0×", "[green]Plain-vanilla; buy-and-hold OK[/]")
        elif p.leverage_factor < 0:
            _row("Leverage Factor", f"{p.leverage_factor:+.1f}×",
                 "[red]Inverse — daily-rebalanced; volatility decay[/]")
        else:
            _row("Leverage Factor", f"{p.leverage_factor:+.1f}×",
                 "[red]Leveraged — not a passive instrument[/]")

    if p.currency_hedged is not None:
        if p.currency_hedged:
            _row("Currency Hedge", f"Hedged to {p.hedged_to or 'home currency'}",
                 "[dim]Adds 0.10–0.30% annual hedging cost[/]")
        else:
            _row("Currency Hedge", "Unhedged",
                 "[dim]Direct FX exposure[/]")

    # Index quality block ----------------------------------------------------
    if p.index_provider or p.index_name:
        _row("Index Provider", p.index_provider or "[dim]N/A[/]")
    if p.index_name:
        _row("Index Name", p.index_name)
    if p.index_constituents is not None:
        _row("Index Constituents", fmt_int(p.index_constituents),
             "[dim]Names selected by the index methodology[/]")
    if p.rebalancing_frequency:
        _row("Rebalancing", p.rebalancing_frequency,
             "[dim]How often the basket is reconstituted[/]")
    if p.free_float_adjusted is not None:
        _row("Free-float adjusted", "Yes" if p.free_float_adjusted else "No",
             "[dim]Adjusts for shares actually available to trade[/]")

    if not rows_added_by_helper():
        return

    t = Table(title="Structure & Regulation", show_lines=True, border_style="blue")
    t.add_column(_t("field"), style="bold", min_width=22)
    t.add_column(_t("value"), min_width=22)
    t.add_column(_t("note"), min_width=30)
    for label, value, note in rows:
        t.add_row(label, str(value), note)
    console.print(t)


# ---------------------------------------------------------------------------
# Premium / discount detail (1Y stats)
# ---------------------------------------------------------------------------

def render_premium_discount_stats(console: Console, report: ETFReport) -> None:
    l = report.liquidity
    if not l:
        return
    fields = [
        l.median_premium_discount_1y,
        l.max_premium_1y,
        l.max_discount_1y,
        l.mean_abs_deviation_1y,
        l.net_flows_1y,
        l.authorised_participants,
        l.closure_risk,
    ]
    if all(f is None for f in fields):
        return
    t = Table(title="Premium / Discount & Flows (1Y)",
              show_lines=True, border_style="cyan")
    t.add_column(_t("metric"), style="bold", min_width=24)
    t.add_column(_t("value"), justify="right", min_width=14)
    t.add_column(_t("note"), min_width=28)

    def _add(label, val, note):
        t.add_row(label, val, note)

    _add("Median Premium / Discount",
         fmt_pct(l.median_premium_discount_1y, 3),
         "[dim]Where the market typically values the fund vs NAV[/]")
    _add("Max Premium (1Y)", fmt_pct(l.max_premium_1y, 3), "")
    _add("Max Discount (1Y)", fmt_pct(l.max_discount_1y, 3), "")
    _add("Mean |Deviation| (1Y)",
         fmt_pct(l.mean_abs_deviation_1y, 3),
         "[dim]≤ 0.10% is the passive guideline[/]"
         if l.mean_abs_deviation_1y is not None else "")
    if l.net_flows_1y is not None:
        flow_note = (
            "[green]Net inflows[/]" if l.net_flows_1y > 0
            else "[yellow]Net outflows[/]"
        )
        _add("Net Flows (1Y)", fmt_money(l.net_flows_1y), flow_note)
    if l.authorised_participants is not None:
        _add("Authorised Participants",
             fmt_int(l.authorised_participants),
             "[dim]More APs ⇒ more competitive arbitrage[/]")
    if l.closure_risk:
        risk_note = {
            "Low": "[green]Closure risk negligible[/]",
            "Low-Medium": "[cyan]Closure risk modest[/]",
            "Medium": "[yellow]Closure risk noticeable[/]",
            "High": "[red]Material closure risk[/]",
        }.get(l.closure_risk, "")
        _add("Closure Risk", l.closure_risk, risk_note)
    console.print(t)


# ---------------------------------------------------------------------------
# Calendar-year return table
# ---------------------------------------------------------------------------

def render_calendar_returns(console: Console, report: ETFReport) -> None:
    if not report.performance or not report.performance.calendar_returns:
        return
    t = Table(title="Calendar-Year Returns",
              show_lines=True, border_style="magenta")
    t.add_column("Year", style="bold", min_width=6)
    t.add_column("Return", justify="right", min_width=12)
    t.add_column("Bar", min_width=24)
    rets = report.performance.calendar_returns
    abs_max = max((abs(r) for _, r in rets), default=1.0) or 1.0
    for year, ret in rets:
        bar_len = max(0, min(20, int(round(abs(ret) / abs_max * 20))))
        bar = "█" * bar_len + "·" * (20 - bar_len)
        color = "green" if ret >= 0 else "red"
        t.add_row(str(year), _colored_return(ret), f"[{color}]{bar}[/]")
    console.print(t)


# ---------------------------------------------------------------------------
# Capture ratios & advanced risk-adjusted returns
# ---------------------------------------------------------------------------

def render_capture_ratios(console: Console, report: ETFReport) -> None:
    p = report.performance
    if not p:
        return
    fields = [
        p.up_capture_3y, p.down_capture_3y, p.calmar_3y,
        p.info_ratio_3y, p.treynor_3y, p.best_quarter,
        p.worst_quarter, p.recovery_days_from_max_dd,
    ]
    if all(f is None for f in fields):
        return
    t = Table(title="Capture Ratios & Recovery",
              show_lines=True, border_style="cyan")
    t.add_column(_t("metric"), style="bold", min_width=24)
    t.add_column(_t("value"), justify="right", min_width=14)
    t.add_column(_t("interpretation"), min_width=28)

    def _capture_assess(c, kind: str):
        if c is None:
            return "[dim]N/A[/]"
        pct = c * 100
        if kind == "up":
            if c >= 1.0:
                return f"[green]{pct:.0f}% — keeps pace or beats benchmark[/]"
            if c >= 0.95:
                return f"[cyan]{pct:.0f}% — close to benchmark[/]"
            return f"[yellow]{pct:.0f}% — trails benchmark in up-markets[/]"
        if c <= 1.0:
            return f"[green]{pct:.0f}% — softer drawdowns than benchmark[/]"
        if c <= 1.05:
            return f"[cyan]{pct:.0f}% — about benchmark loss[/]"
        return f"[yellow]{pct:.0f}% — amplifies losses vs benchmark[/]"

    if p.up_capture_3y is not None:
        t.add_row("Up Capture (3Y)", fmt_num(p.up_capture_3y, 3),
                  _capture_assess(p.up_capture_3y, "up"))
    if p.down_capture_3y is not None:
        t.add_row("Down Capture (3Y)", fmt_num(p.down_capture_3y, 3),
                  _capture_assess(p.down_capture_3y, "down"))
    if p.calmar_3y is not None:
        t.add_row("Calmar (3Y)", fmt_num(p.calmar_3y),
                  "[dim]Return ÷ Max Drawdown — higher is better[/]")
    if p.info_ratio_3y is not None:
        t.add_row("Information Ratio (3Y)", fmt_num(p.info_ratio_3y),
                  "[dim]Excess vs benchmark per unit of tracking error[/]")
    if p.treynor_3y is not None:
        t.add_row("Treynor (3Y)", fmt_num(p.treynor_3y),
                  "[dim]Excess return per unit of beta[/]")
    if p.best_quarter is not None:
        t.add_row("Best Quarter", _colored_return(p.best_quarter), "")
    if p.worst_quarter is not None:
        t.add_row("Worst Quarter", _colored_return(p.worst_quarter), "")
    if p.recovery_days_from_max_dd is not None:
        days = p.recovery_days_from_max_dd
        years = days / 365.25
        t.add_row("Recovery from Max DD", f"{days} days",
                  f"[dim]≈ {years:.1f} years to retake the prior peak[/]")
    console.print(t)


# ---------------------------------------------------------------------------
# Tail-risk metrics
# ---------------------------------------------------------------------------

def render_tail_risk(console: Console, report: ETFReport) -> None:
    r = report.risk
    if not r:
        return
    if all(v is None for v in (r.var_95_1y, r.cvar_95_1y, r.skewness_3y, r.kurtosis_3y)):
        return
    t = Table(title=_t("risk") + " — Tail", show_lines=True, border_style="red")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), justify="right", min_width=14)
    t.add_column(_t("interpretation"), min_width=32)
    if r.var_95_1y is not None:
        t.add_row("VaR (1d, 95%)", fmt_pct(r.var_95_1y, 2),
                  "[dim]Worst expected daily loss in 19 of 20 days[/]")
    if r.cvar_95_1y is not None:
        t.add_row("CVaR / Expected Shortfall (95%)",
                  fmt_pct(r.cvar_95_1y, 2),
                  "[dim]Average loss on the bad 5% of days[/]")
    if r.skewness_3y is not None:
        s = r.skewness_3y
        note = (
            "[green]Positive skew — bigger upside than downside surprises[/]"
            if s > 0.2 else
            "[yellow]Negative skew — fatter left tail[/]"
            if s < -0.2 else
            "[dim]Roughly symmetric[/]"
        )
        t.add_row("Skewness (3Y)", fmt_num(s, 3), note)
    if r.kurtosis_3y is not None:
        k = r.kurtosis_3y
        note = (
            "[yellow]Fat-tailed — extremes are more frequent than a normal distribution[/]"
            if k > 1 else
            "[dim]Tails close to normal[/]"
        )
        t.add_row("Excess Kurtosis (3Y)", fmt_num(k, 3), note)
    console.print(t)


# ---------------------------------------------------------------------------
# ESG / sustainability
# ---------------------------------------------------------------------------

def render_esg(console: Console, report: ETFReport) -> None:
    e = report.esg
    if not e:
        return
    fields = [e.score, e.sfdr_article, e.sustainability_rating,
              e.carbon_intensity, e.controversy_score, e.exclusions]
    if all(not f for f in fields):
        return
    t = Table(title="ESG",
              show_lines=True, border_style="green")
    t.add_column(_t("metric"), style="bold", min_width=22)
    t.add_column(_t("value"), min_width=22)
    t.add_column(_t("interpretation"), min_width=28)
    if e.score is not None:
        t.add_row("ESG Score", f"{e.score:.1f}",
                  "[dim]Higher is better; convention varies by provider[/]")
    if e.sfdr_article is not None:
        sfdr_note = {
            6: "[dim]Generic — no sustainability claim[/]",
            8: "[cyan]Promotes environmental/social characteristics[/]",
            9: "[green]Sustainable investment objective[/]",
        }.get(e.sfdr_article, "")
        t.add_row("SFDR Article", str(e.sfdr_article), sfdr_note)
    if e.sustainability_rating:
        t.add_row("Sustainability Rating", e.sustainability_rating,
                  "[dim]Issuer-published[/]")
    if e.carbon_intensity is not None:
        t.add_row("Carbon Intensity",
                  f"{e.carbon_intensity:.1f} tCO₂e/$M",
                  "[dim]Lower = less carbon-intensive[/]")
    if e.controversy_score is not None:
        t.add_row("Controversy Score",
                  f"{e.controversy_score:.1f}",
                  "[dim]Lower = fewer controversies[/]")
    if e.exclusions:
        t.add_row("Exclusions", ", ".join(e.exclusions),
                  "[dim]Issuer-confirmed exclusion list[/]")
    console.print(t)


# ---------------------------------------------------------------------------
# Passive-investor checklist
# ---------------------------------------------------------------------------

_STATUS_ICON = {
    "pass": ("[bold green]✓ PASS[/]", "green"),
    "warn": ("[bold yellow]⚠ WARN[/]", "yellow"),
    "fail": ("[bold red]✘ FAIL[/]", "red"),
    "info": ("[bold cyan]ⓘ INFO[/]", "cyan"),
}


def render_passive_checklist(console: Console, report: ETFReport) -> None:
    if not report.passive_checklist:
        return
    from lynx_etf.passive_checklist import summarize_status
    counts = summarize_status(report.passive_checklist)
    summary = (
        f"[bold]Summary:[/] "
        f"[green]{counts.get('pass', 0)}✓[/] · "
        f"[yellow]{counts.get('warn', 0)}⚠[/] · "
        f"[red]{counts.get('fail', 0)}✘[/] · "
        f"[cyan]{counts.get('info', 0)}ⓘ[/]"
    )
    t = Table(
        title="Passive Investor Checklist  —  rules of thumb every buy-and-hold ETF investor should run",
        show_lines=True,
        border_style="bold cyan",
        caption=summary,
    )
    t.add_column(_t("status"), min_width=10)
    t.add_column(_t("check"), style="bold", min_width=22)
    t.add_column("Detail", min_width=32)
    t.add_column(_t("rule_of_thumb"), style="dim", min_width=28)
    for c in report.passive_checklist:
        icon, _ = _STATUS_ICON.get(c.status, ("[dim]·[/]", "dim"))
        t.add_row(icon, c.label, c.message, c.rule_of_thumb)
    console.print(t)


# ---------------------------------------------------------------------------
# Educational tips for passive investors
# ---------------------------------------------------------------------------

def render_tips(console: Console, report: ETFReport) -> None:
    if not report.tips:
        return
    text = "\n".join(f"• {t}" for t in report.tips)
    console.print(Panel(
        text,
        title="[bold]Tips for Passive ETF Investors[/]",
        border_style="cyan",
        subtitle="[dim]Tailored to this fund first, then universal heuristics[/]",
    ))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def render_full_report(console: Console, report: ETFReport) -> None:
    render_header(console, report)
    if report.verdict:
        render_verdict(console, report)
    render_structure(console, report)
    render_costs(console, report)
    render_income(console, report)
    render_liquidity(console, report)
    render_premium_discount_stats(console, report)
    render_performance(console, report)
    render_calendar_returns(console, report)
    render_capture_ratios(console, report)
    render_allocation(console, report)
    render_holdings(console, report)
    render_risk(console, report)
    render_tail_risk(console, report)
    render_esg(console, report)
    render_passive_checklist(console, report)
    render_tips(console, report)
    if report.news:
        render_news(console, report)
    console.print()


def render_about(console: Console) -> None:
    """Render the About panel, matching lynx-fundamental's layout."""
    from lynx_etf import get_about_text, get_logo_ascii
    about = get_about_text()
    logo = get_logo_ascii()

    console.print()
    if logo:
        console.print(Panel(f"[green]{logo}[/]", border_style="green"))
    console.print(Panel(
        f"[bold blue]{about['name']} v{about['version']}[/]\n"
        f"[dim]Part of {about['suite']} v{about['suite_version']}[/]\n"
        f"[dim]Released {about['year']}[/]\n\n"
        f"[bold]Developed by:[/] {about['author']}\n"
        f"[bold]Contact:[/]      {about['email']}\n"
        f"[bold]License:[/]      {about['license']}\n\n"
        f"[dim]{about['description']}[/]",
        title="[bold]About[/]",
        border_style="blue",
    ))
    console.print(Panel(
        about["license_text"],
        title="[bold]BSD 3-Clause License[/]",
        border_style="dim",
    ))
    console.print()


display_full_report = render_full_report
