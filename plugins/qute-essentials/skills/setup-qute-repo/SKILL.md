---
name: setup-qute-repo
description: >-
  Guided repo onboarding wizard for the standard regime — the evolution of
  adopt-matt-workflow into a full setup flow. Walks a repo through: repo type
  (webapp / quant package / quant lab / quant production / simple tool / peer
  product), Matt
  spine, task tracker (Linear default, TASKS.md for simple repos), Jimek
  management (conductor.yml), behavioral rules (.claude/rules), worktree
  config, shipping mode, research regime, guards + CI posture, and root files — each step defaulted by repo type,
  diff-first, idempotent, never clobbering. Use when onboarding or re-aligning
  a repo: "set up this repo", "setup qute repo", "adopt matt workflow",
  "set up the standard regime", "onboard this repo to the regime".
argument-hint: "[webapp|quant-package|quant-lab|quant-production|simple|peer] [--standalone]"
---

# /setup-qute-repo

One wizard to take a repo from "pile of files" to a clean single regime
(ADR-0001..0004 in qute-code-kit). It supersedes `adopt-matt-workflow` and
keeps its contract: **defer, don't duplicate** — Matt's
`setup-matt-pocock-skills` owns planning-spine configuration; `/jimek-onboard`
owns the conductor contract; this wizard sequences them and stamps only the
qute deltas.

Every step: detect current state → propose (showing a diff for anything it
would write) → apply on confirmation. Re-running is safe; identical files are
no-ops. Never create a second boot file or a parallel task store — edit in
place.

## Step 0 — Snapshot

**Working-tree guard first:** run `git status` and check for a dirty tree or an
in-progress operation (`.git/MERGE_HEAD`, rebase/cherry-pick state, unmerged
paths). If found, do NOT stamp into that checkout — stop and offer either (a)
let the user clean up first, or (b) stamp from a fresh worktree off the default
branch (`git worktree add ... origin/<default>`) and land the result as a PR,
leaving the dirty checkout untouched.

Run the checks from `/check-agent-regime` (read-only) and show a one-screen
table: what exists (CLAUDE.md, docs/agents/*, docs/adr/, tracker binding,
conductor.yml, worktree.json, ship setup, research/), what's missing, what
conflicts (duplicate task stores, docs/decisions/ vs docs/adr/, stale
Paperclip/gh-track references). This snapshot drives which later steps are
"already done — skip".

## Step 1 — Repo type

Ask (or take from `$ARGUMENTS[0]`): **webapp | quant-package | quant-lab |
quant-production | simple | peer**. This is the master switch — it sets the
default for every later step:

| Step | webapp | quant-package | quant-lab | quant-production | simple | peer |
|---|---|---|---|---|---|---|
| Tracker | Linear | Linear | Linear | Linear | TASKS.md | Linear |
| Jimek-managed | optional | yes | yes | yes | no | no |
| Rigor default | standard | standard | trivial-friendly | **complex-leaning, live-capital escalation** | n/a | n/a |
| Worktrees | ports via allocate-ports | uv venv | uv venv + `shared_dirs: [data, models, output]` | uv venv, PR-only | none | none |
| Shipping | `gstack ship` | `/ship` (commitizen) | **none** (deliverables → `reports/`) | `/ship` (commitizen), tagged deploys | none | none (repo keeps its own) |
| Research regime | no | no | **yes** | no | no | no |
| CI | app CI | ruff+pytest+review-gate | light (lint only) | full + review-gate required | none | none (repo keeps its own) |

Defaults are proposals — the user can override any cell.

**`peer` — peer product, light touch.** A repo that is a full product with its
own conventions and workflow (e.g. atlas): don't pull it under the regime, just
bind it so fleet tooling can interoperate. Runs ONLY step 3 (tracker binding +
repo label) and the `docs/adr/` part of step 10, then jumps to step 11. No
conductor.yml, no `.claude/rules/`, no worktree/shipping/research stamping, and
CLAUDE.md is left alone. (TOM-59 is the reference example.)

## Step 2 — Matt spine

Detect Matt's skills (`to-spec`, `implement`, `setup-matt-pocock-skills`).
- Installed but `docs/agents/` bindings missing → run/point at
  `/setup-matt-pocock-skills` **first**, then continue.
- Not installed → offer `npx skills@latest add mattpocock/skills`, or proceed
  in **standalone mode** (`--standalone`): no Matt command references stamped.
  Standalone is healthy for simple repos, not a defect.

## Step 3 — Tracker binding

Per ADR-0004: **Linear is the task source** for serious repos (GitHub Issues
are issue *records* only — never a queue); `TASKS.md` for Tier-1 simple repos.
Stamp `docs/agents/issue-tracker.md` from
`templates/docs/agents-issue-tracker.md` with the machine marker the `/task`
engine routes on:

```
<!-- qute-tracker: linear team=TOM -->   or   <!-- qute-tracker: tasks-md -->
```

For Linear repos, confirm which Linear **project** the repo maps to (roughly
repo = project; product surfaces may combine repos — e.g. dm-evo covers lab +
app).

**Mint the repo label** (closed catalogue): onboarding is the ONE legitimate
moment a new `repo`-group child label is created on the Linear team. Create
`<owner>/<name>` under the `repo` group (via the dispatcher gateway when
reachable — a `POST /board/issue` for the repo mints it — or deliberately in
the Linear UI). Never mint any other label; the catalogue is closed (statuses
carry state, parents carry structure, groups carry routing facets).

## Step 4 — Jimek management (conductor.yml)

If the repo type says Jimek-managed (and the user agrees), run
`/jimek-onboard` — it detects conventions and stamps a schema-valid
**`conductor.yml`** (validated against the live loader,
`dispatcher.jimek.load_contract`) plus the review-gate CI. Do not hand-write
the contract here. For **quant-production** repos verify the stamped contract
carries live-capital escalation (`escalation.block_on`) and PR-only rigor
paths for all tiers.

Not Jimek-managed → skip; note it in the final report so it's a decision,
not an omission.

## Step 5 — Behavioral rules (`.claude/rules/`) — ADR-0005 §5

Stamp the repo's core behavioral contract into **`.claude/rules/`** (auto-loaded
every session like CLAUDE.md, but modular — regenerable one concern-file at a
time). Both interactive Claude AND autonomous jimek workers load these, so it is
ONE contract for two worlds; rigor tiers only add enforcement on top.

From `templates/rules/` stamp, idempotent per-file (write if absent; if present
and differing, show the diff and ask — never silently clobber):

- `git-workflow.md` — branch off default, Conventional Commits, PR-per-change
- `shipping.md` — `/ship` is the only version writer (skip/adapt when the
  repo's shipping mode is "none")
- `review-expectations.md` — non-trivial changes get an independent review
  (a separate reviewing agent, not an identity trick)
- `governance.md` — mode-conditional: copy `governance-jimek.md` if step 4 made
  the repo conductor-managed, else `governance-standalone.md`

Each file carries a `<!-- qute-rule: <name> vN -->` marker so re-runs can tell a
stamped file from a hand-authored one. `CLAUDE.md` stays human-authored
(overview/architecture) — onboarding never writes rules into it.

## Step 6 — Worktrees

Stamp `.claude/worktree.json` (consumed by the `worktrees` skill AND the
plugin's native `WorktreeCreate`/`WorktreeRemove` hooks — one setup path):

```json
{
  "base_path": "$HOME/workspace/projects/.worktrees/{project}-{slug}",
  "branch_pattern": "{type}/{slug}",
  "default_type": "feat",
  "venv_setup": "uv",
  "base_branch": "dev"
}
```

Adjust by type: quant-lab adds `"shared_dirs": ["data", "models", "output"]`
and `"default_type": "research"`; webapp keeps in-repo default + port
allocation note; Jimek-managed repos should keep branch names compatible with
Linear PR-linking (`<agent>/TOM-<n>-<slug>` is produced by the conductor —
the local pattern only governs human/interactive worktrees). Verify
`base_branch` actually exists; fall back to `main`.

## Step 7 — Shipping

- **Plugin repo** (marketplace.json) → `/ship` plugin mode, nothing to stamp.
- **Python package / production** → run `/ship --dry-run` once so its
  idempotent first-time setup lands (commitizen dev-dep, `[tool.commitizen]`
  with version reconciliation, CHANGELOG.md). `/ship` is the **only** version
  writer — if a `release.yml` workflow bumps versions, warn and neuter it
  (see the ship skill's "Who owns the version").
- **Webapp** → `gstack ship`; stamp nothing.
- **quant-lab / simple** → no releases; deliverables go to `reports/`
  (lab) or nowhere. Record "shipping: none" explicitly in CLAUDE.md.

## Step 8 — Research regime (quant-lab only)

Stamp `docs/agents/research-workflow.md` from the qute template; ensure
`research/_template/` exists and the root `research/README.md` index is
**generated** (run `/research-status` to build it). Lines via
`/research-line`, results only via `/finding`
(`YYYY-MM-DD-<verdict>-<slug>.md`), promotion via `/promote`.

## Step 9 — Guards + CI posture

- Note in CLAUDE.md that qute guards stay active under all workflows;
  quant-production additionally lists its destructive-command surface.
- CI per the type table. If Jimek-managed, review-gate came from step 4;
  otherwise offer it only where independent review is wanted (the gate is
  tier-aware and needs no policy file — installing it is the opt-in).

## Step 10 — Root files + discipline pointer

- CLAUDE.md: ensure it exists (seed from `claude/root-files/` starter if not)
  and carries a short **qute runtime** subsection in its `## Agent skills`
  block: `/task` + `/repo-status` honor `issue-tracker.md`; `/decision` →
  `docs/adr/`; `/handoff` + `/pickup` are the continuity pair; `/ship` is the
  release boundary (or "shipping: none"). Edit in place — never a second
  boot file.
- `docs/adr/` dir if absent (offer, don't force, migration of any
  `docs/decisions/`).
- `.gitignore`: `.worktrees/` (if in-repo paths), research output dirs for
  labs.
- Add a one-line pointer to the skill-router one-pager (qute-code-kit
  `docs/playbooks/skill-router.md`) so "which skill when" survives sessions.

## Step 11 — Exit check + report

Re-run the `/check-agent-regime` checks. Report: stamped / skipped /
needs-human (tracker choice, Linear project mapping, docs/decisions/
migration, review-gate adoption). The repo passes when there is exactly one
task store, one boot file, one ADR location, a stamped `.claude/rules/` with a
mode-correct `governance.md`, and every binding carries its machine marker.

## Policy (unchanged from adopt-matt-workflow)

- Matt (when present) owns grill/spec/tickets/implement/TDD/code-review.
- qute owns guards, task-store ops, handoff/pickup, ADRs, tests/audits,
  `/qute-review`, `/ship`, research regime.
- qute never grows a parallel planning flow; `/task` publishes accepted
  work, it does not decompose unclear work.
- GitHub PR transport / bot identities are Jimek's (ADR-0005; the
  `/qute-coder` / `/qute-reviewer` / `/jimek-onboard` skills ship with jimek).
