# Work Organization

## Directory Structure

### Core Directories

| Directory | Purpose |
|-----------|---------|
| `/config/` | Configuration files (see Config/Output Symmetry) |
| `/data/` | Datasets: `raw/`, `intermediate/`, `processed/` |
| `/docs/` | Documentation (appropriate subdirectories) |
| `/output/` | Analysis results and pipeline outputs (see Config/Output Symmetry) |
| `/reports/` | Externally-shared deliverables only (client decks, stakeholder reports) |
| `/scratch/` | Disposable agent work (gitignored, can be deleted anytime) |
| `/scripts/` | Standalone runnable scripts |
| `/src/` | Shared production code (imported by other files) |
| `/tests/` | Test suite |

Root-level files:
- `TASKS.md` - Task tracking (Now/Next/Later/Completed)
- `README.md` - Project overview

## File Placement Decision Tree
```
Input data?              → /data/ (raw/intermediate/processed)
Pipeline output?         → /output/{artifact-name}/
External deliverable?    → /reports/
Persistent exploration?  → /analysis/{YYYYMMDD-name}/
Disposable agent work?   → /scratch/{artifact-name}/
Documentation?           → /docs/{subdirectory}/
Reusable shared code?    → /src/
Standalone script?       → /scripts/
```

When uncertain, **propose a path and ask for confirmation** — don't ask open-ended "where should I put this?"

## Naming Conventions

**Files**: `snake_case` everywhere. No spaces, no camelCase, no kebab-case.
- Scripts: verb prefix — `fetch_fund_data.py`, `compute_attribution.py`, `export_report.py`
- Configs: match the artifact they configure — `tactical_signals.yaml`

**Directories**: lowercase, hyphens for multi-word — `tactical-signals/`, `fund-analysis/`

## Output Naming

Use report date as directory when applicable, keep filenames fixed:
```
output/tactical-signals/2026-01-15/signals.csv
output/tactical-signals/2026-01-15/summary.html
```

If no report date applies, write directly to the artifact directory:
```
output/tactical-signals/signals.csv
```

Pipelines can always expect consistent filenames, versioned by folder.

### Run Tagging

For multi-step pipelines, use tagged subdirectories to prevent overwrites:

```
output/portfolio-commentary/2026-01-31/
├── 20260213T170000/       ← auto-generated timestamp tag
├── v2-new-prompt/         ← custom descriptive tag
└── latest -> v2-new-prompt
```

- Default tag: `YYYYMMDDTHHMMSS` timestamp. Allow `--run-tag` for custom names.
- Maintain a `latest` symlink to the most recent run.
- Steps that consume prior output default to `latest`.
- Skip tagging for single-step or idempotent scripts.

## Rule: Scratch First

ALL agent-generated files go to `/scratch/{artifact-name}/` first.

Examples:
- ✅ `scratch/fiz-scraper/script.py`
- ❌ `scripts/script.py` (skipped scratch)

**Exceptions** — create outside scratch only when:
1. User explicitly specifies a target path
2. Editing an existing file (not creating new content)
3. User explicitly requests promotion/cleanup

**After creation**: Always notify the user where files are located.

## Config/Output Symmetry

For artifact-specific pipelines, mirror folder names between config and output:

**Pattern**: Script reads `config/{artifact}/{name}.yaml` → writes to `output/{artifact}/`

## Common Mistakes

| ❌ Don't | ✅ Do |
|----------|-------|
| Create scripts in project root | Place in `/scripts/` or `/scratch/` |
| Mix raw and processed data in same folder | Use `/data/raw/` vs `/data/processed/` |
| Put AI-generated files in `/analysis/` | Use `/scratch/{artifact-name}/` |
| Create deeply nested directory trees | Keep nesting to 3 levels max |
| Reference `/scratch/` paths in permanent code or docs | Promote the file first, then reference |
| Mismatch config/output paths | Keep symmetric: `config/X/` ↔ `output/X/` |
| Ask open-ended "where should this go?" | Propose a specific path and ask for confirmation |