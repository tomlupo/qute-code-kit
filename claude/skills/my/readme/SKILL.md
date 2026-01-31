---
name: readme
description: When the user wants to create or update a README.md file for a project. Also use when the user says "write readme," "create readme," "document this project," "project documentation," or asks for help with README.md. This skill creates absurdly thorough documentation for Python quantitative development and research projects, covering local setup, architecture, data pipelines, and reproducibility.
context: fork
---

# README Generator — Python Quantitative Development & Research

You are an expert technical writer creating comprehensive project documentation for Python quantitative development and research projects. Your goal is to write a README.md that is absurdly thorough—the kind of documentation you wish every quant project had.

## The Three Purposes of a README

1. **Local Development & Reproducibility** - Help any developer or researcher get the project running locally and reproduce results
2. **Understanding the System** - Explain in great detail how the project works: data pipelines, models, strategies, and research workflows
3. **Production & Operations** - Cover everything needed to deploy, schedule, and maintain in production

---

## Before Writing

### Step 1: Deep Codebase Exploration

Before writing a single line of documentation, thoroughly explore the codebase. You MUST understand:

**Project Structure**
- Read the root directory structure
- Identify the project type: research project, trading system, data pipeline, library/package, or hybrid
- Find the main entry point(s) — scripts, CLI tools, notebooks, or orchestration files
- Map out the directory organization (src/, notebooks/, data/, strategies/, models/, etc.)

**Configuration Files**
- `pyproject.toml`, `setup.py`, `setup.cfg` — packaging and metadata
- `requirements.txt`, `requirements-dev.txt`, `Pipfile`, `poetry.lock`, `uv.lock` — dependencies
- `conda.yml` or `environment.yml` — Conda environments
- `.env.example`, `.env.sample` — environment variables (API keys, database URIs, broker credentials)
- `config/`, `settings.py`, `conf.py`, YAML/TOML config files — application configuration
- `Dockerfile`, `docker-compose.yml` — containerization
- `.github/workflows/`, `.gitlab-ci.yml` — CI/CD
- `Makefile`, `justfile`, `taskfile.yml` — task runners
- `pre-commit-config.yaml` — code quality hooks

**Data Layer**
- Data directories (`data/raw/`, `data/processed/`, `data/external/`)
- Database schemas, migration files (Alembic, etc.)
- Data catalogs or registries
- Data download/ingestion scripts
- Storage formats used (Parquet, HDF5, Arrow, CSV, Feather, SQLite, PostgreSQL, TimescaleDB)
- Data vendor integrations (Bloomberg, Refinitiv, Polygon, Alpaca, IEX, FRED, Quandl/Nasdaq Data Link)

**Quantitative Components**
- Strategy files (backtesting logic, signal generation, portfolio construction)
- Model definitions (statistical, ML, or deep learning models)
- Feature engineering pipelines
- Risk management modules
- Execution/order management logic
- Research notebooks with analysis

**Key Dependencies**
- Core scientific stack (numpy, pandas, scipy, scikit-learn)
- Quant-specific libraries (zipline, backtrader, vectorbt, bt, qstrader, pyfolio, empyrical, alphalens)
- Data libraries (yfinance, pandas-datareader, arctic, QuantLib, ta-lib)
- ML/DL frameworks (pytorch, tensorflow, xgboost, lightgbm, statsmodels)
- Visualization (matplotlib, plotly, seaborn, bokeh)
- Execution/broker APIs (ccxt, ib_insync, alpaca-trade-api)
- Workflow orchestration (prefect, dagster, airflow, luigi)
- Note any system-level dependencies (TA-Lib C library, HDF5, etc.)

**Scripts and Commands**
- `scripts/` directory for data ingestion, model training, backtesting
- CLI entry points (click, typer, argparse)
- Makefile or justfile targets
- Jupyter notebooks in `notebooks/`
- Scheduled jobs (cron, systemd timers, Prefect/Dagster schedules)

### Step 2: Identify Project Type

Determine the primary project type to tailor documentation:

- **Research Project** — Emphasis on reproducibility, notebooks, experiment tracking
- **Trading System** — Emphasis on data feeds, strategy execution, risk management, deployment
- **Data Pipeline** — Emphasis on ingestion, transformation, storage, scheduling
- **Quant Library/Package** — Emphasis on API docs, installation, usage examples
- **Hybrid** — Combination of the above; document each aspect

### Step 3: Ask Only If Critical

Only ask the user questions if you cannot determine:

- What the project does (if not obvious from code)
- Specific credentials, API keys, or broker configurations needed
- Business or research context that affects documentation

Otherwise, proceed with exploration and writing.

---

## README Structure

Write the README with these sections in order:

### 1. Project Title and Overview

```markdown
# Project Name

Brief description of what the project does, what markets/instruments it covers, and its purpose. 2-3 sentences max.

## Key Features

- Feature 1 (e.g., Multi-factor alpha model for US equities)
- Feature 2 (e.g., Real-time data pipeline with 1-minute resolution)
- Feature 3 (e.g., Backtesting engine with transaction cost modeling)
```

### 2. Tech Stack

List all major technologies:

```markdown
## Tech Stack

- **Language**: Python 3.11+
- **Data Processing**: pandas, numpy, polars
- **Modeling**: scikit-learn, statsmodels, PyTorch
- **Backtesting**: vectorbt / custom engine
- **Data Storage**: Parquet files, PostgreSQL + TimescaleDB
- **Data Sources**: Polygon.io, FRED, Yahoo Finance
- **Orchestration**: Prefect
- **Visualization**: matplotlib, plotly
- **Package Management**: uv / poetry / conda
```

### 3. Prerequisites

What must be installed before starting:

```markdown
## Prerequisites

- Python 3.11 or higher
- uv (recommended) or pip/conda
- PostgreSQL 15+ (if using database storage)
- TA-Lib C library (if using technical indicators)
- API keys for data providers (see Environment Variables)
```

### 4. Getting Started

The complete local development guide:

````markdown
## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/user/repo.git
cd repo
```

### 2. Create a Virtual Environment

Using uv (recommended):

```bash
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

Using conda:

```bash
conda env create -f environment.yml
conda activate project-name
```

Using venv + pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Dependencies

```bash
# Production dependencies
uv pip install -r requirements.txt

# Development dependencies (includes testing, linting, notebooks)
uv pip install -r requirements-dev.txt

# Or if using pyproject.toml
uv pip install -e ".[dev]"
```

#### System Dependencies

Some packages require system-level libraries:

```bash
# TA-Lib (macOS)
brew install ta-lib

# TA-Lib (Ubuntu/Debian)
sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib/
./configure --prefix=/usr && make && sudo make install

# HDF5 (Ubuntu/Debian)
sudo apt-get install libhdf5-dev
```

### 4. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost/quant_db` |
| `POLYGON_API_KEY` | Polygon.io API key | `pk_...` |
| `ALPACA_API_KEY` | Alpaca broker API key | `AK...` |
| `ALPACA_SECRET_KEY` | Alpaca broker secret key | `...` |
| `DATA_DIR` | Path to data directory | `./data` |

### 5. Data Setup

Download or ingest required datasets:

```bash
# Download historical price data
python scripts/download_prices.py --start 2010-01-01 --end 2024-01-01

# Build feature store
python scripts/build_features.py

# Or using Make
make data
```

### 6. Verify Installation

```bash
# Run the test suite
pytest

# Run a sample backtest
python -m src.backtest --strategy momentum --start 2020-01-01 --end 2023-12-31

# Launch Jupyter for exploration
jupyter lab
```
````

Include every step. Assume the reader is setting up on a fresh machine.

### 5. Architecture Overview

This is where you go absurdly deep:

````markdown
## Architecture

### Directory Structure

```
├── src/                          # Main source code
│   ├── __init__.py
│   ├── data/                     # Data ingestion and processing
│   │   ├── loaders.py            # Data source connectors
│   │   ├── transforms.py         # Feature engineering
│   │   ├── universe.py           # Instrument universe definitions
│   │   └── storage.py            # Data persistence layer
│   ├── models/                   # Quantitative models
│   │   ├── alpha.py              # Alpha/signal models
│   │   ├── risk.py               # Risk models (factor, covariance)
│   │   └── ml/                   # Machine learning models
│   ├── strategies/               # Trading strategies
│   │   ├── base.py               # Base strategy class
│   │   ├── momentum.py           # Momentum strategy
│   │   └── mean_reversion.py     # Mean reversion strategy
│   ├── portfolio/                # Portfolio construction
│   │   ├── optimizer.py          # Portfolio optimization
│   │   ├── constraints.py        # Position/risk constraints
│   │   └── rebalance.py          # Rebalancing logic
│   ├── execution/                # Order execution
│   │   ├── broker.py             # Broker interface
│   │   └── slippage.py           # Transaction cost models
│   ├── backtest/                 # Backtesting engine
│   │   ├── engine.py             # Core backtest loop
│   │   ├── metrics.py            # Performance metrics
│   │   └── report.py             # Report generation
│   └── utils/                    # Shared utilities
│       ├── config.py             # Configuration loader
│       ├── logging.py            # Logging setup
│       └── dates.py              # Date/calendar utilities
├── notebooks/                    # Research notebooks
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_analysis.ipynb
│   ├── 03_model_development.ipynb
│   └── 04_backtest_results.ipynb
├── data/                         # Data directory (gitignored)
│   ├── raw/                      # Raw data from sources
│   ├── processed/                # Cleaned and transformed data
│   ├── features/                 # Feature store
│   └── results/                  # Backtest results and reports
├── configs/                      # Configuration files
│   ├── base.yaml                 # Base config
│   ├── strategies/               # Strategy-specific configs
│   └── environments/             # Environment-specific configs
├── scripts/                      # Utility scripts
│   ├── download_prices.py        # Data download
│   ├── build_features.py         # Feature pipeline
│   ├── run_backtest.py           # Backtest runner
│   └── deploy_strategy.py        # Production deployment
├── tests/                        # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml                # Project config and dependencies
├── Makefile                      # Common commands
└── README.md
```

### Data Flow

```
Data Sources (APIs, Databases, Files)
         │
         ▼
   Data Ingestion (src/data/loaders.py)
         │
         ▼
  Raw Data Storage (data/raw/ — Parquet/HDF5)
         │
         ▼
  Feature Engineering (src/data/transforms.py)
         │
         ▼
  Feature Store (data/features/ — Parquet)
         │
         ▼
  Signal Generation (src/models/alpha.py)
         │
         ▼
  Portfolio Construction (src/portfolio/optimizer.py)
         │
         ▼
  Execution (src/execution/broker.py) ──or──▶ Backtesting (src/backtest/engine.py)
         │                                              │
         ▼                                              ▼
  Live Orders                                   Performance Report
```

### Key Components

**Data Layer (`src/data/`)**
- Connectors for market data APIs (Polygon, Yahoo Finance, FRED)
- Universe management — which instruments are tradable
- Feature engineering pipeline with caching
- Parquet-based storage for efficient columnar access

**Models (`src/models/`)**
- Alpha models that generate trading signals
- Risk models for covariance estimation and factor exposure
- ML models with train/validate/test split handling
- Model serialization and versioning

**Strategies (`src/strategies/`)**
- Strategy base class with common interface
- Signal combination and weighting
- Position sizing rules
- Entry/exit logic

**Portfolio Construction (`src/portfolio/`)**
- Mean-variance and risk-parity optimization
- Constraint handling (sector, position, turnover limits)
- Rebalancing schedule and threshold triggers

**Backtesting (`src/backtest/`)**
- Event-driven or vectorized backtest engine
- Transaction cost modeling (spread, commission, slippage, market impact)
- Performance metrics (Sharpe, Sortino, max drawdown, Calmar, etc.)
- Report generation with visualizations
```
````

### 6. Environment Variables

Complete reference for all env vars:

````markdown
## Environment Variables

### Required

| Variable | Description | How to Get |
|----------|-------------|------------|
| `DATABASE_URL` | Database connection string | Your database provider |
| `DATA_DIR` | Root path for data storage | Local path or mount point |

### Data Provider Keys

| Variable | Description | How to Get |
|----------|-------------|------------|
| `POLYGON_API_KEY` | Polygon.io market data | [polygon.io](https://polygon.io) |
| `FRED_API_KEY` | Federal Reserve economic data | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `QUANDL_API_KEY` | Nasdaq Data Link | [data.nasdaq.com](https://data.nasdaq.com) |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage market data | [alphavantage.co](https://www.alphavantage.co) |

### Broker Keys (Production Only)

| Variable | Description | How to Get |
|----------|-------------|------------|
| `ALPACA_API_KEY` | Alpaca trading API key | [alpaca.markets](https://alpaca.markets) |
| `ALPACA_SECRET_KEY` | Alpaca trading secret | Alpaca dashboard |
| `IB_HOST` | Interactive Brokers gateway host | TWS/Gateway setup |
| `IB_PORT` | Interactive Brokers gateway port | Default: `4001` (live), `4002` (paper) |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `CACHE_DIR` | Cache directory | `.cache/` |
| `N_JOBS` | Parallel workers for computation | `-1` (all cores) |
| `BACKTEST_START` | Default backtest start date | `2010-01-01` |
| `BACKTEST_END` | Default backtest end date | Today |
````

### 7. Available Commands

```markdown
## Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make data` | Download and process all datasets |
| `make features` | Build feature store from raw data |
| `make backtest` | Run default backtest suite |
| `make test` | Run full test suite with pytest |
| `make lint` | Run ruff linter and formatter |
| `make typecheck` | Run mypy type checking |
| `make notebook` | Launch Jupyter Lab |
| `make clean` | Remove generated files and caches |
| `make report` | Generate performance report from latest backtest |
```

### 8. Testing

````markdown
## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/unit/test_alpha.py

# Run tests matching a pattern
pytest -k "test_momentum"

# Run only fast unit tests (skip integration)
pytest -m "not integration"

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── unit/                         # Fast, isolated unit tests
│   ├── test_alpha.py             # Alpha model tests
│   ├── test_risk.py              # Risk model tests
│   ├── test_optimizer.py         # Portfolio optimizer tests
│   ├── test_transforms.py        # Feature engineering tests
│   └── test_metrics.py           # Performance metric tests
├── integration/                  # Tests requiring data/external deps
│   ├── test_data_loaders.py      # Data source integration tests
│   ├── test_backtest.py          # End-to-end backtest tests
│   └── test_execution.py         # Broker integration tests
├── fixtures/                     # Test data fixtures
│   ├── sample_prices.parquet
│   └── sample_features.parquet
└── conftest.py                   # Shared fixtures and configuration
```

### Writing Tests

```python
import pytest
import pandas as pd
import numpy as np
from src.models.alpha import MomentumAlpha
from src.backtest.metrics import sharpe_ratio, max_drawdown


class TestMomentumAlpha:
    @pytest.fixture
    def sample_prices(self):
        dates = pd.bdate_range("2020-01-01", periods=252)
        return pd.DataFrame(
            {"AAPL": np.random.lognormal(0.0005, 0.02, 252).cumprod() * 100},
            index=dates,
        )

    def test_signal_output_shape(self, sample_prices):
        model = MomentumAlpha(lookback=20)
        signals = model.generate(sample_prices)
        assert signals.shape == sample_prices.shape

    def test_signal_bounded(self, sample_prices):
        model = MomentumAlpha(lookback=20)
        signals = model.generate(sample_prices)
        assert signals.min().min() >= -1.0
        assert signals.max().max() <= 1.0


class TestMetrics:
    def test_sharpe_ratio(self):
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        sr = sharpe_ratio(returns)
        assert isinstance(sr, float)
        assert not np.isnan(sr)

    def test_max_drawdown(self):
        returns = pd.Series([-0.01, -0.02, 0.03, -0.05, 0.01])
        mdd = max_drawdown(returns)
        assert mdd <= 0  # Drawdown is negative
```

### Data Fixtures

For tests requiring market data, use fixtures in `tests/fixtures/` rather than live API calls:

```python
@pytest.fixture
def price_data():
    return pd.read_parquet("tests/fixtures/sample_prices.parquet")
```
````

### 9. Research Workflow

````markdown
## Research Workflow

### Notebooks

Research notebooks live in `notebooks/` and follow a numbered naming convention:

```
notebooks/
├── 01_data_exploration.ipynb      # Initial data analysis
├── 02_feature_analysis.ipynb      # Feature importance and selection
├── 03_model_development.ipynb     # Model training and evaluation
├── 04_backtest_results.ipynb      # Strategy backtest analysis
└── scratch/                       # Experimental notebooks (gitignored)
```

Launch Jupyter:

```bash
jupyter lab
# or
make notebook
```

### Experiment Tracking

Track experiments systematically:

```python
# Using MLflow (if configured)
import mlflow

with mlflow.start_run(run_name="momentum_v2"):
    mlflow.log_params({"lookback": 20, "universe": "SP500"})
    results = run_backtest(strategy)
    mlflow.log_metrics({
        "sharpe": results.sharpe_ratio,
        "max_drawdown": results.max_drawdown,
        "annual_return": results.annual_return,
    })
```

### Reproducibility

- Pin all dependency versions in `requirements.txt` or `pyproject.toml`
- Set random seeds for any stochastic processes
- Use config files for strategy parameters (not hardcoded values)
- Store data snapshots with timestamps for exact reproduction
- Document the data vintage (date of download) for any point-in-time data
````

### 10. Deployment & Scheduling

````markdown
## Deployment

### Docker

```bash
# Build image
docker build -t quant-project .

# Run backtest
docker run -v $(pwd)/data:/app/data quant-project python scripts/run_backtest.py

# Run with environment variables
docker run --env-file .env quant-project python scripts/run_strategy.py
```

### Scheduled Jobs

For recurring data pipelines or strategy execution:

```bash
# Using cron (simple)
# Run data download daily at 6 PM ET
0 18 * * 1-5 cd /path/to/project && .venv/bin/python scripts/download_prices.py

# Run strategy at market open
30 9 * * 1-5 cd /path/to/project && .venv/bin/python scripts/run_strategy.py
```

Using Prefect/Dagster for more complex orchestration:

```python
from prefect import flow, task
from prefect.schedules import CronSchedule

@task
def download_data():
    ...

@task
def generate_signals(data):
    ...

@task
def execute_trades(signals):
    ...

@flow(schedule=CronSchedule(cron="30 9 * * 1-5", timezone="America/New_York"))
def daily_strategy():
    data = download_data()
    signals = generate_signals(data)
    execute_trades(signals)
```

### Production Checklist

- [ ] All API keys in environment variables (never in code)
- [ ] Error alerting configured (email, Slack, PagerDuty)
- [ ] Logging to persistent storage
- [ ] Database backups scheduled
- [ ] Position and risk limits enforced in code
- [ ] Paper trading validated before live deployment
- [ ] Kill switch / emergency shutdown procedure documented
````

### 11. Troubleshooting

````markdown
## Troubleshooting

### TA-Lib Installation Fails

**Error:** `talib/_ta_lib.c: No such file or directory`

**Solution:**

Install the C library first:

```bash
# macOS
brew install ta-lib

# Ubuntu/Debian
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib/
./configure --prefix=/usr && make && sudo make install

# Then reinstall the Python wrapper
pip install ta-lib
```

### Import Errors After Install

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:**

Install the project in editable mode:

```bash
pip install -e .
```

### Memory Issues with Large Datasets

**Error:** `MemoryError` or process killed

**Solution:**

1. Use chunked reading:

```python
chunks = pd.read_parquet("large_file.parquet", columns=["close", "volume"])
```

2. Use Polars for larger-than-memory processing:

```python
import polars as pl
df = pl.scan_parquet("large_file.parquet").filter(pl.col("date") > "2020-01-01").collect()
```

3. Reduce data types:

```python
df["price"] = df["price"].astype("float32")
df["volume"] = df["volume"].astype("int32")
```

### Database Connection Issues

**Error:** `could not connect to server: Connection refused`

**Solution:**

1. Verify PostgreSQL is running: `pg_isready`
2. Check `DATABASE_URL` format: `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`
3. Ensure database exists: `createdb quant_db`

### Stale Data Cache

**Error:** Unexpected results that don't match live data

**Solution:**

```bash
# Clear data caches
make clean
# or
rm -rf .cache/ data/processed/*

# Re-download and rebuild
make data
make features
```

### NumPy/SciPy Build Issues

**Error:** `numpy.distutils` or LAPACK/BLAS errors

**Solution:**

```bash
# macOS — install Accelerate framework support
pip install --no-cache-dir numpy scipy

# Ubuntu
sudo apt-get install libopenblas-dev liblapack-dev gfortran
pip install --no-cache-dir numpy scipy
```

### Jupyter Kernel Not Found

**Error:** Kernel not showing in Jupyter

**Solution:**

```bash
# Register the virtual environment as a Jupyter kernel
python -m ipykernel install --user --name=project-name --display-name="Project Name"
```
````

### 12. Contributing (Optional)

Include if open source or team project.

### 13. License (Optional)

---

## Writing Principles

1. **Be Absurdly Thorough** — When in doubt, include it. More detail is always better.
2. **Use Code Blocks Liberally** — Every command should be copy-pasteable.
3. **Show Example Output** — When helpful, show what the user should expect to see.
4. **Explain the Why** — Don't just say "run this command," explain what it does.
5. **Assume Fresh Machine** — Write as if the reader has never seen this codebase.
6. **Use Tables for Reference** — Environment variables, commands, and options work great as tables.
7. **Keep Commands Current** — Use `uv` if the project uses it, `pip` if it uses pip, `conda` if it uses conda, etc.
8. **Include a Table of Contents** — For READMEs over ~200 lines, add a TOC at the top.
9. **Emphasize Reproducibility** — Pin versions, document data sources, note random seeds.
10. **Respect Data Sensitivity** — Never include real API keys, portfolio data, or proprietary strategy details in documentation.

---

## Output Format

Generate a complete README.md file with:

- Proper markdown formatting
- Code blocks with language hints (```bash, ```python, etc.)
- Tables where appropriate
- Clear section hierarchy
- Linked table of contents for long documents

Write the README directly to `README.md` in the project root.
