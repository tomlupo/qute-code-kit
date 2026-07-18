---
name: promote
description: >-
  Promote a confirmed research finding into production: ADR + production PR (or wiki concept /
  framework plugin), then mark the finding promoted. Use when a confirmed finding should change
  production methodology — "promote this", "ship the finding", "move this into dm-evo/quantbox",
  "graduate this strategy". Follows the lab→prod lifecycle: methodology spec bump + pinned-SHA
  update belong in the same promotion.
argument-hint: "<line> [finding-file] [--target <repo|wiki|plugin>]"
---

# /promote

Graduate a finding from `research/<line>/findings/` into the production surface.

## Behavior

1. **Resolve the finding.** Latest `confirmed` finding in the line unless one is named.
   Refuse non-confirmed verdicts — refuted/inconclusive results are recorded, not promoted
   (superseded may be promoted only if its successor is the thing being shipped).
2. **Check the evidence contract** before touching production: the finding's `evidence:`
   paths exist, the line's repro entry point runs (or `REPRODUCIBILITY.md` marks it
   accepted), gate metrics present where the repo requires them (deflated Sharpe,
   correlation caps). A finding that can't be reproduced doesn't get promoted — say so and
   stop.
3. **Determine the target** from repo convention (`docs/agents/research-workflow.md`,
   CLAUDE.md lifecycle sections) or `--target`:
   - **prod repo** (e.g. dm-evo, quantbox): branch + PR that lands the spec/code change,
     bumps `docs/methodology/<model>.md` version + verified date in the same PR, and
     updates the research line's engine pin after merge
   - **wiki**: create/update the concept page, citing the finding as source
   - **plugin**: extract into the framework's plugin surface per its contract
4. **Record the decision.** Material methodology change → `/decision` (ADR in `docs/adr/`
   of the *target* repo). Link ADR ↔ finding both ways.
5. **Mark promoted.** Fill the finding's `promoted_to:` (PR URL / ADR / wiki slug); update
   line rollup + root index (same atomic rule as `/finding`).
6. **Track it.** Create/update the tracker item for the production work per
   `docs/agents/issue-tracker.md` — promotion opens engineering work; the tracker owns it
   from here (a Jimek workflow may pick it up from Linear).

## Refusals

- Promotion that copies lab code into prod wholesale — promotion lands the *change*,
  referenced to lab evidence, not the lab tree.
- Skipping the ADR on a methodology change ("just merge it") — record first, then ship.
