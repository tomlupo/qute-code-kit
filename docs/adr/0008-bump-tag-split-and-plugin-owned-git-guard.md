# ADR-0008: Bump and tag are separate acts; the git-workflow guard ships with the plugin

**Status:** Accepted
**Date:** 2026-07-28

Builds on [ADR-0001](0001-matt-planning-spine-qute-runtime.md) (qute owns runtime:
safety/release/continuity) and [ADR-0006](0006-essentials-platform-contract-realignment.md)
(the essentials ↔ platform boundary: pin the contract once, align both sides).

## Context

Two independent defects surfaced on 2026-07-28. They are kept in one record because
they share a root cause and a fix shape: **a policy that existed as prose or as copies,
where it should have existed as a mechanism.**

### `/ship` bumped and tagged atomically

Correct for a single-branch repo. In a `dev → main` repo the tag lands on a `dev`
commit, so unless the release PR merges with a merge commit, the tagged commit is never
an ancestor of `main` — the tag names code that `main` does not contain.

This was not hypothetical. quantbox `v0.4.0` was cut missing a fix that had landed in
between, and had to be re-cut as `v0.4.1`. The mitigation in place was a paragraph in
`CLAUDE.md` forbidding a squash merge on the release PR — a correct rule, enforced by a
human remembering it at the moment it mattered.

A second, related failure had already been paid for: `cz` creates a **lightweight** tag
unless configured otherwise, and `git push --follow-tags` silently skips lightweight
tags. A release therefore stayed on one machine while the push reported success, and
surfaced three steps later as a consumer's lockfile failing to resolve the ref. The fix
applied at the time was a configuration key — which is to say, another rule that has to
be right in every repo.

### The git-workflow guard was hand-deployed and had drifted

A `PreToolUse` hook blocking direct commits to protected branches — the agent-side
stand-in for branch protection, which is unavailable on Free-plan private repos — lived
in `qute-platform/agent-kit/templates/claude-git-guards/`, was referenced by nothing,
and had deploy instructions pointing at a path that stopped existing when agent-kit was
folded into qute-platform. It had been copied into three repos and orphaned.

The drift was one-directional and verifiable: the template gained a fix on 2026-07-06
resolving *which* repo a git command targets when the command names one explicitly
(`git -C`, `--git-dir`, `--work-tree`); all three deployed copies were still the
2026-06-18 original. Since naming the target directory is precisely how worktree-based
agents invoke git, the stale copies could evaluate the wrong repo's policy.

### The pattern underneath

The same defect appears a third time in the material around these two: one release
policy was restated across seven files in quantbox and had drifted into three different
flows. Prose that restates a rule drifts from it. Prose that points at a mechanism
cannot.

## Decision

### Release mechanics

1. **Bump and tag are separate acts.** On the integration branch, `/ship` bumps versions,
   writes the changelog and the lockfile, and commits — no tag. `/ship --tag` on the
   release branch creates the annotated tag after the merge, asserting the branch is in
   sync with its remote, that the version declared at the tip matches, and that the tag
   does not already exist.

2. **The branch selects the mode; no flag is required.** The prior failure was a
   documented convention not applied in the moment, and a flag reproduces that failure
   shape exactly. You cannot not be on a branch. Explicit overrides exist, but the
   default path needs nothing remembered. Any branch that is neither the release nor the
   integration branch is **refused**: a feature branch has no legitimate release, and
   bumping there produces a changelog computed from a branch that is usually behind
   integration — the original defect, relocated.

3. **`/ship` creates the commit and the tag; `cz` computes them.** commitizen remains the
   engine for the increment and the changelog, driven in files-only mode. `/ship` writes
   the commit and creates the tag with `git tag -a`. Every tag this system produces is
   therefore annotated **by construction**, and the lightweight-tag failure cannot recur
   through a missing configuration key. The key is retained as a second line of defence
   for anyone running `cz bump` by hand.

4. **`--tag` pushes.** Not pushing fails silently and late — the tag sits local while
   everything looks green. Pushing wrongly fails loudly and immediately, because the
   tag-ancestry check fires on the push. We build that detector precisely so this step
   can be safe.

5. **The release branch is `main` and the integration branch is `dev`, by house rule**,
   with the topology derived from whether `origin/dev` exists. Where a repo's
   `conductor.yml` declares `release.branch`, that declaration wins — so the release tool
   and the dispatch policy cannot silently disagree.

6. **A bump already in flight blocks a second one.** Between the bump and the tag the
   declared version has no tag, and `cz` computes increments from the last tag; a second
   run would double-bump off a stale baseline. `/ship` refuses, excepting a first release
   (no tags at all).

### The guard

7. **The guard ships with the plugin**, registered beside the other guards, distributed by
   `claude plugin update`. Hand-deployment was the defect; removing the copies abolishes
   the drift class rather than reconciling it.

8. **It denies on both the release and the integration branch, and never prompts.** The
   integration branch matters because that is where the review gate lives: work reaches
   it through a PR, and a direct commit opens no PR, so it runs neither review nor CI.

9. **Consent stays per-repo.** The presence of `.claude/git-guard.json` is what opts a
   repo in; without it the guard is a no-op. Every field is optional with house defaults,
   so a repo restates nothing it does not genuinely differ on — and an explicit
   `integration_branch: null` means "this repo has none", not "unset".

10. **`conductor.yml` stays jimek's.** essentials reads `release.branch` and interoperates;
    it does not absorb the contract or add fields to it.

## Rejected alternatives

**Tag from CI on the release branch.** Reintroduces the two-version-writers problem that
removing `release.yml` from setup was meant to end. Two writers double-bump, and the
branches diverge.

**Detection only — add the ancestry check and leave `/ship` alone.** Kept as a
*complement*, not a substitute: it catches hand-cut tags `/ship` can never see. But on
its own it only finds the bad tag after it is pushed, which is the `v0.4.0 → v0.4.1`
dance with a red check attached.

**Explicit flags (`--bump-only`, `--tag`) as the only interface.** Fixes the mechanism
while preserving the failure mode. See decision 2.

**Per-repo config as `/ship`'s source of truth for branch names.** Reintroduces the
restatement problem for a fact that is the same in every repo we have. `origin/HEAD` was
also considered and rejected as unreliable — it was unset in two of six repos checked.

**Retiring the guard in favour of `pre-push` alone.** `pre-push` is the only layer that
sees humans and scripts — the actor in the 2026-07-28 direct-to-`main` commit, which came
from a shell script and was invisible to the agent guard. But it is not versioned, must be
installed once per clone, and yields to `--no-verify`. The two layers fail in opposite
directions; choosing one accepts a hole we have already been bitten by. `pre-push` is
therefore tracked as complementary work, not a replacement.

**A graduated `deny`/`ask` response, prompting on the integration branch so a deliberate
hotfix stays possible.** This was the working design until an empirical spike disproved
it. A hook returning `permissionDecision: "ask"` renders an interactive confirmation; in a
**backgrounded** agent session that stalls the worker at `status: waiting, state: blocked`
until a human attaches — precisely the failure jimek's own configuration comment describes
("a session that stops to ask has silently stalled until a human happens to look").

Branching on the payload's `permission_mode` does not rescue it: **a stalled background
session and a headless run that blocks cleanly both report `auto`**, and no other field in
the `PreToolUse` payload distinguishes them. The field correlates with attendedness
without determining it, so there is no safe way to prompt only where someone is watching.

What made denial cheap is that the hotfix path it appeared to close was never open in the
first place: the guard observes Claude tool calls, so a person at their own terminal is
unaffected by it either way. The prompt would only ever have served an *agent* performing
a hotfix on someone's behalf — a narrow case, adequately served by `/guard git-workflow off`,
which is deliberate and visible.

## Consequences

- **Squash-merging a release PR becomes safe.** quantbox's merge-commit mandate loses its
  reason and is removed. A rule kept past its reason is how the drift started.
- **A two-stage release is two commands, not one.** The second is reported by the first.
- **An abandoned bump is sticky.** Bump on the integration branch, decide not to merge, and
  `/ship` refuses until the release is completed or the bump reverted. A stuck release is
  loud; a double-bump is silent. Accepted deliberately.
- **`/ship` gains a dependency on the project's package manager** for the lockfile refresh.
  Best-effort: a refresh failure warns rather than blocking an otherwise correct release.
- **Agents lose the ability to commit directly to `dev`.** Under the dispatch contract they
  never had it — a pull request is always opened — so this enforces what the contract
  already claimed.
- **The guard now reaches every session with the plugin installed**, including repos that
  never opted in. Consent is the config file's presence, which is why that mechanism is
  preserved rather than replaced by a house default.
- **Three repos must be migrated off their local copies promptly.** During the overlap both
  guards fire, and the stale one is the copy that can produce false blocks.
