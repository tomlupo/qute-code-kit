---
name: qute-review
description: >-
  The shared review core (ADR-0006, supersedes ADR-0005): adversarial, INDEPENDENT code review —
  Matt's review-skill base plus a quant layer (look-ahead, survivorship, data-path, fabrication) plus
  house quirks — that posts the native GitHub review verdict the review-gate CI requires before merge.
  ONE skill, degradable posting: if the qute-review[bot] App verb is installed it posts as the App
  (author != reviewer by construction); otherwise it posts via `gh pr review` tagged `[session: <name>]`,
  where the tag IS the independence marker. Independence is SESSION-based — the review runs in a session
  separate from the author. Codex-first with a Claude fallback; `review-core.md` is the single
  methodology source. Absorbs the retired `qute-reviewer` skill. Use before merging any non-trivial PR,
  or when the review-gate is red. Triggers: /qute-review, review this PR, run the review gate,
  independent review, post a reviewer verdict, post the independent review, green the review gate.
argument-hint: "[PR ref — e.g. owner/repo#123 — or omit for the current branch's PR]"
---

# qute-review — the single independent review skill

Produce a real review verdict and post it as a native GitHub review, so the **review-gate** CI
passes. This is THE review core (ADR-0006): **Matt's review skill is the base** (general-repo review
tooling), this adds the adversarial framing + the **quant layer** + house quirks on top — so it
serves both general and quant repos. `qute-reviewer` is folded in here; there is one review skill.

This skill exists because of a concrete failure (2026-06-28): a session ran codex on its OWN PRs
(verdict SHIP); an independent codex run with a security prompt then found 3 BLOCKERS it missed
(path traversal, silent overwrite, unguarded symlink).

## Two non-negotiables

1. **INDEPENDENCE is session-based — a SEPARATE session from the author runs the review.** If you
   built the diff, an independent session/process must run this — `codex exec` or a fresh headless
   run, never an in-process subagent of the authoring session (a subagent inherits this caller's
   context and can rationalize the same way). The review-gate CI checks that *a* review object
   exists; you ensure it is *independent*.
2. **ADVERSARIAL FRAMING — hunt failure classes, not "review this diff."** The framing is carried
   by `review-core.md` (sibling of this file) — the canonical, version-marked prompt
   (`qute-review-core vN`). Do not improvise a replacement prompt; feed the core.

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
   "Code Reviewer")` with the SAME core prompt — run from an independent session, not the authoring
   one. Flag in the verdict that codex was unavailable (so it's Claude-on-Claude this round).
5. **Confidence-gate, then verify before posting.** The core prompt instructs the reviewer to do
   this; you re-verify the surviving findings against the actual code (not just the diff hunk)
   before they go in the verdict.
6. **Synthesize the verdict:** `SHIP` / `SHIP-WITH-NITS` / `BLOCKER` + concrete findings, each with
   `file:line` and a one-line fix. Real, verified, >=80%-confidence findings only.
7. **POST it as a native GitHub review — degradable (this is what satisfies the gate).** Pick the
   strongest posting path available on this host:

   **(a) qute-review[bot] App verb present** — if `~/bin/qute_reviewer_post.sh` is installed (the
   canonical verb, shipped by platform `agent-kit/bin/` via `install-runtime.sh`), post AS the App
   so `author != reviewer` **by construction** — independence is structural and the gate passes
   automatically:
   ```
   bash ~/bin/qute_reviewer_post.sh <owner/repo> <pr#> [--force]   # POSITIONAL args
   ```
   It runs in **local mode** (`QUTE_REVIEW_MODE=local`): it mints the qute-review App token from the
   gh-apps creds (`QUTE_GH_APPS_DIR`) and posts a native review OBJECT authored by `qute-review[bot]`.
   Idempotent: if a `qute-review[bot]` review already exists at the PR's current head SHA it no-ops;
   a new commit re-reviews; `--force` overrides. It **confirms** a review object exists (not merely a
   comment) and **fails loud** (non-zero, gate stays red) rather than ever posting as your default
   `gh` user. You may hand it the verdict you composed above, or let it generate one in its own
   separate process — either way it stays independent.

   **(b) No App verb** — post via `gh pr review`, tagged `[session: <name>]`:
   ```
   gh pr review <#> --repo <owner/repo> --comment \
     --body "[session: <name>] codex: <SHIP|SHIP-WITH-NITS|BLOCKER> — <findings>"
   ```
   Derive `<name>` from the session name if set, else the cwd basename. The **`[session: …]` tag IS
   the independence marker**: the PR author shows `[agent: …]`/a human, the reviewer shows
   `[session: …]`, so `author != reviewer` is visible on the PR with no App at all. Use `--comment`
   (agents are not human approvers — never `--approve`); the gate is satisfied by any review in state
   COMMENTED/CHANGES_REQUESTED.

   On `BLOCKER`, the builder fixes + you re-run and update the verdict — don't merge until it's
   SHIP / SHIP-WITH-NITS.

## Relationship to Matt's review + the platform reviewer

- **Matt's code-review skill** is the planning-spine base for general repos; this core layers the
  adversarial framing + quant lens on top and adds the gate-satisfying GitHub posting.
- **The platform reviewer** is the autonomous entry point: `agent-kit/bin/qute_reviewer_post.sh`
  (in qute-platform, installed to `~/bin/`) loads this same `review-core.md` for its codex/claude
  runners. It resolves the core via `QUTE_REVIEW_CORE` (**env > qute-code-kit checkout > embedded
  fallback**); if it keeps an embedded fallback, a CI drift-check on the `qute-review-core vN`
  version marker keeps the two copies honest. Change the review policy HERE, once.

## Caveats

- **Egress:** codex sends the diff to OpenAI — fine for Tom's own code; don't send third-party/confidential
  code without thinking (use the Code Reviewer subagent instead).
- **Record on the PR, not just chat:** the verdict MUST land as a review object so the Reviews tab
  carries the audit trail and the gate passes — a verdict only in chat leaves the PR showing "no
  reviews."
- **This is the cross-model layer**, complementary to a separate Claude review session — not either/or.

Background: the review-gate CI workflow (`templates/review-gate.yml`) + the lesson memory
`feedback-codex-cross-model-review`.
