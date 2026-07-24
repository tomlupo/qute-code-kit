---
name: research-status
description: >-
  Research drift detector + index regenerator. Walks research/, reads line/finding frontmatter,
  regenerates research/README.md, and reports regime violations: stale or lying index, lines
  silent for weeks, missing verdicts, loose dated files in line roots, duplicate findings files,
  non-research dirs under research/. Use when the user says "research status", "what's the state
  of research", "where did we leave X", "I'm lost in the research", or before planning new work.
argument-hint: "[--fix] [--stale-weeks N]"
---

# /research-status

Answer "what do we know and what's rotting" from frontmatter, not memory.

## Behavior

1. **Walk `research/*/`** (skip `_template`). For each line read `README.md` frontmatter
   and `findings/*.md` frontmatter. A dir without frontmatter is itself a finding (of drift).
2. **Regenerate the index** — `research/README.md` Active/Concluded tables, one row per
   line: `line | status | question | latest finding (date + verdict) | tracker`. The
   generated index is authoritative; never preserve hand-edits that contradict frontmatter
   (report them instead).
3. **Report drift**, most severe first:
   - index rows that contradict or omit actual dirs (the "index lies" failure)
   - unregistered dirs under `research/` (no frontmatter)
   - non-research content under `research/` — deliverables (audience outputs → `reports/`),
     app prototypes (→ own repo), idea files (`RESEARCH_IDEAS.md`, session notes → tracker)
   - loose dated `.md` files in line roots (should be `findings/YYYY-MM-DD-<verdict>-*.md`)
   - conflicting rollups (`findings.md` vs `FINDINGS.md`)
   - `active` lines with no finding in `--stale-weeks` (default 4) — propose `paused`,
     `abandoned`, or a next step
   - **stale engine pins (ADR-0007 #4)** — for each line with a Model C pin, run
     `git -C <engine-root> rev-list --count <pin>..<default-branch>` and the age of the
     pinned commit; flag any past the `.research-config.yaml::staleness` thresholds
     (`max_commits` default 200, `max_days` default 60, `default_branch` default `main`).
     This is what surfaces a 498-commit lag with zero manual effort. Engine-root is the
     sibling checkout of `pin_targets[].repo`; if it isn't present locally, report
     "pin staleness unknown (engine checkout not found)" rather than guessing. Recommend
     `/research-repin <line>` for anything flagged.
   - findings missing a verdict in filename or frontmatter
   - confirmed material findings with `promoted_to: null` — promotion candidates
   - **concluded lines that would fail the gate** — a `concluded` line whose
     `reproducibility_class` is unset, or whose `pinned`/`snapshot-frozen` inputs lack
     hashes, or whose `live-data`/`historical` status lacks a `repro_note`. Mirror the
     `check_research_pins.py` provenance-on-conclude check so drift shows here before CI.
4. **`--fix`** (with per-change confirmation): register unregistered lines, move loose
   dated files into `findings/` (inferring verdicts where the text states one), merge
   rollup variants, move deliverables to `reports/`. Never delete; never infer a verdict
   that isn't stated — mark `inconclusive` and flag it.
5. **Output**: regenerated index summary + numbered findings + recommended next actions.
   Keep it to one screen; this skill is a dashboard, not an essay.

Read-only by default — without `--fix`, only `research/README.md` is written.
