---
name: fund-classification
description: Use when assessing or finalizing a fund peer-group / taxonomy for RETURN-COHERENCE in any fund universe or currency — symptoms like "the peer groups aren't homogeneous / funds in a group don't move together", regrouping / merging / splitting / dissolving peer categories, isolating misfit funds (leverage, off-strategy, broken data), classifying funds into core / satellite / standalone, or building a benchmark-anchored (benchmark=50) "is this fund worth holding vs its benchmark ETF" score. Universe-agnostic method; a PLN/dm-evo reference implementation is bundled.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Fund classification — return-coherent peer groups + benchmark score

## Overview

A **universe-agnostic** method to make fund **peer groups** return-coherent and to score each fund against its group benchmark. It **proposes**; a human **disposes** — it augments a maintained taxonomy, never auto-replaces it. Works on any market/currency: give it a fund **returns panel** + the **current grouping**. A complete **PLN/dm-evo reference implementation** is bundled in `scripts/` + `references/` — read it as the worked example and adapt the data-loading seam.

## Inputs (bring these for any universe)

- **Returns panel** — periodic total-return series per fund (e.g. weekly), in **one risk-denomination/currency at a time** so correlations are FX-free.
- **Current grouping** — each fund's current peer-group label (+ optional parent/asset-class level for the role/quarantine structure).
- **Benchmarks** (for scoring only) — one *investable* series per group (ETF/index; a local money-market rate for cash groups).

## When to use

- "The peer groups aren't homogeneous" / a group's funds don't move together
- Merge / split / dissolve peer categories; isolate misfits (leverage, off-strategy, broken data)
- Extend a return-coherent taxonomy to a new currency or market
- Assign core / satellite / standalone roles, or build the benchmark=50 segment score

## Method (universe-neutral; `scripts/` is the PLN/dm-evo reference to adapt)

1. **Cohesion** — correlation of the returns panel → distance `√[2(1−ρ)]` → per-group avg intra-ρ vs inter-ρ, silhouette, misfit flags. (`scripts/cohesion.py`)
2. **Benchmark-fit (single-benchmark attribution test)** — cohesion asks *do members move together*; this asks the separate Morningstar-style question *can one assigned benchmark attribute all of them*. Regress **each member's periodic return on its group's assigned benchmark series** → collect **R² per fund**; a healthy category = high median R² + low dispersion. Apply **per-asset-class floors** (equity 0.50, mixed 0.40, fixed income 0.30 — FI naturally lower vs a single govt/agg ETF). Then cross benchmark-fit with cohesion into a **quadrant that routes the fix**: high-ρ + low-R² = *wrong benchmark* (re-benchmark, group is coherent); low-ρ + low-R² = *split candidate* (decompose). Cash/mandate-defined groups are exempt (near-deterministic drift → R²≈0 is expected, not a violation — see the traps). (`scripts/benchmark_fit.py`)
3. **Stability gate** — recompute cohesion **and the benchmark-fit R² test** over 2–3 rolling multi-year windows; **act only on a signal (a coherence move *or* an R² violation) that persists in ≥2/3 windows.** This operationalizes Morningstar's 3-year profile-stability rule. Never act on one snapshot. (`scripts/stability.py`)
4. **Decompose** — agglomerative sub-cluster a loose group to name its coherent pieces. (`scripts/subcluster.py "<group>"`)
5. **Classify + map** — merge / split / dissolve / isolate → a per-fund `current → proposed` mapping for human sign-off. (`scripts/reclassify.py`)
6. **Roles** — each parent bucket = **≤1 core + N satellites + 1 Other**. `standalone_eligible` is a **separate flag** from role (broad-market satellites qualify; sectors / themes / single-country / leverage do not). Other = low-confidence quarantine. For core-vs-thematic calls, add a **return-profile role audit**: compare each candidate to broad/style/thematic ETF anchors in the investor risk currency, then use realized vol, drawdown, beta/correlation, and holdings/mandate evidence to decide whether it is a durable building block or a capped narrow return driver.
7. **Benchmark + segment score** — re-center the composite per group so its **benchmark = 50** (separate column; raw composite unchanged). The full scoring method (project the benchmark onto *frozen* funds-only cohort stats, σ-shrinkage for thin groups, neutral ML pillar for the index, benchmark≠median validation) lives in the **fund-scoring** companion skill — use it for the actual scoring. `scripts/segment_score.py` here is the early proxy-composite prototype.

### Return-profile role audit

Use this when the label alone is ambiguous, especially for broad global equity funds that may actually be narrow tech/innovation exposure.

1. Normalize the comparison into the investor risk currency. In dm-evo, PLN funds are compared to USD ETFs converted with NBP `USDPLN`.
2. Use weekly returns over 1Y/3Y/5Y where available; require enough overlap before drawing conclusions.
3. Compare against broad and style/thematic anchors. For EQ_DM, the default anchor set is `URTH`, `SPY`, and `QQQ`.
4. Read the profile, not only the return: annualized return, annualized volatility, max drawdown, return/vol, beta and correlation to anchors, top-holdings concentration if available.
5. Classification rule:
   - **Core / Global Blend**: broad beta substitute; diversified return stream; beta/drawdown reasonably close to broad anchor.
   - **Global Style**: durable factor/style tilt such as value, growth, quality, dividend, or size; may be active and concentrated, but return driver is not a single narrow theme.
   - **Thematic/Sector**: return driver is a named theme/sector/megatrend, or realized beta/drawdown looks like a narrow/high-beta sleeve. Strong returns do not make it core; cap it as satellite.
6. Return-profile output is a review queue. It can confirm current taxonomy, propose a role/L2 adjustment, or mark a stale note; never apply edits automatically.

## Adapting to a new universe

The bundled scripts are wired to dm-evo's schema; the analysis below the loader is universe-agnostic. To run elsewhere, change only the **data-loading seam** at the top of each script:
- the loader fn (`weekly_returns_*` / `load_*`) → your returns panel + grouping map;
- constants: `GROUP_COL` (peer-group column), the **currency/market filter**, `WINDOW` (window length at your frequency), and `DM` / paths (or set `DM_EVO_ROOT`);
- benchmarks: swap the dm-evo registry lookups for your universe's investable series.

## Judgment calls / traps (universe-independent — get these wrong and the analysis lies)

| Trap | Rule |
|---|---|
| **Merge-trap** | A "merge" with negative separation driven by *one* incoherent group is a **dissolve** signal, not a merge. A real merge needs **both** groups coherent (intra-ρ ≳ 0.6). |
| **Replace ≠ augment** | Clustering proposes; a human approves. **Honor economic overrides** — deliberate allocation/risk distinctions stay split even at high ρ (e.g. Gold vs Precious Metals; broad-region/sector tilts). Allocation-structure needs are a legitimate split driver too: dm-evo's PL-FI long block (one ρ-block, intra-ρ 0.87) is deliberately split along the mandate line (treasury vs universal) because the allocation model needs two rungs — both on the same anchor, with the disclosure "cohorts differ by mandate, not co-movement". Cohesion-merge is only for *unintentional* redundancy. |
| **Ladder/tier groups** | Risk-ladder rungs (mixed conservative/balanced/flexible) are inter-ρ ≈ 0.9 — **ρ cannot discriminate tiers**. Place funds on rungs (and set tier anchors) with **realized factor betas** vs the anchor legs (2-factor regression on equity+bond legs); compare realized equity beta to the rung's anchor weight. dm-evo case: "Flexible 60/40" had realized betas 0.08–0.78, majority <0.45 → re-anchored 40/60. |
| **Mandate is a prior, returns are the test** | Declared benchmarks / fund cards generate *candidates*; verify each with own-group-ρ vs proposed-group-ρ over 2–3 stability windows (gate ≥2/3) before moving. The data can correct the destination (a "tech" fund by declared benchmark sat with mid-caps by returns; duration funds proposed for one group ρ-matched another). |
| **Benchmark vs median** | Anchor the segment score on a **real-vol investable benchmark**, not the moving median. Validate **benchmark ≠ median** — else it just re-centres on the median and hides whether the whole group lags its index. |
| **Riskless-cash metrics** | `sortino` / `profit_factor` blow up (÷ downside → ∞) on a no-loss (cash/money-market) series; `info_ratio` does **not**. Guard the no-loss case (cap at group max) or score on excess return. Bounded analogues (ulcer / max-dd) cost ~0.2 rank-corr — usually not worth it. |
| **FX / single-denomination** | Run cohesion **one currency/risk-denomination at a time** (FX-free). For benchmarks: hedged fund vs hedged index, unhedged vs converted. Carry matters for bonds, negligible for equity. **Hedged vs unhedged share classes inside one group make peer-ρ meaningless**: a hedged class can show ρ≈0 to its unhedged peers while tracking the anchor at ρ 0.98 — split or compare per hedge denomination before reading misfits. |
| **Cash-like funds** | Cohesion is **uninformative** for quasi-cash/no-vol funds — ρ≈0 to everything *including the cash anchor* (correlations of near-deterministic drift are noise). Classify them by **mandate**, not ρ. |
| **Catch-all buckets** | "Other / Misc / Specialist" grab-bags (ρ ≈ 0.4) aren't peer groups — decompose into coherent satellites + a thematic tail; don't peer-score across them. |
| **Single-currency R² conflation** | A low benchmark-fit R² computed in **one risk currency** conflates three different problems: (i) a genuinely *wrong benchmark*, (ii) a *hedge-denomination mismatch* inside the group (a PLN-hedged member vs an unhedged benchmark FX-converted to PLN — FX noise alone can drop R² to near-zero), and (iii) real *active dispersion* (flexible/absolute-return mandates). **Never declare a violation on R² alone.** Disentangle with the cohesion cross-check: **high ρ + low R² = benchmark problem** (re-benchmark), **low ρ + low R² = grouping problem** (split). Before splitting an FI/mixed group on low R², re-run the fit **per hedge denomination** (hedged member vs hedged index, unhedged vs converted) — dm-evo's "Global Core Bonds" and "EM Bonds" looked incoherent only because they pooled hedge classes; the ccy-suffixed siblings score 0.9+. |

## Reference (bundled — PLN/dm-evo worked example)

- `references/taxonomy_final_pln.yaml` — a complete worked output: final groups + benchmarks + roles + the scoring architecture (raw composite + segment-score spec) in `::meta`. **Copy this structure for a new universe.**
- `references/findings.md`, `references/proposal.md` — narrative + the stability-gated proposal.
- `scripts/*` — the reference implementation (read, then adapt the loader seam). `scripts/benchmark_fit.py` = the single-benchmark R² attribution test + coherence×fit quadrant (method step 2); `scripts/eqdm_return_profile_audit.py` = the dm-evo EQ_DM core/style/thematic role audit; `scripts/quality_metric_candidates.py` = the metric-robustness study behind the no-loss-guard; `scripts/fi_pl_universal.py` = a worked per-fund reclassification.
- A full **final-sweep audit** worked example (candidate verdicts over 3 stability windows, mixed-group beta sweep, anchor ρ-tests) originated in the lab research line: `research/selection-l2-taxonomy/classification_audit.py` + `reclassification_candidates.md` (2026-06-11 — 15 confirmed moves, 6 proposals overturned by the return test). Treat that as background only; production taxonomy sources live in `config/taxonomy/`.
