"""Audit every chosen listing for non-canonical picks.

TIPS resolved to a 10+ year GBP-hedged distribution slice and USD Corporate to an
EUR-hedged class. Both were canonical exposures represented by odd listings, because the
quality scorer optimised history/Acc/hedging and never asked "is this the instrument a
professional would name for this benchmark?".

Flags each pick against the properties a benchmark listing should have:
  plain vanilla   - not a maturity slice, not a sub-index
  physical        - swap/synthetic replication is a tracking choice, not a benchmark
  unhedged equity - equity benchmarks are quoted in their natural currency
  accumulating    - Dis introduces distribution timing noise into the series
  major currency  - USD/EUR for global, natural currency for regional
"""

import re

import pandas as pd

X = "scratch/etf-audit/BENCHMARK_REGISTRY.xlsx"
reg = pd.read_excel(X, sheet_name="Registry Top100")
sel = reg[reg.status.astype(str).str.startswith("ok")].copy()

SLICE = re.compile(
    r"\b(\d+\s*-\s*\d+\s*(y|yr|year|m|month)|\d+\+\s*(y|yr|year)?|0-6|short dated|long dated|10\+|15\+|20\+|25\+)\b",
    re.I,
)
SWAP = re.compile(r"\bswap\b|\bsf\b|synthetic", re.I)
HEDGED = re.compile(r"hedged", re.I)
DIS = re.compile(r"\(Dis\)", re.I)
ODD_CCY = {"SEK", "CHF", "JPY", "CAD", "NOK", "DKK"}

rows = []
for _, r in sel.iterrows():
    nm = str(r["name"])
    tier = str(r.tier)
    issues = []
    # a maturity slice is only legitimate when the concept itself names one
    if SLICE.search(nm) and not SLICE.search(str(r.concept)):
        issues.append("maturity slice / sub-index but the concept is broad")
    if SWAP.search(nm):
        issues.append("swap-based (synthetic replication)")
    if (
        HEDGED.search(nm)
        and not tier.startswith(("L6", "L7"))
        and "hedged" not in str(r.concept).lower()
    ):
        issues.append("currency-hedged share class for an equity benchmark")
    if DIS.search(nm):
        issues.append("distributing share class")
    if r.ccy in ODD_CCY:
        issues.append(f"quoted in {r.ccy}")
    if issues:
        rows.append(
            dict(
                tier=tier,
                concept=r.concept,
                name=nm,
                ccy=r.ccy,
                n_alternatives=r.get("n_alternatives"),
                pinned=bool(r.get("pinned", False)),
                issues="; ".join(issues),
                n_issues=len(issues),
            )
        )

aud = pd.DataFrame(rows).sort_values(["n_issues", "tier"], ascending=[False, True])
aud.to_csv("scratch/etf-audit/v13_canonical_audit.csv", index=False)

print(f"selected rows: {len(sel)}   flagged: {len(aud)}")
print(f"clean (no flags): {len(sel) - len(aud)}")
print("\n=== issue frequency ===")
allissues = [i for s in aud.issues for i in s.split("; ")]
print(pd.Series(allissues).value_counts().to_string())
print("\n=== rows with 2+ issues (fix these first) ===")
pd.set_option("display.max_colwidth", 62)
pd.set_option("display.width", 250)
print(aud[aud.n_issues >= 2][["tier", "concept", "name", "issues"]].to_string(index=False))
print("\n=== all single-issue rows ===")
print(aud[aud.n_issues == 1][["tier", "concept", "name", "issues"]].to_string(index=False))
