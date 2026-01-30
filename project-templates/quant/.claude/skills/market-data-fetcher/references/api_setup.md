# API Setup & Configuration Guide

Configuration instructions for data sources requiring authentication or setup.

## Overview

Most data sources work out-of-the-box without configuration:
- **Stooq**: No setup required
- **NBP API**: No setup required
- **Yahoo Finance**: No setup required (via yfinance)
- **CCXT/Crypto**: No setup required (via ccxt package)
- **Tiingo**: **API key required** (free)
- **FRED**: **API key required** (free)
- **pandas-datareader**: No setup (but some sub-sources may need keys)

---

## FRED API Setup

### Why FRED Requires API Key

FRED (Federal Reserve Economic Data) requires a free API key to access their economic data. This helps them manage usage and provide better service.

### Step 1: Register for API Key

1. Visit: https://fred.stlouisfed.org/
2. Click "My Account" (top right) → "API Keys"
3. Or go directly to: https://fredaccount.stlouisfed.org/apikeys
4. Click "Request API Key"
5. Fill out the form:
   - Name your application (e.g., "Market Data Fetcher")
   - Agree to terms
   - Submit
6. You'll receive an API key immediately (32-character string)

**Example API key format**: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### Step 2: Configure API Key

You have three options for providing the API key:

#### Option 1: Environment Variable (Recommended)

Set the `FRED_API_KEY` environment variable:

**Windows (PowerShell)**:
```powershell
$env:FRED_API_KEY = "your_api_key_here"

# Make permanent (System Properties → Environment Variables)
[System.Environment]::SetEnvironmentVariable('FRED_API_KEY', 'your_api_key_here', 'User')
```

**Windows (Command Prompt)**:
```cmd
set FRED_API_KEY=your_api_key_here

# Make permanent
setx FRED_API_KEY "your_api_key_here"
```

**Linux/Mac**:
```bash
export FRED_API_KEY="your_api_key_here"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export FRED_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option 2: Config File

Create a text file with your API key:

1. Create directory (if doesn't exist):
   ```bash
   mkdir -p config
   ```

2. Create file `config/fred_api_key.txt` with your key:
   ```
   your_api_key_here
   ```

3. The fetcher will automatically look for:
   - `config/fred_api_key.txt`
   - `U:/config_files/fred_api_key.txt`
   - `~/.fred_api_key`

#### Option 3: Direct Parameter

Pass the API key directly in code:

```python
from scripts.fetch_fred import fetch_fred

df = fetch_fred('GDP', api_key='your_api_key_here')
```

Or with unified fetcher:

```python
from scripts.fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher(fred_api_key='your_api_key_here')
df = fetcher.fetch('GDP')
```

### Step 3: Verify Setup

Test that FRED API key is working:

```python
from scripts.fetch_fred import FREDFetcher

try:
    fetcher = FREDFetcher()  # Will auto-detect key
    df = fetcher.fetch('GDP', start_date='20200101')
    print(f"Success! Retrieved {len(df)} data points")
    print(df.head())
except ValueError as e:
    print(f"API key not configured: {e}")
```

### FRED Rate Limits

- **No documented rate limits** for basic usage
- Be respectful: Don't hammer the API
- Caching is enabled by default (24 hours)
- For heavy usage, contact FRED about higher limits

---

## Tiingo API Setup

### Why Tiingo Requires API Key

Tiingo provides high-quality US stock data with a generous free tier (1,000 requests/day). The API key helps them manage usage and provide better service.

### Step 1: Register for API Key

1. Visit: https://api.tiingo.com/
2. Click "Sign Up" (top right)
3. Create account with email
4. Verify email
5. Go to "API" section in your account
6. Copy your API token (40-character string)

**Example API key format**: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`

### Step 2: Configure API Key

#### Option 1: Environment Variable (Recommended)

**Windows (PowerShell)**:
```powershell
$env:TIINGO_API_KEY = "your_api_key_here"

# Make permanent
[System.Environment]::SetEnvironmentVariable('TIINGO_API_KEY', 'your_api_key_here', 'User')
```

**Windows (Command Prompt)**:
```cmd
set TIINGO_API_KEY=your_api_key_here

# Make permanent
setx TIINGO_API_KEY "your_api_key_here"
```

**Linux/Mac**:
```bash
export TIINGO_API_KEY="your_api_key_here"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export TIINGO_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option 2: Direct Parameter

Pass the API key directly in code:

```python
from scripts.fetch_tiingo import fetch_tiingo

df = fetch_tiingo('AAPL', api_key='your_api_key_here')
```

Or with unified fetcher:

```python
from scripts.fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher(tiingo_api_key='your_api_key_here')
df = fetcher.fetch('AAPL')
```

### Step 3: Verify Setup

Test that Tiingo API key is working:

```python
from scripts.fetch_tiingo import TiingoFetcher

try:
    fetcher = TiingoFetcher()  # Will auto-detect key from env
    df = fetcher.fetch('AAPL', start_date='20240101')
    print(f"Success! Retrieved {len(df)} data points")
    print(df.head())
except ValueError as e:
    print(f"API key not configured: {e}")
```

### Tiingo Rate Limits

**Free tier limits**:
- 50 requests per hour
- 1,000 requests per day
- 500 unique symbols per month

Caching is enabled by default (24 hours) to minimize requests.

---

## CCXT (Cryptocurrency) Setup

### No API Key Required

CCXT provides free access to public historical data from 100+ cryptocurrency exchanges. No registration or API key needed for:
- Historical OHLCV data
- Market prices
- Trading pair information

### Step 1: Install CCXT Package

```bash
pip install ccxt
```

### Step 2: Verify Setup

Test that CCXT is working:

```python
from scripts.fetch_ccxt import fetch_crypto

try:
    df = fetch_crypto('BTC/USDT', start_date='20240101')
    print(f"Success! Retrieved {len(df)} candles")
    print(df.head())
except ImportError:
    print("CCXT not installed. Run: pip install ccxt")
```

### Supported Exchanges

By default, the skill uses Binance. You can switch exchanges:

```python
from scripts.fetch_unified import UnifiedMarketDataFetcher

# Use Kraken instead of Binance
fetcher = UnifiedMarketDataFetcher(crypto_exchange='kraken')
df = fetcher.fetch('BTC/USD')
```

Supported exchanges include:
- `binance` (default)
- `kraken`
- `coinbasepro`
- `kucoin`
- `bybit`
- `okx`
- `bitfinex`
- And 100+ more

### Rate Limits

CCXT has built-in rate limiting that respects exchange-specific limits. Additional caching (24 hours default) reduces requests further.

---

## Package Installation

### Required Packages

These are required for basic functionality:

```bash
pip install pandas requests
```

### Optional Packages

Install as needed for specific sources:

#### Yahoo Finance Support

```bash
pip install yfinance
```

Without yfinance:
- Yahoo Finance fetcher will not be available
- Can still use via pandas-datareader fallback

#### pandas-datareader Support

```bash
pip install pandas-datareader
```

Without pandas-datareader:
- pandas-datareader fetcher will not be available
- Individual source fetchers still work

#### CCXT (Cryptocurrency) Support

```bash
pip install ccxt
```

Without ccxt:
- Cryptocurrency fetcher will not be available
- Cannot fetch data from Binance/other exchanges

#### Full Installation

Install everything:

```bash
pip install pandas requests yfinance pandas-datareader ccxt
```

Or using requirements file:

```bash
# Create requirements.txt
echo "pandas>=1.5.0" > requirements.txt
echo "requests>=2.28.0" >> requirements.txt
echo "yfinance>=0.2.0" >> requirements.txt
echo "pandas-datareader>=0.10.0" >> requirements.txt
echo "ccxt>=4.0.0" >> requirements.txt

# Install
pip install -r requirements.txt
```

---

## Project Integration

### Adding to Existing Project

If integrating into an existing project (like the performance attribution system):

1. **Copy skill to project**:
   ```bash
   cp -r market-data-fetcher /path/to/project/
   ```

2. **Install dependencies**:
   ```bash
   cd /path/to/project
   pip install pandas requests yfinance pandas-datareader
   ```

3. **Configure FRED** (if needed):
   ```bash
   # Option 1: Environment variable
   export FRED_API_KEY="your_key"

   # Option 2: Config file
   echo "your_key" > U:/config_files/fred_api_key.txt
   ```

4. **Import in your code**:
   ```python
   import sys
   sys.path.append('market-data-fetcher/scripts')

   from fetch_unified import fetch_market_data

   # Use it
   df = fetch_market_data('pko', start_date='20240101')
   ```

---

## Cache Configuration

### Cache Location

By default, data is cached in:
```
data/cache/market_data/
├── stooq/
├── nbp/
├── yahoo/
├── fred/
└── pandas_datareader/
```

### Custom Cache Directory

Change cache location:

```python
from scripts.utils import CacheManager

# Custom cache location
cache = CacheManager(cache_dir='custom/cache/path')
```

Or when creating fetchers:

```python
from scripts.fetch_unified import UnifiedMarketDataFetcher

# This will use custom cache for all sources
import os
os.environ['CACHE_DIR'] = 'custom/cache/path'

fetcher = UnifiedMarketDataFetcher()
```

### Cache Validity

Control how long cache is valid:

```python
# Cache for 48 hours instead of default 24
fetcher = UnifiedMarketDataFetcher(cache_hours=48)

# Disable caching
fetcher = UnifiedMarketDataFetcher(use_cache=False)
```

### Clear Cache

Manually clear cache:

```bash
# Clear all cache
rm -rf data/cache/market_data/*

# Clear specific source
rm -rf data/cache/market_data/stooq/*
```

---

## Troubleshooting

### FRED API Key Not Found

**Error**:
```
ValueError: FRED API key required. Set FRED_API_KEY environment variable...
```

**Solutions**:
1. Verify environment variable is set:
   ```bash
   echo $FRED_API_KEY  # Linux/Mac
   echo %FRED_API_KEY%  # Windows CMD
   $env:FRED_API_KEY    # Windows PowerShell
   ```

2. Check config file exists and has correct permissions:
   ```bash
   cat config/fred_api_key.txt
   ```

3. Verify no extra spaces in API key

4. Try passing key directly as parameter

### Package Import Errors

**Error**:
```
ModuleNotFoundError: No module named 'yfinance'
```

**Solution**:
```bash
pip install yfinance
```

### Permission Denied (Config File)

**Error**:
```
PermissionError: [Errno 13] Permission denied: 'config/fred_api_key.txt'
```

**Solutions**:
1. Check file permissions:
   ```bash
   chmod 644 config/fred_api_key.txt
   ```

2. Use environment variable instead

3. Check directory permissions

### Cache Write Errors

**Error**:
```
PermissionError: [Errno 13] Permission denied: 'data/cache/market_data/...'
```

**Solutions**:
1. Create cache directory:
   ```bash
   mkdir -p data/cache/market_data
   ```

2. Check directory permissions:
   ```bash
   chmod 755 data/cache/market_data
   ```

3. Use custom cache directory with proper permissions

### Rate Limiting (429 Errors)

**Error**:
```
requests.exceptions.HTTPError: 429 Client Error: Too Many Requests
```

**Solutions**:
1. Enable caching (default)
2. Increase delay between requests:
   ```python
   from scripts.utils import get_rate_limiter
   limiter = get_rate_limiter()
   limiter.min_delay = 5.0  # 5 seconds
   ```
3. Batch requests instead of many individual calls
4. Wait and retry later

---

## Security Best Practices

### API Key Security

**DO**:
- Use environment variables for production
- Keep API keys out of version control
- Use config files with restricted permissions
- Rotate keys periodically

**DON'T**:
- Commit API keys to Git
- Share API keys publicly
- Hardcode API keys in scripts
- Use API keys in client-side code

### .gitignore Configuration

Add to your `.gitignore`:
```
# API keys
config/fred_api_key.txt
*.key
*_api_key.txt

# Cache
data/cache/

# Environment files
.env
.env.local
```

---

## Testing Configuration

### Quick Test Script

Save as `test_config.py`:

```python
"""Test market data fetcher configuration."""

def test_all_sources():
    """Test all data sources."""
    from scripts.fetch_unified import UnifiedMarketDataFetcher

    fetcher = UnifiedMarketDataFetcher()

    print("Available sources:", fetcher.list_available_sources())
    print()

    # Test each source
    tests = [
        ('Stooq (Polish stock)', 'pko', 'stooq'),
        ('NBP (PLN rate)', 'USD', 'nbp'),
        ('Yahoo (US stock)', 'AAPL', 'yahoo'),
        ('Tiingo (US stock)', 'MSFT', 'tiingo'),
        ('CCXT (Crypto)', 'BTC/USDT', 'ccxt'),
        ('FRED (Economic data)', 'GDP', 'fred'),
    ]

    for name, ticker, source in tests:
        print(f"Testing {name}...")
        try:
            if source in fetcher.fetchers:
                df = fetcher.fetch(ticker, source=source, start_date='20240101', end_date='20240131')
                print(f"  ✓ Success: {len(df)} rows")
            else:
                print(f"  ✗ {source.upper()} not available")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        print()

if __name__ == '__main__':
    test_all_sources()
```

Run test:
```bash
python test_config.py
```

---

## Additional Resources

### Documentation Links

- **FRED API**: https://fred.stlouisfed.org/docs/api/
- **Tiingo API**: https://api.tiingo.com/documentation/general/overview
- **CCXT**: https://github.com/ccxt/ccxt/wiki
- **yfinance**: https://github.com/ranaroussi/yfinance
- **pandas-datareader**: https://pandas-datareader.readthedocs.io/
- **Stooq**: https://stooq.pl/
- **NBP API**: http://api.nbp.pl/

### Support

For issues with:
- **This skill**: Check GitHub issues or documentation
- **FRED API**: https://fred.stlouisfed.org/docs/api/fred/
- **Tiingo API**: https://api.tiingo.com/documentation/
- **CCXT**: https://github.com/ccxt/ccxt/issues
- **yfinance**: https://github.com/ranaroussi/yfinance/issues
- **pandas-datareader**: https://github.com/pydata/pandas-datareader/issues
