"""Shared, self-contained HTML reporting library for dm-evo-lab research.

Canonical templates: ``backtest_dashboard``, ``research_story``; shared
primitives in ``base``. Every report is self-contained (plotly.min.js inlined
from the venv, NEVER a CDN) and never scrolls the page horizontally.

Usage::

    from _lib.reporting import base, backtest_dashboard, research_story
    html = base.page("Title", [base.section("§1", evidence_html=base.table(df))])

See README.md for the full contract.
"""

from __future__ import annotations

from . import backtest_dashboard, base, research_story
from .base import (
    SHARED_CSS,
    banner,
    dumps,
    inline_plotly,
    kpi_row,
    page,
    plot,
    section,
    table,
)

__all__ = [
    # sub-modules
    "base",
    "backtest_dashboard",
    "research_story",
    # base primitives
    "inline_plotly",
    "SHARED_CSS",
    "page",
    "section",
    "table",
    "plot",
    "kpi_row",
    "banner",
    "dumps",
]
