# Long-History Asset Series Construction

How to build multi-decade monthly total return series for investment research. Uses ETF/fund data as primary source with academic/government backfill for earlier periods.

## When to Use

- Portfolio backtesting requiring 30+ years of data
- Risk calibration across multiple crisis periods (GFC, dot-com, oil crisis, etc.)
- Strategic asset allocation studies
- Long-run return and risk estimation

## Academic Data Sources

### Damodaran (NYU Stern)

**URL**: `pages.stern.nyu.edu/~adamodar/` → "Historical Returns on Stocks, Bonds and Bills"
**File**: `histretSP.xls` (download as `damodaran_histret.xls`)
**Coverage**: Annual returns 1928-2024
**Series**: S&P 500 (with dividends), 3-month T-Bill, 10Y T-Bond, Gold
**Frequency**: Annual only

```python
def load_damodaran(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Returns by year", header=None)
    # Find header row containing "Year"
    header_row = None
    for i, row in df.iterrows():
        if any(str(v).strip() == "Year" for v in row.values if pd.notna(v)):
            header_row = i
            break
    data = df.iloc[header_row + 1:].copy()
    data.columns = df.iloc[header_row].values
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    data = data[data["Year"].notna() & (data["Year"] >= 1928)].copy()
    data = data.set_index(data["Year"].astype(int))

    result = pd.DataFrame(index=data.index)
    result["sp500"] = pd.to_numeric(data["S&P 500 (includes dividends)"], errors="coerce")
    result["tbill"] = pd.to_numeric(data["3-month T.Bill"], errors="coerce")
    result["tbond"] = pd.to_numeric(data["US T. Bond (10-year)"], errors="coerce")
    result["gold"] = pd.to_numeric(data["Gold*"], errors="coerce")
    return result.dropna()
```

**Gotchas**:
- Column names vary between Excel versions — search for "Year" row dynamically
- Returns are decimal fractions (0.12 = 12%), not percentages
- Annual only — need interpolation or Shiller for monthly

### Shiller (ie_data.xls)

**URL**: `shillerdata.com` → "Online Data Robert Shiller"
**File**: `ie_data.xls`
**Coverage**: Monthly from 1871+
**Series**: S&P 500 price, dividends, earnings, CPI, 10Y GS10 yield
**Frequency**: Monthly

```python
def load_shiller(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Data", header=None, engine="xlrd")
    data = df.iloc[8:].copy()  # Skip header rows
    data.columns = range(data.shape[1])
    data = data[pd.to_numeric(data[0], errors="coerce").notna()].copy()

    # Date is encoded as YYYY.MM (e.g., 2024.01)
    data["year"] = data[0].astype(float).apply(lambda x: int(x))
    data["month"] = data[0].astype(float).apply(lambda x: round((x % 1) * 100))
    data["month"] = data["month"].clip(1, 12).astype(int)
    data["date"] = pd.to_datetime(
        data["year"].astype(str) + "-" + data["month"].astype(str).str.zfill(2) + "-01"
    )
    data = data.set_index("date").sort_index()

    result = pd.DataFrame(index=data.index)
    result["sp500_price"] = pd.to_numeric(data[1], errors="coerce")
    result["sp500_dividend"] = pd.to_numeric(data[2], errors="coerce")  # Annual rate
    result["gs10"] = pd.to_numeric(data[6], errors="coerce")           # 10Y yield %
    return result.dropna(subset=["sp500_price"])
```

**Gotchas**:
- Date column is float (2024.01 = Jan 2024) — parse carefully
- Dividends are annualized — divide by 12 for monthly
- Needs `engine="xlrd"` for .xls format
- Column positions may shift — verify against headers

### FRED (Federal Reserve Economic Data)

**URL**: `fred.stlouisfed.org`
**Key series**: TB3MS (3-month T-bill rate), DGS10 (10Y treasury yield)
**Coverage**: TB3MS from 1934+, monthly
**Access**: Free CSV download, no API key needed for direct download

```python
def fetch_fred_tbill() -> pd.Series:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS"
    df = pd.read_csv(url)
    date_col = [c for c in df.columns if "date" in c.lower()][0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    series = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
    monthly_return = series / 100 / 12  # Annual % → monthly return
    return monthly_return.resample("ME").last().dropna()
```

### Stooq (Gold)

**URL**: `stooq.pl/q/d/l/`
**Coverage**: XAUUSD from 1968+, monthly
**Access**: Free CSV download

```python
def fetch_gold_stooq() -> pd.Series:
    url = "https://stooq.pl/q/d/l/?s=xauusd&d1=19680101&d2=20251231&i=m"
    df = pd.read_csv(url)
    df.columns = ["Date", "Open", "High", "Low", "Close"]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    gold_return = df["Close"].pct_change().dropna()
    gold_return.index = gold_return.index + pd.offsets.MonthEnd(0)
    return gold_return
```

**Why Stooq for gold**: More reliable long history than Yahoo for commodities. Goes back to 1968 (end of gold standard era).

## Construction Patterns

### Pattern 1: ETF-Primary Splice

Use real ETF/fund data where available, synthetic backfill for earlier dates.

```python
def splice_series(primary: pd.Series, backfill: pd.Series, name: str) -> pd.Series:
    """Use primary where available, backfill for earlier dates. No blending."""
    if len(primary) == 0:
        result = backfill.copy()
        result.name = name
        return result

    splice_date = primary.index.min()
    backfill_part = backfill[backfill.index < splice_date]
    result = pd.concat([backfill_part, primary]).sort_index()
    result = result[~result.index.duplicated(keep="last")]
    result.name = name
    return result
```

**Key decisions**:
- No overlap blending — clean switch at splice point
- Primary takes precedence (keep="last" for duplicates)
- Log the splice point for documentation

### Pattern 2: Synthetic Bond Return from Yield

Convert a yield time series to monthly bond total return using duration approximation.

```python
def build_synthetic_bond_return(yields: pd.Series, duration: float = 7.0) -> pd.Series:
    """Monthly total return from yield series.

    Args:
        yields: Monthly yield in decimal (e.g., 0.05 for 5%)
        duration: Modified duration (years). Use ~7 for 10Y benchmark, ~2 for short.
    """
    coupon = yields.shift(1) / 12                      # Monthly income
    dy = yields - yields.shift(1)                       # Yield change
    price_change = -duration * dy                       # Price return (duration approx)
    monthly_return = (coupon + price_change).dropna()
    monthly_return.index = monthly_return.index + pd.offsets.MonthEnd(0)
    return monthly_return
```

**Duration choices**:
- `duration=7.0` → approximates Bloomberg Aggregate / VBMFX
- `duration=2.0` → approximates short treasury / VFISX
- Convexity ignored — acceptable for monthly frequency

### Pattern 3: Equity Total Return from Price + Dividends

```python
def build_equity_total_return(price: pd.Series, annual_dividend: pd.Series) -> pd.Series:
    """Monthly total return from price and annualized dividend series."""
    monthly_dividend = annual_dividend / 12
    total_return = (price + monthly_dividend) / price.shift(1) - 1
    ret = total_return.dropna()
    ret.index = ret.index + pd.offsets.MonthEnd(0)
    return ret
```

### Pattern 4: T-Bill Yield to Monthly Return

```python
# FRED TB3MS is annualized %, convert to monthly return
monthly_return = annual_pct / 100 / 12
```

### Pattern 5: Blended Component Series

For asset classes that are themselves blends (e.g., FI_SHORT = 50% T-bill + 50% short treasury):

```python
def build_blended_series(components: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """Blend multiple component series with fixed weights."""
    df = pd.DataFrame(components).dropna()
    result = sum(df[name] * w for name, w in weights.items())
    return result
```

### Pattern 6: ETF Monthly Return from yfinance

```python
def fetch_etf_monthly(ticker: str, start: str = "1976-01-01") -> pd.Series:
    """Fetch monthly total returns for ETF/fund via yfinance."""
    df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    ts = df[col].squeeze().sort_index()
    monthly = ts.resample("ME").last().dropna()
    returns = monthly.pct_change().dropna()
    returns.name = ticker
    return returns
```

**Use `Adj Close`** for total return (includes dividends). `Close` is price return only.

## Standard Asset Class Recipes

### Equity (S&P 500 Total Return)

```
Primary:  VFINX (Vanguard 500 Index Fund, 1976+) via yfinance
Backfill: Shiller S&P 500 price + dividends → total return (1871+)
Splice:   ~1976
Result:   Monthly TR, 1871-2025
```

### Core Bonds (Aggregate, ~5% vol)

```
Primary:  VBMFX (Vanguard Total Bond Market, 1987+) via yfinance
Backfill: Shiller GS10 yield → synthetic bond return, duration=7 (1871+)
Splice:   ~1987
Result:   Monthly TR, 1871-2025
```

### Short Duration (~1.5% vol)

```
Primary:  50% SHV (T-bill ETF, 2007+) + 50% VFISX (short treasury, 1991+)
Backfill: 50% FRED TB3MS (1934+) + 50% synthetic bond dur=2 from Shiller
Splice:   ~1991 (VFISX), ~2007 (SHV)
Result:   Monthly TR, 1934-2025
```

### Commodities (Gold)

```
Primary:  Stooq XAUUSD monthly (1968+)
Backfill: N/A (or Damodaran annual gold, but loses monthly granularity)
Result:   Monthly price return, 1968-2025
Note:     Price return only — gold has no yield
```

## Validation

### Overlap Comparison

Always compare ETF vs synthetic in the overlap window:

```python
overlap = primary.index.intersection(backfill.index)
if len(overlap) > 12:
    r1 = backfill.loc[overlap]
    r2 = primary.loc[overlap]
    print(f"Correlation: {r1.corr(r2):.3f}")
    print(f"Ann return diff: {((1+r2).prod()**(12/len(overlap)) - (1+r1).prod()**(12/len(overlap)))*100:.1f}pp")
    print(f"Vol ratio: {r2.std() / r1.std():.2f}")
```

**Expected results**:
- Equity (Shiller vs VFINX): correlation >0.99
- Bonds (synthetic vs VBMFX): correlation ~0.95 (duration approximation introduces noise)
- If correlation <0.90, investigate before trusting the splice

### Full-Period Sanity Checks

After construction, verify:
- Ann. return in expected range (equity 8-11%, bonds 4-7%, T-bill 3-5%)
- Vol in expected range (equity 14-17%, bonds 5-7%, T-bill 1-2%)
- Max DD plausible (equity -45 to -55%, bonds -15 to -25%)
- No gaps in time series
- Correct number of months for the date range

## Reference Implementation

See `research/risk-profile-calibration/build_asset_data_v2.py` for the complete working implementation covering all 4 asset classes.
