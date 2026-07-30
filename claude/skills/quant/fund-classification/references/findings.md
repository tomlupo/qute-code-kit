# selection-l2-taxonomy — findings

**Status**: research, in-progress (taxonomy finalized 2026-06-02; segment-score + per-fund mapping pending).

## Hypothesis

The descriptive fund→L2 (selection_group) map is not return-coherent. A
correlation-based, stability-gated grouping — plus a benchmark-anchored segment
score (benchmark=50) — yields more homogeneous, communicable groups and a
fairer cross-group score, without breaking deliberate allocation distinctions.

## Result (so far)

- **L2 groups are materially non-homogeneous, but concentrated:** ~19% strict
  misfits (avg-own-ρ < 0.5), clustered in catch-all buckets ("Other Sectors"
  ρ 0.38, "EM Other Equity" ρ 0.39) and FI sub-type/currency splits
  (FI_GL/FI_CREDIT ARI≈0 vs descriptive labels).
- **"PL Universal Bonds" is a marketing shelf, not a group:** 10/15 funds with
  history track PL govvies at ρ 0.67–0.89 → dissolved into the FI_PL govt core.
- **The FX/hedging axis drives real splits:** the US/USD-govt trio split from
  hedged Global Core purely on FX (unhedged USD vs PLN-hedged) — confirming
  benchmarks must be hedged-vs-unhedged aware.
- **All 10 allocation L1s finalized** (advisor-confirmed) in
  `taxonomy_final_pln.yaml`: ≤1 core + N satellites + 1 Other, with a separate
  `standalone_eligible` flag and sector/thematic tags.
- **Segment score (benchmark=50) is informative, not redundant** (`segment_score.py`,
  prototype with a transparent composite proxy). Anchoring on the benchmark vs
  today's p50-median anchor moves the distribution materially: median PL-govt fund
  = **43** vs TBSP (21% beat), median global-DM fund = **37.5** vs MSCI World (only
  4% beat), median PL-govt-short = **52.8** vs CASH (duration premium). Caveats the
  run surfaced: near-cash synth benchmark breaks Sortino (score on excess-return);
  USD equity benchmark needs PLN/hedge treatment (conclusion robust to it).

## Method

See README. Stability gate = 3 trailing 156w windows (2026-05, 2025-05,
2024-05); a signal must persist ≥2/3. PLN-only (FX-free). Advisor overrides
recorded (e.g. Gold vs Precious Metals kept distinct despite ρ 0.67 merge).

## Explained gaps / caveats

- **Single-broker FX nuance:** within PLN, hedged vs unhedged share classes
  behave differently; benchmark comparison must match (hedged→local+carry,
  unhedged→PLN-converted). Carry matters for FI, negligible for equity.
- **Benchmark series:** PL (TBSP/CASH/WIG/MWIG40) + global proxies are in the
  TAA registry; UCITS equity benchmarks + a few gaps (Miners, MIX blends) need
  sourcing/snapshot from analizy.pl/yfinance.
- **Reads sibling dm-evo data** (not packaged with the SHA pin) — same
  reproducibility class as `../selection/`.
- inPZU passive funds (launched ~2019–2022) have short history → ETF backfill
  needed for older folds.

- **Per-fund reclassification produced** (`reclassify.py` → `output/pln_reclassification.csv`):
  564 PLN funds, 115 changed group, 427 kept. Kept-group renames + explicit
  moves/isolates + new-satellite seeds + nearest-coherent-destination fallback.

## Resolved — rate-synthetic benchmark distortion (2026-06-02)

A zero-vol series breaks only the **ratio metrics that divide by a downside
quantity**: `sortino` (÷downside-vol) and `profit_factor` (÷Σlosses) → ∞ for a
no-loss series (prototype: CASH `sortino=nan`). `info_ratio` is NOT fragile
(TE=0 is a trivial guard→0; CASH IR was finite −0.35), and `hit_rate` (vs L2
median) is already in the model. The distortion bites only the **segment-score
anchor**, not within-L1 ranking.

**Resolution** (`quality_metric_candidates.py` correlation study + decisions):
- **Scope kills most of it:** segment scores needed **YTD only (from 2025-12-31)**
  on **real-vol benchmarks** → no synthetic backfill for the segment score; raw
  scores keep full history for validation.
- **Quality pillar: keep `sortino + profit_factor` + a no-loss guard** (no
  downside → cap at group max). Corr 1.0, model unchanged on 534 risk-bearing
  funds; guard touches only ~3 cash funds. Candidate study showed every
  high-fidelity proxy (sharpe 0.98, gain_to_pain 1.0) *also* needs a guard, and
  guard-free metrics (ulcer/max_dd) cost ~0.2 rank-corr — so guarding the
  originals is best. `omega(MAR=0) == profit_factor`; `tail_ratio` weak (0.80) + needs guard.
- **ML: inference-only** (benchmark scored by existing trained models; models unchanged).
- **Cash behaviour emerges naturally:** quality saturates (guarded) → yield/return + consistency-vs-median decide. No per-class rule.

## score_evo — benchmark-anchored calibrated score, v1 results (2026-06-02)

Implemented `score_evo.py` (+ `prod_scoring.py`; design:
`docs/superpowers/specs/2026-06-02-score-evo-design.md`).
`score_evo = clip(50 + (score_i − score_B,g)/max(σ_g, 5) × 15, 0, 100)`, Option-1
projection (benchmark projected onto the funds-only L1 cohort z-stats; fund
`score_i` untouched). Anchor = **freshly computed 2026-05-22** cross-section
(not the stale 2026-04-24 production snapshot), 554 PLN funds, 23 groups
anchored, 66 `no_anchor`.

- **Fresh, proper, 4-pillar:** refreshed `fund_prices` from on-disk sources;
  `prod_scoring.compute_fresh_scores` runs the real `score_funds` pipeline at
  2026-05-22 (918/932 funds 4-pillar). 2026-05-29 is not full-universe
  scoreable — the daily NAV feed (`fund_data_evo`) ends 2026-05-20, so 05-22 is
  the freshest W-FRI inside the 5-day freshness gate (05-29 keeps only ~356).
- **GATE A exact (0.0000):** cohort μ/σ reproduce the detail's `z_` columns
  bit-for-bit (cohort z-stats span all currencies for EQ/COM/MIX — the fix that
  took Gate A 1.60 → 0.00).
- **Benchmarks are CURRENCY-AGNOSTIC (decision):** a PLN fund (hedged or not) is
  compared directly to its native-currency ETF benchmark — no USDPLN/EURPLN
  conversion. (A USDPLN snapshot was fetched but is NOT used under this rule.)
- **Benchmark ML pillar = ML-NEUTRAL (group-median).** The model's rank/label
  features (`rank_pct`, `rank_accel`, `q1_freq_12m`, `category_enc`=fwd-Q1-rate)
  are ill-posed for a non-fund benchmark. Impact is **bounded ≤3.0 evo pts
  (median 2.4), uniform per group** (no within-group rerank) — the tactical
  pillars (0.90 weight) are exact, only the 0.10 ML anchor term is approximated.
- **Benchmark anchor is informative, not redundant** with a median anchor:
  group-median `score_evo` spans 9–96; materially off 50 (|med−50|>10) in 8/23.
- **Active PLN funds mostly lag their passive benchmarks, strongest in
  equities/commodities:** Technology 25 (8% beat), Commodities 32 (20%),
  Global DM 43 (33%), PL Equity 45 (33%), EM Broad 40 (27%), PL Govt 45 (42%).
  Bonds/mixed sit near benchmark (HY 51, EM Debt 44, Global Core 55, Mixed
  44–59). Consistent with global active-vs-passive evidence.
- **Asia/China fixed** (breadth, not FX): FXI → broad `EQ_EM` (Asia-dominated);
  med_evo 80 → 50.
- **Gold & Mining Equity now anchored** to **GDX** (gold-miners ETF, fetched from
  Yahoo → `data/gdx.parquet`; registry had no miners series): med_evo **50.5,
  50% beat** — the 10 funds sit right around their miners benchmark. Coverage
  now 24 groups / 497 funds (`no_anchor` 66 → 56).

### Data source + watch-item verification (2026-06-02)
- **Use `processed`, not `published`:** `published/prices.parquet` is stale
  (max **2026-05-05**); `processed/fund_prices` is fresh (**2026-06-01**, after
  the on-disk re-combine). dm-evo's loaders + `score_evo` both read `processed`.
- **QRS33 (Quercus Dłużny 1) is NOT a data bug:** clean series to 2026-05-29 in
  `processed` (~5% ann, normal low vol). evo=0 is a genuine composite low-score
  vs a high WIBOR hurdle + peers — resolved, not a data artifact.
- **FIL148 (Fidelity Absolute Return Multi) — recommend reclassify MIX_AGR →
  ALT_ABS:** ~0.30 corr to Mixed GL Flexible AND ~0.28 to ALT_ABS (low to both),
  vol **3.9%** vs ~8% for aggressive-mixed peers → absolute-return profile, not
  aggressive flexible mix. Overlap-limited (~71w history) → low-confidence
  advisor flag. `score_evo` outlier-flagged it (working as a diagnostic).

## PM/Gold dedicated proxies (Phase-2, resolved 2026-06-02)

Empirical anchor selection by 3Y weekly-return correlation of the group's funds
to candidate ETF proxies (`fetch_pm.py` → `data/{silver,pm_basket}.parquet`):

- **Precious Metals → SLV (silver), not COM_GOLD.** The group is silver-dominated
  (QRS32 Silver, SUP23 Silver + the broad-PM IPO190); avg ρ to SLV **0.85** vs
  COM_GOLD 0.67, GLTR-basket 0.84. Anchoring to gold spot was the **96 artifact**
  (silver scored against gold). SLV centers the silver funds within-asset (QRS32
  Silver lands ≈50 = "tracks silver"); **med_evo 96 → 39.5**. The PM-basket GLTR
  (0.84) overstated them as silver-beta vs a gold-heavy basket (med 84); kept as a
  snapshot cross-check, not the operative anchor.
- **Gold → keep COM_GOLD (confirmed best).** Gold spot beats every alternative
  (ρ 0.86–0.91 vs SLV 0.73, GLTR 0.87, GDX 0.82) — the right *asset*. The extreme
  med_evo 9 is NOT a wrong-benchmark bug: PLN retail gold funds structurally lag a
  fee-free USD gold-spot phantom (fees/tracking drag + the PLN-vs-USD leg these
  unhedged funds carry — the *intended* currency-agnostic read, consistent with
  scoring every fund on native NAV), amplified by the σ-floor on an ultra-
  homogeneous n=3 group (σ_g 0.6 → floor 5). Low-confidence, documented — not
  fixable by a different proxy. Same mechanism explains the thin US/USD Govt group.
- **Commodities → COM_BROAD already correct** (ρ 0.52–0.97).

## score_evo Phase-2 — full 45-feature benchmark ML inference (2026-06-02)

`bench_ml.py` replaces the ML-NEUTRAL (group-median) benchmark `pillar_ml` with a
real `upside_clf`/`downside_clf` inference on the benchmark's full 45-feature row,
then measures the residual. **Both faithfulness gates hold:**
- **GATE B exact (0.0000):** funds' production `pillar_ml` reproduces bit-for-bit
  from `ml_dataset` @ 2026-05-01 + the 4 joblibs + the double-normalization
  (min-max is affine → drops out under the subsequent within-cat z; the Option-1
  projection needs only the funds' raw-proba category μ/σ). Despite the sklearn
  1.8→1.9 `LabelEncoder` version-skew warning.
- **GATE A' (calibration, median Spearman 0.985):** `ml_dataset` is a snapshot
  built on a now-superseded price vintage (the 2026-06-01 NAV recombine), so
  neither raw NOR z reproduce from current prices (dataset.py's **own** functions
  give z maxdiff 3.4). Resolved by **percentile-calibration**: keep the funds
  exactly as production has them (stored z; Gate B intact) and place the benchmark
  in that distribution via the funds' own monotone (current_raw → stored_z) curve.
  Robust to drift — raw is used only to *order*. (frac<0.9 = 17%, all in
  `win_rate`/`hit_rate`, ≤0.9% importance.)

**Result — ML-neutral was a good approximation; full-ML reveals a systematic,
defensible level-shift it misses:**
- **|Δ score_evo|: median 1.2pt, mean 1.4pt, max 6.4pt.** The design's "≤3pt"
  bound HOLDS for **19/22** anchored groups. The 3 exceptions are exactly the
  thin/low-σ groups (Commodities −3.3, Gold & Mining +3.8, US/USD Govt −6.4),
  where the σ-floor amplifies. The shift is **uniform per group → no within-group
  rerank** (fund *selection* is identical under either ML choice).
- **Direction is asset-meaningful:** the benchmark reads *higher* on ML in 15/22
  groups — equity/govt **passive indices have `raw_guardrail` 0.95–0.98** (the
  model reads a diversified index as low bottom-quartile risk → downside-safe),
  pushing equity funds down ~1–1.5pt (Global DM Δpillar +13, US +9, Tech +10,
  European +9). Volatile/blended benchmarks read *lower* (Gold & Mining −13,
  conservative mixes −6 to −10, Global Core −8). ML-neutral (≈ median fund) is
  blind to this index-is-downside-safe signal.
- **Not an artifact of the ill-posed features:** sweeping the two genuinely
  history-dependent neutral-set features (`rank_accel`, `q1_freq_12m`; ~2%
  combined importance) to extremes moves `pillar_ml` ≤4pt mean / 7.75 max →
  ≤2.3 evo pt — smaller than the 8.7-pt mean systematic shift, which comes from
  well-defined risk features (vol/drawdown/skew/guardrail). The higher-importance
  rank/label features (`layer2_feat` 11.8%, `log_peer_count` 6.4%, `rank_pct`
  4.9%) are *assignable* from the group (mode L2 label / group peer count /
  cohort-projected rank), not ill-posed.
- **Gold & Precious Metals get no full-ML pillar** (their COM_GOLD scoring
  category is sub-`MIN_FULL` → 3-pillar funds, no ML cohort to project onto) →
  they correctly stay ML-neutral=50.

**Recommendation:** keep score_evo on **ML-neutral as the operative default**
(validated ≤3pt for 19/22 groups, no cross-snapshot drift in the live path, no
within-group rerank either way). The full-ML evidence (`output/bench_ml.parquet`)
quantifies the bound and the systematic equity-benchmark level-shift; the full-ML
score_evo is reproducible as `score_evo_neutral + delta_score_evo` (uniform per
group). Adopting the level-shift is a promotion-time advisor call — it matters
most for the 3 thin low-confidence groups, where full-ML's correction (3–6pt)
exceeds its own ~2pt ill-posed-feature noise floor.

## Methodology validation (2026-06-02, `validate_bench_ml.py`)

Audited score_evo end-to-end. **Two tiers** — the machinery is bit-exact; the
benchmark *phantom* has no ground truth, so it was validated by running real
funds through the phantom path and checking recovery of their true values.

**Tier 1 — machinery (faithful):** Gate A (tactical z-reproduction) **0.0000**,
Gate B (ML pillar) **0.0000**, projection self-consistency **MAE 0.098** (a fund's
own stored proba projected onto the cohort reproduces its production `pillar_ml`).

**Tier 2 — phantom (validated against borrowed ground truth):**
- **Anchor sanity (the 90% tactical weight):** a fund scored against ITSELF as
  benchmark lands at score_evo **median 51.2 / mean 50.7** (target 50) → the
  benchmark=50 anchor is **unbiased**. Tactical reconstruction MAE 2.36 composite
  pts (median |Δevo| **2.4 pt**), driven by the relative-metric reference mismatch
  (benchmark relatives vs new-L2 group, funds' vs old benchmark_category — the
  design's flagged effect, now quantified). Eliminable only by a full re-score on
  new L2 (D3 declines).
- **ML phantom (the 10% weight):** fund-as-phantom `pillar_ml` MAE 4.45 → **~0.6
  evo pt**, bias **−1.8** (the construction UNDER-states, so the "index is
  downside-safe → high guardrail" finding is conservative, not inflated).
  Rank-neutralization = ~40% of the error (intrinsic to a phantom with no rank
  history). Calibration extrapolation/clamping only **3.1%** (0% for equities).
- **Thin/low-σ groups** (n<8, already `low_confidence`): amplified tails (anchor
  |Δevo| p90 8.8, max 38) — the σ-floor magnifies modest reconstruction error.
  Treat those scores as directional only.

**Currency-agnostic benchmark (D10) is CORRECT — earlier "FX bias" finding
RETRACTED (2026-06-02).** I initially flagged a 6–11 evo-pt currency bias and
proposed PLN-converting benchmarks for unhedged funds. **That was wrong.**
Production scores every fund on its **native NAV with no FX conversion**
(`load_prices` does not convert; `load_scoring_universe` puts EQ/COM/ALT in
currency-**mixed** categories — "no carry distortion" — and only FI in
currency-**separated** categories *because carry is a persistent directional
bias*). So the funds in an EQ cross-section are unconverted and mixed-currency;
the benchmark must be **native/unconverted** to sit consistently among them.
PLN-converting only the benchmark would misplace it against unconverted funds —
that inconsistency is exactly what manufactured the 6–11pt "swing." It was an
artifact of the proposed fix, not a bias in the design. Equity FX level moves are
symmetric (no carry) and correctly absorbed into native returns on both sides.
**Only FI benchmarks reflect carry, and score_evo already does this:** WIBOR
short-rate benchmarks use `cash_rate` TR accrual, and the FI_GL series is the
PLN-hedged-to-PLN total return. No per-fund FX routing; unhedged funds need no
special treatment.

**Verdict:** core machinery valid (Gate A/B exact), benchmark=50 anchor unbiased
(fund-vs-self median 51.2), within-group ranking robust, ML-pillar choice
immaterial (≤0.6 evo pt). The currency-agnostic basis is correct and consistent
with production. The relative-metric reference mismatch (~2.4 evo pt) — listed
here as a caveat — was **eliminated at the root by re-scoring on the new L2**
(next section), reversing D3. Remaining caveat: σ-floor amplification on thin
`low_confidence` groups.

## Re-score on new L2 — "proper job", reference mismatch eliminated (2026-06-02)

On user direction, reversed D3 ("score_i byte-identical to production") and
**re-scored every fund with the new L2 as the relative-metric reference**, so
funds and their benchmark phantom finally share one peer basis.

- **`rescore_new_l2.py`** — sets `benchmark_category = final_group` for all 554
  PLN funds (≥8 peers) or the L1 scoring-category fallback (36 thin funds), then
  re-runs production `score_funds`. L1/scoring_category is unchanged for all 564
  funds, so only the relative indicators move; the **full L1 cohort is re-z-scored
  cross-sectionally** (`zscore_within_category` recomputes winsor μ/σ over all
  peers) — so even kept-label funds shift when peers move. ML pillar re-used from
  production (its `layer2_feat` was trained on OLD-L2 labels; new-L2 ML needs a
  retrain — deferred, ≤0.6 evo pt).
- **score_i shift is modest (MAE 0.54 composite pts)** — confirms the mismatch was
  small. Kept-L2 funds DO move (MAE 0.15, max 6.7), proving the cross-sectional
  re-z-score is universe-wide, not a patch. Largest moves (−13.7) are FI
  specialist funds (PZU40, Schroder/Franklin IG credit): production lumped 49/57
  `FI_GL_PLN` funds into one monolithic "Global Core Bonds PLN" pool; the new
  taxonomy split that into a refined Core group (34, keeps its ≥8 reference) plus
  thin specialist groups (IG Corp 5, US/USD Govt 3, Short Duration…) that fall
  back to the **residual** `FI_GL_PLN` L1 (15 funds). A corporate-credit fund that
  stood out vs the core-dominated pool now sits in a mixed specialist residual →
  drops. This is the granularity-vs-`MIN_BENCHMARK_PEERS`(8) tension, an advisor
  taxonomy call (split-but-fall-back-to-L1 vs keep-in-a-broader-FI-reference), not
  a code bug.
- **`score_evo` re-anchored on `rescored_detail`** + thin-group fix: the benchmark
  phantom now computes its relatives vs the **same** `benchmark_category` peer set
  the funds used (group if ≥8, else L1). This corrected the extreme thin groups —
  **Gold med_evo 9 → 39, US/USD Govt 18 → 33, IG Corp 52 → 50** — which were the
  mismatch (benchmark scored vs 3 funds while funds used a broader fallback). Big
  groups (Global DM, US, …) ~unchanged. Gate A still exact (0.0000).
- **Anchor sanity tightened** (`anchor_sanity.py`): changed-L2 funds — the ones
  the mismatch hurt — reconstruct tighter (median |dev| 2.33 → 1.80). Aggregate
  median dev 2.4 → 2.2; the residual is dominated by the self-benchmark test's own
  leave-one-out artifact (kept funds, no mismatch, still ~2.6), not a score_evo
  error — the real anchor (external ETF, full group) is more consistent than this
  upper bound.

## Three decoupled groupings + relative-scoring override (ADR-0001, 2026-06-02)

Encoded the three-grouping principle (`docs/adr/0001`): a fund's **selection
L2** (`final_group`), **relative-scoring peer set** (`benchmark_category`), and
**ETF anchor** (`BENCH`) are now independent. `relative_scoring_overrides.yaml`
lets a thin specialist L2 (<8 peers) **borrow a coherent ≥8 relative-scoring group**
within its L1, instead of the blind L1 fallback — while keeping its distinct
selection label and ETF anchor.

- **29 funds override-borrowed, 7 still L1 fallback** (Gold/PM — no ≥8 COM sibling).
  Gate A still 0.0000; ETF anchors + selection labels unchanged.
- Effect (blind → override): IG Corp score_i 47→51 / evo 50→52; US/USD Govt 38→40;
  Mixed PL Flex 50→46. Modest, sensible — they're now graded vs a coherent broad
  pool, not a residual grab-bag.
- **Borrow is symmetric** (`score_funds` pools by shared `benchmark_category`): the
  borrowers join the host's pool, so the host shifts slightly (Global Core Bonds
  med_evo 60→58). Not a defect — it forms a shared coherent "Global IG Bonds"
  relative-scoring group for all the global-bond specialists. A one-directional
  borrow (no host perturbation) would need a separate per-group relative-metric
  path; deferred unless the host dilution matters.

## EQ_DM split analysis + 4-layer taxonomy + dedup (ADR-0002, 2026-06-03)

Before the ML retrain, audited the currency-MIXED equity cohorts (PLN + non-PLN).

- **Dedup (real bug fixed):** 63 non-PLN funds in mixed EQ/COM/MIX/ALT cohorts are
  share-class duplicates of a PLN strategy (same base code) — currently
  double-counted in the z-scoring cohort. Excluded (keep PLN class);
  `extend_nonpln_eq.py` → `output/dedup_exclude.csv`. FI self-dedups (ccy-split).
- **EQ_DM is one correlated blob** (`eqdm_structure.py`): agglomerative clustering
  puts 246/282 in one cluster. Only **region** is separable (within-ρ 0.75–0.81 vs
  between 0.54–0.66; Japan/Europe most distinct) and only **Technology** (within
  0.73 vs 0.64, n=21) + **Gold & Mining** pass the *distinct-AND-populated* sector
  carve-out test. **Style is real but too thin**: Value within-ρ 0.93 but only 2–4
  funds/region (fails ≥8) — so a `US Value`/`US Core` split is NOT data-supported.
- **4-layer taxonomy adopted** (ADR-0002): L0 asset class · L1 asset category
  (scoring) · L2 market segment (region + Tech/Gold carve-outs; the scoring group) ·
  L3 style/sector (presentation tags only). `classify_eqdm.py` →
  `output/eqdm_l1_l2_l3.csv`. EQ_DM L2 = US (36) / European (48) / Japan (10) /
  Global DM (**142**) / Technology (22) / Gold & Mining (**11**) + PLN Specialist
  (11) / Other (2). **Japan = 0 PLN funds** (all non-PLN). 130/282 carry an
  informative L3 tag.
- Non-PLN L2 assigned by NAME tags (bilingual EN+PL — 159/282 are Polish-named;
  authoritative for region). Region-less thematic funds default into Global DM →
  flagged for advisor eyeball (propose-to-human).
- **Tagger bug fixed (2026-06-03, during the EQ_EM pass):** the L3 `GoldMining`
  sector regex `Gold|…` matched "**Gold**man" → 2 non-PLN Goldman Sachs *global
  equity* funds (`GSF008`, `GSF018`) were wrongly assigned to the **Gold & Mining
  Equity L2 scoring group**. Fixed to `\bGold\b` (still matches World Gold / Global
  Gold / Gold & Precious Metals). Both funds → **Global DM Equity**; Gold & Mining
  **13 → 11** (all genuine gold/mining), Global DM **140 → 142**. PLN-only rescore /
  score_evo unaffected (both funds are non-PLN). Technology L2 audited — clean.

## EQ_EM split analysis — dissolve "Specialist EM" + split "Asia/China" (2026-06-03)

Same pass for the EM scoring category (`eqem_structure.py` → `classify_eqem.py` →
`output/{eqem_tags,eqem_l1_l2_l3}.csv`). **EQ_EM carries Polish equity too** (MSCI
puts Poland in EM): 51 of the 94 PLN funds are PL Equity (33) / PL Small-Mid (18).

- **Deduped universe = 149** (94 PLN + 55 unique non-PLN; 14 non-PLN share-class
  duplicates already in `dedup_exclude.csv`). The 55 non-PLN UCITS funds are
  concentrated in China / Asia / India / Latin America / Emerging Europe — i.e. they
  **populate** the finer EM regions that were too thin in PLN-only data.
- **Carve-out test (distinct ρ-gap ≥0.08 AND ≥8), `eqem_structure.py`:**
  | segment | n | within ρ | to-EM-Broad | Δ | verdict |
  |---|---|---|---|---|---|
  | PL Equity | 33 | 0.92 | 0.53 | +0.40 | DISTINCT |
  | PL Small-Mid | 18 | 0.85 | 0.50 | +0.35 | DISTINCT (but only Δ0.02–0.09 vs PL Broad — weak split, advisor-confirmed, kept) |
  | China | 17 | 0.81 | 0.60 | +0.21 | DISTINCT (soft: clusters with Asia/EM in unsupervised k=8; clear by block test; communicable) |
  | India | 9 | 0.81 | 0.45 | +0.36 | DISTINCT (most decoupled — pure isolated cluster; ρ0.21 to China/LatAm) |
  | Emerging Europe | 10 | 0.60 | 0.49 | +0.12 | DISTINCT but LOOSE (Russia/Turkey/MENA/EMEA mix; ρ0.68 to PL = CEE complex) |
  | Latin America | 5 | 0.86 | 0.55 | +0.31 | DISTINCT but **THIN (<8)** — pure cluster |
  | Asia ex-Japan | 19 | 0.81 | 0.77 | +0.04 | **BLENDS** — broad EM is Asia-dominated → folds into EM Broad |
- **Proposed L2 (7 groups)** dissolves the `Specialist EM` catch-all and splits
  `Asia/China`: **PL Equity (34) / PL Small-Mid (18) / EM Broad (56) / China (17) /
  Emerging Europe (10) / India (9) / Latin America (5)**. Asia ex-Japan → EM Broad
  (kept as an L3 region tag). **Latin America (n=5) borrows EM Broad for relative
  scoring** (ADR-0001; added to `relative_scoring_overrides.yaml`).
- **26 PLN funds relabel** (PROPOSAL — advisor sign-off; `changed` flag +
  `L2_advisor_current` kept): Specialist EM (14) → China 2 / Emerging Europe 5 /
  India 4 / Latin America 3; Asia/China (10) → China 1 / India 1 / EM Broad 8;
  + FIL008 EMEA: EM Broad → Emerging Europe.
- **4 unslotted PLN funds flagged `manual_review`** (advisor never grouped them; bare
  "Akcji" names defeat region tags): BPS01 (→ PL Equity, correct) and ALL102 / QRS07
  / TEM01 (default EM Broad is a placeholder — ALL102 "Turbo Akcji" + QRS07 "QUERCUS
  short" are Polish; TEM01 "Zdywersyfikowany" ambiguous). Resolve before integration.
- **Caveats:** Emerging Europe is the weakest carve-out (loose within-ρ; Russia funds
  e.g. DWS31 may be illiquid/frozen post-2022 — data watch-item). Asia-folds-into-EM-
  Broad and Latin-America-thin-borrow are the two advisor calls to confirm.

### Presentation layer — core/satellite + n_PLN (2026-06-03)

The scoring cohort is currency-MIXED (≥8 incl. non-PLN), but a PLN advisor can only
present PLN-accessible funds — so **n_PLN**, not the mixed total, gates presentation.
`classify_eqem.py` now emits `family / role / standalone_eligible / n_pln_segment /
present_depth` per the `taxonomy_final_pln.yaml` group_structure ("≤1 core + N
satellites + 1 Other").

- **EM Broad Equity = the EQ_EM core** (user-confirmed; matches production
  core/standalone=True) — deep, 25 PLN. All other segments are satellites.
- **standalone_eligible** (yaml rule: core yes; broad-market satellite yes; concentrated
  no): EM Broad ✓, PL Equity ✓ (broad home market), PL Small-Mid ✗ (size-niche),
  China/India/Emerging Europe/Latin America ✗ (single-country/region).
- **EQ_EM holds two allocation families:** *Polish equity* (PL Equity backbone 34 PLN +
  PL Small-Mid 18) and *EM equity* (EM Broad core 25 + China/India/EmEurope/LatAm
  satellites). Note PL Equity is formally a satellite of the EQ_EM L1 (one-core rule)
  but is standalone-eligible — it is the de-facto Polish-sleeve backbone.
- **Presentation depth by n_PLN** (deep ≥8 / ok 5–7 / thin 3–4): EM Broad 25 *deep*,
  PL Equity 34 / PL Small-Mid 18 *deep*; Emerging Europe 6 / India 5 *ok*; **China 3 /
  Latin America 3 *thin***.
- **Decision (advisor): keep all four EM satellites presented** (n_PLN ≥ 3 = a usable
  shortlist; advisor picks the best PLN fund per region). China kept despite 3 PLN —
  advisory-relevant + deep mixed cohort (n=17). The thin ones carry `present_depth=thin`
  as a low-confidence flag; nothing folds into the core. (Considered + rejected: folding
  China/LatAm into EM Broad as L3 tags.)

## FI L3 descriptive layer — credit × duration × type × hedge (2026-06-03)

FI is the inverse of EQ: **L2 is already done and CURRENCY-AWARE** (FI is currency-
*segmented* in scoring because carry/hedging is a persistent directional bias —
`FI_{GL,CREDIT,PL,PL_SHORT}_{PLN,USD,EUR,GBP}`). So this pass is **mainly L3**: L1
(scoring cat) + L2 (`final_group`) + role/standalone all carry forward unchanged;
`classify_fi.py` adds the finer descriptive tags. Scope = the **199 PLN FI funds** (the
PLN-advisory presentation universe; the 139 non-PLN FI live in separate currency
cohorts, not PLN-presented). FI self-dedups (ccy-split) — no dedup step.

**FI L3 = 4 presentation facets** (name + L2 + cat derived, bilingual; NEVER scored):
- **credit_quality** Govt 64 / Mixed 63 / IG 60 / HY 12
- **duration** Core 120 / Short 78 / Long 1 (`FI_PL_SHORT_*` cat ⇒ Short prior; explicit
  long-duration naming is rare in the PLN retail shelf)
- **type** Aggregate 108 / Flexible 36 / Corporate 20 / Sovereign 19 / EM 14 /
  Inflation 1 / Convertible 1
- **hedge (the carry axis)** Native 121 / Hedged 40 / Unhedged 38 — Native = PL-domestic
  (no FX leg); Hedged = foreign→PLN; Unhedged = foreign + FX-exposed
  (from `output/pln_unhedged.csv`).

**Carry-aware L2×hedge** (the user's point — carry/hedge matters): every PL-domestic L2
is 100% Native; the foreign groups carry FX risk where unhedged — **Global Core 14
Hedged / 20 Unhedged**, EM Debt 7/6, HY 7/5, IG Corp 1/4, **US/USD Govt 3 Unhedged**
(matches the earlier FX-split finding). The big hedging splits already happened at L2
(US/USD Govt carved from hedged Global Core); the hedge tag captures the residual
within-group FX exposure for presentation.

**Validation (`classify_fi.py`, 3Y weekly):**
- **duration → annualized vol is cleanly monotonic** ✓ Short **1.1%** < Core **4.5%** <
  Long **11.6%** — the duration tagger tracks real rate sensitivity.
- **credit → drawdown is NOT monotonic** (Govt 0.038 > HY 0.031 > IG 0.015), and stays
  so even **within Core duration** (Govt 0.049 > HY 0.034 > IG 0.032). Not a tagger bug:
  **2023–26 FI drawdowns are rate/duration-driven, with no credit-stress event
  in-sample**, so credit quality doesn't order drawdowns (HY here is short-spread-
  duration high-carry; "Govt" skews longer global/US govt). Credit stays a name-accurate
  *descriptive* tag, not an in-sample risk-orderer — which is exactly why **duration is
  the dominant FI risk facet**.

**13 PLN FI funds have no advisor L2** (not in `pln_reclassification`; mostly newer
short/cash funds — Franklin USD MMF, Fidelity USD Cash, Allianz Dochodowy, BPS
Obligacji, Schroder Securitised Credit…). They get L3 tags but are `flag=unslotted_no_L2`
— L2 is the advisor's call (not invented here, since FI L2 is "done").

Output: `output/fi_l1_l2_l3.csv` (199 PLN FI funds; L1/L2/role/standalone + 4 L3 facets +
family/n_pln_segment/present_depth/flag).

## COM L3 descriptive layer — sub_theme × structure × hedge (2026-06-03)

Like FI, COM's L2 is already done (Gold / Precious Metals / Commodities-broad; advisor-
confirmed + ETF-anchored — Gold→COM_GOLD, Precious Metals→SLV, Broad→COM_BROAD). So
"just L3": L1/L2/role/standalone carry forward; `classify_com.py` adds the metal/sub-
theme tags. Scope = **17 deduped PLN funds** (the 1 non-PLN COM is a share-class dup,
already in `dedup_exclude.csv`; COM is currency-MIXED so dedup applies).

**COM L3 = 3 presentation facets** (name + L2 derived; NEVER scored):
- **sub_theme** Broad 8 / Gold 5 / Silver 3 / PreciousMetals 1
- **structure** Standard 15 / Leveraged 2
- **hedge** Unhedged 15 / Hedged 2 — **DESCRIPTIVE ONLY**: COM is scored CURRENCY-
  AGNOSTIC on native NAV (the carry/FX-conversion rule), so hedge does *not* drive
  scoring or benchmark here (unlike FI). [[scoring-is-currency-agnostic-native-nav]]

**L3 surfaces what L2 hides** (L2×sub_theme): the broad "Commodities" L2 (10) holds 8
true broad funds **+ SUP61 "LEV Gold" (Gold/Leveraged) + SUP62 "LEV Silver"
(Silver/Leveraged)** — leveraged single-metal funds the broad label masks. "Precious
Metals" (3) = 1 PM-basket (IPO190) + 2 silver (QRS32, SUP23) — confirms the silver-
dominated group behind the SLV anchor.

**Validation (`classify_com.py`, 3Y weekly vol) — both monotonic:**
- sub_theme: Broad **0.13** < Gold **0.17** < PreciousMetals **0.21** < Silver **0.43**
  (silver ≈ 2× gold vol, as expected).
- structure: Leveraged **0.40** ≫ Standard **0.16** (≈ 2.5×) — validates the LEV tagging.

**1 unslotted** (`flag=unslotted_no_L2`): PZU99 inPZU Złoto O (gold; not in
`pln_reclassification`). L3-tagged; L2 is the advisor's call.

Output: `output/com_l1_l2_l3.csv`.

## MIX/ALT — finish L2 + L3 risk/strategy + currency-treatment steer (2026-06-03)

`classify_mixalt.py` → `output/mixalt_l1_l2_l3.csv`. Scope = **146 PLN MIX/ALT funds**.

**Currency treatment (user decision — recommendation to dm-evo scoring config):**
- **ALT_\* + MIX_DEF → ccy-split** (like FI): bond-heavy / absolute-return, so carry/
  hedging is a persistent directional bias. Under a ccy-split these self-dedup — the
  cross-ccy share classes land in separate cohorts → the `dedup_exclude` entries for
  **ALT_ABS (1) + MIX_DEF (5) = 6 become moot**; only **MIX_AGR keeps cross-ccy dedup (7)**.
- **MIX_AGR → keep currency-MIXED** (equity-heavy, carry negligible) AND the existing
  **Mixed-PL vs Mixed-GL** L2 split already proxies the currency dimension → smaller issue.
- *Validation (vol by cat):* MIX_DEF **6.7%** ≈ ALT_ABS **6.8%** < MIX_AGR **8.0%** — DEF/ABS
  are the lower-vol bond-heavier cohorts (carry a bigger share of risk), consistent with
  the steer; the gradient is modest (all are moderate-vol mixed), so this is *supportive*,
  not decisive — the case for ccy-splitting DEF/ALT is primarily the directional-carry
  argument. **(ADR-worthy — extends the "FI by CCY" principle to ALT_\*/MIX_DEF.)**

**L2 finished:**
- **ALT_CRP = Crypto** (NOT corporate!) — CAB79/PZU100 are Bitcoin funds → new L2
  **`[ALT_CRP] Crypto`** (n=2, satellite, not standalone).
- **ALT_OTH = Private Markets** — MCI EuroVentures, Eques Lexington PE, closed-end FIZ/
  NFIZW → new L2 **`[ALT_OTH] Private Markets`** (n=5, illiquid, satellite, not standalone).
- **FIL148_AH_PLN** (Fidelity Absolute Return Multi, Mixed-GL-Flexible) → **`[ALT_ABS]
  Absolute Return`** (the prior low-confidence advisor move; vol 3.9% vs ~8% agg-mix peers,
  ~71w history). L2 applied; the L1 scoring-cat move (MIX_AGR→ALT_ABS) is the dm-evo action.
- MIX L2 was already done (PL/GL × Conservative/Flexible). **15 unslotted MIX funds**
  provisionally slotted by cat+geography, flagged `provisional_advisor_review`; **1
  ALT_ABS** (SUP01 Superfund RED) slotted.

**L3 = 3 presentation facets** (name+cat derived; never scored):
- **risk** Aggressive 53 / Conservative 51 / Balanced 20 / AbsoluteReturn 17 / Illiquid 5
- **strategy** Balanced 82 / TargetDate 21 / MultiStrategy 10 / MultiAsset 9 /
  AbsoluteReturn 7 / ActiveAllocation 6 / Income 4 / PrivateEquity 4 / Crypto 2 /
  MarketNeutral 1 (TargetDate = the ING/PKO "Perspektywa 20XX" glidepath families)
- **hedge** Native 42 (PL-domestic) / Unhedged 88 / Hedged 16 — *approximate for MIX/ALT*:
  `pln_unhedged.csv` is equity/COM-scoped, so hedge is derived from the explicit
  "(hedged)"/`_*H_PLN` marker; foreign funds without a marker default to Unhedged
  (advisor-confirm). The Native/foreign split is solid; Hedged/Unhedged within foreign is
  the soft part.

## Experiment grouping FROZEN — consolidation for rescore + retrain (2026-06-03)

`build_experiment_grouping.py` → `output/experiment_grouping.{parquet,csv}` folds all five
per-category passes + ccy-split + dedup into ONE authoritative per-fund grouping that both
the tactical rescore and the ML re-feature/retrain consume. Pure lab data-prep — it only
builds the `scoring_category` / `benchmark_category` Series `score_funds` already takes as
params (no dm-evo change). Architecture decision: dm-evo will get a small **provider
injection seam** (a `ScoringUniverseProvider` accepted by `load_scoring_universe` +
`ml.dataset`, default = current behavior) — the *quantbox DI principle*, NOT the
quantbox-datasets package split (that's quantbox-specific: multi-source crypto data shared
across many strategies; dm-evo has one coupled fund dataset + already-overridable data roots).

**Coverage: 1028 funds (615 PLN + 413 non-PLN). NaN benchmark_category = 0.** Casework
decisions baked in (the ones to sanity-check):
- **ccy-split** (128 funds): ALT_*/MIX_DEF get `_<ccy>` (FI already split) → new L1s
  ALT_ABS_PLN/USD/EUR, ALT_CRP_PLN, ALT_OTH_PLN/EUR, MIX_DEF_PLN/USD/EUR. EQ_*/COM_*/MIX_AGR
  stay currency-MIXED. [user steer]
- **dedup = 57** (EQ_DM 35 / EQ_EM 14 / MIX_AGR 7 / COM_BROAD 1) — only MIXED cohorts; the 6
  MIX_DEF+ALT_ABS dups drop out of exclusion because ccy-split self-dedups.
- **FIL148** L1-moved MIX_AGR → ALT_ABS_PLN (absolute-return profile).
- **benchmark_category** unified ≥8 / borrow(ADR-0001) / L1-fallback for ALL cats: mixed
  cohorts count peers across currencies (China 17, India 9, EmEurope 10 → own group;
  Latin America 5 → borrows EM Broad); ccy-split count within the ccy cohort and ccy-suffix
  the result. **FI borrows restored** (IG Corp 5, US/USD Govt 3, bracketed Govt/Short-Dur →
  Global Core Bonds PLN). Gold/Precious Metals/EQ_DM-Other → L1 fallback (no ≥8 sibling).
- **layer2 = selection_L2** (the new taxonomy) feeds `layer2_feat` at retrain.

Next: tactical rescore on this grouping → provider seam → ML re-feature → retrain → final score.

## ML retrain on frozen grouping + final composite — EXPERIMENT VALIDATES (2026-06-03)

Steps 3–5a of the rescore+retrain pipeline (see `EXPERIMENT_PLAN.md`). Done via subagents
to keep context clean; results independently spot-verified.

- **Provider seam** (dm-evo worktree `feat/grouping-provider`, commits 7547e33c+323d2103;
  main untouched at dd6f1c89): `GroupingOverride(scoring_category, benchmark_category, layer2)`
  + optional `scores_path` threaded through `ml.dataset.build_dataset`/`build_raw_rows`/
  `_apply_categorical_and_encoding`/`load_scores_for_ml`. Default = exact prior behavior
  (verified); override path verified. The *quantbox DI principle*, no datasets-package split.
- **Re-featured dataset** on the frozen grouping: 537,966 rows / 877 funds; **new L2 present**
  (China 12171 / India 6117 / Emerging Europe 9262 / Latin America 3825), **old gone**
  (Asia/China 0, Specialist EM 0), ccy-split L1 present (ALT_ABS_PLN, MIX_DEF_PLN/EUR), 57
  dedup dropped. **Retrained 4 LGBM** (`output/models_experiment/`, 45 feat, layer2_feat
  re-keyed to new taxonomy).
- **Gates PASS**: walk-forward (291 folds) upside IC 0.506 / Q1-prec 0.618, downside
  Q4-avoid 0.945 — all above `scoring.yaml` floors; embargoed OOF overfit check clean
  (deflated P(IC>0)=1.0, t 62–64). `layer2_feat` gain 8.8% (prod 8.1%) — structure preserved.
- **Final composite with retrained ML (5a) — the headline:** composite Δ vs old-ML MAE
  **0.53 pt** (mean +0.00, p90 1.26, max 3.33) — **confirms the long-deferred "≤0.6 evo-pt"
  estimate with the REAL retrain**. The ML pillar moves MAE 5.45 (within-cohort *reranking*,
  within-cat mean ~0) but attenuates to ~0.5 pt under its 0.10 weight (tactical 0.90 unchanged).
  **Selection is robust:** 54 funds (6.2%) change within-group quartile; **top pick changes in
  only 2/39 groups** (FI_GL_USD, PL Govt/Core Bonds PLN). Independently re-verified (MAE 0.533,
  2/39). Conclusion: the refined taxonomy + retrain is sound and barely perturbs selection;
  old-L2 ML was a good approximation.
- **Operational caveats (reproducibility):** retrain ran via kill-recovery — `train_final`
  artifacts written first (~2 min, the real models), walk-forward gate disk-checkpointed
  across harness kills (numerically identical, just resumable). A full historical rescored
  panel was built (`build_rescored_panel.py`) for rank-features/labels (ML pillar at the
  anchor only, 3-pillar historically — as the production panel is built). Worktree `data/`
  dirs symlinked to the main checkout (data isn't in git — the pinnability point we discussed).
- **Output inventory:** `final_scores_experiment.parquet` (retrained-ML composite @2026-05-22 —
  THE result) + `final_detail_experiment.parquet`; `rescored_experiment_detail.parquet`
  (old-ML interim @2026-05-22 — the baseline); ⚠️ `rescored_experiment_scores.parquet` was
  overwritten to the full historical PANEL by the retrain (not the single-date interim —
  re-run `rescore_experiment.py` if a clean interim is needed); `models_experiment/*.joblib`;
  `ml_dataset_experiment.parquet`. Scripts: `rescore_experiment.py`, `rescore_final_experiment.py`,
  `quantify_retrain_effect.py`, `build_experiment_grouping.py`.

**Remaining: 5b — `score_evo`** (benchmark-anchored): blocked on ETF anchors for the new
groups (China→FXI [in registry], India→INDA, Latin America→ILF [need sourcing], Emerging
Europe → un-anchored or EEM proxy [advisor call]). Crypto/Private Markets stay presentation-
only (n<MIN_SCORED). Then promotion to dm-evo (config + `fund_mapping.csv` + model artifacts +
ccy-split rule + doc bumps) is the human-driven step.

## 5b score_evo + advisor selection sheet + purity sweep — EXPERIMENT COMPLETE (2026-06-03)

Final taxonomy persisted (`build_experiment_grouping.py`, consolidation-layer authoritative):
EmergingEurope dissolved → CEE+3 EUR to **Poland & CEE Equity** (ρ0.91 to Polish eq), Turkey/
EMEA/MENA → EM Broad, Russia (DWS31, frozen) dropped; **Asia split out** of the core into its own
L2 (practicality over the ρ0.77 blend — core must be broad-only); cross-asset **Special / Unrated**
(6 leverage/inverse funds, not scored). Final EQ_EM L2 verified vs the locked table.

- **ETFs sourced** (`fetch_em_anchors.py` → `data/`): AAXJ / INDA / ILF (Yahoo, through 2026-05-28).
  Anchor map → registry-series equivalents: EM Broad→EQ_EM(EEM), China→L2_CHINA(FXI), Poland & CEE→
  WIG_TR, PL Small/Mid→L2_MWIG40; Asia→AAXJ, India→INDA, LatAm→ILF.
- **Re-scored composite on final grouping** (`rescore_final_v2.py` → `final_scores_v2.parquet`):
  870 funds @ 2026-05-22 (850 4-pillar), excl. 57 dedup + 6 unrated. 58 funds changed L2 label,
  133 had a relative-pillar shift (max 8pt) from the moved benchmark_category — re-score was needed
  (5a carried old labels).
- **score_evo** (`score_evo_v2.py` → `score_evo_experiment.parquet`): **Gate A exact 0.0000**;
  27 anchored groups / 505 funds; 12 no-anchor / 55; 16 no_score (too-new); 6 unrated.
- **Advisor selection sheet** (`build_selection_sheet.py` → `output/selection_sheet.csv`, 582 rows):
  per L2 group, PLN funds ranked by score_evo with benchmark_beat, `core_eligible`, `present_depth`,
  flag. **`core_eligible`=16, all EM Broad + L3_region==EMBroad** (Asia/EMEA blends excluded → the
  EM core pick is genuinely broad). Special/Unrated shown as a separate unscored block.
  - EM core top = ING45 (63, +13 vs EEM); Poland & CEE = LUK04 (66); Asia = FIL007 (76); China =
    ALL93 (86); India = DWS33 (62); LatAm = FTI060 (40, −10). Active mostly lags passive in
    equity/COM (Tech 27, COM 30, Global DM 41); bonds/mixed near benchmark — consistent w/ prior.

**Purity sweep (all categories):** leverage/inverse = the 6 already quarantined (none missed);
structured/guaranteed/protected = **0** (the 5 regex hits were false positives — infrastructure
equity, capital *accumulation*, absolute-return); **target-date/lifecycle = 33 funds (~26 PLN)
polluting the Mixed groups** — glide-path vol runs 4%→13% within one family (GS Perspektywa
2025→2060, PKO 2020→2070), so they can't share a scored peer group or a static Mixed benchmark.
**DONE (2026-06-03): pulled the 33 into a separate "Target-Date / Lifecycle" group** (horizon-
selected via `target_year`, NOT benchmark-scored; flag `horizon_selected`, distinct from unrated).
Mixed cleaned: GL Flexible 61→34, GL Conservative 57→53, PL Conservative 33→31 (PL Flexible
unchanged); 0 of the 33 remain in any Mixed group. Re-scored: Gate A 0.0000; new Mixed top PLN
picks — GL Flexible SIS160 (74), PL Flexible MIL27 (67), GL Conservative ALL52 (85), PL Conservative
ARK09 (89). Selection sheet → 590 rows (551 scored + 6 unrated + 33 target-date, horizon-sorted).
**Mixed core/satellite now pure.**

**Residual FI/COM labels (low priority, explained):** 147 funds carry production selection_group
strings (no clean new-L2) → land `no_anchor`. **126 are non-PLN** (USD/EUR/GBP FI share classes —
not PLN-presented, zero impact). The **21 PLN** are ~13 near-synonyms of clean groups (`PL Corp
Short Term PLN`≈PL Corp Short, `Global Core Bonds PLN`≈Global Core Bonds, `PL Govt Bonds PLN`≈PL
Govt/Core — a string-normalization folds them in) + 5 genuine `FI_GL Other` catch-all + the unslotted
FI funds.

## FI cleanup DONE in-lab + dashboard — EXPERIMENT COMPLETE (2026-06-03)

Lab-separate mindset: finished the work properly here (not deferred to promotion).
- **FI cleanup** (`build_experiment_grouping.py` FI normalization + `score_evo_v2.py` anchors): the 21
  PLN FI residuals merged into clean groups (PL Corp Short 55, PL Govt/Core 39, Global Core Bonds 38,
  US/USD Govt 4, Gold 4, IG Corp 6), SIS196→IG Corp, 2 USD MMFs→new **Cash / Money Market**, `FI_GL
  Other` kept + anchored to FI_GL (med 68.5), **PL Other Bonds → TBSP** (advisor `other` residual,
  low-confidence). **0 PLN FI no_anchor.** Gate A 0.0000. Only remaining no_anchor: `[ALT_ABS]
  Absolute Return` (18 — no passive index by nature; cash-anchor optional) + `Specialist Equity` (11,
  thin DM residual) — both non-FI, by-design, dashboard-displayed.
- **Calibrated score_evo** re-run on the corrected grouping each step (Gate A exact throughout).
- **Dashboard** → `output/scoring_dashboard.html`. Rebuilt to the dm-evo **investment-research-
  dashboard skill** standard (skill + `evo-dm-brand` copied into `.claude/skills/`): mandatory
  split architecture — thin `build_dashboard.py` (70 lines) + `dashboard/{data,html}.py` +
  `templates/scoring_dashboard.html` (compliance checklist passes). evo-dm-brand navy/blue, 6-KPI
  row (money KPI = median score_evo 46.2 / 42% beat; operational-confidence KPI = freshness +12d,
  Gate A 0.0000), sticky-nav sections. All 6 components (return/risk scatter centred at 50 + ★;
  pillar bars; sortable ranking + click-detail; real flag chips + Special/Target-Date; diagnostic
  strip reproducing score_evo_v2 exactly). **Inline Plotly** (5.1 MB, self-contained — renders on
  mobile/Discord where the CDN was blocked) + **responsive** (verified single-column @390px, both
  charts render, 0 console errors desktop+mobile). `operational_flags` loaded.

**Lab experiment is complete end-to-end:** correct groupings (all categories, EM finalized, FI clean,
leverage→Special, target-date→Lifecycle), retrained ML (validated 0.53pt / 2-of-39 selection),
calibrated benchmark-anchored score_evo, advisor selection sheet, and the dashboard. Deliverables:
`experiment_grouping.parquet`, `score_evo_experiment.parquet`, `selection_sheet.csv`,
`scoring_dashboard.html`.

**Also flagged (minor):** ~12 no-anchor FI/COM funds carry production residual selection_L2 strings
(`Global Core Bonds PLN`, `PL Corp Short Term PLN`, `COM_GOLD`…) from the `selection_L2 = new_l2
else production` fallback — near-synonyms of anchored groups; optional advisor fold.

**Status: experiment validated end-to-end.** Remaining is human-driven dm-evo promotion (ccy-split
rule `loaders.py:125`, `fund_mapping.csv` relabels + L3 cols, `ml.dataset` provider seam already on
`feat/grouping-provider`, retrained model artifacts, `relative_scoring_overrides`, methodology/
version+date bumps) + the two pending advisor calls above.

## Highest/lowest score_evo audit → Convertibles L2 + MIX Balanced tier + Mixed PL anchor (2026-06-05)

Audited the extremes of the `score_evo` distribution: the top/bottom are
disproportionately funds whose **benchmark anchor did not match the asset/risk
profile** — each is rank 1/N or N/N in its group *because* it doesn't belong there.
Fixed the two actionable cases (spec:
`docs/superpowers/specs/2026-06-05-convertibles-and-balanced-l2-design.md`,
ADR-0003). Gate A stays **0.0000** throughout. Before/after:
`output/score_evo_delta_2026-06-05.csv` (58 funds |Δevo|>5, 22 L2-label changes).

- **Convertibles were the universe's top 2** — `SIS105` (Asian Convertible) → EM Debt
  (`FI_EM`) evo **91**, `FOR30` (Global Convertible) → HY (`FI_HY`) evo **90**.
  Convertibles' equity-linked upside beats a pure-credit benchmark. **New
  `Convertible Bonds` L2 anchored to CWB** (SPDR convertibles ETF, sourced
  `data/cwb.parquet` via `fetch_cwb.py`). **Correlation gate passed** (3Y weekly ρ:
  SIS105 0.474 vs FI_EM 0.344; FOR30 0.630 vs FI_HY 0.402 — CWB the better anchor).
  Result: SIS105 91→**79.1**, FOR30 90→**84.5** (`low_confidence`; n=2 → relative
  peers fall back to `FI_CREDIT_PLN`, σ-floor amplifies the residual fund-vs-CWB
  outperformance — directional only). Advisor-confirmed: keep, flagged.
- **Balanced funds topped the Conservative group** — 18/67 `MIX_DEF` funds carry a
  Balanced/Aggressive `L3_risk` tag yet shared the 30/70 Conservative anchor.
  **Re-tier all MIX_DEF+MIX_AGR by risk tag** into Conservative(30/70) /
  **Balanced(50/50, new)** / Flexible(60/40), geo preserved. New `Mixed PL Balanced`
  (8) / `Mixed GL Balanced` (11). `scoring_category` (L1) unchanged — only
  selection_L2/benchmark_category/anchor move (ADR-0001). 6 cross-L1 strays fall back
  cleanly to L1; cohort-sizing fix (`build_experiment_grouping.py`: mixed-cohort count
  restricted to mixed-base funds) prevents a degenerate peer set where the new L2
  spans MIX_DEF (ccy-split) + MIX_AGR (mixed).
- **The carve-out EXPOSED a deeper benchmark bug → Mixed PL anchor.** The tier alone
  *backfired* (tight 8-fund Balanced group collapsed σ 13→6 → scores shot to ~100).
  Root cause: **all `Mixed PL` groups were anchored to a GLOBAL blend (EQ_GL/FI_GL)**,
  but these funds hold Polish assets — PL bonds' high-WIBOR carry beat global bonds,
  so bond-heavy PL funds beat the global blend regardless of tier (Conservative was
  med 58.7, not 50). **Switched Mixed PL → Polish WIG_TR/TBSP blend** (registry series;
  30/70, 50/50, 60/40). Advisor-confirmed (re-bases 38 funds beyond the carve-out).
  Now: Mixed PL Conservative med **37.5** (beat 17%), Balanced **57.4** (beat 88%),
  Flexible **33.7** (beat 14%) — active Polish mixed funds genuinely lag their proper
  passive benchmark, the after-fee picture the global anchor had masked (consistent
  with the equity/COM active-lags-passive finding). Mixed GL stays on the global blend
  (those funds hold global assets): Conservative 56.7 / Balanced 41.0 / Flexible 50.6.
- **Net effect on the extremes:** convertibles drop from #1/#2 to mid-pack; the
  ARK09-led balanced cluster (88/87/82…) re-bases (ARK09 88.5→76.2, UNI02 77.9→50.9,
  ING02 77.3→51.4). New deliverables: `score_evo_experiment.parquet`,
  `selection_sheet.csv` (590 rows), `scoring_dashboard.html`, `score_evo_delta_2026-06-05.csv`.
- **Residual caveats:** (1) thin-group σ-floor still amplifies Convertibles (n=2) and
  the tight Mixed PL Balanced (n=8) — low-confidence/directional. (2) `Mixed PL
  Conservative` still spans a range of equity weights (Stabilny/Senior ~15% eq →
  KAH05 0.0, IPO154 4.2 vs the 30%-equity central anchor) — a finer sub-tier split is
  a possible future refinement, not done here. (3) Other audit findings NOT fixed
  (separate advisor calls): `KAH36` healthcare-as-Technology (evo 7.2), China A-shares
  `ALL93` vs offshore FXI (86), thematic funds defaulted to Global DM, PL Corp/Govt
  Short vs WIBOR cash (QRS33 1.3). ML `layer2_feat` stale for the 21 relabeled funds
  (≤0.6 evo-pt, inference unchanged — no retrain).

### Robustness refinement — all-currency evo cohort + σ shrinkage + KAH36 (2026-06-05)

Follow-up on the σ-floor caveat and a methodology point (use all currencies to *derive*
evo for currency-mixed cats; PLN only for *presentation*). Three changes, Gate A still
**0.0000**, `score_i` untouched (`output/score_evo_delta_step2_2026-06-05.csv`).

- **All-currency evo derivation for currency-mixed cats (EQ/COM/MIX_AGR)** — a
  *consistency fix*, not new behavior: `score_i` is already z-scored across all currencies
  for these cats, but the score_evo layer (group σ + benchmark peer medians) used PLN-only
  funds. `score_evo_v2.py` now scopes the σ cohort + peer set to **all currencies** for
  currency-mixed cats (`_is_ccy_split_cat`), PLN at output only. **FI/ALT/MIX_DEF stay
  currency-scoped** (carry/hedging is a persistent directional bias; their ccy-suffixed
  `benchmark_category` self-restricts). Robustifies thin EQ groups (Asia σ 3.6→11.0, cohort
  6→18). FI groups unchanged (PL Govt/Core 45.2→45.2, HY 45.5→45.7); mixed EQ recalibrate
  modestly (EM Broad 38.5→42.8, Global DM 40.5→42.2 incl. KAH36).
- **σ shrinkage toward the scoring-category σ** replaces the crude `max(σ,5)` floor:
  `σ_eff = (n·σ_group + 8·σ_cat)/(n+8)`. Self-limiting (large groups: n dominates → σ_eff≈σ_group,
  <1pt move) and borrows a stable dispersion for cohorts still thin after the all-ccy switch
  (FI convertibles n=2, Gold/PM n=3-6, India σ genuinely 3.0). Effect: Convertibles FOR30
  84.5→**65.8** / SIS105 79.1→**63.4**; Asia FIL007 75.8→61.0; LatAm BGF032 14.7→33.8;
  Precious Metals IPO190 18→31.3; tight Mixed PL Balanced moderates (LUK02 85.4→74.2).
  `low_confidence` 49→37 (thin EQ groups now robust). **σ-floor caveat from the prior section
  is RESOLVED.** (India staying tight is a deliberate "don't swing 30 evo-pts on a 3% gap"
  choice, not a data fix.)
- **KAH36 healthcare reclassify** (`build_experiment_grouping.py` `EQDM_RECLASSIFY`):
  Esaliens Medycyny i Nowych Technologii (healthcare+tech) Technology→**Global DM Equity**
  (healthcare = 2 PLN funds, fails the ≥8 own-L2 gate). evo **7.2→39.9** — off the hot
  pure-tech benchmark. Technology 22→21. (The other 3 audit items remain advisor calls:
  ALL93 China A-shares vs offshore FXI [1 PLN, optional ASHR anchor], thematic→Global DM
  [present L3 style tag, not re-grouped], PL Corp/Govt Short vs WIBOR [genuine after-fee lag].)

### Three advisor-call fixes — ASHR anchor, CASH benchmark, dashboard L3 (2026-06-05)

Closed the three open audit items (Gate A still **0.0000**):

- **China A-Shares → ASHR (onshore CSI 300), not offshore FXI.** The pure A-share funds
  (ALL93 PLN + FTI108/SIS042/SIS184 USD) were in China Equity, benchmarked against FXI
  (HK H-shares) which decoupled and inflated them. New **`China A-Shares Equity` L2**
  (`build_experiment_grouping.py` `CHINA_ASHARES`), anchored to ASHR (`fetch_ashr.py`,
  correlation-gated: ρ to ASHR 0.77–0.80 vs FXI 0.65–0.72), borrowing China Equity for
  relative scoring (ADR-0001). **ALL93 87.7 → 68.9.** Offshore China funds (ABS012, AIG11)
  stay on FXI. (1 PLN fund + 3 USD; all-currency σ gives n=4.)
- **PL Govt Short + Cash/MM → dm-evo CASH series, not raw WIBOR accrual.** dm-evo already
  defines CASH (`config/tactical-signals/data_sources.yaml` + `build_signals.
  _synth_pl_cash_tr_backfill`: ETFBCASH.WA post-2024-01-02 + WIBOR carry backfill — the
  seam discards the unreliable early ETF NAV after a strategy/policy change). The lab's
  signals snapshot predates it, so `fetch_cash_etf.py` reproduces it with the SAME ticker +
  the SAME dm-evo splice (no reinvention) → `data/cash.parquet` (3Y ann 5.5%, max DD −1.1%
  ⇒ cash-like). Anchored `PL Govt Short` + `Cash / Money Market` to ("CASH", "level"). The
  fee-free WIBOR accrual was an unbeatable hurdle; the investable cash ETF is achievable →
  **PL Govt Short median 36 → 55 (beat 22% → 61%)**, QRS33 4.1 → 22.4. PL Corp Short stays
  on WIBOR cash_rate (credit, lenient bound — left per the audit).
- **Dashboard L3 style/sector chip** (`dashboard/data.py` `_load_l3_tags` →
  `templates/scoring_dashboard.html` detail card): a thematic/factor fund's low evo now
  reads with context (FIL112 "Income", INV55 "Quality", SKR71 "Consumer", AXA41 "IG · Short
  · Corporate", ARK09 "Balanced"). Niche themes the tagger files as Core/Broad (Lifestyles,
  Low-Vol) show blank — the documented tagger gap; advisor knowledge fills it. Thematic
  funds are NOT re-grouped (correctly global equity; broad benchmark is the honest read).

Net: 0 funds score >90; the extreme top is now genuine bond outperformers + the already-
flagged low-confidence Hungarian residual (AXA38). All open audit items from the
highest/lowest review are now either fixed or documented as correct-as-is.

**PL Govt/Core duration sub-bucket (presentation, 2026-06-05).** Q: split PL Govt into
medium/long duration? A: **no scoring split** — the duration axis is a continuum (TBSP beta
0.32–1.41, ~1.5–6y; no natural gap) with **no long cohort** (Polish retail tops out ≈6y; the
beta>1.3 bucket is 6 funds <8) and no long benchmark. Instead **refined the L3 `duration`
tag empirically** (`classify_fi.py` `refine_core_duration`): name-tagged 'Core' PL Govt/Core
funds split by realized vol into **Short-Core (<3%, 5) / Core (3–4.5%, 16) / Long-Core (>4.5%,
16)** — presentation only, surfaced in the dashboard chip. Validates the Aktywny 1 vs 2
divergence (CAB44 Short-Core 0.73β/2.9%vol/evo 64 vs CAB18 Long-Core 1.31β/5.0%vol/evo 46 —
same return, half the risk → risk-adjusted scoring rewards the shorter one). **IPO111/NOB27
stay in PL Govt/Core (Short-Core), NOT moved to PL Govt Short**: despite low vol (1.5/1.8%)
they correlate more with Core (0.78/0.92) than Short (0.71/0.83); the genuine short cohort is
cash-like (median vol 0.91%). Duration sub-bucket is PL-domestic only (global/EM vol mixes
duration with FX/credit).

## Out of scope / next steps

- **Segment score / `score_evo` (benchmark=50):** DONE (v1, fresh 2026-05-22
  4-pillar anchor, currency-agnostic, Gate A exact). PM/Gold dedicated proxies
  DONE (Precious Metals → SLV; Gold COM_GOLD confirmed). Full 45-feature benchmark
  ML inference DONE (`bench_ml.py`; ML-neutral validated ≤3pt for 19/22 groups,
  systematic index-downside-safe level-shift characterized). Remaining: weekly
  series from 2025-12-31. (task #8)
- **Per-fund reclassification CSV:** current selection_group → final L2 / role /
  benchmark, for advisor sign-off + xlsx update. (task #9)
- **Promotion:** methodology change flows via a dm-evo PR against
  `config/reference/fund_mapping.csv` + `docs/methodology/{taxonomy,fund_selection}.md`
  + `config/fund-selection/scoring.yaml` (segment score), with version + verified-date bump.
- **EUR/USD universes:** this line is PLN-only; extend after PLN locks.
