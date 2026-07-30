"""Strip spurious demand out of n_funds_primary.

The raw count is every fund whose argmax correlation lands on a benchmark. That
over-counts badly: fixed-income funds with no adequate benchmark anywhere get dumped onto
whatever correlates marginally, which is how FTSE 250 collected a China RMB bond fund at
rho 0.36 and looked like it served 6 funds when it serves 1.

Two filters, both needed:
  rho floor        - an assignment below 0.75 is not a classification
  asset-class match - an FI fund assigned to an equity benchmark is a mis-assignment
                      regardless of how high the correlation happens to be

Emits n_funds_primary_clean plus a contamination diagnosis per benchmark.
"""

import pandas as pd

SCR = "scratch/etf-audit"
RHO_FLOOR = 0.75
XLS = f"{SCR}/BENCHMARK_REGISTRY.xlsx"

fit = pd.read_csv(f"{SCR}/v8_fund_fit.csv")
reg = pd.read_excel(XLS, sheet_name="Registry Top100")
full = pd.read_excel(XLS, sheet_name="FULL UNIVERSE + findings")

# benchmark asset class implied by tier; L7 carries both PL equity and PL bonds
tier_class = {
    "L1 Market": "EQ",
    "L2 Style Axis": "EQ",
    "L3 Sector": "EQ",
    "L4 Real Asset": "COM",
    "L5 Crypto": "ALT",
    "L6 Fixed Income": "FI",
}
bench_class = {}
for _, r in reg.iterrows():
    if not isinstance(r["isin"], str):
        continue
    # asset class of the INSTRUMENT, not of the tier it is filed under:
    # gold-mining ETFs are equity funds even though they sit in the Real Asset tier
    if r.tier == "L7 Local PL":
        cls = "FI" if any(k in str(r.concept) for k in ("Bond", "TBSP", "Government")) else "EQ"
    elif r.tier == "L4 Real Asset":
        cls = "EQ" if "Miner" in str(r.concept) else "COM"
    else:
        cls = tier_class.get(r.tier, "?")
    bench_class[r["isin"]] = cls

fit["fund_class"] = fit.group.astype(str).str[:2].replace({"CO": "COM", "AL": "ALT"})
fit["fund_class"] = fit.group.astype(str).apply(
    lambda g: (
        "FI"
        if g.startswith("FI")
        else "EQ"
        if g.startswith("EQ")
        else "COM"
        if g.startswith("COM")
        else "ALT"
    )
)
fit["bench_class"] = fit.best_isin.map(bench_class)
fit["class_match"] = fit.bench_class.eq(fit.fund_class) | (
    fit.fund_class.eq("COM") & fit.bench_class.eq("EQ")
    & fit.best_name.astype(str).str.contains("Miner|Mining", case=False))
fit["strong"] = fit.cover_rho >= RHO_FLOOR
fit["counts_clean"] = fit.strong & fit.class_match.fillna(False)
fit.to_csv(f"{SCR}/v11_fund_fit_scored.csv", index=False)

clean = fit[fit.counts_clean].best_isin.value_counts()
raw = fit.best_isin.value_counts()
weak = fit[~fit.strong].best_isin.value_counts()
mism = fit[fit.class_match.eq(False)].best_isin.value_counts()

reg["n_funds_primary_clean"] = reg["isin"].map(clean).fillna(0).astype(int)
reg["n_funds_weak_fit"] = reg["isin"].map(weak).fillna(0).astype(int)
reg["n_funds_wrong_class"] = reg["isin"].map(mism).fillna(0).astype(int)
reg["inflation"] = reg.n_funds_primary.fillna(0).astype(int) - reg.n_funds_primary_clean


def diagnose(r):
    if r.n_funds_primary in (0, None) or pd.isna(r.n_funds_primary) or r.n_funds_primary == 0:
        return ""
    if r.n_funds_primary_clean == 0:
        return "ALL DEMAND SPURIOUS - every assignment is weak or wrong asset class"
    if r.inflation >= r.n_funds_primary_clean:
        return f"HEAVILY INFLATED - {r.inflation} of {int(r.n_funds_primary)} assignments spurious"
    if r.inflation > 0:
        return f"partly inflated - {r.inflation} spurious"
    return "clean"


reg["demand_diagnosis"] = reg.apply(diagnose, axis=1)
# primary score recomputed on the clean count
reg["primary_score"] = pd.cut(
    reg.n_funds_primary_clean, [-1, 0, 4, 14, 10**6], labels=[1, 4, 7, 10]
).astype(int)

for c in [
    "n_funds_primary_clean",
    "n_funds_weak_fit",
    "n_funds_wrong_class",
    "inflation",
    "demand_diagnosis",
    "primary_score",
]:
    full[c] = full["isin"].map(reg.dropna(subset=["isin"]).drop_duplicates("isin").set_index("isin")[c])

with pd.ExcelWriter(XLS, engine="openpyxl", mode="a", if_sheet_exists="replace") as xw:
    reg.to_excel(xw, sheet_name="Registry Top100", index=False)
    full.to_excel(xw, sheet_name="FULL UNIVERSE + findings", index=False)

sel = reg[reg.status.astype(str).str.startswith("ok")]
print(f"rho floor {RHO_FLOOR} + asset-class match")
print(
    f"funds: {len(fit)}  clean assignments: {int(fit.counts_clean.sum())} "
    f"({100 * fit.counts_clean.mean():.1f}%)"
)
print(f"  weak fit (<{RHO_FLOOR}): {int((~fit.strong).sum())}")
print(f"  wrong asset class:      {int(fit.class_match.eq(False).sum())}")
print(
    f"\nraw demand total {int(sel.n_funds_primary.fillna(0).sum())} "
    f"-> clean {int(sel.n_funds_primary_clean.sum())}"
)

print("\n=== rows whose demand was overstated ===")
bad = sel[sel.inflation > 0].sort_values("inflation", ascending=False)
print(
    bad[
        [
            "tier",
            "concept",
            "n_funds_primary",
            "n_funds_primary_clean",
            "inflation",
            "demand_diagnosis",
        ]
    ].to_string(index=False)
)

print("\n=== rows that now have ZERO real demand (were non-zero) ===")
z = sel[(sel.n_funds_primary.fillna(0) > 0) & (sel.n_funds_primary_clean == 0)]
print(
    z[["tier", "concept", "n_funds_primary", "n_funds_weak_fit", "n_funds_wrong_class"]].to_string(
        index=False
    )
)

print(
    f"\nselected rows with clean demand == 0: {int((sel.n_funds_primary_clean == 0).sum())} of {len(sel)}"
)
