---
name: finding
description: >-
  Record a research finding — the ONLY way results are written under research/. Forces a verdict
  (confirmed/refuted/inconclusive/superseded), writes the dated finding file into the line's
  findings/ dir, and updates the line rollup + root research index in the same action so the
  index cannot drift. Use when a research result lands: "record this finding", "the experiment
  concluded", "write up the result", "verdict is X", or when an analysis produces a conclusion
  worth keeping.
argument-hint: "<line> <verdict> \"<slug or one-line result>\""
---

# /finding

Write a finding into a research line. Atomic: file + line rollup + root index in one action.

## Behavior

1. **Resolve the line.** `research/<line>/` must exist and be registered — if not, run
   `/research-line` first (offer it, don't hand-roll).
2. **Force a verdict.** One of `confirmed | refuted | inconclusive | superseded`. If the
   user hasn't stated one, ask — a finding without a verdict is a session note, and those
   don't belong in the tree.
3. **Write the finding** at `research/<line>/findings/YYYY-MM-DD-<verdict>-<slug>.md`:

   ```yaml
   ---
   line: <line>
   date: YYYY-MM-DD
   verdict: confirmed | refuted | inconclusive | superseded
   question: "One sentence: what was tested"
   evidence: [config.yaml, repro.py, results.parquet]   # paths that reproduce it
   backtest_sharpe: null    # optional gate metrics
   dsr_pvalue: null
   correlation_max: null
   promoted_to: null
   ---
   ```

   Body: result summary, method in two sentences, caveats, links. Short — evidence lives
   in the referenced artifacts, not in prose.
4. **Same action, no exceptions:**
   - Update the line's `findings.md` rollup (one line per finding, newest first).
   - Regenerate the line's row in `research/README.md` (status, latest finding, date).
   - If the verdict supersedes an earlier finding, update that finding's frontmatter
     (`verdict: superseded`) and rename its file to match.
5. **Close the loop:** if the line has a `tracker:` ref, offer to comment/close it via
   `/task`. If verdict is `confirmed` and the result is material, offer `/promote`
   (and `/decision` when it changes methodology).
6. **Concluding a line:** when the user says the line is done, set line README
   `status: concluded|abandoned` and ensure a final finding exists — even
   `inconclusive, abandoned`. Silent abandonment is the failure mode this skill exists
   to prevent.

## Refusals

- Results pasted as loose `research/<line>/*.md` dated files, `SESSION_*.md`, or a second
  `FINDINGS.md` variant → route them through this skill instead.
- A "finding" with an audience and no verdict (deck, client analysis) → that's a
  deliverable; it goes to `reports/`.
