# ADR-0005: qute-essentials / jimek boundary — two governance modes, tier is the merge authority

**Status:** Accepted
**Date:** 2026-07-21

## Supersedes

[docs/architecture/jimek-migration.md](../architecture/jimek-migration.md) — the relocation
plan. That doc had `.github/qute-pr.yml` *moving* to jimek; this ADR **deletes** it, and adds
the with/without-jimek axis and the `.claude/rules` behavioral core it didn't have. Builds on
[ADR-0001](0001-matt-planning-spine-qute-runtime.md) (Matt spine / qute runtime),
[ADR-0003](0003-task-tracking-tiers-linear-jimek.md) and
[ADR-0004](0004-linear-task-source-github-issues-record.md) (Linear task source).

## Context

qute-essentials (the kit/plugin) and jimek (the autonomous conductor) grew overlapping
GitHub-flow machinery: jimek built its own in-process review + PR + board logic while
qute-essentials kept the `qute-pr.yml` policy contract, the review-gate CI, and the
`qute-coder`/`qute-reviewer` skills. The migration was half-done, so **both worlds ran at
once** and their seams caused real failures (2026-07-21 e2e session):

- `qute-pr.yml allowAgentSelfMerge: false` (qute-essentials) fought the rigor **tier**
  (jimek's `conductor.yml`) over merge authority — two policy sources, one PR.
- the review-gate CI read `qute-pr.yml enforce` and was **tier-blind** — a trivial-tier
  change (no review by doctrine) could never pass it.
- two review runners (`qute-review` skill vs `src/dispatcher/review.py`) already drifted.

The root question: **what does each component own, and how does a repo work with *or*
without jimek?**

## Decision

### 1. Governance mode is chosen at onboarding — standalone or jimek-managed

Every repo picks one mode when `setup-qute-repo` runs:

- **Standalone (without jimek).** The qute-essentials baseline on Matt's spine. Governance =
  `.claude/rules` + CI. A human (or a skill) drives PRs; the review-gate CI runs; a review is
  posted by a human or a skill; a **human merges**. No conductor, no tiers, no fleet.
- **Jimek-managed (with jimek).** Adds `conductor.yml` (rigor tiers) and the autonomous
  conductor drives the whole PR lifecycle. A pure opt-in overlay on top of the standalone base.

Onboarding is the fork: **no jimek** → stamp `.claude/rules` + review-gate CI, no
`conductor.yml`; **jimek** → additionally stamp `conductor.yml` + tier wiring.

### 2. Responsibility split

| Component | Home | Role |
|---|---|---|
| **qute-essentials** | the standalone base | Matt spine + runtime skills (`/ship`, `/decision`, `/test`, `/audit`, `/task`, guards) + CI templates + `.claude/rules` onboarding. Works alone; where a repo *starts*. |
| **jimek** | opt-in overlay | the conductor + `conductor.yml` (rigor tiers) + the GitHub **transport verbs**. Only present with jimek. |
| **`qute-coder` / `qute-reviewer` / `jimek-onboard`** | → **jimek** | they post AS the bot identities — meaningless without the conductor. Standalone repos use human/`gh` + a reviewer. |
| **`qute-review` (skill)** | stays in qute-essentials, **repositioned as the quant-domain reviewer** | Matt's skills already give *general* repos review tooling; `qute-review` is the deep **quant** reviewer, invoked by a human (or, for quant repos, by jimek). Not "the reviewer." |
| **review-gate CI** | qute-essentials (ships the template) | works both modes; see §4. |
| **`.github/qute-pr.yml`** | **DELETED** | merge/PR governance is `.claude/rules` (standalone) or the rigor **tier** in `conductor.yml` (jimek). §3. |

The two GitHub Apps — **qute-coder[bot]** (authors agent PRs) and **qute-review[bot]** (posts
independent verdicts) — are jimek's transport identities. Their only job is to make
`author ≠ reviewer` true by construction so the review gate passes.

### 3. The rigor tier is the single merge authority (qute-pr.yml is gone)

For jimek-managed repos, `conductor.yml`'s tier decides review + merge + board status
(trivial = auto-merge / standard = on-ship self-merge / complex = human merge). There is no
second policy file. For standalone repos, the human decides the merge; `.claude/rules` states
the expectation and the CI gate enforces "get a review."

### 4. The review-gate CI is tier-aware and degrades gracefully

The gate reads the PR's `jimek-tier:*` label (stamped by the conductor, a trusted writer):

- `jimek-tier:trivial` → **pass** (no independent review required by doctrine).
- `jimek-tier:standard|complex` → require an independent review object.
- **no label** (a standalone repo, or an interactive PR in a jimek repo) → require an
  independent review object — the standalone default.

One template serves both modes: with jimek the label makes it tier-aware; without, it is the
"require a review" gate. It no longer reads `qute-pr.yml`.

### 5. `.claude/rules` is the shared behavioral contract; tiers are the enforcement layer

`setup-qute-repo` stamps the repo's core behavioral rules into **`.claude/rules/`** (auto-loaded
every session, modular, regenerable per-concern — the same additive/never-clobber pattern as the
issue-tracker setup):

- **common core** (both modes): `git-workflow.md` (branch off default, Conventional Commits,
  PR-per-change), `shipping.md` (`/ship`, version/changelog conventions), `review-expectations.md`
  (the human-readable "non-trivial changes get an independent review before merge"), tracker rules.
- **jimek-conditional note**: with jimek — the repo is conductor-managed, tiers live in
  `conductor.yml`, autonomous work is lane-routed, *interactive work is yours and the conductor
  stays out of your lane*; without jimek — governance is `.claude/rules` + CI, human-driven merge.

`.claude/rules` (not `CLAUDE.md`) is the home for the stamped core: it auto-loads at session
start exactly like CLAUDE.md but is modular, so onboarding regenerates one concern-file at a time.
`CLAUDE.md` stays human-authored (project overview/architecture), never clobbered by onboarding.

Because both interactive Claude and autonomous workers run inside a repo checkout, **both
auto-load the same `.claude/rules`** — one behavioral contract, two worlds. Rigor tiers add only
the *automation/enforcement* layer for the autonomous case; they do not restate the rules.

### 6. Interactive sessions in a jimek repo get the standalone behavior

`conductor.yml` governs **machines, not you**. When a human drives an interactive session in a
jimek-managed repo: the conductor stays out of the lane (it only claims `agent:conductor` +
`autonomous`-lane Todos), the rigor tiers are **inert** (they gate autonomous workers only), and
the session is governed by `.claude/rules` + the review-gate CI — i.e. standalone behavior.
Interactive sessions are **not** tier-aware by design: the human is the authority, and the
behaviors tiers encode (get a review, don't self-merge risky changes) already live in
`.claude/rules` as plain guidance. The lane labels (`human`/`interactive`/`autonomous`) do the
routing.

### 7. Board writes are conductor-owned (already implemented)

The dispatcher binds localhost by hardening (the RCE `/sessions` surface stays off the network),
so forge workers can't reach `POST /board/status`. Board writes moved to the conductor (runs on
core, localhost-reachable) — the board-write analogue of the Option D pull-over-SSH status plane.
Workers drive GitHub only (review + `gh pr merge`, which are reachable). Shipped in jimek this
session.

## Resolved sub-decisions (2026-07-21)

### Independence is a separate reviewing *agent*, not an identity

The gate's `author ≠ reviewer` identity check is a **mechanical proxy that is gameable** — you can
post as another identity without any genuine independent look. The real independence is a
**separate reviewing agent** with fresh context and no stake in the code. Consequences:

- The **review capability lives in the shared review core and is invocable in ANY session** —
  interactive or autonomous. A human driving an agent can invoke a genuinely independent review on
  their own PR (spawn a separate review agent), which is the substantive thing; posting the verdict
  as `qute-review[bot]` is a **thin optional adapter** to satisfy a mechanical gate, not the point.
- So there is **no standalone/jimek duplication** of the review capability and no separate
  standalone reviewer to build: one core, called from either entry point.
- The gate rule stays "an independent review object exists" as its *checkable* form, understood as
  a proxy for "a separate agent reviewed this." Human-authored PRs may still invoke it on demand.

### One review core = Matt review base + quant layer, two entry points

A single review implementation. `qute-review` **reuses Matt's review skill and adds a quant layer
on top** — so it handles both general and quant repos (not quant-only). The interactive entry is
the skill; the autonomous entry is the conductor; both call the same core. This retires the two
drifted runners (`qute-review` skill vs `src/dispatcher/review.py`).

### Verifiability classification — deferred to a future classifier

With board writes conductor-side, the worker's per-criterion machine-vs-human verifiability
judgment no longer reaches the board (only the pre-declared `humanQA` globs/markers do). There is
no perfect fix. **Interim:** rely on per-repo `humanQA` rules (a repo knows which paths are
visual). **Later:** add a **classifier** (analogous to a quality gate on the issue body) that
decides machine- vs human-verifiable. Not built now; not blocking (machine-verifiable changes
correctly go Done today).

## Path to target state

Ordered; each step is safe on its own and nothing deletes a working piece before its replacement
is proven (the migration doc's Order §4 discipline is retained).

1. **Tier-aware gate + conductor tier-labelling** — *done this session.* The gate reads
   `jimek-tier:*`; the conductor stamps it via REST. This is the keystone: it lets one gate serve
   both modes and removes the gate's dependency on `qute-pr.yml`.
2. **Conductor-side board writes** — *done this session.* Removes the worker→dispatcher
   reachability dependency.
3. *(done 2026-07-21)* **Delete `qute-pr.yml`.** Point the gate template solely at the tier label (already does) and
   drop the file from onboarding + existing repos. Remove `pr-flow-guard`/`pr_flow_config` reads.
4. *(done 2026-07-21)* **Move `qute-coder` / `qute-reviewer` / `jimek-onboard` into jimek.**
   Resolved: jimek ships them under `skills/<name>/` (SKILL.md + helper scripts) and
   auto-installs them globally as whole-dir symlinks on bot start (`managed_skills`). They are the conductor's
   transport verbs. qute-essentials stops shipping them in a minor-major bump; README drops them.
5. *(done 2026-07-21)* **Stand up `.claude/rules` onboarding in `setup-qute-repo`.** Stamp the common core +
   jimek-conditional note; make it idempotent per-concern-file. Move the review-gate CI template
   ownership here (or to jimek — one unit with the gate; decide with step 4).
6. *(done 2026-07-21)* **Reposition `qute-review` as the quant reviewer.** Update its description/triggers to quant
   scope; document that general repos use Matt's review tooling.
7. *(done 2026-07-21)* **Collapse the two review runners**
   Resolved: the canonical prompt is `skills/qute-review/review-core.md`; jimek's
   `dispatcher/review.py` loads it (env > checkout > plugin cache > embedded fallback). into one shared core (interactive entry = skill, autonomous
   entry = conductor), resolving the quant/general split from the open choices.

All steps 1–7 are done (2026-07-21). Gate-template ownership resolved: qute-essentials ships the
canonical `templates/review-gate.yml`; jimek-onboard renders from it (env > checkout > plugin cache).
