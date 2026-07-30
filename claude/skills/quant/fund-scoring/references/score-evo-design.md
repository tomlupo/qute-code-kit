---
title: score_evo — benchmark-anchored calibrated fund score within new L2
status: design approved (2026-06-02)
research_line: research/selection-l2-taxonomy
author: tomlupo
date: 2026-06-02
dm_evo_pin: 16c158091a85ff2f6d6efb3ef855ef70bcaade3e
---

# score_evo — design

## Build update (2026-06-02, supersedes some design choices)

- **D10 — benchmarks are CURRENCY-AGNOSTIC.** A PLN fund (hedged or unhedged) is
  compared directly to its native-currency ETF benchmark; NO USDPLN/EURPLN
  conversion. This supersedes the FX-conversion edge cases below (unhedged-USD
  handling, USDPLN gap) — they no longer apply. A USDPLN snapshot was fetched
  (`data/usdpln_nbp.parquet`) but is unused under this rule.
- **D11 — anchor on a FRESHLY computed cross-section**, not the stale
  production snapshot. `prod_scoring.compute_fresh_scores` runs the real
  `score_funds` pipeline at the latest properly-scoreable W-FRI (**2026-05-22**;
  4-pillar). 2026-05-29 isn't full-universe scoreable (daily NAV feed ends
  2026-05-20). Needs the dm-evo editable install (live-dev hatch) + `src` on path.
- **Benchmark ML pillar = ML-NEUTRAL (group-median).** The 45-feature inference
  was deferred: the model's rank/label features (`rank_pct`, `rank_accel`,
  `q1_freq_12m`, `category_enc`) are ill-posed for a non-fund benchmark. Impact
  is bounded ≤3.0 evo pts (median 2.4), uniform per group. Full inference remains
  a Phase-2 option if that residual matters.
- **Asia/China fix is breadth, not FX:** FXI → broad `EQ_EM`.

## Goal

Add a new per-fund score column, **`score_evo`**: the existing raw 4-pillar
composite, **re-centered within each new L2 group** so the group's **benchmark
composite = 50**, with dispersion standardized (**1 within-group std = 15
pts**) and a σ-floor. It coexists with the unchanged raw `score` and the
existing p75-anchored `calibrated` score (three columns, like score → calibrated
→ evo). PLN-only. **v1 = latest scoring date only** (2026-04-24); the full
weekly series from 2025-12-31 is a Phase-2 extension.

This is the "fund scoring" half of the `selection-l2-taxonomy` line. The
"grouping" half (the new L2 taxonomy) is finalized in `taxonomy_final_pln.yaml`
+ `output/pln_reclassification.csv` and is an input here, not in scope to change.

## The one formula

```
score_evo(i) = clip( 50 + (score_i − score_B,g) / max(σ_g, σ_floor) × 15 , 0, 100 )
```

- `score_i` — production composite from `scores.parquet`, **unchanged** (old-L2
  relative metrics, L1 z-score — i.e. "scoring stays on L1, nothing changed").
- `score_B,g` — group `g`'s **benchmark composite** (the phantom fund). The only
  genuinely new quantity; everything else is mechanical.
- `σ_g` — std of `score_i` across funds in new-L2 group `g` at the scoring date.
- `σ_floor` — minimum dispersion (default **5.0 pts**, tunable) so ultra-
  homogeneous groups (e.g. Gold, empirical σ ≈ 1.3 pts) don't amplify noise into
  large evo swings.
- Multiplier **×15**: practical realized range ≈ 10–90; 0/100 are safety-rails
  reached only by ~3.3σ outliers.

## Decisions log (settled in brainstorming, 2026-06-02)

| # | Decision | Rationale |
|---|---|---|
| D1 | Output column = `score_evo`; coexists with raw `score` + existing `calibrated` | Single taxonomy, single scoring path (taxonomy `scoring_uniformity`) |
| D2 | New L2 from `output/pln_reclassification.csv` (`final_group`) | Advisor-confirmed grouping; this line's deliverable |
| D3 | Raw composite `score_i` left **unchanged**; score_evo is a post-hoc re-centering | User: "scoring is on L1 so nothing has changed" |
| D4 | Anchor = **full phantom-fund composite** incl ML pillar (inference-only) | Faithful "fund-vs-benchmark on identical basis"; matches `segment_score_spec` |
| D5 | Architecture = **Option 1 (project onto frozen cohort)**, not inject-and-rerun | Funds stay byte-identical to `scores.parquet`; no cohort contamination; avoids old/new-L2 coupling |
| D6 | Benchmark source = **long-history TAA-registry series** (v1) | All start 2002–2009 → satisfy ≤2022-12-31; reproducible now; inPZU/UCITS deferred |
| D7 | Dispersion = **1 std = 15 pts + σ-floor**, benchmark=50 | Uses ~10–90 of the scale while staying standardized + cross-group comparable |
| D8 | Scope = **latest date only** for v1 | User: "focus on last date for now" |
| D9 | ML pillar: **inference-only**, full 45-feature row; ML-neutral fallback as documented safety net | Models unchanged; benchmark-in-training is a separate future experiment |

## Components (isolated units)

### 1. `bench_resolution`
A table mapping each new-L2 group → one long-history registry series in
`signals_data.parquet`, plus `kind` (`level` | `cash_rate`) and an `fx_note`.
Derived from `taxonomy_final_pln.yaml` benchmark assignments, using the
**backfill** series (long history) as the v1 operative anchor rather than the
inPZU/UCITS primaries. Asserts every chosen series has first-date ≤ 2022-12-31.
- *What it does:* group → benchmark series id + handling.
- *Depends on:* taxonomy yaml, signals_data.parquet.

### 2. `cohort_stats`
Recompute the 12 tactical indicators + the 45 ML features for the PLN universe
via **imported dm-evo `src.fund_scoring.features` and `src.fund_scoring.ml`**
(no math re-implementation), over a window ending at the scoring date with ≥36m
of trailing history. Derive, per (L1 category, indicator) at the scoring date:
winsor bounds [5th, 95th pct] + μ/σ (mirroring `zscore_within_category`), and
per (L1) the ML raw min/max used by `_minmax_within_category`.
- *What it does:* the frozen funds-only cohort distribution the benchmark
  projects onto.
- *Depends on:* fund_prices (PLN), scores.parquet (L1 map, currency),
  ml_dataset.parquet (feature reference), features.py / ml.dataset.
- *Gated by Faithfulness Gates A + B (see Testing).*

### 3. `bench_composite`
For each group at the scoring date:
1. Compute the benchmark's 12 indicators from its series (relative metrics
   `spread_ratio`/`info_ratio`/`hit_rate` vs its **new-L2 group** fund median;
   absolute metrics standalone). `cash_rate` benchmarks → TR conversion.
2. Build the benchmark's 45-feature ML row matching `ml_dataset` exactly
   (incl. cross-sectional `rank_pct`/`rank_accel`/`q1_freq_12m`/`log_peer_count`
   computed by projecting the benchmark into the fund ranking, and category
   encodings `category_enc`/`category_feat`/`layer2_feat` set to the group's
   L1/L2).
3. **Project** indicators onto the funds-only cohort stats from (2): winsorize
   to cohort bounds, standardize by cohort μ/σ → z → scale to [0,100] → tactical
   pillars. Run `upside_clf`/`downside_clf` on the feature row →
   `raw_upside`/`raw_guardrail` → min-max-project onto funds' L1 min/max → blend
   `pillar_ml = 0.25·upside + 0.75·guardrail`.
4. No-loss guard on the benchmark's sortino (near-cash groups: no downside →
   cap at the group's finite max).
5. Blend with the weights matching the anchor's fund composite → `score_B`.
   **Anchor-date reality (verified 2026-06-02):** the production weekly score at
   2026-04-24 carries NO ML pillar (`pillar_ml` all NaN; composite == 3-pillar
   `.50·mom+.25·cons+.25·qual` to 1e-4), so v1 uses 3-pillar weights and the
   45-feature benchmark ML build is unnecessary here. Switch to 4-pillar
   (.50/.20/.20/.10) + the benchmark's ML pillar only when scoring an
   ML-carrying anchor (Phase 2).
- *Depends on:* (1), (2), the 4 model joblibs, scoring.yaml weights.

### 4. `recenter`
Apply the formula within each new-L2 group → `score_evo`. Emit `score_i`,
`score_B`, `σ_g`, `score_evo`, group, role, and a confidence flag.
- *Depends on:* (3), scores.parquet (score_i), reclassification (groups).

### 5. `validate`
The research output: per-group median `score_evo` (benchmark-vs-median test),
% of funds beating the benchmark (score_evo > 50), and corr/divergence vs the
existing `calibrated` (non-redundancy). Writes the findings section.

## Data flow

```
scores.parquet (funds: score_i, L1, currency)
fund_prices.parquet (PLN daily)                ─┐
pln_reclassification.csv (new L2)               ├─► cohort_stats ─► bench_composite ─► recenter ─► output/score_evo.parquet
signals_data.parquet (benchmark series)         │        ▲                 ▲                          │
ml_dataset.parquet + 4 joblibs ─────────────────┘   (gates A,B)       bench_resolution                └─► validate ─► findings
```

## Edge cases / flags

- **Thin group** (<3 funds w/ history): σ_g unreliable → emit but flag
  `low_confidence`; σ-floor applies.
- **"Other" / quarantine groups** (QRS07 leverage; KAH33/34; low-conf pools;
  single-fund groups like Global Short Duration): no benchmark anchor →
  `score_evo = NaN`, flag `no_anchor`.
- **CASH/WIBOR benchmark** (FI_PL_SHORT): rate→TR conversion + no-loss guard;
  expected to read slightly >50 (duration premium over pure cash).
- **Foreign-equity benchmarks** (EQ_GL/US/EUR, COM): native-ccy per the
  taxonomy's "equity FX-carry negligible" rule.
- **Unhedged foreign-FI**: flagged as a known approximation — USDPLN/JPYPLN/
  GBPPLN only start 2026-04-30 in the registry, so historical PLN-conversion is
  unavailable; the chosen FI_GL backfill (PLN-hedged-to-PLN) is used as-is.
- Benchmark series gaps → ffill.
- **Relative-metric reference mismatch (known, minor):** funds' `score_i`
  computed its relative metrics (`spread_ratio`/`info_ratio`/`hit_rate`) vs the
  *old* benchmark_category, while the benchmark's relative metrics are computed
  vs its *new*-L2 group median, then both project onto the funds' (old-L2-based)
  z-distribution. Small effect — relative metrics sit only in the 0.20
  consistency pillar + part of momentum, and old/new L2 overlap heavily.
  Eliminated only by a full re-score on new L2, which D3 explicitly declines.

## Testing (verification-first)

1. **Faithfulness Gate A (scoring):** recomputed fund composite reproduces
   `scores.parquet.score` within MAE < 0.5 pts on the scoring date. Proves the
   cohort-stats extraction matches production.
2. **Faithfulness Gate B (ML features):** recomputed fund feature rows match
   `ml_dataset.parquet` (the 45 cols) within tolerance, and re-running the
   classifiers on funds reproduces the production `pillar_ml`. Proves the
   benchmark feature-builder is correct *before* trusting the benchmark's row.
3. **Anchor sanity:** a benchmark scored as a fund and re-centered lands at
   `score_evo = 50` (± float tolerance).
4. **Research validation:** per-group median `score_evo`, % beating benchmark,
   and `corr(score_evo, calibrated)` per group (non-redundancy).

If Gate B proves the 45-feature replication too fragile to land in v1 (e.g.
`category_enc` label-encoder version skew — pickles are sklearn 1.8 vs installed
1.9), fall back to the **ML-neutral anchor**: set the benchmark's `pillar_ml` to
the cohort-mean ML pillar (error bounded by 0.10·|true−mean|, ≤±5 pts). This is
the documented safety net, not the plan.

## Scope / non-goals (v1)

- PLN only.
- Latest scoring date only (weekly series from 2025-12-31 = Phase 2).
- Long-history registry benchmarks only (inPZU/UCITS sourcing = Phase 2).
- ML inference-only; models unchanged.
- No dm-evo promotion PR (this is research evidence + a proposed score).
- EUR/USD universes deferred.

## Phase 2+ (future)

- Full weekly series 2025-12-31 → latest (benchmarks already satisfy
  ≤2022-12-31 by D6, so the extension is free).
- Source inPZU + UCITS primaries; backfill-splice vs the registry series.
- inPZU/UCITS as cross-check of the registry-anchored evo scores.
- EUR/USD universes after PLN locks.
- Promotion: dm-evo PR against `config/reference/fund_mapping.csv` +
  `config/fund-selection/score_calibration.yaml` (or a new `score_evo` config) +
  `docs/methodology/{taxonomy,fund_selection}.md`, version + verified-date bump.

## Provenance

- dm-evo pinned at `16c158091a85ff2f6d6efb3ef855ef70bcaade3e` (matches
  `../selection/`).
- Read-side inputs from sibling dm-evo checkout: `data/processed/{fund_prices,
  fund_selection/scores.parquet, fund_selection/ml_dataset.parquet,
  tactical-signals/signals_data.parquet}`, `models/fund_scoring/*.joblib`,
  `config/fund-selection/scoring.yaml`, `config/reference/fund_mapping.csv`.
- Empirical reference: latest scoring date 2026-04-24; 560 PLN funds mapped to
  new L2; within-group σ median ≈ 11 pts (range 1.3–18.9).
- Reproducibility class: same as `../selection/` — reads sibling dm-evo data
  not packaged with the SHA pin; `output/` derived (gitignored).
