# Dividend Treatment in Market Data Sources

How different data sources handle dividend adjustments in price data.

## Quick Reference

| Source | Price Type | Dividend Adjusted | Corporate Actions Available |
|--------|------------|-------------------|----------------------------|
| **Stooq** | Adjusted only | Yes (automatic) | No API |
| **Yahoo Finance** | Both | Yes (`adj_close`) | Yes (dividends, splits) |
| **NBP** | N/A | N/A | N/A (FX rates only) |
| **FRED** | N/A | N/A | N/A (economic data) |

---

## Stooq (stooq.pl)

### Price Type: Dividend-Adjusted Only

Stooq provides **dividend-adjusted prices**. All historical OHLC values are retroactively adjusted when dividends are paid.

### How It Works

When a company pays a dividend:
1. Historical prices are adjusted DOWN by a factor
2. Adjustment factor = `(price - dividend) / price`
3. All historical data is recalculated
4. Current/recent prices remain at actual trading values

### Example: XTB Dividend (5.45 PLN, ex-div 2025-06-13)

```
Date        Stooq Close   Notes
2025-06-10  75.01         Adjusted (was ~80.58 raw)
2025-06-11  74.30         Adjusted (was ~79.82 raw)
2025-06-12  73.20         Last cum-div day, adjusted (was 78.64 raw)
2025-06-13  74.12         Ex-div day, NOT adjusted (actual trading price)
2025-06-16  73.76         NOT adjusted (current price)
```

### Implications

- **Returns calculated from Stooq prices are total returns** (include dividend reinvestment effect)
- **Cannot recover raw prices** from Stooq alone
- **Multiple dividends compound** - older data has larger adjustments
- **Good for**: Performance attribution, return calculations, backtesting
- **Bad for**: Calculating actual P&L on specific trades

### Validation Results (Jan 2025)

Stooq prices validated against Yahoo Finance `adj_close`:
- 48 tickers tested
- 46/48 (95.8%) match within 1% tolerance
- 2 outliers: DOM (2.22% diff), ASB (1.74% diff)

---

## Yahoo Finance

### Price Types: Both Raw and Adjusted

Yahoo Finance provides **both** price types:

| Column | Description | Use Case |
|--------|-------------|----------|
| `close` | Raw/unadjusted price | Actual trading price, P&L calculation |
| `adj_close` | Dividend-adjusted price | Return calculation, comparison with Stooq |

### Corporate Actions Data

Yahoo provides explicit dividend and split data:

```python
import yfinance as yf

ticker = yf.Ticker('XTB.WA')

# Get dividends
dividends = ticker.dividends
# Returns: Date, Dividend amount

# Get splits
splits = ticker.splits
# Returns: Date, Split ratio

# Get all actions
actions = ticker.actions
# Returns: Date, Dividends, Stock Splits
```

### Direct API (fetch_yahoo_direct.py)

The skill's direct Yahoo fetcher includes:
- Prices with both `close` and `adj_close`
- Dividends via `events=div`
- Splits via `events=splits`
- Combined via `events=div,splits`

### Adjustment Formula

For a dividend of `D` on ex-div date:
```
adjustment_factor = (close_price - D) / close_price
adj_close = close * adjustment_factor  (for all dates before ex-div)
```

### Example: XTB Dividend (5.45 PLN, ex-div 2025-06-13)

```
Date        YF Close   YF Adj_Close   Difference
2025-06-10  80.58      75.00          5.58 (adj for dividend)
2025-06-11  79.82      74.29          5.53 (adj for dividend)
2025-06-12  78.64      73.19          5.45 (= dividend amount)
2025-06-13  74.12      74.12          0.00 (ex-div, no adjustment)
```

### YF adj_close vs Stooq Comparison

```
Date        YF adj_close   Stooq Close   Diff
2025-06-10  75.00          75.01         0.01
2025-06-11  74.29          74.30         0.01
2025-06-12  73.19          73.20         0.01
2025-06-13  74.12          74.12         0.00
```

**Conclusion**: YF `adj_close` matches Stooq prices within rounding tolerance.

---

## Key Dates Terminology

### Last Cum-Dividend Date (Ostatnie notowanie z prawem do dywidendy)
- Last trading day where buying shares entitles you to the dividend
- Example: 2025-06-12 for XTB

### Ex-Dividend Date (Ex-div)
- First trading day WITHOUT dividend rights
- Usually = last_cum_div_date + 1 business day
- Example: 2025-06-13 for XTB
- Yahoo Finance reports dividend on this date

### Payment Date (Dzień wypłaty)
- When dividend is actually paid to shareholders
- Example: 2025-06-25 for XTB

### Record Date
- Date when company determines shareholders entitled to dividend
- Usually = ex_div_date + settlement period

---

## Practical Guidance

### For Performance Attribution

Use **Stooq** or **Yahoo adj_close**:
```python
# Both give dividend-adjusted returns
stooq_return = (stooq_close_t1 / stooq_close_t0) - 1
yf_return = (yf_adj_close_t1 / yf_adj_close_t0) - 1
# These should match
```

### For P&L Calculation

Use **Yahoo close** (raw prices):
```python
# Actual P&L on a position
pnl = (yf_close_sell - yf_close_buy) * shares
# Then add dividend income separately
total_return = pnl + dividends_received
```

### For Cross-Source Validation

Compare Yahoo `adj_close` with Stooq:
```python
# Should match within ~1%
diff_pct = abs(yf_adj_close - stooq_close) / stooq_close * 100
assert diff_pct < 1.0, f"Data mismatch: {diff_pct:.2f}%"
```

### Handling Multiple Dividends

Tickers with multiple dividends in a period will have larger cumulative adjustments:

```
Ticker   Single Div   Adjustment   Notes
XTB      5.45         5.45         Single dividend
TXT      1.66         6.66         ~4 dividends accumulated
BHW      10.29        13.91        Multiple dividends
```

---

## Validation Script

Use `scripts/claude/validate_yfinance_all.py` to validate data:

```bash
python scripts/claude/validate_yfinance_all.py
```

Output includes:
- Per-ticker comparison of YF adj_close vs Stooq
- Mean and max differences
- Identification of problematic tickers

---

## Data Quality Notes

### Known Issues

1. **DOM**: ~2.2% avg difference between YF and Stooq
2. **ASB**: ~1.7% avg difference between YF and Stooq

These may be due to:
- Different ex-div date handling
- Corporate action timing differences
- Data source discrepancies

### Recommendations

1. **Primary source**: Stooq for Polish stocks (consistent dividend adjustment)
2. **Validation**: Cross-check with Yahoo Finance adj_close
3. **Raw prices**: Use Yahoo Finance close when needed
4. **Dividends data**: Use Yahoo Finance or BiznesRadar

---

## Summary

| Need | Recommended Source | Column/Field |
|------|-------------------|--------------|
| Dividend-adjusted prices | Stooq | Close (only option) |
| Dividend-adjusted prices | Yahoo Finance | adj_close |
| Raw/unadjusted prices | Yahoo Finance | close |
| Dividend amounts | Yahoo Finance | dividends |
| Total return calculation | Either Stooq or YF adj_close | - |
| Actual P&L calculation | Yahoo Finance | close + dividends |
