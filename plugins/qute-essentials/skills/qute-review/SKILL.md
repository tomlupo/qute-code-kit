---
name: qute-review
description: >-
  Adversarial, INDEPENDENT code review that posts a native GitHub review verdict — the verdict the
  review-gate CI requires before merge. Runs a cross-model (codex) review with a security-first,
  failure-class-driven prompt (not generic "review this"), multi-run for risky code, with a Code
  Reviewer subagent fallback. Use before merging any non-trivial PR, or when the review-gate is red
  for a missing reviewer verdict. Triggers: /qute-review, review this PR, run the review gate,
  independent review, post a reviewer verdict.
argument-hint: "[PR ref — e.g. owner/repo#123 — or omit for the current branch's PR]"
---

# qute-review — independent, adversarial review that satisfies the gate

Produce a real review verdict and post it as a native GitHub review, so the **review-gate** CI
(`require-reviewer-verdict`) passes. This skill exists because of a concrete failure (2026-06-28): a
session ran codex on its OWN PRs (verdict SHIP); an independent codex run with a security prompt then
found 3 BLOCKERS it missed (path traversal, silent overwrite, unguarded symlink). Two things fix that —
this skill carries both.

## Two non-negotiables

1. **INDEPENDENCE — a different party than the builder runs it.** A skill is just a prompt; if the
   agent that WROTE the code runs it on its own work, it's a rubber-stamp (it frames the review and
   decides how to act on findings). If you built the diff, an INDEPENDENT session/agent must run this.
   The review-gate CI enforces that *a* review exists; you enforce that it's *independent*.
2. **ADVERSARIAL FRAMING — hunt failure classes, not "review this diff."** The framing was the biggest
   factor in catching the miss. Drive the reviewer with the checklist below, as a skeptic that assumes
   the code is wrong until proven otherwise.

## Process

1. **Get the diff.** `gh pr diff <#> --repo <owner/repo>` (or `git diff <base>...<branch>` — use the
   PR's actual base; check `gh pr view <#> --json baseRefName`). Write it to a temp file.
2. **Run the cross-model review (codex by default).** Feed the diff + the adversarial prompt:
   ```
   <DIFF> | codex exec --skip-git-repo-check "<adversarial prompt — see template>"
   ```
   `codex` lives at `~/.local/bin/codex` (and `~/.npm-global/bin/codex`). Use a generous timeout (~320s).
3. **Multi-run for risky code.** If the diff touches auth, file/path IO, user-influenced input, money/
   quant math, secrets, or deletes/overwrites: run codex **2–3×** or with **distinct lenses**
   (correctness · security · data-safety) and UNION the findings — one run misses things (codex is
   non-deterministic).
4. **Fallback if codex is capped/unavailable** (usage limit, egress concern): `Agent(subagent_type:
   "Code Reviewer")` with the SAME adversarial prompt. Flag in the verdict that codex was unavailable
   (so it's Claude-on-Claude this round).
5. **Confidence-gate, then verify before posting.** For each candidate finding, assign a confidence
   score (0–100%) and drop anything below **80%** — pattern-matched hunches are noise, not findings.
   Before it goes in the verdict, **verify each surviving finding against the actual code**: re-read
   the relevant lines/context (not just the diff hunk in isolation) and confirm the issue really
   holds — discard anything that doesn't survive that re-read (a helper defined two lines up, a guard
   already applied earlier in the function, etc.).
6. **Synthesize the verdict:** `SHIP` / `SHIP-WITH-NITS` / `BLOCKER` + concrete findings, each with
   `file:line` and a one-line fix. Real, verified, >=80%-confidence findings only; drop speculative noise.
7. **POST it as a native GitHub review** (this is what satisfies the gate):
   ```
   gh pr review <#> --repo <owner/repo> --comment --body "codex: <SHIP|SHIP-WITH-NITS|BLOCKER> — <findings>"
   ```
   Use `--comment` (agents are not human approvers — never `--approve`). The gate is satisfied by any
   review in state COMMENTED/CHANGES_REQUESTED; the `codex:` prefix is the convention. On `BLOCKER`,
   the builder fixes + you re-run and update the verdict — don't merge until it's SHIP / SHIP-WITH-NITS.

## The adversarial prompt template

> Independent review — you are a SEPARATE reviewer from whoever wrote this; assume nothing was verified.
> Diff at <path>. Context: <one line>. Be a skeptic: assume it's wrong until proven otherwise. Hunt these
> classes, report only REAL findings with file:line + a one-line fix:
> - **Correctness** — logic, edge cases, off-by-one, wrong/empty defaults, error paths.
> - **Path/IO safety** — path traversal (user-influenced slugs/wikilinks joined into paths; `..`/separators
>   escaping a base dir), unguarded overwrite/delete of existing files, unhandled symlinks, resolved-path
>   not asserted under the expected base.
> - **AuthZ/AuthN** — missing/weak checks, allowlist bypass, fail-open.
> - **Injection** — SQL/shell/template/prompt injection from untrusted input.
> - **Secrets / data egress** — logged/committed secrets, data sent to a third party.
> - **Silent failure / data loss** — swallowed errors (`|| true`, bare except), partial writes, stale-but-
>   finite outputs that pass a presence check.
> - **Concurrency / resources** — races, leaks, unbounded growth.
> - **(quant only)** — look-ahead / same-bar leakage, survivorship, wrong data path vs prod, fabricated values.
> Also explicitly sweep these 6 lenses before you finish — they catch classes the list above under-covers:
> - **Comment-analysis** — do comments/docstrings actually match what the code does (stale, aspirational,
>   or contradicted by the implementation)?
> - **Test-analysis** — do the tests assert the RIGHT thing, and do they actually cover this change (not
>   just touch the function)?
> - **Silent-failure** — swallowed exceptions, unchecked return values, no-op fallbacks that look like
>   success.
> - **Type-design** — do the types/shapes allow an invalid state to be represented that shouldn't be?
> - **Correctness** — logic bugs, edge cases, off-by-one (restated as its own explicit pass, not just
>   folded into the first bullet above).
> - **Simplification** — unneeded complexity, dead code, an existing helper/pattern that should have been
>   reused instead of re-implemented.
> For every candidate finding: assign a confidence 0–100%, drop anything under 80%, and re-verify the
> survivors against the actual code (not just the diff hunk) before including them.
> Output: a verdict line SHIP / SHIP-WITH-NITS / BLOCKER, then concise bullets.

## Caveats

- **Egress:** codex sends the diff to OpenAI — fine for Tom's own code; don't send third-party/confidential
  code without thinking (use the Code Reviewer subagent instead).
- **Record on the PR, not just chat:** the verdict MUST land as a `gh pr review` so the Reviews tab carries
  the audit trail and the gate passes — a verdict only in chat leaves the PR showing "no reviews."
- **This is the cross-model layer**, complementary to a separate Claude review session — not either/or.

Background: the review-gate CI workflow (`review-gate.yml`) + the lesson memory `feedback-codex-cross-model-review`.
