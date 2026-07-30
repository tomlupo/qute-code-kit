---
name: fund-allocation
description: Use when turning a scored, recommended fund universe into PORTFOLIO WEIGHTS via a core/satellite construction per L1 — designating cores (broad, high-ρ anchors) vs satellites (concentrated tilts), filling the SAA L1 budget core-first, capping satellites small, and steering tilt selection toward true diversifiers. Codifies the SOFT allocation policies (correlation rule-of-thumb, pinned cores, score basis, suitability caps) that sit on top of the hard structure. Completes the chain after fund-classification (peer groups) → fund-scoring (EVO Score) → fund-recommendation (E/W pools). Rule-based, NOT optimized. Universe-agnostic; a PLN/dm-evo reference is bundled. See ADR-0007.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Fund allocation — core/satellite construction per L1

## Overview

Turn a scored, recommended fund universe into **portfolio weights** by building
each L1 (asset/TAA category) as a **core + satellites**:

- **Core** — the broad, cheap, high-ρ-to-benchmark holding(s) you would default to.
  Goes **first** and takes the majority of the L1 budget.
- **Satellites** — concentrated tilts (sector / geography / duration / credit),
  each **hard-capped small**, included only when they **add diversification**.

This is **rule-based, not optimized** (ADR-0007): the SAA fixes L1 budgets; rules
construct within each L1; **humans veto by exception**. We deliberately do **not**
run a portfolio optimizer — risk-optimization is a deferred, backtest-gated v2 that
would only ever size the satellite budget, never the core.

Companion to **fund-recommendation** (E/W pools feed the eligible set) and
**fund-scoring** (the EVO Score that ranks funds). A complete PLN/dm-evo reference
is in `scripts/core_satellite_alloc.py`.

## The distinction that matters: hard structure vs soft policy

**Hard structure (enforced):**
- SAA L1 budgets are respected exactly; weights are 5pp grid-aligned and sum to 100%.
- **Core first** (up to 3 funds, each ≤20% — no single-fund overflow), then ≤2
  satellites; leftover budget **spills back into the core** (fewer funds, no sub-cap dribs).
- Per-fund cap 20%; satellite cap 10% (5% for narrow/high-SRI); SRI suitability caps.
- **EVO universe only** (`is_evo=True`). **AUM/NAV floors:** HARD 25mln (excluded
  unless explicitly overridden), SOFT 50mln (allowed but flagged — prefer larger).

**Soft policy (rules of thumb — rules PROPOSE, the advisor DISPOSES):**
A "rule of thumb" is **not** a hard rule. The engine applies it as the *default*
and **surfaces the trade-off** so a human can override; every override is logged.

1. **0.80 correlation diversifier rule.** A satellite correlating **> 0.80** (3y
   weekly returns) with an already-picked holding is **flagged redundant**; the
   budget is steered by default to a lower-correlation alternative — **but the score
   given up is shown and the pick is overridable**. (A high-scoring redundant tilt
   may still be chosen if its score edge justifies the lost diversification.) It is
   NOT a hard gate; do not silently drop.
2. **Pinned cores (per L1):**
   - `EQ_DM` → **two cores**: Global DM Equity + US Equity (US is the dominant DM market).
   - `EQ_EM` → core is **EM Broad Equity** (NOT Asia, even if Asia outscores it — Asia
     is a regional satellite).
   - `FI_GL` → Global Core Bonds; `FI_PL` → PL Government Bonds; `FI_PL_SHORT` → PL
     Govt Short; `COM_*` → the single broad fund.
   - `FI_CREDIT` → **all-satellite, no core** (it is a tilt sleeve by nature; appears
     only in P2 at small weight). Cap members narrow.
3. **Score basis = EVO Score (`score_i`).** Rank/select on the raw within-peer
   composite. **Score-vs-ETF is a SOFT signal, not a gate** — carry it for context.
   When per-group investable ETFs become available it is promoted to a hard quality
   floor (core must beat its ETF; satellites a higher bar). Until then, no hard floor.
4. **TFI house cap 35% (soft).** If a fund house exceeds 35% of a profile, swap its
   lowest-conviction holding for the next-best same-L2 fund from another house
   (corr-respecting). If no alternative exists, **the cap yields** (allocation
   possibilities win) and the breach is flagged — never block the allocation to honour it.
5. **Convertibles caution.** In cautious profiles, a convertible-bond fund topping the
   credit sleeve is equity-like; flag the risk mismatch rather than silently allocating.
6. **Country/region soft guardrail (optional).** The 0.80 corr rule is not a country
   cap — two distinct same-country sleeves can both pass if mutually < 0.80. Layer a
   single-country ceiling on top only if wanted.

All soft-policy thresholds (`CORR_SOFT`, `CORE_SHARE`, `TFI_CAP`, `AUM_HARD/SOFT`,
caps, pinned cores) are parameters at the top of the reference script — tune per
universe, don't hardcode in logic.

## The override layer — the advisor's last call

The algo delivers the **mechanical default**. The investment advisor then applies
**documented overrides** with rationale (who / what / why, logged for audit) — e.g.
allowing a house above 35%, keeping a redundant-but-higher-scored satellite, including
a sub-25mln fund, or overriding a pinned core. Defaults are tuned so overrides are the
**exception, not the rule**. The skill's job is the defensible default; the human owns
the exceptions.

## Caveat — the allocator is only as good as the tags

This layer consumes `alloc_role` (core/satellite) and L2/L1 classification. A
2026-06-19 spot-check found the EVO `core` tags polluted with theme/style/size tilts
(climate/ESG/value/growth/small-cap funds tagged as broad "Global DM"/"EM Broad"
cores), plus FI convertibles/short-duration mislabels. If the "broad core" picks look
like theme funds, audit the upstream tags — it is not an allocation bug. See
`research/selection-l2-taxonomy/2026-06-19-core-satellite-allocation-experiment.md`.

## Inputs (bring these for any universe)

- **Scored universe**: per-fund EVO Score (`score`/`score_i`), currency, L1/L2,
  `alloc_role` (core/satellite), Score-vs-ETF (soft), SRI. (dm-evo: `scores.parquet`
  + `fund_mapping.csv` + `score_vs_etf.parquet`.)
- **SAA L1 budgets per profile** (the L1 weight each profile allocates).
- **Return history** for correlations (≈3y weekly) to apply the 0.80 rule.
- **E/W pools** from fund-recommendation (the eligible set per L2), if available.

## Process

1. **Resolve L1 budgets** per profile from the SAA.
2. **Per L1, core first:** allocate `core_share · budget` to the pinned core(s)
   (top EVO-Score fund in each core L2), per-fund-capped, top-heavy.
3. **Fill satellites** from the remaining budget: walk satellite L2s by EVO Score,
   one fund per L2, applying the **soft 0.80 diversifier policy** (flag + steer,
   overridable) and satellite caps; residue → core anchor.
4. **Surface, don't suppress:** emit the redundancy flags + the score given up, the
   soft Score-vs-ETF signal, and any convertibles/country warnings for advisor review.
5. **Round** to the 5pp grid; confirm the profile sums to 100%.

## Reference implementation

`scripts/core_satellite_alloc.py` — runs the full construction on the PLN/dm-evo
universe: per-L1 candidate tables, per-L1 correlation matrices, P1–P5 portfolios,
the soft de-prioritization report (with score given up), and a diff vs the
current-dev engine. Read-only; reads dm-evo production inputs.

## Anti-patterns

- ❌ Treating the 0.80 corr rule as a hard gate (it's soft — flag + override).
- ❌ Letting score alone pick the EQ_EM core (pin EM Broad; Asia is a satellite).
- ❌ Gating on Score-vs-ETF before per-group ETFs exist (soft signal only, for now).
- ❌ Running an optimizer (deferred v2; this layer is rule-based by decision — ADR-0007).
- ❌ Uncapped satellites or satellites placed before the core.
