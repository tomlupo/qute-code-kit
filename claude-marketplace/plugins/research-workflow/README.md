# Research Workflow Plugin

A comprehensive research workflow plugin for ML/data science projects.

## Features

- **Hypothesis tracking** - Document and track testable hypotheses
- **Experiment logging** - Record experiments with reproducible setups
- **Finding documentation** - Capture validated findings with evidence
- **Paper reading** - Extract and analyze academic papers
- **Research index** - Maintain an overview of all research

## Commands

| Command | Description |
|---------|-------------|
| `/research:start <topic>` | Initialize research structure for a topic |
| `/research:hypothesis "<statement>"` | Document a new hypothesis |
| `/research:experiment <name>` | Log an experiment |
| `/research:finding "<title>"` | Document a validated finding |
| `/research:paper <url\|file>` | Read and extract paper insights |
| `/research:index` | Display research index |

## Quick Start

```bash
### Initialize research structure
/research:start model-optimization

### Document a hypothesis
/research:hypothesis "Dropout of 0.3 will reduce overfitting by 15%"

### Log experiments
/research:experiment dropout-baseline
/research:experiment dropout-0.3

### Document findings
/research:finding "Dropout 0.3 reduces overfitting by 18%" --confidence high

### Read relevant papers
/research:paper https://arxiv.org/abs/1234.5678

### View research index
/research:index
```

## Output Structure

```
docs/research/
├── index.md                     # Auto-maintained index
├── hypotheses/
│   └── 2026-01-13_dropout-overfitting.md
├── experiments/
│   ├── 2026-01-13_dropout-baseline.md
│   └── 2026-01-13_dropout-0.3.md
├── findings/
│   └── 2026-01-13_dropout-reduces-overfitting.md
└── papers/
    └── 2026-01-13_attention-is-all-you-need.md
```

## Status Icons

### Hypotheses
- 🔬 Testing
- ✅ Validated
- ❌ Rejected
- ⏸️ Paused

### Experiments
- 🏃 Running
- ✅ Complete
- ❌ Failed

### Findings (Confidence)
- 🟢 High
- 🟡 Medium
- 🔴 Low

## Installation

This plugin is part of qute-marketplace. Install the marketplace:

```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
```

Or from GitHub:

```bash
claude plugin install github:twilc/claude-marketplace
```

## License

MIT
