---
name: adopt-matt-workflow
description: >-
  Configure a repo for the standard regime: Matt Pocock skills as the planning spine,
  qute-essentials as the runtime, docs/agents/ as the binding. THIN by design — defers repo
  configuration to Matt's own setup-matt-pocock-skills and adds only qute deltas (guards note,
  release conventions, research mode, tracker tiers). Use when onboarding a repo to the hybrid
  regime: "adopt matt workflow", "set up the standard regime", "make this repo follow the
  qute/matt split". Works without Matt installed (standalone mode).
argument-hint: "[--research] [--standalone]"
---

# /adopt-matt-workflow

One entry point to stamp the standard regime (ADR-0001..0003 in qute-code-kit). Defer,
don't duplicate: Matt's `setup-matt-pocock-skills` owns issue-tracker/triage/domain-docs
configuration — this skill runs *around* it.

## Behavior

1. **Detect Matt.** Are Matt's skills available (`to-spec`, `implement`,
   `setup-matt-pocock-skills` in the skill list)?
   - Installed → if `docs/agents/issue-tracker.md` / `domain.md` are missing, tell the
     user to run `/setup-matt-pocock-skills` first (or offer to walk through it), then
     continue with the qute deltas below.
   - Not installed → offer `npx skills@latest add mattpocock/skills`, or proceed in
     **standalone mode** (`--standalone`): qute-only, no Matt command references stamped
     anywhere. Standalone is a healthy mode for small repos, not a defect.
2. **Tracker tier** (ADR-0003) — confirm what `docs/agents/issue-tracker.md` declares, or
   help pick: `TASKS.md` (simple/personal) or **Linear** (serious; GitHub Issues stay as
   the repo-local backlog — a Linear task may be "do issue #X"; Jimek monitors Linear for
   assigned tasks and reads `jimek.yml` for how to run them).
3. **qute deltas** — add only what Matt's setup doesn't cover:
   - `docs/agents/research-workflow.md` from the qute template when `--research` or the
     repo has a `research/` dir (research-repo mode: lines + `/finding` + generated index)
   - a short **qute runtime** subsection in the existing `## Agent skills` block of
     CLAUDE.md/AGENTS.md (edit in place, never create a second boot file):
     guards stay active under all workflows; `/task` `/repo-status` honor
     `issue-tracker.md`; `/decision` writes `docs/adr/`; `/handoff`+`/pickup` are the
     continuity pair (qute's handoff shadows Matt's lighter one — use qute's);
     `/ship` is the release boundary
   - `docs/adr/` dir if absent (migrating any existing `docs/decisions/` is offered,
     not forced)
4. **Show diffs before writing.** Preserve existing content; this skill is idempotent and
   never clobbers.
5. **Report** what was stamped, what was skipped, and what needs a human decision
   (tracker choice, Paperclip→Linear migration, research-mode adoption).

## Policy stamped (summary)

- Matt (when present) owns: grill/spec/tickets/implement/TDD/code-review.
- qute owns: guards, task-store ops, handoff/pickup, ADRs, tests/audits, `/qute-review`,
  `/ship`, research regime skills.
- qute never grows a parallel planning flow; `/task` publishes accepted work, it does not
  decompose unclear work (that's grilling).
- GitHub PR transport / bot identities are Jimek's (see qute-code-kit
  `docs/architecture/jimek-migration.md`).
