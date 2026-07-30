# Signal Research Lifecycle

Stage-by-stage playbook for quant signal research: from candidate signals through composite scoring to a verified portfolio backtest. Use when designing or iterating any signal-driven strategy (TAA, factor model, fund scoring, sector rotation).

**Complementary to** the parent `investment-research` skill's 5-phase lifecycle (Question → Data → Analysis → Calibrate → Deliver). The 8 stages below decompose the **Analysis phase** for signal-based research specifically.

## The 8 stages

| # | Stage | Question | Artifact | Anti-pattern |
|---|---|---|---|---|
| 1 | Generation | What candidate signals could predict this? | List of 5–15 raw signals + economic story per signal | Throwing 50 ratios in a hopper (data mining) |
| 2 | Per-signal anatomy | Does each signal individually look like a signal, not noise? | Per-signal dashboard (distribution + history + crisis traces) | Skipping straight to IC tests without inspecting the time series |
| 3 | Per-signal IC | Does each signal predict forward returns? | IC table per signal × horizon × era | Only computing full-sample IC (hides regime fragility) |
| 4 | Distribution & normalization | How do we put signals in compatible units? | Per-component normalization spec, with documented preserved structural info | Z-scoring everything per-asset by reflex (erases structural info) |
| 5 | Ensemble construction | How do we combine N signals into one composite? | Variants v{N} documented in EXPERIMENTS.md, ONE change each | Layering "new normalization + new clip + new weights" into one variant |
| 6 | Weight engine | Given a composite signal, what weight per asset per profile? | Weight engine spec + corridor sensitivity per profile | Tightening corridors on a single tail event without recalibration |
| 7 | Portfolio backtest | Does the composite deliver risk-adjusted return after costs? | Per-profile + per-regime + per-asset attribution table | Manual weighted-sum loops (inflates IR ~0.20) — **MANDATORY: use `backtest` skill** |
| 8 | Lock & promote | Has the candidate met all lock criteria? | STATUS update, EXPERIMENTS lock entry, spec §, feat/ branch | PROVISIONAL → LOCKED → PROVISIONAL flip cycles (lock once, with full evidence) |

## Stage 1 — Signal generation

**Source:** Factor literature (value/momentum/carry/quality/vol), regime classification, expert intuition, replicating known anomalies.

**Discipline:** Every signal needs a *prior reason to work* before it gets a backtest. A random ratio with a great backtest IC is overfit until proven otherwise.

**Output format** — one line per candidate:

```
SIGNAL_NAME = formula
  Story: why this should predict {asset}
  Source: paper / desk practice / regime hypothesis
  Risk: known failure mode (e.g., "fails when curve inverts")
```

## Stage 2 — Per-signal anatomy

**Tests per signal** (run before any combination):
- Distribution shape: histogram, percentiles (P5/P50/P95), fat-tail check
- Time-series stability: no regime breaks in scale/sign
- Coverage: no big NaN gaps, sensible warm-up
- Sanity: current value vs known regime ("Is HY OAS at +800bp visible in 2008?")
- Crisis traces: 2008/2020/2022 episodes look right

**Artifact:** Per-signal section in a validation dashboard. One section per signal, four panels: raw input → derived value → z-score → final signal, full history.

**Decision per signal:** keep / iterate (fix data) / kill (broken).

## Stage 3 — Per-signal predictive power (IC)

**Cross-sectional Spearman IC** at horizons 1M / 3M / 6M / 12M.

**Era split is non-negotiable.** A signal that looks great full-sample but is dead post-2010 is more dangerous than one that's mediocre across eras. Standard era splits (adjust to your data start):
- 2000–07 pre-GFC
- 2008–09 GFC
- 2010–19 expansion
- 2020–21 COVID + recovery
- 2022 rate shock
- 2023–present

**Decay curve** — when does the signal stop working? IC at 1M, 3M, 6M, 12M tells you the holding period.

**IC table per signal × horizon × era.** Output: a panel of per-cell ICs with significance (use Newey-West for time-series IC stats).

**Decision:** Which signals deserve a place in the composite. Note: weak-IC signals can still be useful as **negative-correlated overlays** — e.g., real-rate value signals lose on standalone IC for gold but can act as a brake on extreme overweights. Test in combination, not just standalone.

## Stage 4 — Distribution & normalization design

**Critical decision** — normalization choice changes which structural information survives:

| Method | What it preserves | What it erases | Use when |
|---|---|---|---|
| **Per-asset rolling z** (legacy) | Per-asset historical context | Cross-asset structural premia | Default until you know better — but rarely the right choice |
| **Bucket-pooled z** | Cross-asset structure within bucket | Cross-bucket relativity | Bucket has ≥3 assets; want EQ_EM cheapness preserved relative to other EQs |
| **Globally-pooled z** | All cross-asset structure (per-cat means survive) | Per-asset historical context | Momentum-style signals; want EQ_US momentum advantage to persist |
| **Percentile rank** | Ordinal info, bounded [0,1] | Magnitude info | When magnitudes are non-comparable (mixed units) |
| **Tanh squashing** | Bounded output, soft saturation | Linear differentiation at extremes | Final mapping to [0,1] for weight engine |

**Component clipping** — outlier guard. Carver's literal ±2σ at monthly cadence on indices is too tight (truncates real signal). **±3σ** is "fires only on true outliers" and matches no-clip on avg IR while providing a safety net.

**Composite cap** — bound the final weighted z so tanh doesn't saturate. Typical: ±2.0 on a sum that can reach ±7 on agreement days.

**Tanh σ** — softness of conviction curve. σ=1.5 saturates faster (sharper conviction); σ=2.0 keeps differentiation in the moderate-z range (better worst-profile protection).

**Document per-category post-pool means.** They show what structural info survives. If `EQ_EM value_z` post-pool mean is +0.61 (EM persistently cheap), the strategy will tilt to EQ_EM by default — which is a feature if EM cheapness is real, a bug if it's bias.

### ⚠️ Pool normalization MUST be walk-forward — no exceptions

**The trap:** research panels often compute pool μ/σ over the FULL panel (all dates × all pool members) and apply those stats to every date. This is lookahead: the pool applied at date T contains data from T+1, T+2, etc.

Per-cat rolling z upstream does NOT save you — the pool layer on top of PIT inputs still leaks if it uses full-panel stats.

**Empirical cost observed (dm-evo TAA, 2026-04-24):** replacing full-panel pool with rolling 10Y / 5Y-min pool dropped v4.14.1 avg IR from +0.556 to +0.484 (−0.072, ~13% relative). Lock-candidate survived, but the leaky number was overstated. Other variants would likely show similar shrinkage.

**Rule:** at each eval_date T, pool μ/σ must come from data satisfying `date ≤ T` (or `date ∈ (T−window, T]` for rolling). Never from the full panel.

**Implementations, in order of preference:**
- **Rolling window + minimum** (matches per-cat rolling z convention, e.g. window=120 months, min=60). O(N_dates × pool_size) — trivial cost.
- **Expanding window with min-periods gate.** Grows with each run. Same cost shape.
- **Fixed calibration window** (Carver-original: calibrate on pre-backtest warmup period, apply constants thereafter). Deterministic and fast, but can drift off regime over long horizons.

**Never acceptable:** full-panel pool in a backtest that measures IR/Sharpe/DD. It always flatters early-sample performance by importing late-sample structure.

**Gate before locking any methodology:** if the variant uses a pooled component, confirm a walk-forward re-run matches within the noise floor of the relative ranking. If absolute numbers shift but ranking holds, lock against the walk-forward number, not the full-panel one.

## Stage 5 — Ensemble construction

**One change per variant.** Don't layer "new normalization + new clip + new weights" into v{N+1}. You can't attribute a result to any one change.

**Common composite shapes:**

```
# Weighted z-sum with one primary + overlays
composite_z = 1.0·primary_z + 0.5·overlay_a_z + 0.5·overlay_b_z

# Optional: clip components individually before summing
composite_z = 1.0·clip(primary, ±3) + 0.5·clip(overlay_a, ±3) + 0.5·clip(overlay_b, ±3)

# Cap composite + tanh to [0,1]
final_z = clip(composite_z, ±2.0)
signal = (tanh(final_z / 2.0) + 1) / 2
```

**Weight schemes:**
- **Equal-weighted** — robust, no overfit risk
- **IC-weighted** — fits historical importance, overfits future
- **FDM-corrected (Carver)** — `1/sqrt(w'·Σ·w)` divides by signal correlation; conservative when signals agree
- **Regression / ML** — last resort; needs walk-forward validation

**Iteration discipline** — log each variant in `EXPERIMENTS.md`:

```markdown
## YYYY-MM-DD — v{N+1}: {one-line change}
Hypothesis: {why this should help}
What changed: {single mechanical change vs v{N}}
Result: avg IR {x} → {y} (Δ {z}); per-profile table; era table
Decision: accept / reject / iterate
```

## Stage 6 — Weight engine

Convert a [0,1] signal to a portfolio weight per asset per profile.

**Standard mapping:**

```
weight[cat] = neutral[cat] + (signal[cat] − 0.5) × corridor_span[cat]
```

**Multi-profile** — same signal, different corridors. Each risk profile has its own (min, neutral, max) per category. Corridor *geometry* affects strategy character:
- Symmetric corridors enable bigger trend-following tilts (and bigger flash-crash drawdowns when caught long into a reversal)
- Wider equity corridors at moderate-equity-neutral profiles (the "P4 problem") create the largest reachable upside, which compounds losses in mean-reverting shocks

**Floor consolidation + sum=1 normalization** — handle the case where a corridor floor (e.g., 5% min on FI_HY) interacts with the sum-to-1 constraint. Document the order of operations.

**Output:** Per-profile weight DataFrame, one row per rebalance date.

## Stage 7 — Portfolio backtest

**MANDATORY:** Use `backtest` skill (vbt `run()`). Manual weighted-sum loops over monthly returns inflate IR by ~0.20 because they skip intra-month weight drift.

**Standard outputs per variant** (all in one `pf` call so they share prices/dates/fees):
- Variants under test + current locked baseline + SAA benchmark
- avg + min IR across profiles
- Per-profile IR + Sharpe + MaxDD vs SAA
- Per-regime MaxDD via `pf.drawdowns.records_readable` filtered by `valley_idx` window
- Per-asset attribution via `pf.value(group_by=False)` (which assets contributed how much)
- Turnover + realized fees

**Realistic fees from day 1.** 10bps per rebalance for liquid index ETFs; more for narrow/illiquid. Don't run zero-fee backtests then "add fees later" — you won't, and the unfees results will mislead your iteration.

**Apples-to-apples comparison.** When ranking variants, all variants must use the SAME prices, SAME dates, SAME fees, SAME rebalance schedule. Easiest: pass them all as a dict to `vbt_run()` in a single call.

## Stage 8 — Lock & promote

**Lock criteria** (all must pass before flipping STATUS to LOCKED):

- [ ] Beats baseline on avg IR by ≥X (define X up front, not after seeing the result)
- [ ] Beats baseline on min IR (worst-profile protection)
- [ ] No regime catastrophe (no era worse than baseline by ≥X pp)
- [ ] Turnover within 1.2× baseline
- [ ] MaxDD vs SAA: tied or shallower on majority of profiles
- [ ] Attribution understood — "the win comes from {factor}" (don't lock if you can't say where the alpha lives)
- [ ] Known weaknesses documented in spec §Known risks
- [ ] Reproducible: rerun from clean state produces same numbers

**Then:**
1. Update STATUS.md row to LOCKED with date + drift-aware metrics
2. Append EXPERIMENTS.md entry with full rank table + decision
3. Update spec §{X} with formula + parameters + IR table + known risks
4. Open `feat/{subsystem}-v{X}` off `dev` for promotion (see `.claude/rules/research-workflow.md`)

**Lock once.** Avoid PROVISIONAL → LOCKED → PROVISIONAL → LOCKED cycles by running drift-aware backtest *before* the first lock attempt, not as a retrofit.

## Mapping to directory structure

The 4-track directory pattern (`validation/` + `scoring/` + `backtesting/` + `comparison/`) maps cleanly to the 8 stages:

| Stage | Directory |
|---|---|
| 1 — generation | `docs/signal-definitions-v{N}.md` |
| 2 — anatomy | `validation/` (per-signal modules + dashboard) |
| 3 — IC | `scoring/ic_analysis.py` |
| 4–5 — normalization + ensemble | `scoring/backtest.py` (variant loop) |
| 6 — weight engine | `src/{subsystem}/compute_weights.py` (or local equivalent) |
| 7 — backtest | `backtesting/backtest_vbt.py` |
| 8 — lock | `STATUS.md` + `EXPERIMENTS.md` + spec |

See `investment-research` parent skill "Mature-stage directory evolution" section for when to split flat → 4-track.
