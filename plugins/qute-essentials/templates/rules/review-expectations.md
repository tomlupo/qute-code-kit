<!-- qute-rule: review-expectations v1 — stamped by /setup-qute-repo; regenerate per-file, never hand-merge -->
# Review expectations

- **Non-trivial changes get an independent review before merge.** Independent
  means a SEPARATE reviewing agent (or human) with fresh context and no stake
  in the code — not the author re-reading their own diff, and not a subagent
  of the authoring session. Posting under a different identity is only the
  gate's checkable proxy; the separate reviewer is the substance (ADR-0005).
- The verdict must land as a native GitHub **review object** on the PR
  (COMMENTED / APPROVED / CHANGES_REQUESTED) — a chat verdict or plain comment
  satisfies nothing.
- Trivial mechanical changes (typos, comment fixes, config value bumps) may
  merge on green CI without a review.
- On a BLOCKER verdict: fix, re-review, and only then merge.
