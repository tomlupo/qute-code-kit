# Tier taxonomy

Seven tiers. Counts are the finalized 2026-07-20 build (~100 total); treat as a
guide, not a quota.

| Tier | What it holds | Count | Notes |
|---|---|---:|---|
| L1 Market | Geography + broad-cap indices (World, S&P500, Europe, EM, single countries, regionals) | 34 | Regionals (MEA/Africa, LatAm, Asia-ex-Japan, CEE) preferred over single countries when demand is thin |
| L2 Style Axis | Value/Growth/Quality/Momentum/MinVol × World, + USA/Europe/EM Value | 8 | These are TILT AXES, not assignment targets. World Growth/Europe Growth have NO clean UCITS ETF |
| L3 Sector | GICS sectors (World-based) + a few thematics + Listed Private Equity | 21 | Prefer MSCI World sector over regional. Europe Banks is a legit distinct style |
| L4 Real Asset | Gold, Silver, Gold Miners, Brent, Broad Commodities | 5 | Gold Miners is EQUITY (mis-tiering it as commodity breaks asset-class matching). Brent not WTI, not Energy-equity |
| L5 Crypto | Bitcoin, Ethereum | 2 | |
| L6 Fixed Income | Global agg, govvies by duration, IG corp EUR/USD, HY, EM bond, TIPS, money market | 18 | Demand metric NOT APPLICABLE. Require hedged share classes |
| L7 Local PL | TBSP, short bonds, WIG20/mWIG40/sWIG80, PLN-hedged S&P/Nasdaq, PZU/Beta local products | 12 | Some are mandated + too young to score. Only genuinely PLN-clean rows in the whole registry |

## Style axis vs primary benchmark

The registry is ONE record set, three axes. A concept can be both:
- **Gold Miners**: primary benchmark for 15 gold-mining funds (ρ~0.93) AND a
  mining descriptor for diversified funds. Don't split into two registries.
- **World Momentum**: ~0 as a primary (no fund's single best), high as a tilt
  axis (48 pos / 48 neg loadings). Scored via the long-short spread regression,
  NOT argmax-correlation.

## Known permanent gaps (no UCITS ETF exists)

- World Growth, Europe Growth — Value exists, Growth doesn't. Needs synthetic
  (World − World Value) or an index licence.
- WIBOR floaters, PL corporate bonds — the FI_PL_SHORT / FI_CREDIT hole. Needs
  GPW Benchmark series, not an ETF.
- VanEck Listed Private Equity — not in the lista-etf universe; Northern Trust
  Listed PE is the substitute.
