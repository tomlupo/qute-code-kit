# Jimek verb contract — qute-essentials

**Status:** reference implementation landed for the PR/review verbs (`qute-coder`,
`qute-reviewer`). This doc is the contract the remaining verbs follow as they are
promoted to conductor-composable.

## Why

qute-essentials verbs are LLM-driven `SKILL.md` prose with baked-in policy and no
machine-readable returns. That's fine for a human at a prompt, but a conductor
(Jimek) can't **sequence** or **branch** on a verb it can't parameterize or read a
result from. The contract closes that gap **without changing human-invocation
behavior** — every knob defaults to what the verb does today.

## The three guarantees

Every Jimek-invokable verb MUST provide:

### 1. Parameterized policy (defaults = today's behavior)

Baked-in policy becomes explicit flags. The conductor passes them from `jimek.yml`;
a human who passes nothing gets the current behavior. Precedence, high → low:

```
CLI flag  >  env  >  built-in default
```

(ADR-0005 removed the `.github/qute-pr.yml` policy layer — merge/PR governance is
the rigor tier in `conductor.yml`, or `.claude/rules` + CI for standalone repos.)

Reference verbs:

| Verb | Flag | Default | Was (baked-in) |
|------|------|---------|----------------|
| qute-coder | `--base <b>` | `gh` repo default | implicit base |
| qute-coder | `--no-review` | review ON | always reviewed |
| qute-coder | `--no-assign` | assign ON | always assigned |
| qute-coder | `--assign-to <u>` | `$QUTE_ASSIGN_TO` (`tomlupo`) | hardcoded human |
| qute-coder | `--review-mode <m>` | `auto` | auto |
| qute-reviewer | `--force` | idempotent (off) | always posted |

### 2. Structured return (exit code + JSON)

With `--json`, the verb prints **exactly one JSON object as the final stdout line**;
all human/progress logging goes to **stderr**. The conductor reads the last stdout
line and branches on it. Exit code is the coarse signal; JSON carries the detail.

`qute-coder`:

```json
{"verb":"qute-coder","ok":true,"pr_url":"…/pull/7","pr_number":7,"repo":"o/r",
 "base":"main","head":"feature","created":true,
 "review":{"ran":true,"ok":true,"verdict":"SHIP-WITH-NITS"},
 "assign":{"ran":true,"ok":true,"to":"tomlupo"},"review_requested":true}
```
Exit: `0` PR open/reused + review ok-or-skipped · `2` PR could not be opened ·
`3` PR open but independent review FAILED (gate red).

`qute-reviewer`:

```json
{"verb":"qute-reviewer","ok":true,"repo":"o/r","pr":7,"mode":"local",
 "verdict":"SHIP-WITH-NITS","posted":true,"idempotent_skip":false,"review_count":1}
```
Exit: `0` a review object is present (posted or pre-existing) · non-zero if none.

Verbs **compose**: `qute-coder`'s chain invokes `qute-reviewer --json` and lifts the
`verdict` field straight out of the sub-verb's structured return.

### 3. Idempotency (re-invoking a step is safe)

A conductor retries. Re-running a verb must not duplicate side effects:

- **qute-coder** — before opening, probes `gh pr list --head <branch> --state open`.
  An existing OPEN PR is REUSED (`created:false`); no second PR. Review + assign
  (both idempotent) then run against it.
- **qute-reviewer** — keyed on the PR's **head SHA**. If a qute-review[bot] review
  object already exists at the current head SHA, it NO-OPS (`idempotent_skip:true`).
  A new commit (new head SHA) re-reviews. `--force` overrides.

Idempotency keys on *identity that should be stable* (branch for the PR, head SHA
for the review) — not a blind "already ran once", so legitimate re-review after a
fix still happens.

## Conventions for promoting the remaining verbs

1. **Flags default to current behavior.** Adding a flag must not change what a
   human who omits it sees. Regression-test this (see
   `tests/test_qute_coder_flow.py::test_defaults_regression_open_review_assign`).
2. **stdout = one JSON line under `--json`; stderr = everything else.** Never
   interleave logs into stdout, or the conductor can't parse the result.
3. **Fail-loud, structured.** On failure with `--json`, still emit an `ok:false`
   object before a non-zero exit so the conductor gets a result, not just a code.
4. **Idempotency key = stable identity**, and expose it in the return (`created`,
   `idempotent_skip`) so the conductor can tell "did work" from "already done".
5. **No policy file** (ADR-0005): flags + env are the whole policy surface; the
   conductor passes flags from `jimek.yml`'s `prFlow` block.

## Files

- `scripts/qute_coder_flow.sh` — the open→review→assign chain (contract reference).
- `scripts/qute_reviewer_post.sh` — the independent-review poster (contract reference).
- `tests/test_qute_coder_flow.py`, `tests/test_qute_reviewer.py` — contract +
  regression tests.
