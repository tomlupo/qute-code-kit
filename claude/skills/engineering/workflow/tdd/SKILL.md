---
name: tdd
description: Execute one slice under a test/gate-first loop — pick the right variant (deterministic-TDD, methodology-gate, or exploratory-spike), then RED/gate → audit → GREEN → audit → refactor, landing one PR. Use when implementing a slice — "build this slice with TDD", "red-green-refactor", "implement TOM-NNN test-first". Adapted from mattpocock/skills `tdd`, reconciled with the dm-evo quant-coding / methodology / research-workflow contract. Stage 5 of the engineering workflow (docs/engineering-workflow.md).
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# tdd — three-variant execution loop

## Role
Stage 5 of `docs/engineering-workflow.md`. Land one slice as one PR. **First pick the
variant** by change type — RED-first is NOT universal here.

## Variant (a) — deterministic engine code → TRUE TDD
E/W hysteresis, distress triggers, pillar blend, vectorization.
```
RED      failing hermetic unit test, tiny hand-built cohort, assert the EXACT decision
         (rank order / demotion / NaN-renorm). Pattern: tests/regression/test_l2_rules.py,
         tests/unit/fund_scoring/test_scoring_blend.py
AUDIT-1  tolerance + exact/excluded split correct? does it pin the load-bearing thing
         (rank EXACT, not just score-within-atol)?
GREEN    minimal implementation
AUDIT-2  ruff → quant-coding.md (NO Python loops over time in hot paths — BLOCKER;
         vbt_run for portfolio returns; perf-acknowledged: hatch) → re-run unit + goldens
REFACTOR clean/vectorize; the atol=1e-9 equivalence test is the safety net
```
**Override Matt here:** test **private helpers** and **exact rank order** — in a quant
engine the order IS the observable behavior. Do NOT relax goldens to "public interface only".

## Variant (b) — methodology / config change → GREEN-first, gate-as-test
3p weights, σ-shrink, taxonomy, Score-vs-ETF. The golden is *generated*, not hand-authored.
```
SPIKE    author in research/<line>/ (own pyproject, pinned dm-evo SHA); run the experiment
GATE     the "test" = the BACKTEST: vbt drift-aware harness + walk-forward + bootstrap-CI
         on Δ Sharpe. Finding must SURVIVE the gate, not pass a pre-written assert.
STABILIZE capture expected_metrics golden + report.md frontmatter (status/spec_change) + provenance
PROMOTE  feat/{alias}-{slug} PR → dm-evo /src/; re-pin scoring golden (regen_golden.py, GREEN-first);
         BUMP docs/methodology/{model}.md version + verified IN THE SAME PR (reviewer-enforced, not CI)
```

## Variant (c) — exploratory research → spike-then-stabilize
"Is this signal real?" has no RED. `status: abandoned` is a valid, documented outcome.
```
SPIKE    no test; run repro.py, look (quant-coding.md still bans naive loops in the spike)
VERDICT  status: concluded | abandoned | superseded
STABILIZE if concluded & worth keeping → capture golden + provenance → feeds variant (b)
```

## Audit gates (workflow §8) — Audit-2 in bite order
`ruff` → **quant-coding.md** forbidden-pattern review → **vbt drift-aware harness** →
regression goldens → **methodology-doc version bump** → deflated-Sharpe / walk-forward.

## Before `in_review`
- **Run goldens against `DM_EVO_PROCESSED_ROOT`** — they `pytest.skip` without a data
  clone; green CI ≠ pipeline ran.
- **If your change touches a runbook's `src_paths`, re-verify that runbook + bump its
  `verified:` to today** — else the `verified-drift` check fails (don't `[no-runbook-update]`
  a real behavior change). Same for `docs/methodology/{model}.md` on a methodology change.
- One PR, base `dev` (dm-evo) / `main` (dm-evo-lab), body `Closes TOM-NNN`.
- Edit PR via `gh api -X PATCH` (not `gh pr edit` — broken on dm-evo).

## Merge ≠ done
- **A task going `done` (review-approved) does NOT mean its PR is merged or CI is green.**
  Reviewer-approve gates code, not CI — a PR can be `done` with `verified-drift` red.
  **Do not merge until ALL checks are green** (`gh pr checks <n>`); confirm `mergeStateStatus=CLEAN`.
- Task closes via review-approval, not the merge webhook — reconcile done-vs-merged drift
  with the `paperclip-task` chase sweep.
