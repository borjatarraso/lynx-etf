"""Rich rendering for ETF analysis reports."""

from __future__ import annotations

from typing import Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lynx_etf import APP_NAME, SUITE_LABEL, __version__
from lynx_etf.models import ETFReport, FundSizeTier


# Formatters -----------------------------------------------------------------

def fmt_pct(v: Optional[float], decimals: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v*100:.{decimals}f}%"


def fmt_bps(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.1f} bps"


def fmt_num(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}"


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


# Panels ---------------------------------------------------------------------

def render_header(console: Console, report: ETFReport) -> None:
    p = report.profile
    table = Table.grid(padding=(0, 2))
    table.add_row(
        Text("Ticker", style="dim"), Text(p.ticker, style="bold cyan"),
        Text("ISIN", style="dim"), Text(p.isin or "—"),
    )
    table.add_row(
        Text("Name", style="dim"), Text(p.name or "—"),
        Text("Family", style="dim"), Text(p.fund_family or "—"),
    )
    table.add_row(
        Text("Category", style="dim"), Text(p.category or "—"),
        Text("Asset Class", style="dim"), Text(p.asset_class or "—"),
    )
    table.add_row(
        Text("Domicile", style="dim"), Text(p.domicile or "—"),
        Text("Inception", style="dim"), Text(p.inception_date or "—"),
    )
    table.add_row(
        Text("Benchmark", style="dim"), Text(p.benchmark or "—"),
        Text("Policy", style="dim"), Text(p.distribution_policy or "—"),
    )
    table.add_row(
        Text("AUM", style="dim"), Text(fmt_money(p.aum)),
        Text("Size Tier", style="dim"), Text(p.tier.value, style=tier_style(p.tier)),
    )
    console.print(Panel(table, title=f"[bold]{APP_NAME}[/] — {p.name}", box=ROUNDED, expand=False))


def render_costs(console: Console, report: ETFReport) -> None:
    c = report.costs
    if not c:
        return
    t = Table(box=ROUNDED, title="Costs", show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Expense Ratio (TER)", _colored_er(c.expense_ratio))
    t.add_row("Management Fee", fmt_pct(c.management_fee, 3))
    t.add_row("Bid-Ask Spread", fmt_bps(c.spread_bps))
    if c.estimated_cost_10k_year1 is not None:
        t.add_row("Est. yr-1 cost on $10k", f"${c.estimated_cost_10k_year1:.2f}")
    console.print(t)


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


def render_income(console: Console, report: ETFReport) -> None:
    i = report.income
    if not i:
        return
    t = Table(box=ROUNDED, title="Income & Distributions", show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Dividend Yield (TTM)", fmt_pct(i.dividend_yield))
    t.add_row("SEC 30-day Yield", fmt_pct(i.sec_yield_30d))
    t.add_row("Distribution Frequency", i.distribution_frequency or "—")
    t.add_row("Distribution Policy", i.distribution_policy or "—")
    console.print(t)


def render_liquidity(console: Console, report: ETFReport) -> None:
    l = report.liquidity
    if not l:
        return
    t = Table(box=ROUNDED, title="Size & Liquidity", show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("AUM", fmt_money(l.aum))
    t.add_row("Avg Daily Volume", fmt_int(l.avg_volume))
    t.add_row("Avg Daily $ Volume", fmt_money(l.avg_dollar_volume))
    t.add_row("Bid-Ask Spread", fmt_bps(l.spread_bps))
    t.add_row("Fund Age", fmt_years(l.fund_age_years))
    t.add_row("Shares Outstanding", fmt_int(l.shares_outstanding))
    if l.premium_discount_pct is not None:
        t.add_row("Premium / Discount", fmt_pct(l.premium_discount_pct, 3))
    console.print(t)


def render_performance(console: Console, report: ETFReport) -> None:
    p = report.performance
    if not p:
        return
    t = Table(box=ROUNDED, title="Performance", show_header=True, header_style="bold")
    t.add_column("Window")
    t.add_column("Total Return", justify="right")
    t.add_row("1M", _colored_return(p.return_1m))
    t.add_row("3M", _colored_return(p.return_3m))
    t.add_row("YTD", _colored_return(p.return_ytd))
    t.add_row("1Y", _colored_return(p.return_1y))
    t.add_row("3Y CAGR", _colored_return(p.return_3y))
    t.add_row("5Y CAGR", _colored_return(p.return_5y))
    t.add_row("10Y CAGR", _colored_return(p.return_10y))
    t.add_row("Since Inception CAGR", _colored_return(p.cagr_since_inception))
    console.print(t)

    t2 = Table(box=ROUNDED, title="Risk-Adjusted Returns", show_header=True, header_style="bold")
    t2.add_column("Metric")
    t2.add_column("Value", justify="right")
    t2.add_row("Sharpe (1Y)", fmt_num(p.sharpe_1y))
    t2.add_row("Sharpe (3Y)", fmt_num(p.sharpe_3y))
    t2.add_row("Sortino (3Y)", fmt_num(p.sortino_3y))
    console.print(t2)


def _colored_return(r: Optional[float]) -> Text:
    if r is None:
        return Text("—")
    sign = "+" if r >= 0 else ""
    value = f"{sign}{r*100:.2f}%"
    return Text(value, style="green" if r >= 0 else "red")


def render_allocation(console: Console, report: ETFReport) -> None:
    a = report.allocation
    if not a:
        return
    t = Table(box=ROUNDED, title="Allocation Overview", show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Holdings Count", fmt_int(a.holdings_count))
    t.add_row("Top 10 Concentration", fmt_pct(a.top10_concentration))
    t.add_row("Sector HHI", fmt_num(a.herfindahl_sector))
    t.add_row("Sector Count", fmt_int(a.sector_count))
    t.add_row("Country Count", fmt_int(a.country_count))
    console.print(t)

    if a.sector_breakdown:
        st = Table(box=ROUNDED, title="Sector Breakdown", show_header=True, header_style="bold")
        st.add_column("Sector")
        st.add_column("Weight", justify="right")
        for sector, weight in a.sector_breakdown[:12]:
            st.add_row(str(sector), fmt_pct(weight))
        console.print(st)

    if a.country_breakdown:
        ct = Table(box=ROUNDED, title="Country Breakdown", show_header=True, header_style="bold")
        ct.add_column("Country")
        ct.add_column("Weight", justify="right")
        for country, weight in a.country_breakdown[:10]:
            ct.add_row(str(country), fmt_pct(weight))
        console.print(ct)


def render_holdings(console: Console, report: ETFReport) -> None:
    if not report.holdings:
        return
    t = Table(
        box=ROUNDED,
        title=f"Top {min(len(report.holdings), 15)} Holdings",
        show_header=True,
        header_style="bold",
    )
    t.add_column("#", justify="right")
    t.add_column("Symbol")
    t.add_column("Name")
    t.add_column("Weight", justify="right")
    ordered = sorted(report.holdings, key=lambda h: h.weight or 0, reverse=True)[:15]
    for i, h in enumerate(ordered, 1):
        t.add_row(str(i), h.symbol or "—", h.name or "—", fmt_pct(h.weight))
    console.print(t)


def render_risk(console: Console, report: ETFReport) -> None:
    r = report.risk
    if not r:
        return
    t = Table(box=ROUNDED, title="Risk Profile", show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    t.add_row("Volatility (1Y)", fmt_pct(r.volatility_1y))
    t.add_row("Volatility (3Y)", fmt_pct(r.volatility_3y))
    t.add_row("Max Drawdown (3Y)", fmt_pct(r.max_drawdown_3y))
    t.add_row("Beta (3Y)", fmt_num(r.beta_3y))
    t.add_row("Tracking Error", fmt_pct(r.tracking_error))
    t.add_row("Tracking Difference", fmt_pct(r.tracking_difference))
    t.add_row("R²", fmt_num(r.r_squared))
    console.print(t)


def render_verdict(console: Console, report: ETFReport) -> None:
    v = report.verdict
    if not v:
        return
    style = verdict_style(v.verdict)
    head = Text()
    head.append(f"{v.verdict}  ", style=f"bold {style}")
    head.append(f"· score {v.overall_score:.0f}/100", style="dim")

    body = Table.grid(padding=(0, 2))
    for cat, score in v.category_scores.items():
        bar_len = int(round(score / 5))
        bar = "█" * bar_len + "·" * (20 - bar_len)
        body.add_row(
            Text(cat, style="dim"),
            Text(bar, style=_score_color(score)),
            Text(f"{score:.0f}", style=_score_color(score)),
        )

    strengths = Text()
    if v.strengths:
        strengths.append("Strengths:\n", style="bold green")
        for s in v.strengths:
            strengths.append(f"  + {s}\n", style="green")

    risks = Text()
    if v.risks:
        risks.append("Risks:\n", style="bold red")
        for r in v.risks:
            risks.append(f"  − {r}\n", style="red")

    suitable = Text()
    if v.suitable_for:
        suitable.append("Suitable for: ", style="dim")
        suitable.append(", ".join(v.suitable_for), style="cyan")

    sub = Table.grid(padding=(1, 0))
    sub.add_row(body)
    if v.tier_note:
        sub.add_row(Text(v.tier_note, style="dim italic"))
    if strengths.plain:
        sub.add_row(strengths)
    if risks.plain:
        sub.add_row(risks)
    if suitable.plain:
        sub.add_row(suitable)

    console.print(Panel(sub, title=head, box=ROUNDED, border_style=style))


def _score_color(score: float) -> str:
    if score >= 80:
        return "bold green"
    if score >= 65:
        return "green"
    if score >= 50:
        return "cyan"
    if score >= 35:
        return "yellow"
    return "red"


def render_news(console: Console, report: ETFReport, limit: int = 5) -> None:
    if not report.news:
        return
    t = Table(
        box=ROUNDED,
        title=f"News (latest {min(limit, len(report.news))})",
        show_header=True,
        header_style="bold",
    )
    t.add_column("Date")
    t.add_column("Source")
    t.add_column("Title")
    for n in report.news[:limit]:
        t.add_row(n.published or "—", n.source or "—", n.title or "—")
    console.print(t)


def render_full_report(console: Console, report: ETFReport) -> None:
    render_header(console, report)
    render_verdict(console, report)
    render_costs(console, report)
    render_income(console, report)
    render_liquidity(console, report)
    render_performance(console, report)
    render_allocation(console, report)
    render_holdings(console, report)
    render_risk(console, report)
    if report.news:
        render_news(console, report)


def render_about(console: Console) -> None:
    body = Text()
    body.append(f"{APP_NAME}\n", style="bold cyan")
    body.append(f"{SUITE_LABEL}\n", style="dim")
    body.append(f"Version {__version__}\n\n", style="dim")
    body.append("Exchange-Traded Fund analysis — costs, holdings, allocation, performance, risk.\n")
    body.append("Scope: ETFs only. Stocks, mutual funds, and index funds are rejected.\n\n")
    body.append("Part of the Lince Investor Suite.\n", style="dim italic")
    console.print(Panel(body, title="About", box=ROUNDED, border_style="cyan"))


display_full_report = render_full_report
