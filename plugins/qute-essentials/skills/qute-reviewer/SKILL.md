---
name: qute-reviewer
description: >-
  Post an INDEPENDENT review verdict authored by the qute-review GitHub App (qute-review[bot], app id
  4172333) and confirm a native review OBJECT was created — the review the review-gate CI requires
  before merge. Wraps the dispatcher auto-review service (POST /review), falling back to the
  qute-review-verdict helper. Because the verdict is authored by a different identity than the PR author
  (qute-coder[bot]/a human), it satisfies require-independent-reviewer. Triggers: /qute-reviewer, "post
  the independent review", "green the review gate", "run the qute review bot".
argument-hint: "<owner/repo> <pr#> [verdict body]"
---

# /qute-reviewer — post the independent qute-review[bot] verdict

Run the helper and print stdout verbatim:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/qute_reviewer_post.sh" $@
```

## What it does

1. Prefers the **dispatcher auto-review service** — `POST http://localhost:8001/review {repo,pr}` — which
   runs a cross-model review and posts it AS **qute-review[bot]** (it generates the verdict content too).
2. Falls back to `$HOME/.config/gh-apps/qute-review-verdict <repo> <pr> <body>`, which posts a supplied
   verdict body directly as qute-review[bot].
3. **Confirms a native review OBJECT** now exists (`gh api repos/<repo>/pulls/<pr>/reviews` → a review
   whose author login is `qute-review[bot]`) — not merely a PR comment. A comment does NOT satisfy the
   gate; only a review object does.

**FAIL-LOUD:** if neither path can post as the App on this host, it errors non-zero and tells you the
gate will stay red — it never hand-posts as the default gh user (that would not be an independent review).

## Relationship to `/qute-review`

`/qute-review` is the cross-model (codex) reviewer that *composes* an adversarial verdict from the diff.
`/qute-reviewer` is the thin poster that ensures the verdict lands as a **qute-review[bot]** review object
via the dispatcher/App path. Use `/qute-review` to produce the analysis; use `/qute-reviewer` to guarantee
an App-authored, independent review object exists for the gate. They compose.

## Related

- `/qute-coder` — author the PR as qute-coder[bot] so this review is independent by construction.
- `scripts/qute_reviewer_post.sh` — the kernel. Override with `QUTE_DISPATCHER_URL` / `QUTE_GH_APPS_DIR`.
