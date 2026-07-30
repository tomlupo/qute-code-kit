# PLN allocation-group taxonomy — quant cohesion proposal

**Status:** prototype / proposal for advisor finalization (propose-to-human governance).
**Snapshot:** 2026-05-08, 537 PLN funds, 3Y W-FRI weekly log returns, FX-free (all PLN).
**Method:** Pearson correlation → Mantegna distance `d=√[2(1−ρ)]`; per-group avg
intra-ρ; group-pair between-ρ (merge); within-group agglomerative sub-clustering
(split); per-fund best avg-ρ to any L1 group (isolate). Code: `cohesion.py`,
`propose_taxonomy_pln.py`. Not auto-applied — advisor finalizes the xlsx.

## Reading rule (avoids the merge artifact)

A genuine **merge** needs *both* groups coherent (intra-ρ ≳ 0.6) and small
separation. A pair with negative separation where one side has low intra-ρ is a
**dissolve/split** signal for the incoherent group, NOT a merge.

## Per-L1 proposal (allocation sleeves)

### FI_PL — Polish bonds
- **PL Govt Bonds PLN** — ρ **0.863**, tightest group in the whole universe. Keep. De-facto **core** (coherent + foundational).
- **PL Universal Bonds PLN** — ρ **0.497**, intra < inter (funds correlate *more* with the rest of FI_PL than with each other). **Dissolve/split**: reclassify members by behaviour — govvy-like → fold toward govt/aggregate core; credit-like → credit sleeve.
- ⚠️ Resolves the earlier "broadest wins" tension: the "broad" universal-bond group is not a coherent group, so per-L1 the **coherent** core for FI_PL is govvies.

### FI_GL — global bonds
- **Global Core Bonds PLN** — ρ **0.519**, splits into one dominant 29-fund cluster (ρ 0.75) + small tight outliers. **Split**: extract the dominant core; review the small clusters.
- **PIO87, PCS54** — ρ ≈ −0.06 to a bond group → **investigate as data quality** (off-strategy or broken series), candidate isolates.
- IG Corporate Bonds PLN (n=4, ρ 0.719) — thin but coherent; keep.

### FI_CREDIT — EM Debt PLN (0.695), HY Bonds PLN (0.736)
- Both coherent and distinct. Keep.

### EQ_DM — developed equity
- **Global DM Equity** (n=67, ρ 0.641) — broad **core** candidate.
- **US Equity** (ρ 0.654) ↔ Global DM between-ρ 0.625 — heavy overlap (Global DM is US-heavy). Decide whether US is a distinct sleeve or part of the DM core.
- **European Equity** (0.761), **Technology** (0.691), **Miners** (0.808) — coherent satellites; Technology/Miners stay separate regardless (sector caps per `allocation.yaml::sector_equity_l2`).
- **Other Sectors** (n=21, ρ **0.376**) — grab-bag. **Dissolve** into real sectors / isolate.

### EQ_EM — emerging + Polish equity
- **EM Broad Equity** (0.805) — coherent EM **core** candidate.
- **PL Equity** (0.725) + **PL Equity Small Mid** (0.769) — between-ρ 0.690 → genuine **merge candidate** (or keep as a deliberate size split).
- **EM Other Equity** (n=23, ρ **0.393**) — grab-bag. **Split** into the 4 tight subclusters found (ρ 0.77–0.84; single-country/region EM tilts).
- **QRS07** — ρ −0.85, confirmed **leverage fund** → **isolate** (own group, singleton OK).

### MIX
- MIX_DEF: Mixed PL Conservative (0.801) tight; Mixed GL Conservative (0.695) ok. Keep.
- MIX_AGR: Mixed GL Flexible (0.695) + Mixed PL Flexible (0.608) — between-ρ 0.595, **merge candidate**.

### COM
- **COM_GOLD: Gold (0.751) + Precious Metals (0.697)** — between-ρ 0.670 → **merge** (effectively the same exposure).
- COM_BROAD Commodities (0.558) — loose; review.

## Caveats / open

1. **Single snapshot.** No rolling-window stability yet (task #5). Lock nothing until splits/merges persist across windows.
2. **ISOLATE floor 0.45 over-flags** (55 funds, many ALT_ABS). True singletons have ρ→0/negative to *everything* (QRS07, PIO87, PCS54). The 0.20–0.45 band = loose members of loose groups → tighten the parent, don't isolate. Recommend a true-isolate floor ≈ 0.20.
3. **PLN ≠ single FX axis.** Within PLN there are PLN-hedged (FX-neutral) and PLN-denominated-USD-exposed (unhedged) share classes. Some EQ_DM "splits" (US Equity 3-way) may be a *hedging* axis, not a strategy axis — confirm before splitting.
4. **ALT_ABS / "Other"** low cohesion is by design (idiosyncratic strategies); not a fixable taxonomy error — out of allocation focus.
5. Thresholds (SEP_MARGIN 0.05, SPLIT_CUT 0.65, ISOLATE 0.45) are heuristic — tune with advisor.

---

## FINAL — stability-gated recommendation (`stability.py`)

Signals recomputed across **3 trailing 156w windows** ending 2026-05-08, 2025-05-09,
2024-05-10. Only signals persisting in **≥2/3 windows** survive. Isolate floor
tightened to ρ<0.20 (true singletons). Genuine merge requires *both* groups
coherent (intra-ρ ≥ 0.60).

### A. Confident — act now (mechanical-safe, all persisted)
| Group | Signal | Persistence | Action |
|---|---|---|---|
| EQ_EM **EM Other Equity** (0.385) | incoherent + splits | **3/3** | dissolve → 4 tight subclusters |
| FI_GL **Global Core Bonds PLN** (0.513) | incoherent + splits | **3/3** | extract dominant core (29 funds, ρ 0.75); review outliers |
| FI_PL **PL Universal Bonds PLN** (0.506) | incoherent | persistent | reclassify members by behaviour |
| EQ_DM **Other Sectors** (0.414) | incoherent + splits | 2/3 | dissolve into real sectors |
| COM_GOLD **Gold + Precious Metals** | redundant (both coherent) | **3/3** | merge → one group |
| Isolates: **QRS07** (leverage), **PCS54, PIO87** (FI_GL off-strategy/data), **ABS011_AH_PLN**, **AGF04** | ρ<0.20 to all | **3/3** | own singleton group |

### B. Judgment-required — quant says MERGE but allocation intent may override
The stability gate found the entire **EQ_DM developed-equity complex merges 3/3**:
Global DM ↔ US ↔ Technology ↔ European are not separable by returns. **But these
are deliberate regional/sector allocation levers** (Tech/Miners carry tighter caps
per `allocation.yaml::sector_equity_l2`). High correlation is expected and does
NOT mean they should collapse — merging would destroy the ability to tilt
regionally/by-sector. **Do not auto-merge; advisor decides.** Same class:
- EQ_EM PL Equity + PL Equity Small/Mid (3/3) — deliberate size split
- MIX_AGR Mixed GL + PL Flexible (2/3)
- FI_PL_SHORT PL Corp + PL Govt Short Term (2/3) — credit vs govt, may stay distinct

**Lesson:** cohesion-merge is valid for *unintentional* redundancy (Gold+Precious
Metals), invalid for *intentional* distinctions. Dissolve-incoherent and isolate
are the unambiguous wins; merges need the allocation lens.

### C. Keep — stable-strong, no signal
COM_BROAD; EQ_DM Miners; EQ_EM EM Broad; FI_CREDIT EM Debt + HY; FI_GL IG Corp;
**FI_PL PL Govt Bonds (ρ 0.864 — coherent core);** MIX_DEF (both).

Artifacts: `pln_actions_final.csv`, `pln_proposed_mapping_final.csv`,
`pln_stability_groups.csv`.
