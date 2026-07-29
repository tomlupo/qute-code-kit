---
name: setup-qute-repo
description: >-
  Guided repo onboarding wizard for the standard regime — the evolution of
  adopt-matt-workflow into a full setup flow. Walks a repo through: repo type
  (webapp / quant package / quant lab / quant production / simple tool / peer
  product), Matt
  spine, task tracker (Linear default, TASKS.md for simple repos), Jimek
  management (conductor.yml), behavioral contract (CLAUDE.md), worktree
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
`setup-matt-pocock-skills` owns planning-spine configuration; jimek owns the
conductor contract and ships its canonical `conductor.yml` template (step 4
renders from it — there is no separate `/jimek-onboard` skill; ADR-0006 folded
its job into step 4); this wizard sequences them and stamps only the qute
deltas.

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
| CI | app CI + lock check | ruff+pytest+review-gate+release/lock guards | light (lint) + lock check | full + review-gate required + release/lock guards | none | none (repo keeps its own) |

Defaults are proposals — the user can override any cell.

**`peer` — peer product, light touch.** A repo that is a full product with its
own conventions and workflow (e.g. atlas): don't pull it under the regime, just
bind it so fleet tooling can interoperate. Runs ONLY step 3 (tracker binding +
repo label) and the `docs/adr/` part of step 10, then jumps to step 11. No
conductor.yml, no behavioral-contract sections, no worktree/shipping/research
stamping, and CLAUDE.md is left alone. (TOM-59 is the reference example.)

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

Team TOM carries three issue **templates** — surface them so hand-filed issues
match agent-filed ones: **Dispatchable task** (the What / Repro / Acceptance
criteria / Pointers / Tier hint skeleton the `/task` engine emits, TOM-216),
**Issue record → work** (a code-attached issue promoted into a task), and
**Research idea** (a line for the research regime). New UI-authored issues
should start from one of these.

**Mint the repo label** (closed catalogue): onboarding is the ONE legitimate
moment a new `repo`-group child label is created on the Linear team. Create
`<owner>/<name>` under the `repo` group via the **Linear MCP**
(`create_issue_label`, this being an interactive session) or deliberately in the
Linear UI. Never mint any other label; the catalogue is closed (statuses carry
state, parents carry structure, groups carry routing facets).

**A grouped label's name is the BARE child — never `group:child`.** Write
`autonomous`, not `lane:autonomous`; `tomlupo/qute-platform`, not
`repo:tomlupo/qute-platform`. The group is how Linear displays it, not part of the
string. This is not cosmetic: the issue-create path **silently skips** a label name
it cannot resolve, so a prefixed string produces an unlabelled — and therefore
unroutable — card. Prefixed forms are tolerated only when *reading* an owner.

**The catalogue spans TWO axes — don't collapse them.** All of these already exist
on team `TOM`; none is mintable here.

- **Dispatch** — who executes it, where, and supervised or not:
  `lane` (`autonomous`/`interactive`/`human`), `agent`, `machine` (`core`/`forge`),
  `tier`, `repo`, plus `model` and `reviewer` — the last two exist as override
  knobs that **nothing currently reads** (see TOM-376). jimek routes ownership off
  the `agent` group; only the personas in the live roster (`GET :8002/agents`)
  resolve, so `conductor` and `none` fall through.
- **Intake** — is this request real, specified, and ready for whom:
  `intake` (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
  `wontfix`) and `kind` (`bug`, `enhancement`). Driven by the `triage` skill
  (mattpocock/skills), whose five canonical roles are kept verbatim as label
  strings. Both are Linear label **groups**, so "exactly one state role" is
  enforced server-side.

The two pairs that look redundant and are not: `ready-for-agent` means a brief
exists that an agent can act on cold, while the `lane` label `autonomous` means it
may run unsupervised — an issue can carry `ready-for-agent` + `interactive` because
it touches production. And `ready-for-human` is an intake verdict, while
`needs-human` is the conductor's hand-off flag. Separately, the standalone `triage`
label is *provenance* (auto-recorded alarm finding, one deduped card per
fingerprint), not "a human should evaluate this" — that is `needs-triage`.

**Verify against the registry, never against a code comment or usage count.**
`list_issue_labels` is the only authority. Two claims in qute-platform's jimek
source are stale as of 2026-07-28: it says there is no `machine` group (there is,
with both children described) and that an `executor` group is deliberately retained
(it is absent entirely). A zero-usage label is indistinguishable from a missing one
unless you enumerate.

If a repo adopts the mattpocock engineering skills, `/setup-matt-pocock-skills`
writes `docs/agents/triage-labels.md` recording the mapping — and it does so only
when the `triage` skill is installed. Where that file exists, onboarding leaves it
alone rather than restating the vocabulary; where it does not, onboarding neither
creates nor references it.

## Step 4 — Jimek management (conductor.yml)

If the repo type says Jimek-managed (and the user agrees), onboard it to jimek
here — this absorbs the old `/jimek-onboard` skill (which never existed as a
standalone; ADR-0006 folds its job into this step):

1. **Detect jimek.** Is a jimek checkout/runtime present (e.g.
   `/opt/qute-platform/services/jimek`, or the dev clone under
   `~/workspace/projects/qute-platform/services/jimek`)? If not, tell the user
   the repo can still onboard standalone and can be promoted later — do not
   fabricate jimek wiring.
2. **Create `conductor.yml`** — the per-repo rigor-tier contract. **Render from
   jimek's canonical template** `services/jimek/config/conductor.example.yml`
   (the schema's single source of truth) when the jimek checkout is reachable;
   otherwise scaffold the same minimal starter and point the user at jimek's
   `ARCHITECTURE.md`. Rigor tiers (ADR-0005 §3): `trivial` = auto-merge on green,
   `standard` = independent review + self-merge on ship, `complex` = independent
   review + human merge. **Note:** tier *enforcement* is v1-pending in the jimek
   runner — today `conductor.yml` is the documented policy the conductor/human
   follows, so keep the file minimal.
3. **Review-gate CI** — stamp the tier-aware `templates/review-gate.yml`.
4. For **quant-production** repos, set `escalation.block_on` globs so
   live-capital paths force the `complex` tier (human merge), and confirm PR-only
   flow for all tiers.

Not Jimek-managed → skip; note it in the final report so it's a decision,
not an omission.

## Step 5 — Behavioral contract → `CLAUDE.md` (ADR-0005 §5, narrowed)

**Stamp nothing into `.claude/rules/`. Do not create the directory.** The repo's
behavioral contract goes into **`CLAUDE.md`**, as sections.

### 5a — Which sections, from which source

The prose sources are `templates/contract/*.md`, plugin-relative — resolve them
with `${CLAUDE_PLUGIN_ROOT}/templates/contract/` — the plugin root this skill is
running from, the same idiom `guard`, `audit`, `ship`, `task`, `repo-status` and
`worktrees` use. If it is unset, resolve relative to this skill file's own
directory instead (`../../templates/contract/`). Write these concerns, in this
order, each as a `##` section of `CLAUDE.md`:

| Concern | Prose source | Write it when |
|---|---|---|
| Git workflow | `templates/contract/git-workflow.md` | always |
| Shipping | `templates/contract/shipping.md` | the **confirmed shipping mode** is **not** `none` |
| Review expectations | `templates/contract/review-expectations.md` | always |
| Governance | `templates/contract/governance-jimek.md` if step 4 made the repo conductor-managed, else `templates/contract/governance-standalone.md` | always — exactly one of the two, never both |

**Settle the shipping mode once, here.** Step 1's table proposes one per repo
type, but step 1 also lets the user override any cell — so ask which mode this
repo actually ships in (`/ship` commitizen · `/ship` plugin mode · `gstack
ship` · `none`) and write it down. Step 7 branches on this **same confirmed
answer**, not on the repo type, so an overridden repo cannot be told one thing
here and the opposite there.

**Confirmed mode `none`** (the quant-lab / simple default, and any repo
overridden to it): skip the Shipping section and instead write the one-line
alternative into `CLAUDE.md` here — `shipping: none`, deliverables go to
`reports/`, no versions or tags are cut. Step 7 only confirms that line is
present. That line and the section are alternatives; writing both is the
contradiction to avoid. So this step writes **four** sections normally, and
**three** sections plus the `shipping: none` line when the mode is `none`.

These are **prose sources, not files to copy**: drop the
`<!-- prose source: … -->` header, fit the heading depth to the host `CLAUDE.md`,
and otherwise keep the wording — it is the wording the rest of the regime cites.

### 5b — Per-concern, never clobbering

Same additive discipline as the tracker binding in step 3, applied one concern at
a time:

- **Concern absent** → propose the section, show the diff, write on confirmation.
- **Concern already documented, equivalently** → no-op. Report it as "already
  covered", naming the section that covers it.
- **Concern already documented, differently** → show the diff and **ask**. Never
  silently overwrite, and never append a second section for the same concern —
  a repo that documents a concern better than the template does keeps its own
  wording, and two sections on one concern is exactly the drift this step exists
  to prevent.
- Always edit `CLAUDE.md` **in place**. Never create a second boot file, and
  never split the contract across `CLAUDE.md` and `AGENTS.md`.

Re-running the step on an already-onboarded repo must be a no-op.

### 5c — Why `CLAUDE.md` and not the `.claude/rules` layer

A `.claude/rules/*.md` file with no `paths:` frontmatter loads as the same
project-memory object as a `CLAUDE.md` section, from the same ancestor walk, at
the same session cost. It is a `CLAUDE.md` section with a second place to look.
The mechanism stays sanctioned — ADR-0005 §5 still stands, as amended — but
**only for `paths:`-scoped rules**, whose one real capability is not loading
until an accessed file matches the glob.

**A scoped rule is discovered, never stamped.** It is justified when you have a
specific set of files whose instructions should be absent the rest of the time,
which you learn during work, not at onboarding. This step used to stamp four
files: the evidence is that its `<!-- qute-rule: <name> vN -->` marker headed
every one of the five templates and matched **zero** files anywhere on the box —
the step prescribed rules before anyone had a reason for one. Those headers are
now `<!-- prose source: … -->`, and the marker is retired: nothing writes it and
nothing reads it.

Two further traps if you do reach for a scoped rule:

- The matcher resolves the project root as `dirname(dirname(rulesDir))` and
  rejects any accessed file outside it, so globs pointing at a sibling tree
  **never fire**. Three such rules sat unreachable in an agent home for weeks.
- Never move an invariant out of `CLAUDE.md` into a scoped rule. If it must hold
  every session, scoping it is how it silently stops holding.

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

**Branch on the mode step 5a confirmed, not on the repo type.** Step 1's table
only proposes a mode and the user may have overridden it, so a type-keyed bullet
here can contradict the section step 5a actually wrote. Take the confirmed mode
from step 5a and act on it:

- **`/ship` plugin mode** (repo carries `marketplace.json`) → nothing to stamp.
- **`/ship` commitizen** (the Python package / production default) → run
  `/ship --dry-run` once so its idempotent first-time setup lands (commitizen
  dev-dep, `[tool.commitizen]` with version reconciliation, CHANGELOG.md).
  `/ship` is the **only** version writer — if a `release.yml` workflow bumps
  versions, warn and neuter it (see the ship skill's "Who owns the version").
- **`gstack ship`** (the webapp default) → stamp nothing.
- **`none`** (the quant-lab / simple default) → no releases; deliverables go to
  `reports/` (lab) or nowhere. Step 5a wrote `shipping: none` into `CLAUDE.md`
  in place of the Shipping section, so **confirm that line is there** rather
  than adding a second one.

For every mode other than `none`, step 5a wrote the Shipping **section** and
there is no `shipping: none` line to look for — do not add one, and do not run
commitizen setup for a repo whose confirmed mode is `none`.

## Step 8 — Research regime (quant-lab only)

Stamp, all from the kit's `templates/research/` canonical sources (edit them
there, never per-repo — ADR-0007 Rollout #1):

- `docs/agents/research-workflow.md` from `templates/docs/agents-research-workflow.md`.
- `research/_template/` from `templates/research/_template/` — includes
  `data_inputs.yaml` (the hashed data-plane manifest) and `ref_resolver.py`
  (new-name-first engine-path resolver).
- `.research-config.yaml` at the repo root from `templates/research/.research-config.yaml`
  (set `pin_targets` to the repo's engine; keep the `staleness` block).
- `scripts/check_research_pins.py` from `templates/research/check_research_pins.py`
  — the deterministic gate (Model C pins + ADR-0007 provenance-on-conclude). Wire
  it into CI (`ruff`/`pytest` light job already present for quant-lab). If the repo
  already carries a drifted copy, replace it with the canonical one.

Ensure the root `research/README.md` index is **generated** (run `/research-status`
to build it). Lines via `/research-line`, results only via `/finding`
(`YYYY-MM-DD-<verdict>-<slug>.md`), promotion via `/promote`. Each line declares a
`reproducibility_class` (`pinned | snapshot-frozen | live-data | historical`); the
gate binds it on conclude.

## Step 9 — Guards + CI posture

- Note in CLAUDE.md that qute guards stay active under all workflows;
  quant-production additionally lists its destructive-command surface.
- **Migrate off any hand-copied guard, and stamp the config — FIRST** (TOM-351).
  Before installing anything, run the migrator. It is the same edit in every
  repo, so it is a script rather than a description. In a repo that never had
  the legacy copy it does nothing except stamp the config (and nothing at all
  once that exists) — so every run after the first is a true no-op:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/migrate_git_guard.py" --repo . --check   # see the plan
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/migrate_git_guard.py" --repo . \
      [--integration-branch none|<name>] [--protected-branch <name>] [--release-tool "…"]
  ```

  It does three things and **reports each one** — put its output in the step
  summary; a silent migration is indistinguishable from one that did nothing:

  - **Removes `.claude/hooks/git-workflow-guard.py`.** A repo carrying that file
    has a fork of the plugin's guard frozen at 2026-06-18 — *before* the fix for
    resolving which repo a `git -C <path>` command targets. Left in place
    alongside the plugin guard it is not harmless duplication: the stale copy
    can raise a FALSE BLOCK the plugin copy would not. quantbox, quantbox-live
    and quantbox-lab each carry the identical copy (their migrations are their
    own tickets).
  - **Unwires it from `.claude/settings.json` / `settings.local.json`,
    surgically.** Only the entries whose `command` names that script go; sibling
    hooks keep their structure and order — and their bytes, since the file is
    re-emitted at its own detected indent — and containers left empty are pruned
    rather than left as `[]`. A settings file that is not valid JSON is reported
    and left alone, never rewritten.
  - **Stamps `.claude/git-guard.json` when absent, minimally.** The guard
    supplies the house defaults, so `{}` is the complete config for a repo that
    wants them and a field appears only where this repo differs. The exception
    is a repo that genuinely has **no** integration branch while `origin/dev`
    exists (quantbox-live): pass `--integration-branch none` so the file says
    `"integration_branch": null` out loud — omitting it would let detection
    resurrect `dev`. An existing config is never rewritten; the repo's own
    answer outranks the stamp.

  Re-running is safe by construction: a migrated repo and a repo that never had
  the copy both come out unchanged, and `--json` reports `"changed": false`.

- **`pre-push` branch guard** (TOM-348) — the deterministic stand-in for
  server-side branch protection, which is unavailable on these repos' plan.
  Opt-in is `.claude/git-guard.json` in the repo root: its **presence** arms the
  guard, all fields are optional (`{}` = protect `main`, plus `dev` when
  `origin/dev` exists; `"integration_branch": null` = this repo genuinely has
  none) — the migrator above already stamped it, so `--opt-in` is only for a
  repo you are installing into without having run that step. Skip scratch repos
  and third-party clones. Do NOT hand-copy files or
  hand-run `pre-commit install`; run the installer, which detects the world,
  installs, and then *measures* the result:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_pre_push_guard.py" \
      --repo . [--opt-in] [--adopt-existing]
  ```

  Read the report it prints, and put its `verification:` block in the step's
  summary — "ran the installer" is not evidence, and a hook that silently is
  not installed is worse than no hook because it manufactures confidence.
  Things to get right:

  - **The hook path is git's answer, not a guess.** The installer resolves it
    with `git rev-parse --git-path hooks/pre-push`, which honours
    `core.hooksPath` — and a repo with `core.hooksPath` set makes git ignore
    `.git/hooks` entirely, so anything dropped there would never run.
  - **Always the native path; never the pre-commit framework's `pre-push`
    stage.** The framework drops ref lines whose local sha is all zeros (branch
    *deletions* never reach any hook it runs) and exposes only the first
    pushable ref of a multi-ref push. Fine for a convenience hook, not for the
    enforcement layer — so a repo that uses pre-commit still gets the native
    install, and pre-commit's generated shim is relocated to
    `pre-push.d/50-pre-commit` where it runs behind the guard with the ref lines
    replayed to it. If you ever pass `--mechanism pre-commit`, expect
    verification to FAIL on the coverage it cannot provide; do not "fix" that by
    ignoring it.
  - **An existing hand-authored `pre-push` is never clobbered.** Without
    `--adopt-existing` the installer reports `BLOCKED` and stops. With it, the
    old hook moves to `<hooks dir>/pre-push.d/00-legacy-pre-push` and the qute
    dispatcher runs in front of it, replaying the ref lines so the adopted hook
    still gets its stdin.
  - **A hook path resolving outside the repo is refused by default** — judged on
    the path, not on which config scope set it, because a repo-local
    `core.hooksPath = /home/me/.githooks` or `../shared-hooks` is exactly as
    shared as a global one. Read the refusal: it names the resolved path, the
    repo it is not inside, the config file that set it, and what is already in
    that directory. Fix the path, or pass `--allow-shared-hooks-path`
    deliberately — do not pass it just to make the message go away.
  - **Re-check after any `pre-commit install`.** It reclaims the hook slot and
    moves the dispatcher to `<slot>.legacy`, where coverage survives intact —
    **but `pre-commit install -f` deletes that file and silently uninstalls the
    guard.** Nothing prevents that; only `--check` detects it. Say so in the
    onboarding report, because it is the kind of thing that quietly stops
    protecting a repo months after anyone remembers this step.
  - **A malformed `.claude/git-guard.json` stops pushes, on purpose.** Both
    branch fields must be strings (`integration_branch` may be an explicit
    `null`); `{"protected_branch": ["main","dev"]}` or `123` is refused by name
    rather than silently guarding nothing. If a user hits this, read them the
    message — it names the field, the value, and the two-slot shape — and do NOT
    "fix" it by deleting the config, which disarms the guard entirely.
  - **The installer will not write outside the repo**, including through a
    symlink checked into the repo. If it reports a symlinked destination, that
    is worth understanding before overriding anything.
  - **`git push --no-verify` bypasses it**, as it does every client-side hook.
    That is the design, not a defect: this catches the accidental push and
    yields to the deliberate one. It is not a substitute for server-side branch
    protection — it exists precisely because protection is unavailable on these
    repos' plan.

- **The same file also arms the agent-side `git-workflow` guard.** One
  `.claude/git-guard.json`, two layers, and they are not alternatives:

  - `pre-push` is the one that HOLDS. Git hands it the resolved refs, so no
    command-line parsing is involved and it covers a human's own terminal.
  - the `git-workflow` PreToolUse hook is a SPEED BUMP in front of it: it sees
    Claude tool calls only and infers intent from a shell string, so it has an
    inherent tail of shapes it has never met — but it catches `git commit` too
    (which never reaches `pre-push`) and explains the route BEFORE the command
    runs, rather than after the work is done.

  Nothing extra to install for the second layer — it ships with the plugin and
  reads the same file. Toggle it with `/guard git-workflow off` when a
  deliberate override is wanted; that does NOT disarm `pre-push`, which yields
  only to `git push --no-verify`. Both of those facts, and "presence of
  `.claude/git-guard.json` is the opt-in", reach the repo through step 5's
  **Git workflow** section (`templates/contract/git-workflow.md`) — that is
  where the guard's contract is documented now, not in a stamped rules file.
- CI per the type table. If Jimek-managed, review-gate came from step 4;
  otherwise offer it only where independent review is wanted (the gate is
  tier-aware and needs no policy file — installing it is the opt-in).

**Release/lock guards** — stamp into `.github/workflows/`, same mechanism as
review-gate (copy the template, adjust only the marked lines). Both degrade to
a silent pass in repos they don't apply to, so stamping them is cheap:

| Template | Stamp when | Adjust at stamp time |
|---|---|---|
| `templates/release-tag-guard.yml` | the repo cuts `v*` release tags (shipping mode `/ship` or CI-owned) | `RELEASE_BRANCH` job env; the `tags:` pattern if `tag_format` isn't `v$version` |
| `templates/lockfile-check.yml` | any repo — meaningful once a `uv.lock` exists | the `push: branches:` list if the default branch isn't `main` |

- **`release-tag-guard.yml`** carries two jobs. `tag-on-release-branch` asserts
  the tagged commit is an **ancestor of the release branch** — the check the
  quantbox `version-guard.yml` ancestor lacked, which let a tag cut on an
  integration branch survive a squash-merge pointing at code the release branch
  never contained. `version-matches-tag` is the generalised version-string
  check, driven off commitizen's own `version_files` rather than hardcoded
  paths. Both need `fetch-depth: 0`; leave it alone.
- **`RELEASE_BRANCH` resolution:** leave it `""` and the workflow uses the
  repo's GitHub default branch — correct for every repo tagging off `main`, and
  the reason nothing is hardcoded. Set it explicitly ONLY when the repo's
  `conductor.yml` carries a `release.branch` that differs from the default
  branch (step 4 already read that file; reuse the value).
- **`lockfile-check.yml`** runs `uv lock --check` (staleness), not
  `--check-exists` (presence only). A repo's own version lives in its lockfile,
  so every `/ship` bump staleness the lock — this is what catches it. No
  `uv.lock` → the job reports the absence and passes.

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
task store, one boot file, one ADR location, a `CLAUDE.md` carrying the
behavioral contract with the mode-correct governance section, no unscoped
`.claude/rules` file anywhere, and every binding carrying its machine marker.

**`peer` repos are exempt from most of that** — step 1 runs only the tracker
binding and the `docs/adr/` part of step 10, so a peer repo passes on those two
criteria alone. Do not report a peer repo as failing for a `CLAUDE.md` contract
it was deliberately never given.

Two of the remaining criteria are mechanical; the rest are a read.

- **No unscoped rule file** — `.claude/rules` need not be absent, only free of
  files that would be `CLAUDE.md` sections. Run this; empty output passes:

  ```bash
  find .claude/rules -name '*.md' 2>/dev/null | while read -r f; do
    grep -qE '^paths:' "$f" || echo "UNSCOPED (belongs in CLAUDE.md): $f"
  done
  ```

- **Machine markers present** — `grep -rn 'qute-tracker:' docs/agents/` must
  find the tracker binding from step 3.
- **The behavioral contract is a HUMAN CHECK.** "Carries the contract with the
  mode-correct governance section" is not mechanized by anything: no script
  knows whether a `CLAUDE.md` section actually says what step 5's source says,
  and a repo may legitimately word it its own way. Open `CLAUDE.md` and confirm
  that the concerns of step 5a **that apply to this repo** are each covered
  exactly once — **four** sections normally, or **three** sections plus a
  `shipping: none` line when the confirmed shipping mode is `none` — and that the
  governance section matches the mode step 4 chose. Then say in the report that
  you read it. Do not report this criterion as verified on the strength of the
  two commands above, and do not fail a `shipping: none` repo for the Shipping
  section step 5a told you to skip.

## Policy (unchanged from adopt-matt-workflow)

- Matt (when present) owns grill/spec/tickets/implement/TDD/code-review.
- qute owns guards, task-store ops, handoff/pickup, ADRs, tests/audits,
  `/qute-review` (the single independent-review skill), `/ship`, research regime.
- qute never grows a parallel planning flow; `/task` publishes accepted
  work, it does not decompose unclear work.
- GitHub PR **transport / bot identities** are Jimek's (ADR-0005/0006; the
  `/qute-coder` skill ships with jimek). Onboarding a repo *to* jimek
  (conductor.yml) is Step 4 of this skill, not a separate `jimek-onboard` skill.
  Independent review itself is `/qute-review` in essentials (it absorbed the
  retired `qute-reviewer`).
