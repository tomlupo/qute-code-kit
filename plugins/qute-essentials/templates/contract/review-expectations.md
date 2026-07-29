<!-- prose source: review-expectations v1 — /setup-qute-repo step 5 writes this as a section of the repo's CLAUDE.md. It is prose, not a file to copy: nothing stamps it into .claude/rules (ADR-0005 §5 as amended 2026-07-28). -->
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
