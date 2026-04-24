"""Entry-point registration for the Lince Investor Suite plugin system.

Exposed via ``pyproject.toml`` under the ``lynx_investor_suite.agents``
entry-point group. See :mod:`lynx_investor_core.plugins` for the
discovery contract.

``lynx-etf`` is the ETF-specialist agent. Scope is strictly Exchange-Traded
Funds — stocks, mutual funds, and index funds are rejected at the
resolver level.
"""

from __future__ import annotations

from lynx_investor_core.plugins import SectorAgent

from lynx_etf import __version__


def register() -> SectorAgent:
    """Return this agent's descriptor for the plugin registry."""
    return SectorAgent(
        name="lynx-etf",
        short_name="etf",
        sector="ETFs (any asset class)",
        tagline="Exchange-Traded Fund analysis: costs, holdings, allocation, risk",
        prog_name="lynx-etf",
        version=__version__,
        package_module="lynx_etf",
        entry_point_module="lynx_etf.__main__",
        entry_point_function="main",
        icon="\U0001f4c8",
    )
