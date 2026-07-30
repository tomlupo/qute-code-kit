# Pitfalls — the wrong picks this build actually hit

Every one of these shipped in a draft and was caught only by a human spot-check.
If you re-run the pipeline, check for each specifically.

## Resolution errors (name-matching is fragile)

| Concept | Wrong pick | Cause | Fix |
|---|---|---|---|
| Global DM Equity | MSCI World **Health Care** | negative-lookahead excluded style words but not sector names | exclude sector terms from broad-market regex |
| Global DM Equity | MSCI World **ex-Europe** | no ex-region exclusion | exclude `ex-europe/ex-usa/ex-uk/...` |
| US Large Cap | Amundi **PEA** S&P 500 (French tax wrapper) | no wrapper exclusion | exclude `PEA` |
| Inflation-Linked | UBS TIPS **10+** GBP-hedged Dis | hedging rule preferred any hedged listing over a better unhedged one | canonicity (broad, Acc) must outrank hedging |
| Broad Commodities | Bloomberg Commodity **ex-agriculture** | no ex- exclusion on commodities | exclude `ex-agriculture/ex-livestock` |
| Global Aggregate | Global Aggregate **Green Bond** | ESG term missed | add `green bond` to exclusions |
| Gold Miners | flagged as commodity, demand collapsed 15→1 | asset class taken from TIER not INSTRUMENT | miners are equity; class follows the instrument |

## Metric errors

- **Raw `n_funds_primary` is inflated.** FI funds with no real benchmark argmax
  onto noise (a China RMB bond fund matched UK equity at ρ0.36). Symptom: a niche
  equity row shows surprising demand. Fix: `n_funds_primary_clean` = ρ≥0.75 AND
  asset-class match; use it only on equity tiers.
- **Pure-demand ranking elects garbage.** Without an eligibility filter, the top
  of the demand ranking is 3x-leveraged ETPs and ESG clones (correlation is
  scale-invariant; daily-reset noise dodges the clone filter). Filter FIRST, rank
  WITHIN eligible.
- **AUM weighted directly overrode canonicity** (a big distributing fund beat a
  small accumulating one). Make AUM a strict tiebreak, not an additive term.

## Compound-name leaks in the exclusion regex

`\bleveraged?\b` misses `LevDAX`; `\bshort\b` misses `WIG20TRsht`. Compound and
abbreviated names slip through word-boundary patterns. Before production, do a
pass for glued forms.

## Process lesson

The concepts and tiers were sound throughout; the **ticker-per-concept was the
soft part** and needed human read-through every round. Build the flat
FULL-UNIVERSE sheet with per-row `why_not_selected` precisely so the user can
audit listing choices — that is what caught all of the above.
