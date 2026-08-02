"""The step-by-step research narrative template.

``render(sections, *, thesis, kpis, ...)`` assembles a self-contained
storytelling dashboard: a title + thesis banner + KPI row + numbered
reasoning-block-plus-evidence sections + sticky nav.

Generalized from ``research/saa-finalization/scratch/scripts/build_story.py``.
Each section is a ``base.section(...)`` dict, typically built with a ``why(...)``
reasoning block followed by evidence cards/plots/tables.
"""

from __future__ import annotations

from . import base


def why(lead: str, body: str, *, kind: str = "") -> str:
    """A reasoning block — the WHY. ``kind`` = ""|good|warn."""
    k = f" {kind}" if kind else ""
    lead_html = f'<span class="lead">{lead}</span>' if lead else ""
    return f'<div class="why{k}">{lead_html}{body}</div>'


def card(title: str, inner_html: str, *, note: str | None = None) -> str:
    """An evidence card. ``note`` renders a small caption under the content."""
    head = f"<h3>{base._esc(title)}</h3>" if title else ""
    cap = (
        f'<div class="section-desc" style="margin:6px 0 0">{note}</div>' if note else ""
    )
    return f'<div class="card">{head}{inner_html}{cap}</div>'


def render(
    sections: list,
    *,
    title: str,
    thesis: str | None = None,
    kpis: list[dict] | None = None,
    subtitle: str | None = None,
    eyebrow: str | None = None,
    badges: list[str] | None = None,
    favicon: str | None = "📊",
    footer_html: str = "",
    extra_head: str = "",
    extra_script: str = "",
) -> str:
    """Render the narrative story report.

    ``sections`` is a list of :func:`base.section` dicts (each with a ``step``
    label for the numbered arc). ``kpis`` is passed to :func:`base.kpi_row` and
    rendered above the sections.
    """
    body_prefix = ""
    if kpis:
        body_prefix = f'<div class="container">{base.kpi_row(kpis)}</div>'

    return base.page(
        title,
        sections,
        favicon=favicon,
        subtitle=subtitle,
        thesis=thesis,
        eyebrow=eyebrow,
        badges=badges,
        body_prefix_html=body_prefix,
        footer_html=footer_html,
        extra_head=extra_head,
        extra_script=extra_script,
    )
