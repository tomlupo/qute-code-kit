# ADR-0001: Matt skills are the planning spine; qute-essentials is the runtime + quant additions

**Status:** Accepted
**Date:** 2026-07-18

## Context

qute was accreting planning-flavored features (spec-ish docs, workflow docs, ever-growing
CLAUDE.md files) and target repos ended up with several competing regimes: duplicate task
boards, inconsistent doc structures, no discipline at the moment of work.
[Matt Pocock's skills](https://github.com/mattpocock/skills) already provide a disciplined
engineering method (grill → spec → tickets → implement → TDD → code-review) **and** the
repo-configuration conventions to anchor it (`docs/agents/*.md`, `docs/adr/`, root
`CONTEXT.md`, `setup-matt-pocock-skills`).

## Options Considered

1. **Federation** — qute and Matt as peer frameworks with an ownership treaty (the approach
   drafted in PRs #67/#68)
2. **Adoption** — Matt's workflow and file conventions are the spine; qute shrinks to what
   Matt doesn't cover and speaks his conventions
3. **Independence** — qute grows its own planning layer

## Decision

Adoption (option 2). `qute-essentials = Matt workflow (assumed installed) + runtime layer
+ quant/research additions`. Concretely:

- ADRs live in `docs/adr/` (Matt's convention); `/decision` writes there.
- Repo agent policy lives in `docs/agents/*.md` prose files (no qute-specific YAML schema);
  `/task` and `/repo-status` honor `docs/agents/issue-tracker.md` when present.
- Repo config is stamped by Matt's `setup-matt-pocock-skills`; qute's `/setup-qute-repo` (né adopt-matt-workflow)
  is a thin complement that adds only qute deltas (guards, release, research mode).
- Matt is **assumed installed, never required**: every qute core skill works standalone;
  Matt-aware behavior activates only on detection (graceful degradation).
- GitHub PR transport and bot identities (`/qute-coder`, `/qute-reviewer`, `/jimek-onboard`,
  `.github/qute-pr.yml`, review-gate CI) are Jimek infrastructure that landed in qute; they
  will relocate to Jimek (see `docs/architecture/jimek-migration.md`). This is a
  relocation, not a deprecation.

## Consequences

- (+) One regime per repo: Matt plans, qute runs, `docs/agents/` binds both to the domain
- (+) Interop by construction — Matt's and qute's skills read the same config files
- (+) qute stops growing planning features; new-skill litmus test: "is this runtime,
  research, or domain — or is it Matt's job?"
- (-) Docs reference an external toolkit we don't control; skill renames upstream can
  stale our routing blocks
- (-) `/handoff` name-collides with Matt's lighter handoff skill; qute's (with `/pickup`)
  is the one to use
