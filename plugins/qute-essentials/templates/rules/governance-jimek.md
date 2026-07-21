<!-- qute-rule: governance v1 (jimek) — stamped by /setup-qute-repo; regenerate per-file, never hand-merge -->
# Governance mode: jimek-managed

This repo is **conductor-managed**. The rigor tiers in `conductor.yml` are the
sole merge authority for **autonomous** work (trivial = auto-merge on green CI,
standard = self-merge on SHIP verdict, complex = human merges). The conductor
stamps `jimek-tier:*` labels on managed PRs; the review-gate CI reads them.

**Interactive sessions get standalone behavior** (ADR-0005 §6): the conductor
stays out of your lane (it only claims `agent:conductor` + `autonomous`-lane
Todos), the tiers are inert for you, and your work is governed by these
`.claude/rules` + the review-gate CI. Lane labels
(`human`/`interactive`/`autonomous`) do the routing — never pick up an
autonomous-lane Todo interactively without relabeling it.
