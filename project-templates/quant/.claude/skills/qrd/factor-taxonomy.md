# Factor & Alpha Taxonomy

Common factors and alpha sources for systematic strategies.

## Classic Equity Factors (Fama-French Extended)

| Factor | Construction | Economic Rationale |
|--------|--------------|-------------------|
| Market (MKT) | Market return - Rf | Equity risk premium |
| Size (SMB) | Small - Big market cap | Compensation for illiquidity |
| Value (HML) | High - Low book/market | Mean reversion, distress risk |
| Momentum (UMD) | Winners - Losers (12-1m) | Behavioral: underreaction |
| Profitability (RMW) | Robust - Weak gross profit | Quality premium |
| Investment (CMA) | Conservative - Aggressive | Overinvestment penalty |

## Alternative Factors

### Quality
- Gross profitability (GP/Assets)
- ROE stability
- Accruals (low better)
- Leverage (low better)

### Low Volatility
- Historical volatility (prefer low)
- Beta (prefer low)
- Idiosyncratic volatility

### Liquidity
- Bid-ask spread
- Amihud illiquidity
- Turnover

## Crypto-Specific Factors

| Factor | Construction | Rationale |
|--------|--------------|-----------|
| Size | Market cap ranked | Liquidity premium |
| Momentum | 7d, 30d returns | Trend continuation |
| Volume | Trading volume / mcap | Activity/attention |
| Network | Active addresses, txns | Fundamental usage |
| NVT | Network value / txn volume | Valuation metric |
| MVRV | Market cap / realized cap | Mean reversion signal |

## Signal Categories

### Price-Based
- Momentum (time-series, cross-sectional)
- Mean reversion
- Volatility breakout
- Support/resistance

### Volume-Based
- Volume momentum
- On-balance volume
- VWAP deviation
- Order flow imbalance

### Fundamental
- Earnings surprise
- Analyst revisions
- Valuation ratios
- Quality scores

### Alternative Data
- Sentiment (news, social)
- Web traffic
- App downloads
- Satellite imagery
- Credit card data

## Signal Combination Methods

### Simple
- Equal weight
- Rank-based
- Z-score averaging

### Advanced
- IC-weighted (inverse covariance)
- Machine learning (random forest, XGBoost)
- Neural networks

## Decay Profiles

| Signal Type | Typical Half-Life | Rebalance Frequency |
|-------------|-------------------|---------------------|
| HFT signals | Seconds-minutes | Continuous |
| Intraday momentum | Hours | Hourly |
| Short-term reversal | 1-5 days | Daily |
| Cross-sectional momentum | 1-3 months | Weekly-monthly |
| Value | 1-3 years | Quarterly |
| Quality | 1-5 years | Quarterly |
