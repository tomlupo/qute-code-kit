---
name: qute-coder
description: >-
  Create a pull request authored by the qute-coder GitHub App (qute-coder[bot], app id 4172326)
  instead of `gh pr create`. Authoring agent PRs as the App — not your default gh user (e.g. tomlupo) —
  makes the require-independent-reviewer gate pass BY CONSTRUCTION (author != reviewer). Same args as
  `gh pr create`. Use whenever you (an agent) open a PR. Triggers: /qute-coder, "open a PR", "create the
  PR as the bot", "author this PR independently".
argument-hint: "[gh pr create args — e.g. --repo o/r --base main --title \"…\" --body \"…\"]"
---

# /qute-coder — open a PR authored by qute-coder[bot]

Run the helper, passing the user's args straight through (they are exactly `gh pr create` args),
and print stdout verbatim:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/qute_coder_pr.sh" $@
```

## What it does

- Mints a short-lived installation token for the **qute-coder** GitHub App (app id 4172326) from the
  shared gh-apps creds (`$HOME/.config/gh-apps/coding.env` + `coding.pem` + `gh-app-token`), then runs
  `gh pr create "$@"` with that token so the PR is authored by **qute-coder[bot]**.
- **FAIL-LOUD** if the App creds are absent on this host: it errors and exits non-zero rather than
  silently falling back to your default gh user. (This is deliberately different from `~/bin/coder-pr`,
  which fails soft.) A forge/CI host without creds must error, not mis-attribute the PR to a human.

## Why author as the App

`require-independent-reviewer` needs the PR's review to come from a DIFFERENT identity than the author.
If an agent opens the PR as `tomlupo` and then posts a review as `tomlupo`, the gate stays red (same
identity). Authoring the PR as qute-coder[bot] means any review — `/qute-reviewer` (qute-review[bot]),
codex-via-dispatcher, or a human — is independent by construction, and the gate greens.

## Related

- `/qute-reviewer` — post the independent qute-review[bot] verdict that satisfies the gate.
- `scripts/qute_coder_pr.sh` — the kernel this skill dispatches to.
- Override the creds dir for a non-standard host with `QUTE_GH_APPS_DIR`.
