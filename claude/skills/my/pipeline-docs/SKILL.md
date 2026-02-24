---
name: pipeline-docs
description: Create or audit documentation for a data pipeline using the 4-doc pattern (instruction, dataset, methodology, reference). Use when adding a new pipeline, when documentation is missing or incomplete for an existing pipeline, or when the user says "document this pipeline", "create pipeline docs", "4-doc pattern", or "/pipeline-docs".
---

# Pipeline Documentation — 4-Doc Pattern

Create complete documentation for a data pipeline. Every pipeline gets exactly 4 docs, each answering one question.

## The 4 Docs

| Doc | Location | Answers | Audience |
|-----|----------|---------|----------|
| **Instruction** | `docs/instructions/{name}_pipeline.md` | What to run | Operator (human or AI) |
| **Dataset** | `docs/datasets/{dataset_name}.md` | What the data looks like | Consumer of the data |
| **Methodology** | `docs/methodology/{name}_extraction.md` | Why it works this way | Future maintainer |
| **Reference** | `docs/reference/{name}_convention.md` | What the conventions are | Anyone mapping IDs or configs |

## Process

### Step 1: Gather Context

Before writing, collect:

1. **Pipeline name** and dataset name (may differ — e.g., pipeline "fund_holdings", dataset "fund_holdings")
2. **Scripts**: entry points, CLI flags, pipeline orchestrator
3. **Config files**: what they contain, when to edit
4. **Data paths**: raw → intermediate → processed
5. **Schema**: columns, types, examples
6. **Design decisions**: why this approach, what alternatives were rejected

Search the codebase:
- `scripts/` for pipeline scripts and CLIs
- `config/` for config files used by this pipeline
- `data/` for directory structure and file formats
- `extraction/` or `src/` for processing logic

### Step 2: Check Existing Docs

Look for existing docs that cover this pipeline:
- `docs/instructions/` — any operational guide?
- `docs/datasets/` — any schema doc?
- `docs/methodology/` — any design doc?
- `docs/reference/` — any convention doc?

If some exist, audit them against the templates below. Fill gaps, don't duplicate.

### Step 3: Write Missing Docs

Create each missing doc using the templates below. Rules:

- **One concern per doc** — instructions don't explain "why", methodology doesn't list commands
- **Cross-reference all 4** — every doc's "Related" section links to the other 3
- **No duplication** — file paths, CLI options, and schema appear in exactly one doc
- **Concrete over abstract** — use real values, real paths, real examples from this project

### Step 4: Update Routing Pages

After creating docs, update:

1. **`docs/README.md`** — add entries under Quick Links for each new doc
2. **`docs/data_operations.md`** (if it exists) — add routing table for this pipeline

---

## Template: Instruction Doc

`docs/instructions/{name}_pipeline.md`

````markdown
# {Pipeline Name} Pipeline

> Quick reference for running the {pipeline_name} pipeline. For schema details see [dataset doc]. For design decisions see [methodology doc].

## Quick Reference

| Task | Command |
|------|---------|
| **Full pipeline** | `uv run python scripts/pipelines/{script}.py --latest` |
| ... | ... |

## Steps

### 1. {First Step Name}

{Exact command with flags. Expected output location. What to check.}

### 2. {Second Step Name}

{Same pattern.}

## Maintenance

| Task | Command | When |
|------|---------|------|
| ... | ... | ... |

## Related

- [Dataset doc](../datasets/{dataset_name}.md) — schema, loading, data quality
- [Methodology doc](../methodology/{name}_extraction.md) — design decisions, trade-offs
- [Reference doc](../reference/{name}_convention.md) — IDs, config files, naming
````

**Style**: imperative voice ("Run X", "Check Y"). Copy-pasteable commands. No explanatory prose.

---

## Template: Dataset Doc

`docs/datasets/{dataset_name}.md`

Use the **dataset template** from the `datasets.md` rule if available in this project. Otherwise use this structure:

````markdown
# {Dataset Name}

## Overview

**Purpose**: {One sentence — why this dataset exists}

**Data Source**: {Where it comes from}

**Last Updated**: {YYYY-MM-DD}

**Maintainer**: {Name/team}

## Scope

- **Time Period**: {Date range}
- **Record Count**: {Approximate}
- **Update Frequency**: {Quarterly, monthly, etc.}
- **Coverage**: {What's included}

## File Location

**Processed Data**: `data/processed/{dataset_name}/{partitioning}/`

**Raw Data**: `data/raw/{dataset_name}/`

**Format**: {Parquet, CSV, etc.}

**Partitioning**: {By provider, by date, etc.}

## Schema

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| ... | ... | ... | ... | ... |

## Data Quality

### Validation Status

| Check | Status | Details |
|-------|--------|---------|
| ... | ... | ... |

### Known Issues

- **{Issue}**: {Description}. Workaround: {if applicable}.

## Usage

### Loading

```python
import pandas as pd
df = pd.read_parquet('data/processed/{dataset_name}/...')
```

### Common Operations

```python
# {Useful operation}
```

## Processing

**Script**: `scripts/datasets/{dataset_name}/{script}.py`

**Pipeline**:
1. **Extract**: {source} -> `data/raw/...`
2. **Transform**: {processing} -> `data/intermediate/...` (if applicable)
3. **Process**: {final step} -> `data/processed/...`

**Reproducibility**: {Can processed data be regenerated from raw?}

## Related

- [Pipeline doc](../instructions/{name}_pipeline.md) — commands, steps
- [Methodology doc](../methodology/{name}_extraction.md) — design decisions
- [Reference doc](../reference/{name}_convention.md) — IDs, config files

---

**Last Updated**: {YYYY-MM-DD}
````

**Style**: factual, schema-focused. Loading examples must work. Include real column names and real example values.

---

## Template: Methodology Doc

`docs/methodology/{name}_extraction.md`

````markdown
# {Pipeline Name} — Methodology

Why the {pipeline_name} pipeline works the way it does: design decisions, algorithms, trade-offs.

## Why {Data Source}

{Why this source? Why not an API, database, or other format?}

## Architecture

### {Component Type}

{How components are organized. Why per-X instead of generic.}

| Type | When used | Engine/Tool |
|------|-----------|-------------|
| ... | ... | ... |

### Why {Key Decision}

{Explain the reasoning behind the most important architectural choice.}

## Processing Pipeline

{Numbered sub-steps, applied in order. Each is independent and idempotent.}

### 1. {Step Name}

{What it does. Data sources used. Key guards or heuristics.}

### 2. {Step Name}

{Same pattern.}

## Trade-offs

| Decision | Alternative Considered | Why This Way |
|----------|----------------------|--------------|
| ... | ... | ... |

## Related

- [Pipeline doc](../instructions/{name}_pipeline.md) — commands, steps
- [Dataset doc](../datasets/{dataset_name}.md) — schema, loading
- [Reference doc](../reference/{name}_convention.md) — IDs, config files
````

**Style**: explain the "why". Future maintainers should understand what was tried and rejected. No commands — those go in the instruction doc.

---

## Template: Reference Doc

`docs/reference/{name}_convention.md`

````markdown
# {Pipeline Name} — Conventions

IDs, config files, naming rules, and mapping logic for the {pipeline_name} pipeline.

## ID Schemes

| ID | Format | Example | Source |
|----|--------|---------|--------|
| ... | ... | ... | ... |

## Config Files

| File | Purpose | Key Columns | When to Edit |
|------|---------|-------------|--------------|
| `config/{file}.csv` | {What it maps} | {Key columns} | {When} |

## Naming Conventions

### File Naming

{Pattern for raw files, processed files, output directories.}

### Folder Structure

```
data/{dataset_name}/
├── {provider}/
│   └── {date}/
│       └── {filename}
```

## Mapping Rules

### {Mapping Name}

{How X maps to Y. Explicit vs fuzzy. Priority order. What happens when no match.}

## Related

- [Pipeline doc](../instructions/{name}_pipeline.md) — commands, steps
- [Dataset doc](../datasets/{dataset_name}.md) — schema, loading
- [Methodology doc](../methodology/{name}_extraction.md) — design decisions
````

**Style**: lookup-oriented. Tables over prose. A developer should find the answer to "what's the naming convention for X?" in seconds.

---

## Duplication Rules

Each piece of information lives in exactly one doc:

| Information | Lives In | NOT In |
|-------------|----------|--------|
| CLI commands and flags | Instruction | Methodology, Dataset |
| File paths and partitioning | Dataset | Instruction, Reference |
| Schema (columns, types) | Dataset | Methodology |
| Config file roles and columns | Reference | Instruction, Dataset |
| Design decisions and trade-offs | Methodology | Instruction, Reference |
| ID formats and naming rules | Reference | Dataset, Methodology |

Other docs may **link** to these sections but must not repeat them.

## Checklist

Before finishing, verify:

- [ ] All 4 docs exist for this pipeline
- [ ] Each doc's "Related" section links to the other 3
- [ ] No information is duplicated across docs
- [ ] `docs/README.md` updated with links to all 4
- [ ] Routing page (e.g., `data_operations.md`) updated if it exists
- [ ] All file paths in docs are real and correct
- [ ] Code examples in dataset doc actually work
