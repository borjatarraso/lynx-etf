"""Educational tips for passive ETF investors.

The display layer renders these in a final ``Tips for Passive Investors``
panel after the analysis. Tips fall into two buckets:

* **Universal** — buy-and-hold rules of thumb every passive investor
  should internalise, independent of the fund being analysed.
* **Tailored** — generated from the report itself (e.g. "this fund is
  Irish-domiciled, so 15% withholding on US dividends applies").

Tips are deliberately short (one-liners), opinionated, and reference
the source (Bogle / Vanguard / academic consensus) where it helps the
reader trust the heuristic.
"""

from __future__ import annotations

from typing import List

from lynx_etf.models import ETFReport


# ---------------------------------------------------------------------------
# Universal tips — render even when no specific fund is loaded.
# ---------------------------------------------------------------------------

UNIVERSAL_TIPS: tuple[str, ...] = (
    # Cost
    "Cost is the single most reliable predictor of long-term return — "
    "every basis point of TER compounds against you for decades (Sharpe, 1991).",
    "Total cost of ownership = TER + bid-ask spread + tracking error. "
    "Compare all three before switching funds, not just headline TER.",
    "Mid-cap and small-cap index TERs are higher than large-cap; benchmark "
    "your fund against peers covering the same segment, not against SPY.",

    # Tax & domicile (huge for European investors)
    "US-domiciled ETFs charge 15% US withholding on dividends for treaty "
    "countries; Irish-domiciled UCITS charge 15% too thanks to the US-IE "
    "treaty — but European-domiciled non-Irish funds often suffer ≥30%.",
    "Accumulating share classes compound dividends inside the fund — best "
    "for tax-deferred / ISA / IRA accounts. Distributing classes pay out — "
    "best when you need income or live in a country that taxes notional "
    "accumulating income (e.g. UK reporting funds).",
    "US ETFs issuing K-1 (commodity / partnership) are more tax-painful "
    "than 1099 ETFs; if avoidable, prefer ETFs that issue 1099s.",

    # Distribution & compounding
    "If you reinvest dividends manually inside a Distributing fund, you "
    "lose the compounding benefit unless your broker offers a free DRIP.",
    "Capital-gain distributions are the silent tax drag of poorly-managed "
    "ETFs; a fund that historically pays them out is structurally less "
    "tax-efficient.",

    # Replication
    "Physical full replication > stratified sampling > synthetic / swap "
    "for buy-and-hold investors. Synthetic ETFs concentrate counterparty "
    "risk in a swap counterparty — fine if disclosed and well-collateralised, "
    "a problem if neither.",
    "Securities-lending revenue is fine for an investor when ≥85% of it "
    "is returned to the fund. Below that, the issuer is keeping a tax "
    "you didn't agree to pay.",

    # Liquidity & closure
    "Look at the *underlying* basket's liquidity, not just the ETF's: an "
    "illiquid ETF tracking a liquid index can still be cheap to trade via "
    "creation/redemption. The reverse is much worse.",
    "ETFs under $50M AUM close more often than they don't. Verify the "
    "issuer's stated AUM growth or pick a peer fund with $1B+.",
    "Avoid trading at market open and close — bid-ask spreads widen. "
    "Use limit orders during the middle of the trading day.",

    # Risk
    "Cap-weighted indexes drift toward concentration during bull runs "
    "(see the Magnificent 7 in S&P 500). Equal-weight or fundamental-weight "
    "alternatives diversify but cost more.",
    "Tracking error tells you how faithfully the ETF follows its index; "
    "tracking *difference* tells you whether the ETF beat or trailed it.",
    "A volatile ETF is not a riskier investment for a 30-year passive "
    "holder — sequence-of-returns risk only matters if you sell during a drawdown.",
    "Rebalance once a year, not monthly. Frequent rebalancing increases "
    "transaction cost without measurable performance benefit (Vanguard, 2010).",

    # Behavioural
    "Past performance does not predict future returns; cost, structure, "
    "and diversification are the only durable signals at the ETF level.",
    "Don't compare a small-cap ETF to SPY on Sharpe alone — risk-adjusted "
    "metrics need same-segment benchmarks.",
    "Time in the market beats timing the market. The biggest risk to "
    "passive investors is themselves.",
)


# ---------------------------------------------------------------------------
# Tailored tips — derived from the report
# ---------------------------------------------------------------------------

def for_passive_investor(report: ETFReport) -> List[str]:
    """Return tips tailored to *report*'s specific characteristics."""
    out: List[str] = []
    p = report.profile

    # ── Cost ─────────────────────────────────────────────────────────────
    if report.costs and report.costs.expense_ratio is not None:
        er = report.costs.expense_ratio
        if er > 0.005:
            out.append(
                f"This fund's TER is {er*100:.2f}%. Over 30 years that's "
                f"~{er*30*100:.0f}% of cumulative cost drag. Cheaper peers exist for "
                f"most mainstream indices."
            )
        elif er <= 0.001:
            out.append(
                f"At {er*100:.2f}% TER this fund is in the bottom-cost decile — "
                "ideal for a passive core position."
            )

    # ── Domicile / tax ────────────────────────────────────────────────────
    domicile = (p.domicile or "").upper()
    if domicile == "IE":
        out.append(
            "Irish domicile: 15% US withholding on US dividends (treaty rate). "
            "If you live in the EU, this is usually the most tax-efficient option "
            "for US-equity exposure."
        )
    elif domicile == "LU":
        out.append(
            "Luxembourg domicile: 30% US withholding by default — typically "
            "0.30%–0.45% drag vs an Irish-domiciled equivalent for US equity."
        )
    elif domicile == "US":
        if p.ucits is False:
            out.append(
                "US-domiciled: most US ETFs are not UCITS-compliant and "
                "many EU retail brokers will refuse them post-PRIIPs."
            )
        out.append(
            "US-domiciled: simplest tax handling for US residents; for EU "
            "residents, watch estate-tax exposure on amounts > $60k."
        )

    # ── Replication / structure ──────────────────────────────────────────
    rep = (p.replication or "").lower()
    if "synthetic" in rep or "swap" in rep:
        cps = ", ".join(p.swap_counterparties) if p.swap_counterparties else "not disclosed"
        out.append(
            f"Synthetic / swap-based replication. Counterparties: {cps}. "
            "Verify the swap collateralisation policy in the prospectus."
        )
    elif "sample" in rep or "stratified" in rep:
        out.append(
            "Sampled replication. Expect a few extra bps of tracking error vs "
            "full physical; perfectly fine for very large or illiquid indices."
        )

    if p.securities_lending:
        if p.lending_revenue_split is not None and p.lending_revenue_split < 0.7:
            out.append(
                f"Securities lending returns only {p.lending_revenue_split*100:.0f}% "
                "of revenue to investors — issuer is keeping a meaningful share."
            )

    # ── Distribution ─────────────────────────────────────────────────────
    pol = (p.distribution_policy or "").lower()
    if "accum" in pol:
        out.append(
            "Accumulating share class — dividends compound inside the fund. "
            "Ideal for tax-deferred (IRA / SIPP / ISA) or holdings you don't "
            "spend from."
        )
    elif "distribut" in pol:
        out.append(
            "Distributing share class — pays cash. Best when you need income "
            "or live in a regime that taxes accumulating income notionally."
        )

    # ── Currency ─────────────────────────────────────────────────────────
    if p.currency_hedged:
        out.append(
            f"Hedged to {p.hedged_to or 'home currency'}. Hedging removes FX "
            "swings but adds 0.10%–0.30% annual hedging cost; rarely worth it "
            "for equity > 5y horizon (Vanguard, 2014)."
        )

    # ── Leverage / inverse ───────────────────────────────────────────────
    if p.leverage_factor is not None and abs(p.leverage_factor - 1.0) > 0.01:
        out.append(
            f"Leverage / inverse factor {p.leverage_factor:+.1f}×. These funds "
            "rebalance daily and suffer volatility decay over multi-day holds — "
            "they are *not* buy-and-hold passive instruments."
        )

    # ── Tracking ─────────────────────────────────────────────────────────
    if report.risk:
        te = report.risk.tracking_error
        td = report.risk.tracking_difference
        if te is not None and te > 0.01:
            out.append(
                f"Tracking error {te*100:.2f}% — relatively wide. Rule of thumb: "
                "≤ 0.50% / 50 bps for liquid indices."
            )
        if td is not None and td < -0.005:
            out.append(
                f"Tracking difference {td*100:.2f}% — fund is trailing its "
                "benchmark by more than the TER alone explains."
            )

    # ── Concentration ────────────────────────────────────────────────────
    a = report.allocation
    if a:
        if a.top10_concentration is not None and a.top10_concentration > 0.40:
            out.append(
                f"Top-10 weight {a.top10_concentration*100:.0f}% — the fund is "
                "more concentrated than a typical total-market product. "
                "Pair with an equal-weight or small-cap fund if you want broader exposure."
            )
        if a.holdings_count is not None and a.holdings_count < 30:
            out.append(
                f"Only {a.holdings_count} holdings — closer to a thematic basket "
                "than a passive index. Diversification benefit is limited."
            )

    # ── Bond-specific ────────────────────────────────────────────────────
    if a and a.duration_years is not None:
        d = a.duration_years
        if d > 10:
            out.append(
                f"Effective duration {d:.1f} years — large interest-rate "
                "sensitivity. A 1% rise in yields would drop NAV by ~"
                f"{d:.0f}%."
            )
        elif d > 5:
            out.append(
                f"Effective duration {d:.1f} years — moderate rate sensitivity."
            )

    # ── ESG ──────────────────────────────────────────────────────────────
    if report.esg and report.esg.sfdr_article == 9:
        out.append(
            "SFDR Article 9 — strict sustainability mandate. Verify the "
            "exclusion list matches your values."
        )

    # ── Closure risk ─────────────────────────────────────────────────────
    aum = (report.liquidity.aum if report.liquidity else None) or p.aum
    if aum is not None and aum < 100e6:
        out.append(
            f"AUM ${aum/1e6:.0f}M — closure risk is real for funds below $100M. "
            "If the fund liquidates, you may face capital-gains tax on the forced sale."
        )

    # ── Volatility / risk ────────────────────────────────────────────────
    if report.risk:
        vol = report.risk.volatility_3y
        if vol is not None and vol > 0.30:
            out.append(
                f"3-year volatility {vol*100:.0f}% — high. Make sure your "
                "drawdown tolerance and time horizon support this exposure."
            )

    # ── Tier / size guidance ────────────────────────────────────────────
    tier_value = p.tier.value if p.tier else None
    if tier_value in ("Mega Fund", "Large Fund"):
        out.append(
            f"{tier_value}: deep liquidity makes large rebalances cheap. Ideal "
            "for a passive core."
        )
    elif tier_value in ("Micro Fund", "Nano Fund"):
        out.append(
            f"{tier_value}: prefer a larger peer fund tracking the same index "
            "to reduce closure-risk exposure."
        )

    return out


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------

def compose_tips(report: ETFReport, *, max_universal: int = 6) -> List[str]:
    """Return a final list of tips: tailored first, then a curated few universals."""
    tailored = for_passive_investor(report)
    universal = list(UNIVERSAL_TIPS[:max_universal])
    # Avoid dup if a tailored tip happens to repeat an universal one.
    return tailored + [u for u in universal if u not in tailored]
