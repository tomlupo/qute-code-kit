---
name: fund-scoring
description: Use when building or reproducing a benchmark-anchored "is this fund worth holding vs its benchmark" score (group benchmark = 50) for a fund universe — re-centering a within-peer composite per peer-group so the group's investable ETF/index benchmark anchors at 50, scoring an index/ETF benchmark as a phantom fund on the same footing, or faithfully reproducing a production fund-composite engine from a research workspace. Companion to fund-classification (which builds the peer groups). Universe-agnostic; a PLN/dm-evo reference is bundled.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Fund scoring — benchmark-anchored (benchmark=50) calibrated score

## Overview

Turn a within-peer **composite** into a **benchmark-relative** score: re-center each
peer group so its **investable benchmark = 50** (1 within-group std = `MULT` pts).
"55" beats the index by ~⅓ std; "<50" means the typical fund **lags its benchmark**.
The raw composite is **unchanged** — the relative score is a separate column.
**Fix the published names ONCE and bake them into every artifact**: the raw composite
and the benchmark-relative score need distinct, stable names (dm-evo 2026-06-11:
**"score_evo" = the RAW composite**, **"Score vs ETF" = the relative score**; a
midstream rename forced relabeling every surface — UI, exports, commentary).
Companion to **fund-classification** (which makes the
peer groups return-coherent); this skill scores funds *within* those groups.
**Universe-agnostic**; a PLN/dm-evo reference implementation is bundled in
`scripts/` + `references/` — read it as the worked example, adapt the loader seam.

## Inputs

- **A within-peer composite per fund** — computed **FRESH** (not a stale snapshot).
  For dm-evo this is the production 4-pillar score; **reproduce it via the engine,
  don't reimplement.**
- **A grouping** — each fund's peer group (the fund-classification output).
- **An investable benchmark per group** — one ETF/index series (a money-market
  rate for cash). **Reuse an existing benchmark registry before sourcing your own.**

## The one formula

`score_evo(i) = clip( 50 + (score_i − score_B,g) / max(σ_g, σ_floor) × MULT , 0, 100 )`

- `score_i` = fund composite, **unchanged**. `score_B,g` = the group benchmark's
  composite (scored as a phantom fund). `σ_g` = within-group composite dispersion
  (**shrunk** — step 4). `MULT` = points per std (≈15; sets how much of 0–100 is used).

## Method

1. **Anchor on a FRESH composite over the right cohort.** Use a composite computed
   at the latest *properly-scoreable* date (freshness-gated), not a stale snapshot,
   and ensure it was z-scored over the cohort its definition intends (e.g.
   all-currency for currency-mixed categories — pre-filtering to one currency
   silently distorts it). *If you must reproduce a production engine* (as with
   dm-evo), re-run the engine rather than reimplement, and add **Gate A**:
   reproduce the engine's z-scores from its raw indicators (max-abs-diff < 0.01)
   to prove your cohort stats match production.
2. **Score the benchmark as a phantom fund — by PROJECTION, not injection.** Compute
   the benchmark's raw indicators (relative metrics vs its own group's funds), then
   **project** them onto the **funds-only** cohort z-stats (winsor bounds + μ/σ).
   Do NOT add the benchmark into the cohort — it contaminates μ/σ (~1/n, worse for
   thin groups) and shifts every fund. Funds stay byte-identical.
3. **Neutralize learned/peer-relative pillars for the benchmark + guard cash.**
   Rank / forward-label / peer-percentile ML features are **ill-posed for a non-fund
   index** (an index has no peer-rank or forward-quartile) → set the benchmark's ML
   pillar to the group-median (neutral) and **bound the residual** (0.10 weight →
   ≤~3 pts, uniform per group). No-loss cash series blow up sortino/profit_factor
   (÷0 downside) → cap at group max; info_ratio is safe.
4. **Re-center per group with σ-shrinkage.** `σ_g = (n·σ_group + K·σ_parent)/(n+K)`
   (K ≈ min-peers, e.g. 8) so thin groups borrow the parent-cohort dispersion instead
   of amplifying noise; floor σ. Then apply the formula.
5. **Validate.** Per group report median evo + %beat. **Benchmark ≠ median** — if the
   benchmark's composite ≈ the group median, the score just re-centers on the median
   and hides whether the whole group lags its index. Flag thin / no-benchmark groups
   (`low_confidence` / `no_anchor`) — surface them, don't hide.

## Traps (universe-independent — get these wrong and the score lies)

| Trap | Rule |
|---|---|
| **Stale anchor** | Re-score FRESH at the latest freshness-gated date; a stale composite snapshot misdates every fund. |
| **Inject vs project** | Adding the benchmark to the cohort contaminates μ/σ and changes fund scores. PROJECT onto frozen funds-only stats; keep funds unchanged. |
| **Wrong cohort** | Reproduce the engine's exact z-grouping (incl. cross-currency for mixed categories). Gate A catches drift. |
| **ML for a benchmark** | Rank / label / peer-relative features don't exist for an index → neutral ML pillar, bound the residual. Don't fabricate a rank. |
| **No-loss cash** | sortino / profit_factor → ∞ on a no-loss series; guard (cap at group max) or score excess return. info_ratio is fine. |
| **Thin-group σ** | A tiny within-group σ turns noise into big swings; shrink toward the parent-cohort σ + floor. |
| **Benchmark = median** | Validate the benchmark sits away from the peer median, else the anchor is uninformative (it's just the median in disguise). |
| **Currency / FX** | Compare a fund to its **native-NAV** benchmark directly; do NOT FX-convert ETF benchmarks (verified decision — scoring is currency-agnostic). Carry matters for bonds, negligible for equity. |
| **Untested anchor** | Anchor fit is **empirical** — ρ-gate every anchor against the actual members, including "obviously better" baskets: a diversified metals basket (GLTR) fit the silver funds *worse* than plain SLV; the fund's own declared benchmark can also mislead (a WIGtech fund fit the mid-cap index, not QQQ). Test, don't assume. |
| **Cross-cohort moves** | A fund moved to a different scoring cohort must have its relative metrics **re-z-scored in the destination cohort** — carrying pillars z-scored vs the old cohort puts apples-vs-oranges percentiles inside one group ranking. |
| **Unscoreable ≠ invisible** | Groups with no honest common anchor stay **visible-unrated** (flagged), never hidden. Cash-plus mandates (absolute return) CAN be scored — anchor to the investable cash rate; that's their honest passive alternative. |

## dm-evo reference (bundled) + adapting

- **Import bridge (the painful seam).** dm-evo is src-layout: pipelines import
  `src.X`, src modules import top-level `shared.X` / `fund_scoring.X`. To run its
  engine from the lab: `uv pip install -e ../dm-evo` (live-dev hatch) **and** put
  **both** `<dm-evo>` and `<dm-evo>/src` on `sys.path` — else top-level `shared`
  resolves to a stale site-packages copy whose `PROJECT_ROOT` points into the venv
  and every config/data path breaks. **Verify which checkout resolves** (a
  leftover editable install from another worktree is silent).
- **Fresh composite seam:** `scripts/prod_scoring.py::compute_fresh_scores(as_of)`
  mirrors `compute_scores.py` (load_scoring_universe → load_prices →
  filter_freshness → compute_ml_pillars → score_funds) and returns the detail
  (raw + z + pillars) in-memory — anchor on this, not the stale `scores.parquet`.
- **Data freshness:** read `processed`, not `published` (stale); re-run the price
  combine if the parquet lags its sources; the daily NAV feed caps the latest
  full-universe date — don't anchor past it (the freshness gate drops stale funds).
- **Benchmarks:** reuse dm-evo's `config/tactical-signals/data_sources.yaml` +
  `signals_data.parquet` registry first; snapshot a missing series via a public API
  (`scripts/fetch_gdx.py` = Yahoo chart via urllib; NBP for FX) into `data/`.
- `scripts/score_evo.py` = core method (`cohort_stats` / `bench_indicators` /
  `project_pillars` / the formula + Gate A). `scripts/score_evo_v2.py` = production
  refinements (σ-shrinkage toward the scoring-category σ, all-currency cohort for
  currency-mixed cats / currency-split routing for carry-segmented FI, snapshot
  anchors). `references/score-evo-design.md` = the decision log (D1–D11 + ML-neutral
  rationale).

**To adapt to a new universe:** keep steps 1–5; change only the data-loading seam
(your fresh composite + grouping + investable benchmarks) and skip the dm-evo
import bridge.
