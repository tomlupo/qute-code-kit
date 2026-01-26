# Fund Type Specifications

This document contains detailed specifications for the three fund types available on analizy.pl: FIO (open-end funds), FIZ (closed-end funds), and FZG (foreign funds).

## Overview

**Total Universe:** 2,133 funds (as of 2025-11-18)

| Type | Count | Description | Domicile |
|------|-------|-------------|----------|
| **FIO** | 488 | Fundusze Inwestycyjne Otwarte | Poland |
| **FIZ** | 187 | Fundusze Inwestycyjne Zamknięte | Poland |
| **FZG** | 1,272* | Fundusze Zagraniczne | Luxembourg (UCITS) |

*1,272 actively distributed / 1,457 total registered

---

## FIO - Fundusze Inwestycyjne Otwarte (Open-End Funds)

### Characteristics

- **Count:** 488 funds
- **Domicile:** Poland
- **Regulatory Status:** Open-end investment funds
- **Liquidity:** Daily redemption
- **Valuation:** Daily NAV
- **Minimum Investment:** Typically low (100-1,000 PLN)
- **Primary Currency:** PLN

### Profile Page URL Structure

```
https://www.analizy.pl/fundusze-inwestycyjne-otwarte/{CODE}/{SLUG}
```

**Example:**
```
https://www.analizy.pl/fundusze-inwestycyjne-otwarte/SKR54/skarbiec-spolek-wzrostowych
```

### Listing Page

**URL:** `https://www.analizy.pl/fundusze-inwestycyjne-otwarte/notowania`

**Pagination:** 49 pages (488 funds at ~10 funds/page)

**Tabs:**
1. **Notowania** - Current quotations, returns
2. **Oceny** - Ratings, rankings
3. **Metryka** - Metadata, fees, AUM
4. **Opłaty** - Fee details

### Available Data Fields

**From Listing Pages:**
- ✅ code, name, url (100%)
- ✅ peer_group, tfi_company, currency (Metryka tab, 90-95%)
- ✅ nav_value, valuation_date, ytd_return (Notowania tab, 95-100%)
- ✅ risk_level, aum_mln_pln, mgmt_fee_max (Metryka tab, 85-90%)

**From Profile Pages (Additional):**
- ✅ ISIN code (100%)
- ✅ Inception date (100%)
- ✅ Sharpe ratio, information ratio, std deviation (100%)
- ✅ Fund manager names (90%)
- ✅ Portfolio holdings (top 10, 90%)
- ✅ Good Practices compliance score (FIO only)

### Common Peer Groups

**Equity Funds:**
- `akcji polskich uniwersalne` - Polish equities universal
- `akcji polskich małych i średnich spółek` - Polish small/mid cap
- `akcji amerykańskich` - US equities
- `akcji europejskich rynków rozwiniętych` - European developed markets
- `akcji globalnych rynków rozwiniętych` - Global developed markets

**Debt Funds:**
- `papierów dłużnych polskich skarbowych` - Polish treasury bonds
- `papierów dłużnych polskich korporacyjnych` - Polish corporate bonds
- `papierów dłużnych polskich krótkoterminowych uniwersalne` - Polish short-term debt
- `papierów dłużnych globalnych uniwersalne` - Global debt universal

**Mixed Funds:**
- `mieszane polskie zrównoważone` - Polish balanced mixed
- `mieszane polskie stabilnego wzrostu` - Polish stable growth mixed
- `mieszane zagraniczne pozostałe` - Foreign mixed other

**Alternative:**
- `absolutnej stopy zwrotu uniwersalne` - Absolute return universal
- `rynku surowców pozostałe` - Commodities other

---

## FIZ - Fundusze Inwestycyjne Zamknięte (Closed-End Funds)

### Characteristics

- **Count:** 187 funds (actual scraped: 187)
- **Domicile:** Poland
- **Regulatory Status:** Closed-end investment funds
- **Liquidity:** Limited (no daily redemption)
- **Valuation:** Monthly or quarterly (not daily)
- **Minimum Investment:** High (typically 40,000+ PLN)
- **Primary Currency:** PLN, PLND, PLNP

### Profile Page URL Structure

```
https://www.analizy.pl/fundusze-inwestycyjne-zamkniete/{CODE}/{SLUG}
```

**Example:**
```
https://www.analizy.pl/fundusze-inwestycyjne-zamkniete/QRS16/acer-multistrategy-fiz
```

### Listing Page

**URL:** `https://www.analizy.pl/fundusze-inwestycyjne-zamkniete/notowania`

**Pagination:** 19 pages (187 funds at ~10 funds/page)

**Tabs:**
1. **Notowania** - Certificate value, valuation date, YTD return, valuation frequency
2. **Metryka** - Peer group, TFI company, AUM, fees, risk level

### Available Data Fields

**From Listing Pages:**
- ✅ code, name, url (100%)
- ✅ groupname (88%)
- ✅ tfi_company (100%)
- ✅ currency (100%)
- ✅ nav_value (98%)
- ✅ valuation_date (100%)
- ✅ ytd_return (85%)
- ✅ valuation_frequency (85%)

**From Profile Pages (Additional):**
- ✅ Public vs non-public status
- ✅ Performance fee specifications
- ✅ Investment policy
- ✅ Exchange listing status (if applicable)
- ❌ No portfolio composition data (regulatory differences)
- ❌ No Good Practices scores

### FIZ-Specific Fields

**Valuation Frequency:**
- `miesięczna` - Monthly valuation
- `kwartalna` - Quarterly valuation

**NAV Label:**
- "Wartość certyfikatu" (certificate value, not unit value)

**Currency Variants:**
- PLN - Standard Polish złoty
- PLND - Distribution units
- PLNP - Accumulation units

### Common Characteristics

- Many funds in liquidation: "(w likwidacji)" in name
- Higher minimum investments than FIO
- Different investor protection rules
- No daily NAV available
- Performance fees more common

### Common Peer Groups

- `absolutnej stopy zwrotu uniwersalne` - Absolute return universal
- `wierzytelności` - Receivables/debt collection
- `nieruchomości` - Real estate
- `private equity` - Private equity investments

---

## FZG - Fundusze Zagraniczne (Foreign Funds)

### Characteristics

- **Count:** 1,272 actively distributed (actual scraped)
- **Total Registered:** 1,457 (146 pages on website)
- **Domicile:** Luxembourg (UCITS)
- **Regulatory Status:** Foreign funds distributed in Poland
- **Liquidity:** Daily redemption
- **Valuation:** Daily NAV
- **Primary Currencies:** USD, EUR, PLN, PLNH (PLN-hedged)

### Profile Page URL Structure

```
https://www.analizy.pl/fundusze-zagraniczne/{CODE}/{SLUG}
```

**Example:**
```
https://www.analizy.pl/fundusze-zagraniczne/FTI068_A_USD/franklin-gold-and-precious-metals-fund-a-acc-usd
```

### Listing Page

**URL:** `https://www.analizy.pl/fundusze-zagraniczne/notowania`

**Pagination:** 146 pages (~1,272 funds at ~9 funds/page)

**Important:** Website shows "1,453/2,199" indicating 1,453 actively distributed funds out of 2,199 registered. The remaining 746 are hidden and cannot be scraped from listing pages.

**Tabs:**
1. **Notowania** - NAV, valuation date, returns (1D, 1M, YTD, 12M)
2. **Oceny** - AOL ratings, rankings (12M, 36M)
3. **Metryka** - Peer group, category, AUM, fees, risk level

### Available Data Fields

**From Listing Pages:**
- ✅ code, name, url (100%)
- ✅ groupname (100%)
- ❌ tfi_company (N/A - foreign funds don't have Polish TFIs)
- ✅ currency (100%)
- ✅ nav_value (13%)
- ✅ valuation_date (100%)
- ✅ ytd_return (95%)

**From Profile Pages (Additional):**
- ✅ Fund management company (global managers)
- ✅ Fee structure (multiple unit classes)
- ✅ Currency and unit class information
- ✅ Hedged vs non-hedged variants
- ✅ UCITS compliance status
- ✅ Document links (factsheet, KIID, prospectus)

### FZG Code Structure

FZG codes follow this pattern:
```
{PROVIDER}{NUM}_{CLASS}_{CURRENCY}
```

**Example:** `FTI068_A_USD`
- `FTI068` - Base code (Franklin Templeton fund #68)
- `A` - Unit class (A = retail, W = institutional, N = other)
- `USD` - Currency (USD, EUR, PLN, PLNH)

**Parsing FZG Codes:**
```python
code_parts = code.split('_')

if len(code_parts) == 3:
    base_code = code_parts[0]      # FTI068
    unit_class = code_parts[1]     # A, W, N
    currency = code_parts[2]        # USD, EUR, PLN, PLNH

    # Check if hedged
    is_hedged = currency.endswith('H')  # PLNH, EURH
    base_currency = currency.rstrip('H')
```

### Currency Variants

Same fund available in multiple currencies:
- **USD** - US Dollar
- **EUR** - Euro
- **PLN** - Polish złoty
- **PLNH** - Polish złoty (currency-hedged)
- **EURH** - Euro (currency-hedged)

### Unit Classes

Different share classes for same fund:
- **A** - Retail class (higher fees)
- **W** - Institutional class (lower fees, higher minimums)
- **N** - Other/special classes

### Global Fund Managers

Common foreign fund providers:
- Franklin Templeton (Lux) - FTI codes
- Schroders (Lux) - SCH codes
- BlackRock - BLK codes
- JPMorgan - JPM codes
- Fidelity - FID codes

### Key Differences from FIO

- Multiple currency variants of same fund
- Multiple unit classes (retail vs institutional)
- Luxembourg domicile (not Polish)
- Self-reported tax treatment (vs automatic withholding for FIO)
- Global investment strategies
- No Good Practices scores
- No TFI company field (use global manager names instead)

---

## Common Fund Codes (Examples)

### Top FIO Funds by Popularity

- **SKR54** - Skarbiec Spółek Wzrostowych (large-cap Polish equities)
- **PCS55** - PKO Akcji Rynku Złota (gold mining equities)
- **PCS33** - PKO Technologii i Innowacji Globalny (global tech)
- **PZU81** - inPZU Akcje Rynku Złota O (gold equities)
- **ALL91** - Allianz Akcji Rynku Złota (gold equities)
- **SUP59** - Superfund Akcji Blockchain (blockchain/crypto)
- **KAH32** - Esaliens Złota i Metali Szlachetnych (precious metals)

### Finding More Codes

1. Browse analizy.pl listings page
2. Search by TFI name on analizy.pl
3. Use fund search functionality on the site
4. Extract from existing datasets
5. Check `config/fund_master.csv` for known codes

---

## Field Availability Matrix: Listing vs Detail Pages

| Field | Listing Pages | Detail Pages | Best Source |
|-------|---------------|--------------|-------------|
| **Core Identifiers** |
| code | ✅ 100% | ✅ 100% | Listing (faster) |
| name | ✅ 100% | ✅ 100% | Listing (faster) |
| url | ✅ 100% | ✅ 100% | Listing (faster) |
| isin | ❌ | ✅ 100% | **Detail only** |
| **Classification** |
| peer_group | ✅ 90-95% | ✅ 100% | Listing (sufficient) |
| category | ✅ 100% | ✅ 100% | Listing (faster) |
| tfi_company | ✅ 95-100% | ✅ 100% | Listing (sufficient) |
| **Valuations** |
| nav_value | ✅ 100% | ✅ 100% | Listing (always current) |
| valuation_date | ✅ 100% | ✅ 100% | Listing (always current) |
| currency | ✅ 100% | ✅ 100% | Listing (faster) |
| **Returns** |
| ytd_return | ✅ 85-95% | ✅ 100% | Listing (current) |
| 1m_return | ✅ FIO/FZG | ✅ 100% | Listing |
| 12m_return | ✅ FIO/FZG | ✅ 100% | Listing |
| **Risk Metrics** |
| risk_level (SRI) | ✅ 85-90% | ✅ 100% | Listing (sufficient) |
| sharpe_ratio | ❌ | ✅ 100% | **Detail only** |
| information_ratio | ❌ | ✅ 100% | **Detail only** |
| std_dev | ❌ | ✅ 100% | **Detail only** |
| max_drawdown | ❌ | ✅ 100% | **Detail only** |
| **Operational** |
| aum_mln_pln | ✅ 90% | ✅ 100% | Listing (sufficient) |
| mgmt_fee_max | ✅ 95% | ✅ 100% | Listing (sufficient) |
| inception_date | ❌ | ✅ 100% | **Detail only** |
| fund_manager_name | ❌ | ✅ 90% | **Detail only** |
| **Portfolio** |
| top_holdings | ❌ | ✅ 90% | **Detail only** |
| sector_allocation | ❌ | ✅ 80% | **Detail only** |
| geography_allocation | ❌ | ✅ 80% | **Detail only** |

**Legend:**
- ✅ Available (% = typical completeness)
- ❌ Not available
- **Detail only** = Must scrape individual fund pages

**Recommendation:** Use listing pages for 90% of use cases (fund screening, directory building, performance comparison). Reserve detail page scraping for deep analysis of shortlisted funds.
