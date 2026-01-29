# Dataset Management

## Directory Structure

```
data/
├── raw/
│   ├── {source}/{datasetname}/    # Optional source grouping (e.g., "api", "scraping")
│   └── {datasetname}/              # Or directly under raw/ if no source grouping
├── intermediate/{datasetname}/     # Only if multi-step processing needed
└── processed/{datasetname}/       # Final datasets ready for use

docs/datasets/{datasetname}.md      # Documentation (see .ai/templates/dataset_template.md)
```

## Data Flow

```
data/raw/{source}/{datasetname} 
  → data/intermediate/{datasetname}  (only if needed)
  → data/processed/{datasetname} 

```

**Principles:**
- **Raw**: Immutable source data. Can be generated/scraped/collected, never modified in place.
- **Intermediate**: Temporary transformation stages. Only create if multi-step processing is needed.
- **Processed**: Stable, final datasets ready for project use. Must be reproducible from raw data.
- **Documentation**: Every processed dataset must have `docs/datasets/{datasetname}.md`

## Examples

### Simple Dataset
```
data/
├── raw/customer_orders/
│   ├── orders_2024.csv
│   └── orders_2025.csv
├── processed/customer_orders/
│   └── orders_combined.csv  # or .parquet, .json, etc. based on needs
└── docs/datasets/customer_orders.md
```

### Dataset with Source Grouping
```
data/
├── raw/api/weather_data/daily_forecasts.json
├── raw/scraping/product_reviews/reviews_raw.csv
├── intermediate/product_reviews/reviews_cleaned.parquet
├── processed/weather_data/weather_aggregated.json  # or .parquet, .csv, etc.
└── processed/product_reviews/reviews_with_sentiment.csv  # or .parquet, etc.
```

## When to Use Intermediate Directory

Use `data/intermediate/` only when:
- Multi-step transformations need checkpoints
- Processing is expensive and intermediate results are reused
- Debugging complex transformations requires inspection
- Different processes work on different stages

**Otherwise**: Process directly from `raw/` to `processed/` to keep it simple.

## Data Handling

When working with datasets:
- **Check documentation first**: Always read `docs/datasets/{datasetname}.md` before accessing data
- **Use loading functions**: Prefer provided loading functions over direct file access
- **Review schema**: Understand data structure, field descriptions, and types from documentation
- **Respect structure**: Maintain existing organization (partitioning, naming, formats)

## Processing Pipeline

1. **Extract**: Collect/generate raw data → `data/raw/{source}/{datasetname}/`
2. **Transform** (if needed): Create intermediate stages → `data/intermediate/{datasetname}/`
3. **Process**: Final transformation → `data/processed/{datasetname}/`
4. **Document**: Create/update `docs/datasets/{datasetname}.md` following `.ai/templates/dataset_template.md`
5. **Validate**: Run validation checks and document results

## Best Practices

### Naming Conventions
- **Dataset names**: Lowercase with underscores (`customer_orders`, `weather_daily`)
- **File names**: Descriptive with date/version if applicable (`orders_2024_q1.csv`, `products_v2.parquet`)
- **Source directories**: Clear, consistent names (`api`, `scraping`, `manual`, `external`)

### Data Organization
- **Partitioning**: For large datasets, use date-based partitioning (e.g., `date=2024-01-01/`)
- **Formats**: 
  - Raw: Preserve original format (CSV, JSON, etc.)
  - Processed: Choose format based on use case and requirements:
    - CSV: Good for small datasets, human-readable, universal compatibility
    - Parquet: Efficient for large datasets, columnar storage, good for analytics
    - JSON: Good for nested/hierarchical data, API compatibility
    - Feather: Fast read/write for Python/R workflows
    - Other formats as needed (SQLite, HDF5, etc.)
  - **Format selection**: Consider dataset size, access patterns, tool compatibility, and team preferences
- **Version control**: Track raw data if small; use git-lfs or external storage for large files

## Data Collection & Scraping

When building scrapers or collecting data:
- **Development**: Prototype in `scratch/{agent-name}/` first (see work-organization.md)
- **Production**: Create master scripts in `/scripts/`, update documentation
- **Data Quality**: Document actual results, not estimates ("187 items scraped" not "~188 expected")
- **Storage**: Save raw collected data to `data/raw/{source}/{datasetname}/` with clear naming
- **Documentation**: Record API versions, rate limits, pagination details, completeness percentages

## Data Quality

- **Validation**: Run validation checks before marking dataset as processed
- **Documentation**: Record validation results in dataset documentation
- **Completeness**: Document missing data patterns and percentages
- **Reproducibility**: Ensure processed data can be regenerated from raw data via documented scripts
