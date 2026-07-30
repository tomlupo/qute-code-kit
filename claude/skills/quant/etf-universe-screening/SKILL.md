---
name: etf-universe-screening
description: >-
  Screen a large ETF universe down to a curated benchmark registry for fund
  classification — select the best LISTING per exposure, organize into tiers,
  and score by coverage/style/semantics. Use when building or refreshing a
  "top-N benchmark dictionary" from a raw ETF list (e.g. lista-etf xlsx),
  choosing which ETF represents each index, deduping share-class clones, or
  deciding coverage vs canonical completeness. Triggers: "benchmark registry",
  "top 100 ETFs", "which ETF for this index", "benchmark dictionary", "screen
  the ETF universe", "pick the reference ETF".
---

# ETF Universe Screening → Benchmark Registry

Turns a raw ETF universe (thousands of listings) into a curated set of ~100
benchmarks for a fund-classification / benchmark-selection engine. The output is
a *registry*: one row per market exposure, each resolved to the single best
listing, organized into tiers and scored on independent axes.

The reference build is `scratch/etf-audit/` (v10 build, v11 clean-demand, v13
canonical audit) producing `BENCHMARK_REGISTRY.xlsx`. Read those scripts before
re-implementing — they encode every rule below.

## The one idea that reframes everything

**A benchmark registry is a dictionary of EXPOSURES, not a list of ETFs.** Each
concept (MSCI World, Gold, EUR IG Corp) appears once; the job is picking which
*listing* represents it. Two funds at ρ=0.98 are the same dictionary entry.
Conflating exposure-selection with listing-selection is the root of most errors.

## Non-negotiable requirements (the user's flagged needs)

These are the rules that were learned the hard way on this project. Violating any
one produced a wrong registry that had to be caught by hand.

1. **Screen the FULL universe, never a pre-curated shortlist.** Letting funds
   choose a benchmark from an already-filtered list bakes in the curation —
   "no benchmark fits" becomes indistinguishable from "the right one was filtered
   out." Price and evaluate all ~2,285.

2. **Coverage saturates early (~40 benchmarks).** Measure it (greedy set-cover,
   marginal-gain curve). Past the knee, adding benchmarks buys ~nothing in fit.
   Spend the remaining slots on canonical/semantic completeness, not more
   coverage. Hitting exactly N is cosmetic — say so.

3. **It is NOT only about demand — it is about benchmarking.** A canonical index
   (World Momentum, UK Gilts, Obligacji 6M) earns its slot even with zero funds
   assigned to it. Score demand and semantics as SEPARATE axes; never trim a
   canonical row on a demand number.

4. **Fixed income: correlation is the WRONG yardstick.** FI funds are benchmarked
   by mandate/duration/currency, not return correlation. Mark FI demand "not
   applicable." Critically: WIBOR floaters and PL corporate paper have NO ETF —
   those need non-ETF series (GPW Benchmark). Don't try to fix FI with more ETFs.

5. **"Hedged" UCITS share classes hedge to EUR/GBP, never PLN.** An unhedged USD
   bond ETF in PLN terms is largely an FX series (ρ~0.99 to USDPLN). Require
   hedged share classes for FI; flag that residual EUR|PLN risk always remains.

6. **Prefer the biggest-AUM listing — but only as a TIEBREAK.** Canonicity comes
   first (physical > synthetic, accumulating > distributing, broad > maturity-
   slice, natural-currency > hedged-equity). AUM breaks ties among equally
   canonical candidates. Make it strictly lexicographic so a large distributing
   fund never beats a smaller accumulating one. AUM/replication/distribution come
   from the atlasetf scrape, not from parsing the fund name.

7. **Currency follows the underlying.** USD default; EUR/GBP/PLN/JPY where the
   market is local. For unhedged listings this is cosmetic (FX cancels back to
   PLN) but keeps the registry readable.

8. **Name-based auto-resolution is FRAGILE — always audit the picks.** This build
   produced wrong picks (World→HealthCare, World→ex-Europe, S&P500→PEA wrapper,
   TIPS→10y-GBP-hedged) that only human spot-checks caught. Run a canonicity
   audit, eyeball the core rows, and expose a `PIN` override (concept→analizy
   code) for exposures the data resolves wrongly or where a specific listing is
   preferred for reasons the data can't see (liquidity, provider).

## Workflow

1. **Load** the raw universe xlsx (`kod_jednostki`, `nazwa_jednostki`, `isin`).
2. **Price** every ISIN (EODHD; resumable, checkpoint per row). See
   `scripts/full_pull.py` pattern in `scratch/etf-audit/`.
3. **Enrich** with AUM/TER/replication/distribution via the `atlasetf-scraper`
   skill (`fund_size` is AUM in PLN; `replication_name_lang`,
   `distribution_policy_lang` are clean fields).
4. **Convert** to PLN weekly returns; **dedupe** clones (ρ≥0.98) keeping the
   longest-history representative.
5. **Coverage**: greedy set-cover over the fund population → the ~40 that matter,
   plus a saturation curve so you can SEE the knee.
6. **Concepts + tiers**: define the exposure list (see `references/tiers.md`),
   resolve each to its best listing via a canonicity-first quality score with
   AUM as tiebreak, honoring `PIN` overrides.
7. **Score** three axes — Primary (clean demand, equity only), Style (long-short
   tilt regression), Semantic (expert canonicity). Keep them separate.
8. **Audit** every pick for non-canonical listings; fix or PIN. Verify a core-
   index checklist (World, S&P500, EM, Gold, Treasury, TBSP, …) is all present.
9. **Emit** one workbook: a Registry sheet AND a single FULL-UNIVERSE sheet where
   every non-selected ETF carries a `why_not_selected` reason (clone / lost to
   better listing / excluded by rule / no price / unhedged variant). The flat
   sheet is what makes the result auditable — the user reviews it row by row.

## Verifying against a prior selection

If the user has an earlier hand-picked list (a `top50`/`topN` column), report
overlap three ways: exact-ISIN, same-exposure (concept kept, listing differs),
and genuinely-dropped exposures. The middle number is the real agreement; the
gap between exact and same-exposure is pure share-class churn.

## References

- `references/tiers.md` — the 7-tier concept taxonomy and per-tier rules.
- `references/pitfalls.md` — the specific wrong-picks this build hit and why.
- Reference implementation: `scratch/etf-audit/v10_registry.py` (+ v11, v13).
- Companion skills: `atlasetf-scraper` (AUM/fundamentals), `market-datasets` /
  EODHD (prices), `gpw-benchmark-scraper` (WIBOR/TBSP for the FI gap),
  `fund-classification` (the downstream consumer).
