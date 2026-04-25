"""Rules-of-thumb checklist for passive ETF investors.

Returns a list of :class:`PassiveCheck` records — each is one pass /
warn / fail / info line that the display layer renders as a colour-coded
flag table. The checklist intentionally mirrors what a Boglehead-style
buy-and-hold investor would scan before buying:

* **TER** under 10 bps for plain-vanilla index trackers, 25 bps for
  factor / smart-beta, 50 bps for thematic / sector funds.
* **AUM** ≥ $100M to keep closure risk negligible.
* **Fund age** ≥ 3 years for an established track record.
* **Bid-ask spread** ≤ 5 bps for liquid trades.
* **Tracking error** ≤ 0.5% / 50 bps for liquid-index trackers.
* **Top-10 concentration** ≤ 30% to stay broadly diversified.
* **Holdings count** ≥ 50 (more for total-market funds).
* **Securities lending** policy disclosed.
* **Replication method** (physical vs synthetic) disclosed.
* **Distribution policy** declared (Acc/Dist).
* **Premium / discount** stays close to NAV.
* **Sharpe** non-negative (positive = at least beating risk-free).
* **Counterparty risk** flagged for synthetic/swap-based funds.
* **Leverage / inverse** flagged because they're not buy-and-hold tools.

Every check returns a *rule of thumb* string so the user sees both
their fund's value and the passive-investor convention.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from lynx_etf.models import ETFReport, PassiveCheck


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(label: str, message: str, rule: str) -> PassiveCheck:
    return PassiveCheck(label=label, status="pass", message=message, rule_of_thumb=rule)


def _warn(label: str, message: str, rule: str) -> PassiveCheck:
    return PassiveCheck(label=label, status="warn", message=message, rule_of_thumb=rule)


def _fail(label: str, message: str, rule: str) -> PassiveCheck:
    return PassiveCheck(label=label, status="fail", message=message, rule_of_thumb=rule)


def _info(label: str, message: str, rule: str = "") -> PassiveCheck:
    return PassiveCheck(label=label, status="info", message=message, rule_of_thumb=rule)


def _na(label: str, rule: str) -> PassiveCheck:
    """Data-not-available — surfaced as an info line, not a failure."""
    return PassiveCheck(label=label, status="info",
                        message="No data available — verify on the issuer factsheet.",
                        rule_of_thumb=rule)


def _category_ter_threshold(report: ETFReport) -> tuple[float, str]:
    """Return (threshold, label) for the TER rule based on category.

    Plain-vanilla cap-weighted trackers should be 10 bps; factor / smart
    beta funds get up to 25 bps; thematic / sector funds get up to 50.
    """
    cat = (report.profile.category or "").lower()
    if any(k in cat for k in ("thematic", "sector", "industry", "leveraged")):
        return (0.0050, "thematic / sector")
    if any(k in cat for k in ("factor", "smart", "active", "strategic", "dividend")):
        return (0.0025, "factor / smart-beta")
    return (0.0010, "plain index tracker")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_ter(report: ETFReport) -> PassiveCheck:
    threshold, label = _category_ter_threshold(report)
    rule = f"TER ≤ {threshold * 100:.2f}% for a {label}"
    er = report.costs.expense_ratio if report.costs else None
    if er is None:
        return _na("Expense Ratio (TER)", rule)
    pct = er * 100
    if er <= threshold:
        return _pass("Expense Ratio (TER)",
                     f"{pct:.2f}% — within the {label} threshold.", rule)
    if er <= threshold * 2:
        return _warn("Expense Ratio (TER)",
                     f"{pct:.2f}% — above the {label} threshold; "
                     "compare with cheaper alternatives.", rule)
    return _fail("Expense Ratio (TER)",
                 f"{pct:.2f}% — well above the {label} threshold; "
                 "this drag compounds over decades.", rule)


def _check_aum(report: ETFReport) -> PassiveCheck:
    rule = "AUM ≥ $100M to minimise closure risk"
    aum = (report.liquidity.aum if report.liquidity else None) or report.profile.aum
    if aum is None:
        return _na("Assets Under Management", rule)
    if aum >= 1e9:
        return _pass("Assets Under Management",
                     f"${aum/1e9:.1f}B — deep liquidity, closure risk negligible.", rule)
    if aum >= 100e6:
        return _pass("Assets Under Management",
                     f"${aum/1e6:.0f}M — above the $100M closure-risk floor.", rule)
    if aum >= 50e6:
        return _warn("Assets Under Management",
                     f"${aum/1e6:.0f}M — modest size; closures occur in this band.", rule)
    return _fail("Assets Under Management",
                 f"${aum/1e6:.1f}M — high closure risk for buy-and-hold investors.", rule)


def _check_age(report: ETFReport) -> PassiveCheck:
    rule = "Fund age ≥ 3 years for an established record"
    age = report.liquidity.fund_age_years if report.liquidity else None
    if age is None:
        return _na("Fund Age", rule)
    if age >= 5:
        return _pass("Fund Age", f"{age:.1f} years — established track record.", rule)
    if age >= 3:
        return _pass("Fund Age", f"{age:.1f} years — meets the 3-year guideline.", rule)
    if age >= 1:
        return _warn("Fund Age",
                     f"{age:.1f} years — under the 3-year guideline; "
                     "performance signals are noisy this early.", rule)
    return _fail("Fund Age",
                 f"{age:.1f} years — too young to evaluate as a passive holding.", rule)


def _check_spread(report: ETFReport) -> PassiveCheck:
    rule = "Median bid-ask spread ≤ 5 bps for liquid trading"
    spread = (
        report.liquidity.spread_bps if report.liquidity else None
    ) or (report.costs.spread_bps if report.costs else None)
    if spread is None:
        return _na("Bid-Ask Spread", rule)
    if spread <= 2:
        return _pass("Bid-Ask Spread", f"{spread:.1f} bps — institutional-tier liquidity.", rule)
    if spread <= 5:
        return _pass("Bid-Ask Spread", f"{spread:.1f} bps — within the passive guideline.", rule)
    if spread <= 15:
        return _warn("Bid-Ask Spread",
                     f"{spread:.1f} bps — wider than the 5 bps guideline; "
                     "use limit orders.", rule)
    return _fail("Bid-Ask Spread",
                 f"{spread:.1f} bps — wide spreads erode passive returns; "
                 "trade in low-volume windows at your own cost.", rule)


def _check_tracking(report: ETFReport) -> PassiveCheck:
    rule = "Tracking error ≤ 0.5% / 50 bps for a liquid-index tracker"
    te = report.risk.tracking_error if report.risk else None
    if te is None:
        return _na("Tracking Error", rule)
    pct = te * 100
    if te <= 0.005:
        return _pass("Tracking Error",
                     f"{pct:.2f}% — tight replication of the benchmark.", rule)
    if te <= 0.01:
        return _warn("Tracking Error",
                     f"{pct:.2f}% — above the 0.5% guideline; "
                     "fund is replicating less faithfully.", rule)
    return _fail("Tracking Error",
                 f"{pct:.2f}% — large gap to benchmark; "
                 "no longer behaves like a passive tracker.", rule)


def _check_top10(report: ETFReport) -> PassiveCheck:
    rule = "Top-10 weight ≤ 30% to stay broadly diversified"
    a = report.allocation
    top10 = a.top10_concentration if a else None
    if top10 is None:
        return _na("Top-10 Concentration", rule)
    pct = top10 * 100
    if top10 <= 0.20:
        return _pass("Top-10 Concentration",
                     f"{pct:.1f}% — broadly diversified.", rule)
    if top10 <= 0.30:
        return _pass("Top-10 Concentration",
                     f"{pct:.1f}% — at the diversification ceiling.", rule)
    if top10 <= 0.50:
        return _warn("Top-10 Concentration",
                     f"{pct:.1f}% — concentrated; cap-weighted indexes can drift here.", rule)
    return _fail("Top-10 Concentration",
                 f"{pct:.1f}% — heavily concentrated; not a substitute for total-market exposure.",
                 rule)


def _check_holdings_count(report: ETFReport) -> PassiveCheck:
    rule = "≥ 50 holdings (more for total-market funds)"
    a = report.allocation
    n = a.holdings_count if a else None
    if n is None:
        return _na("Holdings Count", rule)
    if n >= 500:
        return _pass("Holdings Count",
                     f"{n} holdings — total-market-grade diversification.", rule)
    if n >= 100:
        return _pass("Holdings Count",
                     f"{n} holdings — broadly diversified.", rule)
    if n >= 50:
        return _pass("Holdings Count",
                     f"{n} holdings — meets the diversification guideline.", rule)
    if n >= 25:
        return _warn("Holdings Count",
                     f"{n} holdings — narrow basket; idiosyncratic risk is meaningful.", rule)
    return _fail("Holdings Count",
                 f"{n} holdings — concentrated; closer to single-stock risk than passive.", rule)


def _check_replication(report: ETFReport) -> PassiveCheck:
    rule = "Replication method disclosed (physical preferred for passive)"
    rep = report.profile.replication
    if not rep:
        return _warn("Replication Method",
                     "Not disclosed in this dataset — check the KIID or factsheet.",
                     rule)
    rep_lower = rep.lower()
    if "synthetic" in rep_lower or "swap" in rep_lower:
        return _warn("Replication Method",
                     f"{rep} — counterparty risk; verify swap-counterparty quality.", rule)
    if "sample" in rep_lower or "stratified" in rep_lower:
        return _info("Replication Method",
                     f"{rep} — acceptable but more tracking error than full replication.",
                     rule)
    return _pass("Replication Method",
                 f"{rep} — direct, transparent ownership of the underlying basket.", rule)


def _check_distribution(report: ETFReport) -> PassiveCheck:
    rule = "Distribution policy declared (Accumulating vs Distributing)"
    pol = report.profile.distribution_policy or (
        report.income.distribution_policy if report.income else None
    )
    if not pol:
        return _info("Distribution Policy",
                     "Not disclosed; if you reinvest dividends manually, "
                     "either Acc or Dist works.", rule)
    pol_lower = pol.lower()
    if "accum" in pol_lower:
        return _pass("Distribution Policy",
                     f"{pol} — best for compounding inside tax-advantaged accounts.", rule)
    if "distribut" in pol_lower:
        return _pass("Distribution Policy",
                     f"{pol} — fits an income-focused strategy.", rule)
    return _info("Distribution Policy", f"{pol} — verify how it suits your goal.", rule)


def _check_premium_discount(report: ETFReport) -> PassiveCheck:
    rule = "Premium / discount close to NAV (mean |abs| ≤ 0.10%)"
    l = report.liquidity
    if l is None:
        return _na("Premium / Discount", rule)
    val = (
        l.mean_abs_deviation_1y
        if l.mean_abs_deviation_1y is not None
        else (abs(l.premium_discount_pct) if l.premium_discount_pct is not None else None)
    )
    if val is None:
        return _na("Premium / Discount", rule)
    pct = val * 100
    if val <= 0.001:
        return _pass("Premium / Discount",
                     f"|{pct:.3f}%| — trading essentially at NAV.", rule)
    if val <= 0.005:
        return _warn("Premium / Discount",
                     f"|{pct:.3f}%| — small but persistent gap; check intraday too.",
                     rule)
    return _fail("Premium / Discount",
                 f"|{pct:.3f}%| — material gap; AP arbitrage may be impaired.", rule)


def _check_sharpe(report: ETFReport) -> PassiveCheck:
    rule = "Sharpe (3Y) > 0 — at least beating cash"
    p = report.performance
    s = p.sharpe_3y if p else None
    if s is None:
        return _na("Sharpe (3Y)", rule)
    if s >= 1.0:
        return _pass("Sharpe (3Y)", f"{s:.2f} — strong risk-adjusted return.", rule)
    if s >= 0.5:
        return _pass("Sharpe (3Y)", f"{s:.2f} — acceptable risk-adjusted return.", rule)
    if s >= 0:
        return _warn("Sharpe (3Y)", f"{s:.2f} — barely beating risk-free.", rule)
    return _fail("Sharpe (3Y)", f"{s:.2f} — underperforming cash on a risk-adjusted basis.", rule)


def _check_leverage(report: ETFReport) -> PassiveCheck:
    rule = "Leverage factor = 1.0 for buy-and-hold passive investors"
    lev = report.profile.leverage_factor
    if lev is None:
        return _info("Leverage / Inverse", "No leverage flag set.", rule)
    if abs(lev - 1.0) < 0.01:
        return _pass("Leverage / Inverse",
                     "1.0× — plain-vanilla; suitable for buy-and-hold.", rule)
    if lev < 0:
        return _fail("Leverage / Inverse",
                     f"{lev:+.1f}× — inverse ETF; designed for daily rebalancing, "
                     "not long-term holding.", rule)
    return _fail("Leverage / Inverse",
                 f"{lev:+.1f}× — leveraged; volatility decay erodes returns over time.",
                 rule)


def _check_securities_lending(report: ETFReport) -> PassiveCheck:
    rule = "Securities-lending policy disclosed; revenue mostly returned to investors"
    if report.profile.securities_lending is None:
        return _warn("Securities Lending",
                     "Policy not disclosed in this dataset; check the issuer's factsheet.",
                     rule)
    if not report.profile.securities_lending:
        return _pass("Securities Lending",
                     "Fund does not lend securities — no counterparty risk from lending.",
                     rule)
    split = report.profile.lending_revenue_split
    if split is None:
        return _info("Securities Lending",
                     "Fund lends securities; revenue split not disclosed.", rule)
    if split >= 0.85:
        return _pass("Securities Lending",
                     f"{split*100:.0f}% of lending revenue returned — investor-aligned.",
                     rule)
    if split >= 0.65:
        return _warn("Securities Lending",
                     f"{split*100:.0f}% of lending revenue returned — average split.",
                     rule)
    return _fail("Securities Lending",
                 f"{split*100:.0f}% of lending revenue returned — issuer keeps the bulk.",
                 rule)


def _check_ucits(report: ETFReport) -> Optional[PassiveCheck]:
    """Only emitted when UCITS information is present (EU-relevant)."""
    if report.profile.ucits is None:
        return None
    rule = "UCITS-compliant for EU retail eligibility"
    if report.profile.ucits:
        return _pass("UCITS Compliance",
                     "UCITS-compliant — eligible across EU retail brokerages.", rule)
    return _warn("UCITS Compliance",
                 "Not UCITS-compliant — EU retail brokers may not allow this fund.",
                 rule)


def _check_synthetic_counterparty(report: ETFReport) -> Optional[PassiveCheck]:
    rep = (report.profile.replication or "").lower()
    if "synthetic" not in rep and "swap" not in rep:
        return None
    rule = "Synthetic ETFs need disclosed swap counterparties"
    cps = report.profile.swap_counterparties or []
    if not cps:
        return _warn("Synthetic Counterparty Risk",
                     "Synthetic / swap-based fund — counterparty list not disclosed.",
                     rule)
    return _info("Synthetic Counterparty Risk",
                 f"Counterparties disclosed: {', '.join(cps)}.", rule)


def _check_max_drawdown(report: ETFReport) -> PassiveCheck:
    rule = "Investor must accept the worst observed drawdown (>30% means equity-tier risk)"
    r = report.risk
    dd = r.max_drawdown_3y if r else None
    if dd is None:
        return _na("Max Drawdown (3Y)", rule)
    pct = dd * 100
    if dd > -0.10:
        return _pass("Max Drawdown (3Y)",
                     f"{pct:.1f}% — mild; suitable for low-volatility allocations.", rule)
    if dd > -0.20:
        return _info("Max Drawdown (3Y)",
                     f"{pct:.1f}% — typical for diversified equity.", rule)
    if dd > -0.40:
        return _warn("Max Drawdown (3Y)",
                     f"{pct:.1f}% — severe; verify your time horizon survives this.", rule)
    return _fail("Max Drawdown (3Y)",
                 f"{pct:.1f}% — crash-tier loss; not a low-risk holding.", rule)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_CHECKS = (
    _check_ter,
    _check_aum,
    _check_age,
    _check_spread,
    _check_tracking,
    _check_top10,
    _check_holdings_count,
    _check_replication,
    _check_distribution,
    _check_premium_discount,
    _check_sharpe,
    _check_max_drawdown,
    _check_leverage,
    _check_securities_lending,
)

# Optional checks that may return None when irrelevant.
_OPTIONAL_CHECKS = (_check_ucits, _check_synthetic_counterparty)


def run_passive_checklist(report: ETFReport) -> List[PassiveCheck]:
    """Run every passive-investor check against *report* and return results."""
    out: List[PassiveCheck] = []
    for fn in _CHECKS:
        try:
            result = fn(report)
        except Exception as exc:  # noqa: BLE001 — checklist is best-effort
            result = PassiveCheck(
                label=fn.__name__.replace("_check_", "").replace("_", " ").title(),
                status="info",
                message=f"Check skipped: {exc}",
                rule_of_thumb="",
            )
        out.append(result)

    for fn in _OPTIONAL_CHECKS:
        try:
            result = fn(report)
            if result is not None:
                out.append(result)
        except Exception:
            pass
    return out


def summarize_status(checks: Iterable[PassiveCheck]) -> dict:
    """Return a `{pass, warn, fail, info}` count summary of *checks*."""
    counts = {"pass": 0, "warn": 0, "fail": 0, "info": 0}
    for c in checks:
        counts[c.status] = counts.get(c.status, 0) + 1
    return counts
