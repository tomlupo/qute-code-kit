# ADR-0002: One standard research regime across lab repos and the vault

**Status:** Accepted
**Date:** 2026-07-18

## Context

Four sibling research regimes diverged from shared DNA: dm-evo-lab (research lines,
hand-maintained index — stale at 1 listed / 13 dirs), quantbox-lab (same lineage, different
status vocabulary, also stale), the quant-research vault (frontmatter-as-database hypothesis
notes with gate metrics), and ad-hoc one-off analyses in production repos. Every
hand-maintained index rotted at the same spot; conventions forked per line
(`findings.md` vs `FINDINGS.md`, loose dated files, session notes in line dirs).

## Options Considered

1. **Numbered discrete experiments** — `research/NNNN-slug/` as the atom
2. **Continuous research lines + dated findings** — line dirs with a findings stream,
   index generated from frontmatter
3. **Leave per-repo conventions**, document each

## Decision

Option 2 — it matches how the work actually flows (research is continuous). The standard:

```text
Intake      one tracker per repo, declared in docs/agents/issue-tracker.md
Atom        research line = research/<line>/ (continuous; own pyproject + pin where applicable)
Result      finding = <line>/findings/YYYY-MM-DD-<verdict>-<slug>.md
Verdicts    confirmed | refuted | inconclusive | superseded          (per finding)
Line status active | paused | concluded | abandoned | superseded      (line README frontmatter)
Index       research/README.md generated from frontmatter — never hand-edited
Outputs     reports/ = audience-facing, dated;  artifacts/ = machine run outputs
Promotion   confirmed finding → ADR (docs/adr/) + prod PR / wiki concept / plugin
```

Enforcement is by skill, not doctrine: `/research-line` (open/register a line),
`/finding` (the only way results are written — forces a verdict and updates the index in
the same action), `/research-status` (drift detector + index regenerator), `/promote`
(finding → production). The vault's gate metrics (DSR, correlation) are optional
frontmatter fields in the same finding schema, so the autonomous pipeline and manual labs
write one format.

Deliverables (client decks, dashboards, point-in-time analyses) are **not** research: they
have an audience, not a verdict. They live in `reports/`, dated. Prototypes/apps graduate
to their own repo — they don't live under `research/`.

## Consequences

- (+) "What do we know / what did we try" answered from one generated index per repo
- (+) Index drift impossible by construction (write-and-index is atomic in `/finding`)
- (+) Ideas never live in the research tree — they go to the tracker (kills
  `RESEARCH_IDEAS.md`, stray session notes)
- (-) Migration cost in dm-evo-lab and quantbox-lab (renames, index regeneration —
  `/research-status` drives it)
- (-) Two status vocabularies retired; `REPRODUCIBILITY.md` keeps owning
  reproduced/drifted state separately
