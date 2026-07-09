---
name: qute-coder
description: >-
  Open a pull request as the qute-coder GitHub App (qute-coder[bot], app id 4172326) AND chain the
  whole PR flow: open → independent review (qute-review[bot]) → assign to the human + request their
  review. Authoring agent PRs as the App — not your default gh user (e.g. tomlupo) — makes the
  require-independent-reviewer gate pass BY CONSTRUCTION (author != reviewer). Policy comes from the
  repo's committed .github/qute-pr.yml. Same create args as `gh pr create`. Use whenever you (an agent)
  open a PR. Triggers: /qute-coder, "open a PR", "create the PR as the bot", "author this PR independently".
argument-hint: "[chain flags] [gh pr create args — e.g. --repo o/r --base main --title \"…\" --body \"…\"]"
---

# /qute-coder — open a PR as qute-coder[bot] and chain open → review → assign

Run the chain helper, passing the user's args straight through (chain-control flags are consumed;
everything else is exactly `gh pr create` args), and print stdout verbatim:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/qute_coder_flow.sh" $@
```

## Verb contract (composable by Jimek / any conductor)

This verb is machine-composable while **human defaults stay unchanged** — every chain-control flag
defaults to today's behavior. See `docs/playbooks/jimek-verb-contract.md` for the full contract.

| Flag | Effect | Default |
|------|--------|---------|
| `--base <b>` | PR base branch (native `gh` flag; also `baseBranch` in `.github/qute-pr.yml`) | `gh` repo default |
| `--no-review` | skip the independent-review step | review ON (policy `independentReview`) |
| `--no-assign` | skip assign + request-review | assign ON |
| `--assign-to <login>` | override `assignTo` for this run | policy `assignTo` (`tomlupo`) |
| `--review-mode <m>` | force reviewer mode (`dispatcher\|local\|auto`) | `auto` |
| `--json` | emit ONE machine-readable JSON result as the final stdout line | off (human logs only) |

**Precedence:** flag > `.github/qute-pr.yml` policy > built-in default. A caller `--base` always
wins over policy `baseBranch`.

**Structured return (`--json`)** — the conductor branches on this:

```json
{"verb":"qute-coder","ok":true,"pr_url":"…/pull/7","pr_number":7,"repo":"o/r","base":"main",
 "head":"feature","created":true,
 "review":{"ran":true,"ok":true,"verdict":"SHIP-WITH-NITS"},
 "assign":{"ran":true,"ok":true,"to":"tomlupo"},"review_requested":true}
```

**Exit codes:** `0` PR open/reused + review ok-or-skipped · `2` PR could not be opened · `3` PR is
open but the independent review FAILED (gate stays red).

**Idempotent:** re-invoking for the same head branch REUSES an existing OPEN PR (`created:false`)
instead of opening a second one; review + assign (both idempotent) then run against it.

## The chain (one command)

1. **OPEN** — mint a short-lived installation token for the **qute-coder** GitHub App (app id
   4172326) from the shared gh-apps creds and run `gh pr create "$@"` with it, so the PR is authored
   by **qute-coder[bot]**. **FAIL-LOUD** if the App creds are absent on this host: it errors and exits
   non-zero rather than silently falling back to your default gh user. (A forge/CI host without creds
   must error, not mis-attribute the PR to a human.)
2. **REVIEW** — unless the policy disables it, automatically run the independent review (the same logic
   as `/qute-reviewer`): a **qute-review[bot]** native review object generated in a separate headless
   process (codex exec primary, `claude -p` fallback) — never an in-process subagent. This is what
   greens `require-independent-reviewer`.
3. **ASSIGN** — assign the PR to the human (`assignTo`, default `tomlupo`) **and** request their review
   (`gh pr edit --add-assignee` + `--add-reviewer`, with `gh api` fallbacks). This is the step that
   lands the PR in the human's queue.
4. **REPORT** — prints the PR URL, the review verdict, and that it's assigned. It **never merges** —
   merge is the human's (unless `allowAgentSelfMerge: true`, see below).

## Per-repo policy — `.github/qute-pr.yml` (single source of truth)

Policy lives in a **committed, tool-agnostic** file at the repo root, **`.github/qute-pr.yml`**, read by
BOTH the CI `review-gate.yml` workflow (the server-side gate) AND this client chain + the hooks — one
source of truth. Schema + defaults:

| key                    | type | default   | meaning                                                          |
|------------------------|------|-----------|------------------------------------------------------------------|
| `assignTo`             | str  | `tomlupo` | who the PR is assigned to + review requested from                |
| `independentReview`    | bool | `true`    | run the auto independent review inside the chain                 |
| `allowAgentSelfMerge`  | bool | `false`   | if `false` the agent must NOT merge (assign to the human)        |
| `enforce`              | bool | `false`   | whether the blocking PR-flow hooks + the CI review-gate fire     |

**Defaults when the file/keys are absent:** review on, assign to `tomlupo`, self-merge off, enforce off.
A repo overrides any subset. A repo with **no** `.github/qute-pr.yml` behaves exactly as these
defaults — nothing new fails (non-breaking).

Example `.github/qute-pr.yml`:

```yaml
assignTo: alice            # assign PRs to + request review from @alice
independentReview: true    # auto-run the qute-review[bot] review in the chain
allowAgentSelfMerge: false # agent must not merge; @alice merges
enforce: true              # turn on the blocking merge/create guard + CI gate
```

Keys may also be nested under a top-level `qutePrWorkflow:` mapping — both forms are accepted. A copy
you can drop in lives at `templates/qute-pr.yml`.

**Backward-compat (transition):** a repo that still has the original `"quteEnforcePrReview": true` marker
in `.claude/settings.json` is honored as `enforce: true`. `.github/qute-pr.yml` is the documented
primary home going forward.

## `allowAgentSelfMerge` gates merge

The merge-guard hook respects `allowAgentSelfMerge` when `enforce: true`:

- **`false` (default)** — the agent's `gh pr merge` is **blocked** unconditionally; the PR is assigned to
  the human, who merges.
- **`true`** — the agent's `gh pr merge` is allowed **only after** a passing **qute-review[bot]** review
  object exists on the PR (otherwise still blocked).

## Why author as the App

`require-independent-reviewer` needs the PR's review to come from a DIFFERENT identity than the author.
If an agent opens the PR as `tomlupo` and then reviews as `tomlupo`, the gate stays red (same identity).
Authoring as qute-coder[bot] means any review — `/qute-reviewer` (qute-review[bot]), codex-via-dispatcher,
or a human — is independent by construction, and the gate greens.

## Related

- `/qute-reviewer` — the standalone independent-review poster the chain invokes (also usable directly).
- `scripts/qute_coder_flow.sh` — the chain orchestrator this skill dispatches to.
- `scripts/qute_coder_pr.sh` — the open-only kernel (step 1).
- `scripts/pr_flow_config.py` — resolves `.github/qute-pr.yml` (used by the chain, hooks, and tests).
- `templates/qute-pr.yml` — annotated policy template; `templates/review-gate.yml` — the CI gate.
- Override the creds dir for a non-standard host with `QUTE_GH_APPS_DIR`.
