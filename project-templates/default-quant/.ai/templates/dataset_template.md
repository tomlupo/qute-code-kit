# Dataset Name

## Overview

**Purpose**: [One-sentence description of why this dataset exists]

**Data Source**: [Where the data comes from - API, scraping, file extraction, etc.]

**Source Directory**: [If using source grouping: `api`, `scraping`, `manual`, `external`, etc. - otherwise omit]

**Last Updated**: [YYYY-MM-DD]

**Maintainer**: [Name/team]

## Scope

- **Time Period**: [Date range covered, if applicable]
- **Record Count**: [Number of records/entities]
- **Update Frequency**: [daily, weekly, monthly, on-demand]
- **Coverage**: [Geographic, categorical, or other scope details]

## File Location

**Processed Data**: `data/processed/{dataset_name}/[filename]`

**Raw Data**: `data/raw/{source}/{dataset_name}/[files]` or `data/raw/{dataset_name}/[files]`

**Intermediate Data**: `data/intermediate/{dataset_name}/[files]` (if applicable)

**Format**: [CSV, Parquet, JSON, etc.]

**Size**: [rows × columns, file size]

**Partitioning**: [If applicable - e.g., "date-partitioned by date=YYYY-MM-DD"]

## Schema

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `column_name` | data_type | Description | Example value | Optional notes |

## Data Quality

### Validation Status

| Check | Status | Details |
|-------|--------|---------|
| Unique Keys | ✓/✗ | [Details] |
| Required Fields | ✓/✗ | [Completeness %] |
| Data Types | ✓/✗ | [Any issues] |
| Value Ranges | ✓/✗ | [Outliers/invalid values] |

### Known Issues

- **Issue**: [Description]
  - Impact: [How this affects usage]
  - Workaround: [If applicable]

## Usage

### Loading

```python
import pandas as pd
df = pd.read_parquet('data/processed/{dataset_name}/[filename]')
# or
df = pd.read_csv('data/processed/{dataset_name}/[filename]')
```

### Common Operations

[Add brief examples if helpful - filtering, aggregations, joins]

## Processing

**Script**: `scripts/create_{dataset_name}.py` (if applicable)

**Pipeline**:
1. **Extract**: Collect/generate raw data → `data/raw/{source}/{dataset_name}/`
2. **Transform** (if needed): Create intermediate stages → `data/intermediate/{dataset_name}/`
3. **Process**: Final transformation → `data/processed/{dataset_name}/`

**Inputs**: 
- Raw: `data/raw/{source}/{dataset_name}/[files]` or `data/raw/{dataset_name}/[files]`
- Intermediate: `data/intermediate/{dataset_name}/[files]` (if applicable)

**Outputs**: 
- Processed: `data/processed/{dataset_name}/[filename]`

**Reproducibility**: [Note if processed data can be regenerated from raw data via script]

## References

- **Source**: [Link to source dataset or external reference]
- **Related**: [Links to related datasets/docs]

---

**Last Updated**: [YYYY-MM-DD]

