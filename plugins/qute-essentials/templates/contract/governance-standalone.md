<!-- prose source: governance v1 (standalone) — /setup-qute-repo step 5 writes this as a section of the repo's CLAUDE.md. It is prose, not a file to copy: nothing stamps it into .claude/rules (ADR-0005 §5 as amended 2026-07-28). -->
# Governance mode: standalone

This repo is **not** jimek-managed. Governance = this `CLAUDE.md` + CI:

- A human (or a skill the human drives) opens PRs; the review-gate CI (if
  installed) enforces "get an independent review"; a **human merges**.
- There is no conductor, no rigor tiers, no fleet routing.
