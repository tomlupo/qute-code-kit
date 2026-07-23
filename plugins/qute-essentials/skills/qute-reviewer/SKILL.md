---
name: qute-reviewer
description: >-
  Post an INDEPENDENT review verdict authored by the qute-review GitHub App (qute-review[bot], app id
  4172333) and confirm a native review OBJECT was created — the review the review-gate CI requires
  before merge. PORTABLE: LOCAL mode (the old dispatcher POST /review is retired 2026-07-23) on forge/any box with
  gh-apps creds (generates the verdict in a separate headless process, posts via the direct App token).
  Because the verdict is authored by a different identity than the PR author (qute-coder[bot]/a human),
  it satisfies require-independent-reviewer. Triggers: /qute-reviewer, "post the independent review",
  "green the review gate", "run the qute review bot".
argument-hint: "[--json] [--force] <owner/repo> <pr#> [verdict body]"


---

> **Re-homed 2026-07-23:** the executable verbs live in qute-platform
> `agent-kit/bin/` and install to `~/bin/` via `install-runtime.sh` — this skill
> is the thin wrapper. Invoke: `bash ~/bin/qute_coder_flow.sh <args>` (coder
> chain) / `bash ~/bin/qute_reviewer_post.sh <owner/repo> <pr#> [--force]`
> (reviewer — POSITIONAL args). Never reference the retired jimek repo paths.


# /qute-reviewer — post the independent qute-review[bot] verdict

Run the helper and print stdout verbatim:

```bash
bash "$HOME/.claude/skills/qute-reviewer/qute_reviewer_post.sh" $@
```

## Verb contract (composable by Jimek / any conductor)

| Flag | Effect |
|------|--------|
| `--json` | emit ONE machine-readable JSON result as the final stdout line (human logs stay on stderr) |
| `--force` | post a fresh review even if one already exists at the PR's current head SHA |

**Structured return (`--json`):**

```json
{"verb":"qute-reviewer","ok":true,"repo":"o/r","pr":7,"mode":"local",
 "verdict":"SHIP-WITH-NITS","posted":true,"idempotent_skip":false,"review_count":1}
```

**Exit codes:** `0` a review object is present (freshly posted OR already existed) · non-zero if none
could be posted (gate stays red).

**Idempotent (default):** if a qute-review[bot] review object already exists for the PR's **current
head SHA**, this NO-OPS (`idempotent_skip:true`, `posted:false`) and reports the existing verdict —
re-running is safe, no duplicate review. A **new commit** (new head SHA) re-reviews. `--force`
overrides. Full contract in `docs/playbooks/jimek-verb-contract.md`.

## Two modes (portable) — `QUTE_REVIEW_MODE=dispatcher|local|auto` (default `auto`)

The old design hard-depended on `POST localhost:8001/review`, which is dispatcher-only (core, 127.0.0.1:8001)
and unreachable from forge or any other box. It is now portable:

- **`dispatcher`** — `POST $QUTE_DISPATCHER_URL/review {repo,pr}`. The dispatcher runs codex and posts the
  review AS **qute-review[bot]** (it generates the verdict too). Reachable only on core.
- **`local`** — dispatcher NOT reachable (forge / any box with gh-apps creds). Generates the verdict
  **locally in a separate headless process** (see independence below), then posts a native review OBJECT
  via the **direct qute-review App token** — minted from `$GHAPPS/review.pem` and sent with
  `gh api repos/<o>/<r>/pulls/<n>/reviews -X POST -f event=COMMENT -f body=…`. Needs ONLY the gh-apps
  creds, **not** the dispatcher.
- **`auto`** (default) — probes dispatcher reachability (`GET /health`); picks `dispatcher` if up, else `local`.

## Independence guarantee (local mode)

Local-mode verdict generation runs in a **SEPARATE OS PROCESS with its own CLEAN CONTEXT**, fed ONLY the PR
diff — **never an in-process Agent-tool subagent** (a subagent inherits this caller's context and can
rationalize the same way, defeating independence):

1. **PRIMARY — `codex exec`** (separate process, cross-model gpt-5.x, clean context). Strongest independence.
2. **FALLBACK — a fresh `claude -p` headless invocation** (its own clean context, given only the diff),
   when codex is unavailable/usage-capped. Still a separate process, explicitly not the Agent tool.

Either way the generated verdict is posted as the **qute-review[bot]** review object via the direct
App-token path above. (Skip codex for testing/egress reasons with `QUTE_REVIEW_NO_CODEX=1`.)

## Confirmation + fail-loud

Both modes **confirm a native review OBJECT** now exists (`gh api repos/<repo>/pulls/<pr>/reviews` → a
review whose author login is `qute-review[bot]`) — not merely a PR comment. A comment does NOT satisfy the
gate; only a review object does. **FAIL-LOUD:** if no path can post as the App on this host, it errors
non-zero and tells you the gate stays red — it never posts as the default gh user (not an independent review).

## Relationship to `/qute-review`

`/qute-review` is the cross-model (codex) reviewer that *composes* an adversarial verdict from the diff.
`/qute-reviewer` is the thin poster that ensures the verdict lands as a **qute-review[bot]** review object
via the dispatcher/App path. Use `/qute-review` to produce the analysis; use `/qute-reviewer` to guarantee
an App-authored, independent review object exists for the gate. They compose.

## Related

- `/qute-coder` — author the PR as qute-coder[bot] so this review is independent by construction.
- `scripts/qute_reviewer_post.sh` — the kernel. Env: `QUTE_REVIEW_MODE` (dispatcher|local|auto),
  `QUTE_DISPATCHER_URL`, `QUTE_GH_APPS_DIR`, `QUTE_REVIEW_NO_CODEX`.
