---
name: fund-recommendation
description: Use when building or operating a RULE-BASED fund recommendation & allocation feed on top of a scored, benchmark-anchored fund universe — constructing E/W pools (recommended primaries + pre-approved replacements, watchlist as a staging gate), calibrating promotion/demotion hysteresis to minimize churn, designing a distress channel that reacts fast (freeze vs eject), guaranteeing full allocation coverage with replacement chains and passive fallbacks, or simulating/backtesting an E/W cadence on monthly score history. Completes the chain after fund-classification (peer groups) and fund-scoring (benchmark=50 score). Universe-agnostic; a PLN/dm-evo reference is bundled.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Fund recommendation — rule-based E/W pools + distress channel

## Overview

Turn a scored fund universe into a **recommendation & allocation feed** that is
rule-based end-to-end: **rules decide, humans veto by exception** (logged, expiring).
Two channels with opposite cost asymmetries do the work: a **slow relative channel**
(rank hysteresis — relative shuffling among decent funds is noise) and a **fast
distress channel** (absolute, fund-specific triggers that bypass hysteresis — the
left tail is where waiting is expensive). Companion to **fund-classification**
(peer groups + roles) and **fund-scoring** (benchmark=50 score); a complete
**PLN/dm-evo reference** is bundled in `scripts/` + `references/`.

## Inputs (bring these for any universe)

- **Monthly score panel** — per-fund composite per EoM (any within-peer composite;
  only the *within-group ordering* is consumed, so scale changes don't matter).
- **Peer groups + roles** — from fund-classification: allocatable groups (core /
  satellite), slots per group (how many allocation cells use it).
- **Benchmark-relative score** — from fund-scoring (benchmark=50), for the
  lags-benchmark disclosure and the passive fallback decision. NEVER as an entry gate.
- **Distress data** — monthly net flows, prices (crash / tracking / staleness),
  optional ML downside probability, and an **event register** (liquidation notices,
  gating, regulator action — the one human-fed input).

## Pool structure (per allocatable group; slots = cells using the group)

- **E (recommended) = 2×slots**: top half **primaries**, bottom half **named
  replacements** — all formally recommended, so a replacement activates same-day with
  no approval. Force **≥1 replacement from a non-incumbent manager/TFI** (a
  manager-level event must not invalidate primaries and replacements together).
- **W (gate) = ≥2**: rank-refreshed monthly, carries no approval weight. E-entry
  requires **W tenure ≥1 month** (the staging discipline).
- **Entry is rank-based, never absolute.** The benchmark-relative score orders funds;
  an absolute bar would starve groups where no fund beats the benchmark — yet the
  allocation still needs slots. E-members below benchmark carry a standing disclosure
  ("best available active; lags the index — passive substitute available").

## Relative channel (slow — minimizes changes)

- **Promotion W→E and replacement→primary**: challenger must out-rank the incumbent
  for **3 consecutive EoMs** (rank-based → scale-free, one parameter across asset
  classes). Validated: a 2-EoM streak and a 3m-median rule each bought a spike
  round-trip the 3-EoM streak absorbed (0 trades vs 2). `scripts/ew_cadence.py`.
- **W membership**: pure monthly rank refresh — W changes are trade-free, so churn
  there is costless and keeps the bench warm.

## Distress channel (fast — bypasses hysteresis)

Doctrine: **anticipatory signals freeze; realized signals eject.** Freezing (stop new
money, halt promotions) is instant and costs zero turnover — it is the tool that
reconciles "minimize changes" with "react fast".

| Tier | Trigger family | Action |
|---|---|---|
| L3 hard | liquidation/gating notice, price stale, NAV frozen, regulator action | immediate ejection + comms |
| L2 realized | 2-of-N incl. ≥1 realized: idiosyncratic crash (kσ below group), tracking break (short-window ρ collapse vs long-window base) | eject; in-E replacement steps up same-day |
| L1.5 anticipatory | 2-of-N anticipatory only: flow run, ML downside gate | **freeze** + next-EoM review |
| L1 watch | any single signal | flag |

- **Entry stricter than exit**: the ML gate refuses E-entry outright but alone never
  ejects an incumbent (refusing to buy risk is free; selling costs).
- **Coverage invariant**: if an ejection/veto would leave the group below 2×slots
  eligible, degrade the action one level (eject → freeze) and surface the passive
  substitute. Coverage is the invariant; vetoes are conditional.
- Fallback ladder when a cell can't fill: same-group passive proxy → parent-sleeve
  core E fund → cash.

## Calibration method

Minimize expected forced trades **subject to** P(still holding a distressed fund
after T days) ≤ target. Build a distress-event label set from history (liquidations,
gates, NAV freezes, AUM collapses), sweep trigger thresholds + the 2-of-N rule, plot
false ejections/year vs detection lead time, pick the knee. Until then run the
best-guess set in `references/process_spec.md` (YTD-checked: L3 caught every true
wreck with zero false positives; anticipatory/realized doctrine produced ≈0 forced
E-trades while the raw 2-of-N would have been too hot).

## Judgment calls / traps

| Trap | Rule |
|---|---|
| **Absolute entry bars** | Never gate E-entry on the benchmark-relative level — groups with no benchmark-beater still need slots. Rank in, disclose the lag. |
| **One-dial hysteresis** | Relative noise and distress have opposite cost asymmetries — separate channels, separate speeds. One dial is always wrong on one side. |
| **Short rank streaks** | 2-EoM streaks (and 3m medians) buy head-fakes; monthly cadence needs 3 consecutive EoMs. Distress, not the rank channel, handles genuine breaks. |
| **Distress ≠ low rank** | A #1 fund can be distressed (redemption spiral, manager exit); a last-ranked fund can be healthy (style headwind). Distress triggers are absolute and fund-specific, never rank-based. |
| **Veto-starved groups** | A hard veto that guts a group breaks allocation. Make vetoes coverage-conditional (the dm-evo ML gate flagged 7/12 of one FI group — the pool survived only by luck). |
| **Same-TFI bench** | Without forced diversity, top-of-group can be one manager × 3 (Rockbridge case) — a TFI event then kills primaries AND replacements. |
| **W churn ≠ E churn** | Only primary/replacement-activation changes are client trades. Let W rotate freely; measure turnover only where it costs. |
| **Static-signal backtests** | If a signal has no history (ML), applying today's values backwards overstates persistence — label it an upper bound, don't tune on it. |

## Reference (bundled — PLN/dm-evo worked example)

- `references/process_spec.md` — the full v0.3 rule set + parameter status ledger
  (best-guess vs evidence) + YTD validation results.
- `scripts/ew_cadence.py` — E/W cadence simulator (rank-hysteresis variants A/B/C) on
  a monthly composite panel; adapt the loader seam at the top.
- `scripts/distress_scan.py` — the distress trigger battery (flow run / crash /
  tracking break / staleness / ML) over a fund universe with tier classification;
  thresholds as constants at the top.
