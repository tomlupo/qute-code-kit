---
name: qute-review
description: >-
  The shared review core (ADR-0005): adversarial, INDEPENDENT code review — Matt's review-skill
  base plus a quant layer (look-ahead, survivorship, data-path, fabrication) — that posts a native
  GitHub review verdict, the verdict the review-gate CI requires before merge. ONE review core, two
  entry points: this skill (interactive) and jimek's conductor (autonomous) both drive the same
  canonical prompt (review-core.md). Runs cross-model (codex) with a security-first,
  failure-class-driven framing, multi-run for risky code, with a Code Reviewer subagent fallback.
  Use before merging any non-trivial PR, or when the review-gate is red. Triggers: /qute-review,
  review this PR, run the review gate, independent review, post a reviewer verdict.
argument-hint: "[PR ref — e.g. owner/repo#123 — or omit for the current branch's PR]"
---

# qute-review — the shared review core (one core, two entry points)

Produce a real review verdict and post it as a native GitHub review, so the **review-gate** CI
passes. Per ADR-0005 this is THE review core: **Matt's review skill is the base** (general-repo
review tooling), and this adds the adversarial framing + the **quant layer** on top — so it serves
both general and quant repos. The same canonical prompt drives jimek's autonomous review runner
(`dispatcher/review.py` loads `review-core.md`), so the two entry points can never drift.

This skill exists because of a concrete failure (2026-06-28): a session ran codex on its OWN PRs
(verdict SHIP); an independent codex run with a security prompt then found 3 BLOCKERS it missed
(path traversal, silent overwrite, unguarded symlink).

## Two non-negotiables

1. **INDEPENDENCE — a separate reviewing AGENT runs it** (ADR-0005: independence is a separate
   agent with fresh context, not an identity trick). If you built the diff, an independent
   session/process must run this — codex exec or a fresh headless run, never an in-process subagent
   of the authoring session. The review-gate CI checks that *a* review object exists; you ensure
   it's *independent*.
2. **ADVERSARIAL FRAMING — hunt failure classes, not "review this diff."** The framing is carried
   by `review-core.md` (sibling of this file) — the canonical prompt. Do not improvise a
   replacement prompt; feed the core.

## Process

1. **Get the diff.** `gh pr diff <#> --repo <owner/repo>` (or `git diff <base>...<branch>` — use the
   PR's actual base; check `gh pr view <#> --json baseRefName`). Write it to a temp file.
2. **Run the cross-model review (codex by default).** Feed the diff + the canonical core prompt
   (`review-core.md` in this skill's directory, prefixed with one line of context: repo + PR + diff
   location):
   ```
   cat <difffile> | codex exec --skip-git-repo-check "$(cat <skill-dir>/review-core.md)" > <scratch>/codex-review.log 2>&1
   ```
   `codex` lives at `~/.local/bin/codex` (and `~/.npm-global/bin/codex`). Use a generous timeout (~320s).

   **STDIN IS MANDATORY, NOT DECORATIVE.** In an agent shell stdin is a pipe, and `codex exec`
   invoked without piped input prints "Reading additional input from stdin..." and **blocks
   forever** — it will sit silent past any timeout while looking alive in `ps` (real incident:
   2×50 min wasted, 2026-07-21). Either pipe the diff (preferred) or close stdin with
   `< /dev/null` if the prompt references a file path instead. **Always redirect output to a
   log file** (as above), never through `| tail` — the user must be able to `tail -f` a
   long-running review, and a tail-pipe buffers everything until exit. Liveness check when in
   doubt: `~/.codex/sessions/<yyyy>/<mm>/` should show a fresh `.jsonl` within a minute of
   starting; a running process with no session file is a stdin-wedged process.
3. **Multi-run for risky code.** If the diff touches auth, file/path IO, user-influenced input, money/
   quant math, secrets, or deletes/overwrites: run codex **2–3×** or with **distinct lenses**
   (correctness · security · data-safety) and UNION the findings — one run misses things (codex is
   non-deterministic).
4. **Fallback if codex is capped/unavailable** (usage limit, egress concern): `Agent(subagent_type:
   "Code Reviewer")` with the SAME core prompt. Flag in the verdict that codex was unavailable
   (so it's Claude-on-Claude this round).
5. **Confidence-gate, then verify before posting.** The core prompt instructs the reviewer to do
   this; you re-verify the surviving findings against the actual code (not just the diff hunk)
   before they go in the verdict.
6. **Synthesize the verdict:** `SHIP` / `SHIP-WITH-NITS` / `BLOCKER` + concrete findings, each with
   `file:line` and a one-line fix. Real, verified, >=80%-confidence findings only.
7. **POST it as a native GitHub review** (this is what satisfies the gate):
   ```
   gh pr review <#> --repo <owner/repo> --comment --body "codex: <SHIP|SHIP-WITH-NITS|BLOCKER> — <findings>"
   ```
   Use `--comment` (agents are not human approvers — never `--approve`). The gate is satisfied by any
   review in state COMMENTED/CHANGES_REQUESTED; the `codex:` prefix is the convention. On `BLOCKER`,
   the builder fixes + you re-run and update the verdict — don't merge until it's SHIP / SHIP-WITH-NITS.
   To post AS qute-review[bot] (App-authored, for `author != reviewer` by construction), hand the
   verdict to `/qute-reviewer` (ships with jimek) instead of `gh pr review`.

## Relationship to Matt's review + jimek

- **Matt's code-review skill** is the planning-spine base for general repos; this core layers the
  adversarial framing + quant lens on top and adds the gate-satisfying GitHub posting.
- **jimek's conductor** is the autonomous entry point: `dispatcher/review.py` loads the same
  `review-core.md` (env `QUTE_REVIEW_CORE` > qute-code-kit checkout > plugin cache > embedded
  fallback) for its codex/claude runners. Change the review policy HERE, once.

## Caveats

- **Egress:** codex sends the diff to OpenAI — fine for Tom's own code; don't send third-party/confidential
  code without thinking (use the Code Reviewer subagent instead).
- **Record on the PR, not just chat:** the verdict MUST land as a `gh pr review` so the Reviews tab carries
  the audit trail and the gate passes — a verdict only in chat leaves the PR showing "no reviews."
- **This is the cross-model layer**, complementary to a separate Claude review session — not either/or.

Background: the review-gate CI workflow (`templates/review-gate.yml`) + the lesson memory
`feedback-codex-cross-model-review`.
