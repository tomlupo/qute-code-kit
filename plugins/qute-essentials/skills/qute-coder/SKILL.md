---
name: qute-coder
description: >-
  Open a pull request as the qute-coder GitHub App (qute-coder[bot], app id 4172326) AND chain the
  whole PR flow: open → independent review (qute-review[bot]) → assign to the human + request their
  review. Authoring agent PRs as the App — not your default gh user (e.g. tomlupo) — makes the
  require-independent-reviewer gate pass BY CONSTRUCTION (author != reviewer). Policy is flags + env
  only (ADR-0005 deleted .github/qute-pr.yml). Same create args as `gh pr create`. Use whenever you (an agent)
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
| `--base <b>` | PR base branch (native `gh` flag) | `gh` repo default |
| `--no-review` | skip the independent-review step | review ON |
| `--no-assign` | skip assign + request-review | assign ON |
| `--assign-to <login>` | override the assignee for this run | `$QUTE_ASSIGN_TO` (`tomlupo`) |
| `--review-mode <m>` | force reviewer mode (`dispatcher\|local\|auto`) | `auto` |
| `--json` | emit ONE machine-readable JSON result as the final stdout line | off (human logs only) |

**Precedence:** flag > env (`QUTE_ASSIGN_TO`) > built-in default. There is NO policy file —
ADR-0005 deleted `.github/qute-pr.yml`; merge governance is the rigor tier (jimek) or
`.claude/rules` + review-gate CI (standalone).

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
2. **REVIEW** — unless `--no-review`, automatically run the independent review (the same logic
   as `/qute-reviewer`): a **qute-review[bot]** native review object generated in a separate headless
   process (codex exec primary, `claude -p` fallback) — never an in-process subagent. This is what
   greens `require-independent-reviewer`.
3. **ASSIGN** — assign the PR to the human (default `tomlupo`; `--assign-to` / `$QUTE_ASSIGN_TO`)
   **and** request their review (`gh pr edit --add-assignee` + `--add-reviewer`, with `gh api`
   fallbacks). This is the step that lands the PR in the human's queue.
4. **REPORT** — prints the PR URL, the review verdict, and that it's assigned. It **never merges** —
   merge authority is the rigor tier (jimek-managed repos) or the human (standalone).

## Merge authority (ADR-0005)

This chain never merges. Who merges is decided elsewhere:

- **Jimek-managed repo** — the rigor tier in `conductor.yml` (trivial = auto-merge,
  standard = self-merge on SHIP, complex = human merges).
- **Standalone repo** — the human, guided by `.claude/rules` + the review-gate CI.

## Why author as the App

`require-independent-reviewer` needs the PR's review to come from a DIFFERENT identity than the author.
If an agent opens the PR as `tomlupo` and then reviews as `tomlupo`, the gate stays red (same identity).
Authoring as qute-coder[bot] means any review — `/qute-reviewer` (qute-review[bot]), codex-via-dispatcher,
or a human — is independent by construction, and the gate greens.

## Related

- `/qute-reviewer` — the standalone independent-review poster the chain invokes (also usable directly).
- `scripts/qute_coder_flow.sh` — the chain orchestrator this skill dispatches to.
- `scripts/qute_coder_pr.sh` — the open-only kernel (step 1).
- `templates/review-gate.yml` — the tier-aware CI gate (in qute-essentials).
- Override the creds dir for a non-standard host with `QUTE_GH_APPS_DIR`.
