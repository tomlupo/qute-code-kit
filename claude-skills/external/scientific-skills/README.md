# Scientific Skills for Quantitative Investing

A curated subset of [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) focused on quantitative finance, portfolio management, and investment research.

## Skills Overview

### Machine Learning & Statistical Modeling

| Skill                 | Use Case                                                                                |
| --------------------- | --------------------------------------------------------------------------------------- |
| **scikit-learn**      | Factor models, portfolio classification, return prediction, cross-validation            |
| **pytorch-lightning** | Deep learning alpha signals, neural network factor models                               |
| **statsmodels**       | Regression analysis, time series econometrics, Fama-French models, ARIMA/VAR            |
| **scikit-survival**   | Event-time modeling, trade duration analysis, regime survival                           |
| **pymc**              | Bayesian portfolio optimization, hierarchical factor models, uncertainty quantification |
| **aeon**              | Time series classification, regime detection, temporal pattern recognition              |
| **shap**              | Model interpretability, factor importance attribution                                   |
| **torch_geometric**   | Graph neural networks for asset relationships, supply chain modeling                    |
| **transformers**      | NLP for sentiment analysis, earnings call processing                                    |

### Optimization & Simulation

| Skill     | Use Case                                                                           |
| --------- | ---------------------------------------------------------------------------------- |
| **pymoo** | Multi-objective portfolio optimization (risk/return/constraints), Pareto frontiers |
| **simpy** | Backtesting simulation, order flow modeling, market microstructure                 |
| **sympy** | Symbolic math for derivative pricing, analytical solutions                         |

### Data Processing & Engineering

| Skill      | Use Case                                                    |
| ---------- | ----------------------------------------------------------- |
| **dask**   | Large-scale financial data processing, parallel computation |
| **polars** | Fast DataFrame operations, tick data processing             |
| **vaex**   | Out-of-core DataFrames for massive datasets                 |

### Analysis & Visualization

| Skill                         | Use Case                                                          |
| ----------------------------- | ----------------------------------------------------------------- |
| **statistical-analysis**      | Hypothesis testing for strategy validation, significance tests    |
| **exploratory-data-analysis** | Factor return analysis, data quality checks                       |
| **networkx**                  | Correlation networks, sector clustering, portfolio graph analysis |
| **matplotlib**                | Performance charts, drawdown plots                                |
| **seaborn**                   | Factor tearsheets, heatmaps, distribution plots                   |
| **plotly**                    | Interactive dashboards, real-time monitoring                      |
| **scientific-visualization**  | Publication-quality figures                                       |
| **umap-learn**                | Dimensionality reduction, market regime visualization             |

### Research & Literature

| Skill                   | Use Case                                         |
| ----------------------- | ------------------------------------------------ |
| **openalex-database**   | Academic finance paper search, citation networks |
| **perplexity-search**   | Real-time market research, news analysis         |
| **literature-review**   | Systematic review of factor research             |
| **citation-management** | Reference management, BibTeX generation          |

## Usage with Claude Code

Reference these skills in your `CLAUDE.md`:

```markdown
## Skills
- Use skills in `claude-skills/scientific-skills/` for quantitative analysis
- statsmodels for regression and time series
- pymoo for portfolio optimization
- scikit-learn for factor models
```

## Directory Structure

```
scientific-skills/
├── scikit-learn/
│   ├── SKILL.md
│   └── references/
├── statsmodels/
│   ├── SKILL.md
│   └── references/
├── pymoo/
│   ├── SKILL.md
│   └── references/
└── ... (27 skills total)
```

## License

Skills are from [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) (MIT License).
Individual skills may have their own licenses - check each `SKILL.md` for details.

## Source

Curated from K-Dense-AI scientific skills collection, selecting skills relevant for:

- Systematic trading strategy development
- Portfolio construction and optimization
- Factor investing and alpha research
- Risk management and attribution
- Investment research automation
