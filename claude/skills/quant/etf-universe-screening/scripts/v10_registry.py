"""Final deliverable: annotated ETF universe + curated Top100 benchmark registry.

Combines everything measured across v5-v9:
  - v8 coverage (greedy set-cover) -> Primary score
  - v9 style loadings              -> Style score (World factors only; rest untested)
  - the take's tier architecture   -> Semantic layer

The registry is ONE set of records scored on three axes, not two registries: a record can
be both a primary benchmark and a style descriptor (Gold Miners is primary for 15 funds at
rho 0.93 AND a mining descriptor), so Type A / Type B is emergent from scores, not schema.

Each canonical concept is resolved to the best available listing in the universe by a
quality score (history, accumulating, clean currency, no leverage/ESG, hedging rule per
asset class).
"""

import json
import os
import re

import numpy as np
import pandas as pd

SCR = "scratch/etf-audit"
FU = "data/processed/etf_prices/full_universe"
OUT = f"{SCR}/BENCHMARK_REGISTRY.xlsx"

# tier, concept, regex, semantic score (10 = canonical index everyone recognises)
CONCEPTS = [
    # ---- L1 MARKET / CORE EQUITY ----
    (
        "L1 Market",
        "Global DM Equity",
        r"(core )?msci world(?!.*(small|value|growth|quality|momentum|volatil|sector|health|financ|technolog|energy|material|utilit|consumer|industrial|communication|real estate|estate|staples|discretionary|bank|insur|telecom|media|semiconduct))",
        10,
    ),
    ("L1 Market", "Global All-Cap incl EM", r"(msci acwi|all[- ]world|all country world)", 10),
    ("L1 Market", "US Large Cap", r"s&p ?500(?!.*(equal|low|quality|value|growth))", 10),
    ("L1 Market", "US Technology (Nasdaq)", r"nasdaq[- ]?100|eqqq", 10),
    ("L1 Market", "US Small Cap", r"russell 2000", 9),
    (
        "L1 Market",
        "Europe Broad",
        r"(msci europe|stoxx europe 600|core stoxx europe)(?!.*(small|mid|value|growth|quality|momentum|volatil|ex-uk|sector|health|financ|technolog|energy|material|utilit|consumer|industrial|communication|real estate|estate|staples|discretionary|bank|insur|telecom|media|semiconduct))",
        10,
    ),
    ("L1 Market", "Eurozone", r"msci emu|euro stoxx 50|prime eurozone", 10),
    ("L1 Market", "Europe Small Cap", r"europe small cap(?!.*(value|growth|quality|weighted))", 9),
    ("L1 Market", "Europe Mid Cap", r"europe mid|stoxx europe mid", 8),
    ("L1 Market", "Germany", r"\bdax\b(?!.*(plus|maximum))", 9),
    ("L1 Market", "France", r"msci france|\bcac\b", 8),
    ("L1 Market", "UK Large Cap", r"ftse 100", 9),
    ("L1 Market", "UK All-Share", r"ftse uk all share|uk all-share", 9),
    ("L1 Market", "Switzerland", r"msci switzerland|\bsmi\b", 8),
    ("L1 Market", "Japan", r"(msci japan|topix)(?!.*small)", 10),
    ("L1 Market", "Japan Small Cap", r"japan small cap", 7),
    ("L1 Market", "Nordics", r"msci nordic|omx stockholm", 7),
    ("L1 Market", "Italy", r"ftse mib", 7),

    ("L1 Market", "Canada", r"msci canada", 7),
    ("L1 Market", "Australia", r"msci australia", 7),
    ("L1 Market", "World Small Cap", r"world small cap", 9),
    (
        "L1 Market",
        "EM Broad",
        r"(msci )?emerging markets(?!.*(small|value|growth|quality|volatil|bond|sovereign|debt|health|financ|technolog|energy|material|utilit|consumer|industrial|communication|real estate|estate|staples|discretionary|bank|insur|telecom|media|semiconduct))",
        10,
    ),
    ("L1 Market", "EM Small Cap", r"em small cap|emerging markets small", 8),
    ("L1 Market", "Asia ex-Japan", r"(ac )?(far east|asia).*ex[- ]japan", 9),
    ("L1 Market", "China Broad", r"msci china(?!.*(tech|min te))", 10),
    (
        "L1 Market",
        "China Tech / Internet",
        r"china (internet|technology)|csi china internet|chinext",
        8,
    ),
    ("L1 Market", "India", r"(msci|ftse) india(?!.*bond)", 9),
    ("L1 Market", "Korea", r"msci korea", 8),
    ("L1 Market", "Taiwan", r"msci taiwan", 8),
    ("L1 Market", "Latin America", r"latin america", 9),
    ("L1 Market", "Brazil", r"msci brazil", 8),
    ("L1 Market", "CEE / EM Europe", r"eastern europe|cee", 8),
    ("L1 Market", "Turkey", r"msci turkey", 6),
    ("L1 Market", "MEA / Africa", r"pan africa", 6),
    ("L1 Market", "Frontier", r"frontier", 6),
    # ---- L2 STYLE AXES ----
    ("L2 Style Axis", "World Value", r"world value", 10),
    ("L2 Style Axis", "World Growth", r"world growth", 10),
    ("L2 Style Axis", "World Quality", r"world quality(?!.*dividend)", 10),
    ("L2 Style Axis", "World Momentum", r"world momentum", 10),
    ("L2 Style Axis", "World Min Vol", r"world minimum volatility", 10),
    ("L2 Style Axis", "USA Value", r"usa value", 9),
    ("L2 Style Axis", "USA Growth", r"(usa growth|russell 1000 growth)", 9),
    ("L2 Style Axis", "Europe Value", r"europe value|emu value", 9),
    ("L2 Style Axis", "Europe Growth", r"europe growth|emu growth", 9),
    ("L2 Style Axis", "EM Value", r"em value|emerging markets value", 8),
    # ---- L3 SECTORS ----
    ("L3 Sector", "Technology", r"world (information )?technology|msci world tech", 10),
    ("L3 Sector", "Healthcare", r"world health ?care", 10),
    ("L3 Sector", "Financials", r"world financials", 10),
    ("L3 Sector", "Europe Banks", r"(euro ?stoxx|europe).*bank", 8),
    ("L3 Sector", "Energy", r"world energy(?!.*(commod|carbon))", 10),
    ("L3 Sector", "Materials", r"world materials", 10),
    ("L3 Sector", "Industrials", r"world industrials|europe industrial", 9),
    ("L3 Sector", "Consumer Discretionary", r"world consumer discretionary", 9),
    ("L3 Sector", "Consumer Staples", r"world consumer staples", 9),
    ("L3 Sector", "Utilities", r"world utilities", 9),
    ("L3 Sector", "Communication", r"communication services", 9),
    ("L3 Sector", "Real Estate / REIT", r"(epra|nareit|property yield|real estate)", 10),
    ("L3 Sector", "Biotech", r"biotech", 8),
    ("L3 Sector", "Semiconductors", r"semiconductor", 8),
    ("L3 Sector", "Artificial Intelligence", r"artificial intelligence|robotics", 7),
    ("L3 Sector", "Cybersecurity", r"cybersecurity", 7),
    ("L3 Sector", "Clean Energy", r"clean energy|global clean|renewable", 7),
    ("L3 Sector", "Water", r"clean water|global water", 7),
    ("L3 Sector", "Aerospace & Defence", r"defen[cs]e|aerospace", 7),
    ("L3 Sector", "Infrastructure", r"global infrastructure", 8),
    ("L3 Sector", "Mining / Basic Resources", r"global mining|basic resources|metals producers", 8),
    ("L3 Sector", "Listed Private Equity", r"listed private equity|private equity", 8),
    # ---- L4 REAL ASSETS ----
    ("L4 Real Asset", "Gold", r"physical gold|gold bullion", 10),
    ("L4 Real Asset", "Silver", r"physical silver|silver trust", 10),
    ("L4 Real Asset", "Gold Miners", r"gold miners|gold producers", 10),
    ("L4 Real Asset", "Brent Crude", r"brent", 10),
    (
        "L4 Real Asset",
        "Broad Commodities",
        r"(bloomberg commodity|rogers international commodity|cmci composite)(?!.*ex-)",
        10,
    ),
    ("L4 Real Asset", "Industrial Metals", r"industrial metals", 7),
    ("L4 Real Asset", "Agriculture", r"(?<!ex-)agriculture(?!.*\bex\b)", 6),
    # ---- L5 CRYPTO ----
    ("L5 Crypto", "Bitcoin", r"bitcoin", 9),
    ("L5 Crypto", "Ethereum", r"ethereum", 8),
    # ---- L6 FIXED INCOME (global) ----
    ("L6 Fixed Income", "Global Aggregate (hedged)", r"global aggregate", 10),
    ("L6 Fixed Income", "Euro Government", r"euro government bond(?!.*(0-6|1-3|10-15|25|month))", 10),
    ("L6 Fixed Income", "Euro Govt Short 1-3y", r"euro government bond 1-3", 8),
    ("L6 Fixed Income", "Euro Govt Long 10y+", r"euro government bond (10-15|15|25)", 8),
    ("L6 Fixed Income", "US Treasury Short 1-3y", r"treasury bond 1-3", 8),
    ("L6 Fixed Income", "US Treasury Mid 3-7y", r"treasury bond 3-7", 8),
    ("L6 Fixed Income", "US Treasury Long 20y+", r"treasury bond 20\+|treasury.*long dated", 9),
    ("L6 Fixed Income", "Inflation-Linked (TIPS)", r"\btips\b|inflation[- ]linked", 10),
    ("L6 Fixed Income", "IG Corporate EUR", r"(€|eur) corp(orate)? bond", 10),
    ("L6 Fixed Income", "IG Corporate USD", r"(\$|usd) corp(orate)? bond", 10),
    ("L6 Fixed Income", "High Yield EUR", r"eur high yield", 10),
    ("L6 Fixed Income", "High Yield USD", r"usd high yield|\$ high yield", 10),
    (
        "L6 Fixed Income",
        "EM Bond Hard Ccy",
        r"em bond|emerging markets sovereign|usd emerging markets bond",
        10,
    ),
    ("L6 Fixed Income", "EM Bond Local Ccy", r"em local|local currency bond", 9),
    ("L6 Fixed Income", "Convertibles", r"convertible", 8),
    ("L6 Fixed Income", "China Bonds", r"china cny bond", 7),
    ("L6 Fixed Income", "UK Gilts", r"\bgilt", 8),
    ("L6 Fixed Income", "Money Market USD", r"t-bill|treasury bill|1-3 month", 9),
    # ---- L7 LOCAL PL ----
    ("L7 Local PL", "PL Government (TBSP)", r"tbsp", 10),
    ("L7 Local PL", "PL Short Bonds", r"obligacji 6m", 9),
    ("L7 Local PL", "PL Large Cap (WIG20)", r"wig20tr(?!lev|sht)", 10),
    ("L7 Local PL", "PL Mid Cap (mWIG40)", r"mwig40tr(?!lv|sh)", 10),
    ("L7 Local PL", "PL Small Cap (sWIG80)", r"swig80tr", 10),
    ("L7 Local PL", "PL S&P 500 hedged", r"beta etf s&p 500 pln", 8),
    ("L7 Local PL", "PL Nasdaq hedged", r"beta etf nasdaq-100 pln", 8),
]

# Explicit listing pins: concept -> analizy code. Overrides the quality contest and the
# FI hedging rule. Use when a specific listing is preferred for reasons the data cannot
# see (liquidity, spread, provider, recognisability) or when the auto-pick is simply worse.
PIN = {
    "Listed Private Equity": "E_FSICAV001_A_USD",  # Northern Trust Listed PE Acc - VanEck not in universe
    "Bitcoin": "E_ISRDA001_A_USD",              # iShares Bitcoin ETP, preferred over VanEck
    "Inflation-Linked (TIPS)": "E_ISHII002_A_USD",  # iShares $ TIPS - the canonical broad TIPS
    "IG Corporate USD": "E_VANG024_A_USD",      # Vanguard USD Corporate Bond
}

# Cut to hold the registry at exactly 100 selected rows. Chosen as the weakest on the
# composite of all three axes (primary + semantic + style), each scoring 0 funds as a
# primary benchmark. Agriculture and Industrial Metals were already dropped in v3 for
# failing all four of the take's admission criteria - this is consistent, not new.
# Australia swapped in for Frontier per user 2026-07-20: Frontier is the only EM-edge
# breadth row, Australia is a DM single-country with 0 demand already covered by World.
DROP_CONCEPTS = {"Turkey", "Australia", "Agriculture", "Industrial Metals"}
# UK Mid Cap (FTSE 250) replaced by UK All-Share 2026-07-20: its 6 raw assignments were
# 5 bond funds + 1 genuine UK equity fund (Fidelity UK Special Situations), whose real
# benchmark is All-Share. Confirmed no factor/sector need competes for the slot (v12).

# Mandated by the user 2026-07-20: local PLN access layer. These bypass the quality
# contest entirely -- they are in the registry by instruction, not by measurement.
# Several are too young to have been scored (PZU launches have <2y of history).
FORCE_INCLUDE = {
    "E_AGF100_A_PLN":  ("L7 Local PL", "PL Bitcoin (local)", 9, "MANDATED. GPW-listed PLN Bitcoin access."),
    "E_PZU103_A_PLN":  ("L7 Local PL", "PL Gold hedged (local)", 9, "MANDATED. PLN-hedged gold - the only clean-FX gold row available."),
    "E_PZU104_AH_PLN": ("L7 Local PL", "PL MSCI World hedged (local)", 9, "MANDATED. PLN-hedged World - removes the EUR/PLN residual that every global row carries."),
    "E_PZU102_A_PLN":  ("L7 Local PL", "PL WIG20+mWIG40 (local)", 8, "MANDATED. Combined PL large+mid exposure."),
    "E_AGF101_AD_PLN": ("L7 Local PL", "PL Dividend (local)", 7, "MANDATED (nice-to-have). PL dividend strategy."),
}

BAD = re.compile(
    r"\b(\d+(\.\d+)?x|leverage[d]?|short|inverse|bear|ultra)\b|\bESG\b|\bSRI\b|\bPAB\b|\bCTB\b"
    r"|climate|paris[- ]aligned|sustainab|screened|transition|low\s+carbon|equal\s+weight"
    r"|research\s+enhanced|covered\s+call|premium\s+income|aristocrat|\bsdg\b|socially|green\s+bond|equal[-\s]weight|ex-agriculture|ex-livestock|\benhanced\b|\bPEA\b|ex[-\s]europe|ex[-\s]usa|ex[-\s]us\b|ex[-\s]uk\b|ex[-\s]china|ex[-\s]korea",
    re.I,
)

# ---- load everything measured ---------------------------------------------
uni = pd.read_excel("data/raw/lista-etf-2026-06-02.xlsx").dropna(subset=["isin"])
res = pd.DataFrame([json.loads(line) for line in open(f"{FU}/resolution.jsonl")])
v8 = pd.read_csv(f"{SCR}/v8_top100.csv")
trace = pd.read_csv(f"{SCR}/v8_selection_trace.csv")
clone = pd.read_csv(f"{SCR}/v7_clone_map.csv", index_col=0)["representative"].to_dict()
fit = pd.read_csv(f"{SCR}/v8_fund_fit.csv")

atlas = pd.read_csv(f"{SCR}/atlas_etfs.csv")[
    ["isin", "fund_size", "expense_ratio", "replication_name_lang",
     "distribution_policy_lang", "currency_hedged_lang", "fund_provider"]
].drop_duplicates("isin")
atlas = atlas.rename(columns={"fund_size": "aum_pln", "expense_ratio": "ter",
                              "replication_name_lang": "replication",
                              "distribution_policy_lang": "distribution"})
u = uni.merge(res[["isin", "status", "currency", "n_obs", "first", "last"]], on="isin", how="left")
u = u.merge(atlas, on="isin", how="left")
u["priced"] = u.status.eq("ok")
u["excluded_by_rule"] = u.nazwa_jednostki.astype(str).str.contains(BAD)
u["clone_of"] = u["isin"].map(clone)
u["is_clone"] = u.clone_of.notna() & (u.clone_of != u["isin"])
prim = fit.best_isin.value_counts()
u["n_funds_primary"] = u["isin"].map(prim).fillna(0).astype(int)
u["v8_rank"] = u["isin"].map(dict(zip(v8["isin"], v8["rank"])))
u["v8_marginal_gain"] = u["isin"].map(dict(zip(v8["isin"], v8.marginal_gain)))

# ---- resolve each concept to its best listing -----------------------------
STYLE_SCORE = {
    "World Value": 10,
    "World Momentum": 10,
    "World Quality": 8,
    "World Min Vol": 3,
    "World Small Cap": 9,
}
pool = u[u.priced & ~u.excluded_by_rule].copy()
pool["nm"] = pool.nazwa_jednostki.astype(str)


NATURAL_CCY = [
    (r"Europe|Eurozone|Germany|France|Italy|Spain|Switzerland|Nordics|CEE|EM Europe", "EUR"),
    (r"^UK ", "GBP"),
    (r"^PL ", "PLN"),
    (r"Japan", "JPY|USD"),
]


def natural_ccy(concept):
    """Quote currency a benchmark should carry: the natural currency of its underlying,
    USD otherwise. For unhedged listings this is cosmetic (FX cancels on conversion to
    PLN) but it keeps the registry readable and consistent."""
    for rx, c in NATURAL_CCY:
        if re.search(rx, concept, re.I):
            return c.split("|")
    return ["USD"]


SLICE_RX = re.compile(r"\b(\d+\s*-\s*\d+\s*(y|yr|year|m|month)|\d+\+\s*(y|yr)?|0-6|short dated|long dated)\b", re.I)


def quality(row, tier, concept=""):
    """Score a candidate listing. Canonicity dominates: a benchmark should be the plain,
    physically-replicated, accumulating listing in its natural currency. History and
    demand only break ties among equally canonical candidates."""
    s = float(row.n_obs or 0) / 500.0
    nm = row.nm
    # --- canonicity, from atlas fundamentals rather than name parsing ---
    if str(getattr(row, "replication", "")) == "syntetyczna":
        s -= 12          # synthetic replication is a tracking choice, not a benchmark
    if str(getattr(row, "distribution", "")) == "Dystrybucja":
        s -= 6           # distribution timing adds noise to the return series
    if SLICE_RX.search(nm) and not SLICE_RX.search(concept):
        s -= 15          # a maturity slice must not stand in for a broad concept
    if "(Acc)" in nm:
        s += 3
    if row.currency in natural_ccy(concept):
        s += 7           # quote in the natural currency of the underlying
    elif row.currency in ("USD", "EUR"):
        s += 1
    hedged = "hedged" in nm.lower()
    # FI: hedging helps, but never at the cost of picking a non-canonical instrument
    if tier.startswith("L6"):
        s += 3 if hedged else 0
    elif hedged and "hedged" not in concept.lower():
        s -= 8           # equity benchmarks are quoted in their natural currency
    s += 2 * row.n_funds_primary**0.5
    return s


rows, used, CAND, HEDGE_DROP = [], set(), {}, {}
_force = uni[uni.kod_jednostki.isin(FORCE_INCLUDE)]
used |= set(_force["isin"])  # reserve so no concept can consume them
ORDER = sorted(CONCEPTS, key=lambda c: 0 if c[0].startswith("L7") else 1)
for tier, concept, pat, sem in ORDER:
    if concept in DROP_CONCEPTS:
        continue
    rx = re.compile(pat, re.I)
    if concept in PIN:
        m = pool[pool.kod_jednostki.eq(PIN[concept])]
    else:
        m = pool[pool.nm.str.contains(rx) & ~pool["isin"].isin(used)]
    if tier.startswith("L6") and concept not in PIN:
        h = m[m.nm.str.contains("hedged", case=False)]
        if len(h):
            for iso in m.loc[~m.index.isin(h.index), "isin"]:
                HEDGE_DROP[iso] = concept
            m = h  # unhedged USD FI in PLN terms is an FX series, not a bond series
    if not len(m):
        rows.append(
            dict(
                tier=tier,
                concept=concept,
                semantic=sem,
                status="NOT FOUND",
                name=None,
                isin=None,
                ccy=None,
                n_funds_primary=0,
            )
        )
        continue
    m = m.assign(q=[quality(r, tier, concept) for r in m.itertuples()]).sort_values("q", ascending=False)
    top = m.iloc[0]
    for pos, iso in enumerate(m["isin"].tolist(), 1):
        CAND.setdefault(iso, []).append((concept, pos, len(m), str(top.nazwa_jednostki)))
    used.add(top["isin"])
    rows.append(
        dict(
            tier=tier,
            concept=concept,
            semantic=sem,
            status="ok",
            name=top.nazwa_jednostki,
            isin=top["isin"],
            ccy=top.currency,
            analizy_code=top.kod_jednostki,
            n_obs=int(top.n_obs or 0),
            n_funds_primary=int(top.n_funds_primary),
            v8_rank=top.v8_rank,
            n_alternatives=len(m),
        )
    )

for _, fr_ in _force.iterrows():
    tier, concept, sem, note = FORCE_INCLUDE[fr_.kod_jednostki]
    meta = u[u["isin"].eq(fr_["isin"])].iloc[0]
    wk = int((meta.n_obs or 0) / 5)
    rows.append(dict(
        tier=tier, concept=concept, semantic=sem,
        status="ok (mandated)", name=fr_.nazwa_jednostki, isin=fr_["isin"],
        ccy=meta.currency, analizy_code=fr_.kod_jednostki, n_obs=int(meta.n_obs or 0),
        n_funds_primary=int(meta.n_funds_primary), v8_rank=meta.v8_rank, n_alternatives=1,
        mandated=True,
        too_short=wk < 104,
        forced_note=note + (f" NOT SCORED: only ~{wk} weeks of history (needs 104)." if wk < 104 else "")))

reg = pd.DataFrame(rows)
reg["mandated"] = reg.get("mandated", pd.Series(False, index=reg.index)).fillna(False)
reg["check"] = np.where(reg.mandated.fillna(False) & reg.get("too_short", pd.Series(False, index=reg.index)).fillna(False), "MANDATED - too short to score",
                 np.where(reg.status.eq("NOT FOUND"), "NO ETF EXISTS",
                 np.where(reg.mandated.fillna(False), "MANDATED - in by instruction",
                 np.where(reg.get("n_alternatives", 0).fillna(0) > 12, "many alternatives - verify pick",
                 np.where(reg.n_funds_primary.fillna(0) == 0, "no fund picks it as primary", "")))))
reg["primary_score"] = np.where(
    reg.n_funds_primary.fillna(0) >= 15,
    10,
    np.where(
        reg.n_funds_primary.fillna(0) >= 5, 7, np.where(reg.n_funds_primary.fillna(0) >= 1, 4, 1)
    ),
)
reg["style_score"] = reg.concept.map(STYLE_SCORE)
reg["style_score"] = reg.style_score.fillna("untested")
reg["record_type"] = np.where(
    reg.tier.str.startswith("L2"),
    "Style descriptor",
    np.where(reg.primary_score >= 7, "Primary benchmark", "Primary (thin) + descriptor"),
)

# ---- notes ----------------------------------------------------------------
NOTES = {
    "World Min Vol": "Kept for canonicity, NOT for information: 480 of 489 fund loadings negative -> the label separates nothing. Style score 3. Suppress the emitted tilt label.",
    "World Growth": "MSCI World Growth barely exists as a UCITS ETF (0 clean matches vs 6 for Value). Needs a proxy or synthetic long-short construction.",
    "World Momentum": "Best discriminator measured: 48 positive vs 48 negative loadings. Near-zero as a primary benchmark - this is a tilt axis, not an assignment target.",
    "World Value": "40% of equity funds load significantly (187 pos / 28 neg).",
    "World Quality": "Developed-market phenomenon: 23.8% of EQ_DM funds vs 1.7% of EQ_EM. Do not extend to EM.",
    "EM Value": "The one factor that travels to EM (41.9% significant). EM Quality/Momentum are not supported by the data.",
    "Gold Miners": "Primary benchmark for 15 funds at median rho 0.926 - among the best fits in the book. This is why the registry must not be split into separate primary/descriptor sets.",
    "Europe Banks": "Primary for 2 funds at rho 0.924. A distinct style, not a redundant sector - confirmed.",
    "Brent Crude": "Take mandates Brent over WTI and over Energy equity.",
    "PL Short Bonds": "FI_PL_SHORT is 55.7% unfitted and CANNOT be fixed by any ETF: 79 funds hold WIBOR floaters and PL corporate paper that no UCITS ETF tracks. Needs GPW Benchmark WIBOR series.",
    "PL Government (TBSP)": "Works: FI_PL median rho 0.91, only 8.9% weak - because TBSP is a PLN instrument.",
    "Money Market USD": "In PLN terms this had rho 0.999 to USDPLN and 11% vol - it was measuring the dollar, not money markets. Must be hedged.",
    "Global Aggregate (hedged)": "Unhedged version had rho 0.92 to USDPLN. Hedged share class is mandatory for every FI row.",
}
reg["note"] = reg.concept.map(NOTES).fillna("")
reg["note"] = np.where(reg.get("forced_note", "").astype(str).ne("nan") & reg.mandated,
                       reg.get("forced_note", "").astype(str), reg.note)
_nm = reg.name.astype(str)
reg["fx_treatment"] = np.where(reg.tier.str.startswith("L6") | reg.tier.str.startswith("L4"),
    np.where(_nm.str.contains("hedged", case=False), "hedged to EUR/GBP - residual EUR/PLN remains",
    np.where(reg.ccy.eq("PLN"), "PLN native - clean",
    np.where(reg.ccy.eq("EUR"), "EUR asset, EUR/PLN unhedged", "UNHEDGED USD - in PLN this is largely an FX series"))),
    "")
reg.loc[reg.concept.eq("Money Market USD"), "note"] = (
    "NO hedged UCITS T-Bill ETF exists. Unhedged, this had rho 0.999 to USDPLN and 11% vol - "
    "it measures the dollar, not money markets. Use a PLN cash/WIBOR series instead.")

gaps = pd.DataFrame(
    [
        dict(
            tier="L7 Local PL",
            concept="WIBOR floater index",
            why="79 FI_PL_SHORT funds, 55.7% unfitted. No ETF exists.",
            source="GPW Benchmark (gpw-benchmark-scraper skill)",
        ),
        dict(
            tier="L7 Local PL",
            concept="PL corporate bonds",
            why="Part of the 52% unfitted FI_CREDIT block.",
            source="GPW Benchmark / Catalyst",
        ),
        dict(
            tier="L7 Local PL",
            concept="TBSP duration buckets",
            why="Single TBSP row cannot separate short/mid/long PL govt funds.",
            source="GPW Benchmark",
        ),
        dict(
            tier="L2 Style Axis",
            concept="World Growth",
            why="No clean UCITS ETF in 2,285.",
            source="synthetic (World minus World Value) or index licence",
        ),
    ]
)

summary = pd.DataFrame(
    [
        ("Universe (xlsx rows)", len(uni)),
        ("Priced via EODHD", int(u.priced.sum())),
        ("Excluded by rule (leveraged/ESG/strategy)", int(u.excluded_by_rule.sum())),
        ("Distinct after clone dedupe", int((~u.is_clone.fillna(False) & u.priced).sum())),
        ("Registry concepts defined", len(reg)),
        ("Registry concepts resolved", int((reg.status == "ok").sum())),
        ("Registry concepts NOT FOUND", int((reg.status == "NOT FOUND").sum())),
        ("Coverage: median fund fit (top100 greedy)", 0.824),
        ("Coverage: funds unfitted <0.7", "17.1%"),
        ("Coverage ceiling (all 840 eligible)", "16.8% unfitted - dictionary is at its ceiling"),
        ("Equity funds with >=1 significant style tilt", "98.7%"),
    ("FX caveat", "UCITS 'hedged' share classes hedge to EUR/GBP, never PLN - every FI row keeps residual EUR/PLN or USD/PLN risk"),
    ("Registry design", "ONE record set scored on 3 axes (Primary / Style / Semantic). Type A vs B is emergent, not schema: Gold Miners is primary for 15 funds AND a descriptor"),
    ],
    columns=["metric", "value"],
)

# ---- ONE sheet: original universe + every metric, comment and reason -------
sel = reg[reg.status.astype(str).str.startswith("ok")].set_index("isin")
full = u.copy()
for col in ["tier", "concept", "semantic", "primary_score", "style_score",
            "record_type", "fx_treatment", "note", "check"]:
    full[col] = full["isin"].map(sel[col]) if col in sel.columns else None
full["selected"] = np.where(full["isin"].isin(sel.index),
    np.where(full["isin"].map(sel.get("mandated", pd.Series(dtype=bool))).fillna(False),
             "YES (mandated)", "YES"), "")

cand_concept, cand_rank, cand_lost = [], [], []
for iso in full["isin"]:
    c = CAND.get(iso)
    if c:
        best = min(c, key=lambda t: t[1])
        cand_concept.append(best[0]); cand_rank.append(f"{best[1]} of {best[2]}")
        cand_lost.append("" if best[1] == 1 else best[3])
    else:
        cand_concept.append(""); cand_rank.append(""); cand_lost.append("")
full["concept_matched"] = [c or HEDGE_DROP.get(i, "") for c, i in zip(cand_concept, full["isin"])]
full["rank_within_concept"] = cand_rank
full["lost_to"] = cand_lost

full["why_not_selected"] = np.where(
    full.selected.eq("YES"), "",
    np.where(~full.priced, "no price history (EODHD could not resolve the ISIN)",
    np.where(full.excluded_by_rule, "excluded by rule: leveraged / inverse / ESG / equal-weight / strategy overlay",
    np.where(full.is_clone.fillna(False), "clone: correlated >=0.98 with " + full.clone_of.astype(str),
    np.where(full["isin"].isin(HEDGE_DROP), "unhedged fixed-income variant - excluded by the hedging rule; "
             "the exposure IS in the registry via a hedged share class",
    np.where(full.concept_matched.ne(""), "matched a concept but a better listing won (see lost_to)",
             "no registry concept matches this ETF"))))))

ORDER_COLS = ["kod_firmazarz", "kod_parasola", "kod_funduszu", "kod_jednostki", "nazwa_jednostki",
              "isin", "selected", "tier", "concept", "primary_score", "style_score", "semantic",
              "record_type", "n_funds_primary", "v8_rank", "v8_marginal_gain", "fx_treatment",
              "note", "check", "why_not_selected", "concept_matched", "rank_within_concept",
              "lost_to", "priced", "excluded_by_rule", "is_clone", "clone_of",
              "currency", "n_obs", "first", "last", "status"]
full = full[[c for c in ORDER_COLS if c in full.columns]]
full = full.sort_values(["selected", "tier", "concept", "n_funds_primary"],
                        ascending=[False, True, True, False])

with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
    summary.to_excel(xw, sheet_name="Summary", index=False)
    reg.to_excel(xw, sheet_name="Registry Top100", index=False)
    gaps.to_excel(xw, sheet_name="Gaps (no ETF exists)", index=False)
    v8.to_excel(xw, sheet_name="v8 coverage election", index=False)
    trace.to_excel(xw, sheet_name="Saturation curve", index=False)
    full.to_excel(xw, sheet_name="FULL UNIVERSE + findings", index=False)

print(f"wrote {OUT}")
print(
    f"\nregistry: {len(reg)} concepts, {(reg.status == 'ok').sum()} resolved, "
    f"{(reg.status == 'NOT FOUND').sum()} not found"
)
print(
    reg.groupby("tier")
    .agg(concepts=("concept", "size"), resolved=("status", lambda s: (s == "ok").sum()))
    .to_string()
)
print("\nNOT FOUND:")
print(reg[reg.status == "NOT FOUND"][["tier", "concept"]].to_string(index=False))
