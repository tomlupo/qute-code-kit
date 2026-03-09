---
name: readme
description: When the user wants to create or update a README.md file for a project. Also use when the user says "write readme," "create readme," "document this project," "project documentation," or asks for help with README.md. Creates thorough documentation for Python quantitative development and research projects.
context: fork
allowed-tools: Read, Grep, Glob
---

# README Generator — Python Quant Projects

Create comprehensive project documentation for Python quantitative development and research projects. The goal is thorough, reproducible documentation.

## Three Purposes of a README

1. **Local Development & Reproducibility** — Get the project running and reproduce results
2. **Understanding the System** — Data pipelines, models, strategies, research workflows
3. **Production & Operations** — Deploy, schedule, and maintain

## Before Writing

### Step 1: Deep Codebase Exploration

Before writing anything, explore the codebase thoroughly:

**Project structure:**
- Root directory layout, main entry points
- Project type: research, trading system, data pipeline, library, or hybrid

**Configuration files:**
- `pyproject.toml`, `requirements.txt`, `uv.lock` — dependencies
- `.env.example` — environment variables
- `Dockerfile`, `docker-compose.yml` — containerization
- `Makefile`, `.github/workflows/` — tasks and CI/CD

**Data layer:**
- Data directories (`data/raw/`, `data/processed/`)
- Storage formats (Parquet, HDF5, SQLite, PostgreSQL)
- Data vendor integrations and download scripts

**Quantitative components:**
- Strategy files, model definitions, feature engineering
- Risk management, execution, research notebooks

**Key dependencies:**
- Scientific stack (numpy, pandas, scipy, scikit-learn)
- Quant libraries (vectorbt, backtrader, QuantLib, yfinance)
- ML/DL (pytorch, xgboost, statsmodels)
- Execution (ccxt, ib_insync, alpaca)

### Step 2: Identify Project Type

| Type | Documentation Emphasis |
|------|----------------------|
| Research project | Reproducibility, notebooks, experiment tracking |
| Trading system | Data feeds, execution, risk management, deployment |
| Data pipeline | Ingestion, transformation, storage, scheduling |
| Quant library | API docs, installation, usage examples |
| Hybrid | Document each aspect |

### Step 3: Ask Only If Critical

Only ask about:
- What the project does (if not obvious from code)
- Specific credentials or broker configs needed
- Business context affecting documentation

Otherwise, proceed with exploration and writing.

## README Sections

Write these sections in order. See `references/section-templates.md` for complete markdown templates.

| # | Section | Content |
|---|---------|---------|
| 1 | **Title & Overview** | What it does, key features (2-3 sentences) |
| 2 | **Tech Stack** | All major technologies |
| 3 | **Prerequisites** | What must be installed first |
| 4 | **Getting Started** | Clone → venv → install → env setup → data → verify |
| 5 | **Architecture** | Directory structure, data flow, key components |
| 6 | **Environment Variables** | Complete reference table (required, optional, secrets) |
| 7 | **Available Commands** | Make/script targets table |
| 8 | **Testing** | How to run, test structure, writing tests |
| 9 | **Research Workflow** | Notebooks, experiment tracking, reproducibility |
| 10 | **Deployment** | Docker, scheduling, production checklist |
| 11 | **Troubleshooting** | Common errors with solutions |

Include every step. Assume the reader is on a fresh machine.

## Writing Principles

1. **Be thorough** — when in doubt, include it
2. **Use code blocks liberally** — every command should be copy-pasteable
3. **Show example output** — when helpful, show what the user should expect
4. **Explain the why** — don't just say "run this," explain what it does
5. **Use tables for reference** — env vars, commands, options
6. **Keep commands current** — use `uv` if the project uses it, `pip` if pip, etc.
7. **Include a TOC** — for READMEs over ~200 lines
8. **Emphasize reproducibility** — pin versions, document data sources, note random seeds
9. **Respect data sensitivity** — never include real API keys or proprietary details

## Output

Write the README directly to `README.md` in the project root with proper markdown formatting, code blocks with language hints, and clear section hierarchy.

## Reference Documentation

| Reference | When to Load |
|-----------|-------------|
| [section-templates.md](references/section-templates.md) | Complete markdown templates for all 11 sections |
