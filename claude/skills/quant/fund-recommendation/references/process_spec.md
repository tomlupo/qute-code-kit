# Recommendation & allocation process — rule-based spec (v0.3 draft, 2026-06-11)

Design goal: **rule-based, full allocation always possible, every fund has a pre-approved
replacement; minimize changes, react fast to distress.** Humans approve runs and file
expiring exceptions — they do not pick funds.

## Architecture

```
SCORING (monthly)  →  POOLS (E/W per group, rules)  →  ALLOCATION (engine)  →  APPROVAL (human gate)
                              ↑ distress channel (continuous, bypasses hysteresis)
```

## Pool structure per allocatable group (slots = allocation cells using the group)

- **E (recommended) = 2×slots**: top half = **primaries**, bottom half = **named
  replacements** — all formally recommended, so replacement activation needs no approval.
  ≥1 replacement must come from a non-incumbent TFI (forced diversity).
- **W (gate) = ≥2**: rank-refreshed monthly, no approval weight. E-entry requires
  **W tenure ≥1 month**.
- Entry is **rank-based** (Score vs ETF orders; never an absolute gate — thin/lagging
  groups must still fill). E-members with vs < 50 carry the disclosure column
  *"lags ETF — passive substitute available"* (inPZU proxies where applicable).

## Relative channel (slow — minimizes changes)

| Rule | Setting | Status |
|---|---|---|
| W → E promotion | out-ranks bottom-E for **3 consecutive EoMs** + W tenure ≥1m | validated on PL Govt Bonds YTD (0 trades; 2-month streak and 3m-median variants each produced a round-trip) |
| Replacement → primary | same 3-EoM rank streak (it is a client trade) | same evidence |
| W membership | pure monthly rank refresh (trade-free) | — |

Rank-based hysteresis is scale-free → one parameter across asset classes (re-examine for
equities in the full backtest).

## Distress channel (fast — bypasses hysteresis)

Doctrine: **anticipatory signals freeze; realized signals eject.**
Freezing (stop new money, halt promotions) is instant and costs zero turnover.

| Tier | Trigger (best-guess, to calibrate) | Action |
|---|---|---|
| **L3 hard** | liquidation/gating notice; price stale > 30d; NAV frozen ≥ 8 weeks; KNF action | immediate ejection + client comms |
| **L2 realized** | 2-of-N with ≥1 *realized* signal: 13w return < group median − 2σ_g (crash); 13w ρ to group < 0.30 while 3y ρ ≥ 0.60 (tracking break) | eject from E; in-E replacement steps up same-day |
| **L1.5 anticipatory** | 2-of-N from *anticipatory* only: 3m net flow ≤ −10% or neg-streak ≥ 5m (flow run); P(downside) ≥ 0.35 (ML gate) | **freeze**: no new money, no promotion, review next EoM |
| **L1 watch** | any single signal | flag + monitor |

Coverage invariant: if ejection/veto would leave the group with < 2×slots eligible,
degrade the action one level (eject → freeze) and surface the passive substitute.
Entry is stricter than exit for the same signal (ML ≥ 0.35 refuses E-entry outright;
alone it never ejects an incumbent).

## YTD evidence (2026-01 → 2026-05, evo universe n=255, best-guess thresholds)

- **L3**: 11 funds, all genuinely broken (SPM24 frozen NAV; CAB71/80–83 FIZ stale
  pricing; TEM01/02/03 — TEM03 in liquidation; MCI02; SPM64). Zero false positives;
  all already unscored, so zero E-impact.
- **L2 (2-of-N, any)**: 12–22 fund-months/month, 39 unique funds — too hot as a raw
  ejector, BUT only **10 fund-months collide with hypothetical E pools**, all in thin
  groups (Asia, India, HY, European) where top-4 = whole group, and all with weak vs
  (17–50). Zero collisions with genuinely strong funds.
- Under the anticipatory/realized doctrine, YTD **forced E-trades from distress ≈ 0**
  (all collisions were flow+ml → freeze, not eject), while every true wreck was caught
  at L3. Caveat: ML history unavailable — current-month flags applied statically
  (upper bound on ML-driven counts).

## Parameters (status ledger)

| Parameter | Best guess | Calibration evidence |
|---|---|---|
| Rank streak (promotion/demotion) | 3 EoMs | PL Govt YTD sim (A/B/C variants) |
| W tenure gate | 1 month | legacy editorial discipline |
| E size | 2×slots; W ≥ 2 | PL Govt: pool of 4 exactly absorbs current vetoes |
| Flow run | 3m ≤ −10% or streak ≥ 5m | YTD scan — sane firing set |
| Crash | < med − 2σ_g (13w) | YTD scan |
| Tracking break | ρ13 < 0.30 & ρ156 ≥ 0.60 | YTD scan |
| Stale / frozen | > 30d / ≥ 8w | YTD scan — exact L3 set |
| ML gate | P ≥ 0.35 entry-veto; anticipatory in confirmations | dm-evo calibration (Q4-avoid 0.95) |
| TFI diversity | ≥1 non-incumbent-TFI replacement | Rockbridge×3 case in PL Govt |

Full calibration backtest (distress-event label set + threshold sweep vs turnover) is the
promotion gate for v1.0; everything above is the operating draft until then.
