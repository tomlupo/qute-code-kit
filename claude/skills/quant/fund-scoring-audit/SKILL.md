---
name: fund-scoring-audit
description: Use when reviewing a benchmark-anchored fund score (benchmark=50 / score_evo) for correctness — symptoms like "are the top/bottom scores right?", "why does fund X score so high/low?", "is this fund classified / benchmarked correctly?", a fund topping or bottoming a group that looks wrong, a suspiciously extreme or thin-group score, or sanity-checking scores before they reach an advisor. Closes the loop after fund-classification + fund-scoring. Universe-agnostic; a PLN/dm-evo reference is bundled.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Fund scoring audit — is this score real, or an artifact?

## Overview

The **extremes** of a benchmark-anchored score (`score_evo`) are disproportionately
**artifacts** — a fund is rank 1/N or N/N *because it is in the wrong group or against
the wrong benchmark*, not because of skill. Auditing = **decompose** each extreme into
its parts, **attribute** the cause, **verify** with an independent test, and emit a
**gated fix** that flows back to the companion skills. It proposes; a human disposes.

**REQUIRED COMPANIONS:** regroup fixes use **fund-classification**; re-anchor / σ fixes
use **fund-scoring**. This skill consumes their output and feeds fixes back.

## When to use

- "Are the top/bottom scores right?" / "why does fund X score so high/low?"
- A fund tops or bottoms a group and the result looks off
- An extreme or thin-group (`low_confidence`) score before it reaches an advisor
- A score that contradicts the fund's known nature (a value fund beating a hot index)

## Inputs

- The **score table**: per fund `score_evo`, `score_i` (composite vs peers), `score_B`
  (benchmark composite), `σ_g`, group, benchmark, flag, cohort `n`.
- A **returns panel** (for the verification regressions) + the **benchmark series**.
- **Fund documents** (high-yield audit source): the fund card / KID PDF (declared
  benchmark, investment policy, success fee, liquidation clauses) + the platform feed's
  card fields. dm-evo: `fund_data_evo` carries `cardlink`/`kiidlink` (dokumenty.analizy.pl,
  fetchable + PyMuPDF-extractable per fund) and a `benchmark` (declared) column.

## Method

1. **Pull the extremes** (top/bottom by `score_evo`, or the named fund). For each,
   note `score_i`, `score_B`, `σ_g`, `n`, group, benchmark, flag.
2. **Decompose BEFORE judging** — `evo = 50 + (score_i − score_B)/σ_g × MULT`
   (`MULT` = points per within-group std, ≈15, set by the scoring engine; so
   `(score_i − score_B)/σ_g` is how many std the fund sits above/below its benchmark —
   e.g. evo 81 ⇒ ≈ +2σ). A high evo is NOT automatically "good fund". Split it: is it
   `score_i ≫ score_B` (fund beats benchmark), or a **low `score_B`** (easy/wrong
   benchmark), or a **tiny `σ_g`** (thin-group amplification)? Same three suspects for low.
3. **Attribute to a cause** (run the matching test):

   | Cause | Tell | Verify |
   |---|---|---|
   | **Misclassified** | asset/sub-type ≠ group (convertible-as-credit, healthcare-as-tech, balanced-as-conservative) | factor-regress: duration = beta to a rate/bond index; equity-weight = beta to equity-vs-bond. For **region/style use UNIVARIATE ρ / corr_gate per candidate, NOT a joint regression** — regional/style indices are ~0.9 collinear, so joint betas are unstable and mislead. Does behaviour match the group? |
   | **Wrong benchmark** | right group, wrong anchor (onshore vs offshore, global blend for local funds, fee-free rate vs investable ETF) | **correlation-gate**: ρ(fund, assigned anchor) vs ρ(fund, alternative). Adopt the alternative only if ρ ≥ incumbent. |
   | **Thin-group σ** | small `n` (below min-peers, commonly 8), tiny `σ_g`, extreme tail | does the all-currency cohort (mixed cats) or σ-shrinkage toward the parent σ tame it? |
   | **Mandate mismatch (from documents)** | declared benchmark / investment policy diverges materially from the scoring anchor (a WIBOR-mandate fund vs a duration anchor scores +2σ on duration mismatch, not skill; a broad-region mandate vs a single-country anchor) | pull the fund card; compare declared vs anchor; then **return-test the candidate move** (own-ρ vs proposed-ρ over stability windows) — the card is a prior, not a verdict |
   | **Structural (not a score fix)** | ETF-wrapper funds (card shows 70–95% in index ETFs at full active fee), feeder/master share-class duplicates, liquidation clauses, strategy-change track breaks (3Y metrics non-comparable), feed-vs-card data discrepancies | flag for pool treatment / dedup / data fix — the score is "right", the fund's pool status is the issue |
   | **Genuine** | classification + benchmark correct; score reflects real **risk-adjusted** performance | confirm and STOP — do not "fix" a real result. Worked case: a corporate-bond fund's gold tier vs a govt anchor *looked* like credit-carry artifact; ρ-test (govt anchor 0.84 > cash 0.67) proved real duration — anchor kept. |

4. **Gate the fix.** Re-anchor only if **correlation-gated**. Regroup only if the new
   group clears **both** gates: ≥ min-peers (commonly 8) AND an investable benchmark
   exists — else it is an **L3 presentation tag, not a scoring split**. **Reuse** an
   existing sourced benchmark series before building one.
5. **Emit verdict + gated fix** per fund: cause · evidence · fix (regroup →
   fund-classification; re-anchor / σ → fund-scoring; or L3 tag) · does it change
   *selection*? Keep `score_i` untouched; re-run scoring; confirm the faithfulness gate
   (e.g. Gate A) still holds.

## Traps (the ways an audit lies — each cost me a wrong call)

| Trap | Rule |
|---|---|
| **Judge before decompose** | "High evo = good" is wrong — it can be an easy benchmark or a thin σ. Always split `score_i` / `score_B` / `σ_g` first. |
| **Return ≠ skill** | A fund with *higher total return* can correctly score *lower* (more duration/vol for the same return). Check risk (vol, factor beta) before calling a low score wrong. |
| **Backfire = deeper bug** | If a narrow fix makes the score WORSE (a carve-out → ~100), there is a bigger mismatch underneath (e.g. local funds on a global benchmark). Diagnose the root, don't paper over. |
| **Ungated anchor swap** | Never swap a benchmark on a hunch — correlation-gate it (ρ ≥ incumbent) or you trade one artifact for another. |
| **Split vs tag** | A real distinction (duration, style, region) becomes a *scoring* group only if it clears ≥min-peers AND has a benchmark; otherwise it is a presentation tag. A continuum with no cluster and no benchmark is not a split. |
| **Units / scale** | Verify a threshold's units against the data before trusting buckets (a vol cut of "3" means 0.03 if vol is decimal). One mis-scaled constant silently mislabels everything. |
| **Reuse before sourcing** | Check the benchmark registry / upstream data sources before constructing a series — a naive reimplementation misses domain nuances (policy changes, seam dates). |
| **Currency cohort** | For currency-mixed categories derive the score over ALL currencies (present one); the σ + benchmark peers must match the basis the composite was built on. Carry-segmented (FI) stays per-currency. |
| **Hedge-class artifact** | A fund with ρ≈0 to its *peers* but ρ≈0.98 to its *anchor* is not misfit — it's a hedged share class among unhedged peers (denomination artifact). Fix the cohort comparison, not the anchor. |
| **Marketing in documents** | Fund cards are marketing: use only factual content (policy, declared benchmark, fees, dates, clauses); ignore awards/superlatives. Liquidation clauses and policy-change dates hide in KIDs — read them, they invalidate scores silently. |

## Reference (bundled — PLN/dm-evo worked example)

- `scripts/audit_score.py` — the reusable helpers: `decompose()` (pull score_i/score_B/σ/n
  per fund or extremes), `factor_fit()` (duration / equity-weight / region betas), and
  `corr_gate()` (anchor ρ vs alternatives). Read it, adapt the dm-evo loader seam.
- The companion **fund-scoring** skill bundles the scoring engine (`score_evo.py` /
  `score_evo_v2.py`) this audits; **fund-classification** bundles the regroup tooling.
