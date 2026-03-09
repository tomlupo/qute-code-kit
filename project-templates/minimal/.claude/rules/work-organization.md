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
| `/research/` | Foundational studies: `/{study-name}/` — permanent, referenced by other work |
| `/analysis/` | Dated exploratory work: `/{YYYYMMDD-name}/` — ad-hoc, may be archived |
| `/scratch/` | Disposable agent work (gitignored, can be deleted anytime) |
| `/scripts/` | Standalone runnable scripts |
| `/src/` | Shared production code (imported by other files) |
| `/models/` | Serialized model artifacts (not design docs — those live in `docs/models/`) |
| `/notebooks/` | Jupyter notebooks for exploration |
| `/tests/` | Test suite |

Root-level files:
- `TASKS.md` - Task tracking (Now/Next/Later/Completed)
- `README.md` - Project overview

## Task Tracking (TASKS.md)

Use a simple `TASKS.md` in the project root with four sections:

```markdown
# Tasks

## Now
- [ ] Active work items for this session

## Next
- [ ] Queued items to start soon

## Later
- [ ] Ideas and backlog (link to `docs/ideas/` if details needed)

## Completed
- [x] Finished items (move here when done)
```

- Move items between sections as priorities change
- Keep Now to 1-3 items — if it's longer, reprioritize
- For ideas that need more detail, create `docs/ideas/YYYY-MM-DD-slug.md` and link from Later
- When a plan completes, move it to `docs/plans/completed/`

## File Placement Decision Tree
```
Input data?              → /data/ (raw/intermediate/processed)
Pipeline output?         → /output/{artifact-name}/
External deliverable?    → /reports/
Foundational study?      → /research/{study-name}/
Dated exploratory work?  → /analysis/{YYYYMMDD-name}/
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
- ✅ `scratch/risk-profile-calibration/simulate.py`
- ❌ `scripts/script.py` (skipped scratch)
- ❌ `docs/notes.md` (skipped scratch)

**Exceptions** — create outside scratch only when:
1. User explicitly specifies a target path
2. Editing an existing file (not creating new content)
3. User explicitly requests promotion/cleanup

**After creation**: Always notify the user where files are located.

## When to Promote Files

| From | To | When |
|------|----|------|
| scratch output | `/data/processed/{dataset-name}/` | Output becomes input to other analyses |
| scratch code | `/src/` or `/scripts/` | Code becomes reusable (`/src/` if imported, `/scripts/` if standalone) |
| scratch study | `/research/{study-name}/` | Study becomes foundational (keep scripts, data, outputs together) |
| scratch report | `/reports/` | Report ready to share externally |
| scratch docs | `/docs/reference/` | Output becomes reference material |

AI origin doesn't matter for promoted work — the scratch rule is about *unreviewed* output, not permanent provenance.

## Config/Output Symmetry

For artifact-specific pipelines, mirror folder names between config and output:

| Artifact | Config | Output |
|----------|--------|--------|
| tactical-signals | `config/tactical-signals/` | `output/tactical-signals/` |
| features | `config/features/` | `output/features/` |
| ml | `config/ml/` | `output/ml/` |

**Pattern**: Script reads `config/{artifact}/{name}.yaml` → writes to `output/{artifact}/`

## Research as Sub-Projects

`/research/{study-name}/` entries are self-contained — each study defines its own structure with co-located scripts, data, outputs, and documentation. They do NOT follow the project-wide config/output symmetry because they are independent sub-projects.

```
research/risk-profile-calibration/
├── RISK_PROFILE_CALIBRATION.md    # methodology + results doc
├── build_asset_data.py            # data pipeline (study-specific)
├── simulate_profiles.py           # simulation engine
└── output/                        # study outputs
    ├── exec_summary.html          # interactive dashboard
    └── *.parquet                   # data artifacts
```

## Common Mistakes

| ❌ Don't | ✅ Do |
|----------|-------|
| Create scripts in project root | Place in `/scripts/` or `/scratch/` |
| Mix raw and processed data in same folder | Use `/data/raw/` vs `/data/processed/` |
| Put AI-generated files in `/analysis/` | Use `/scratch/{artifact-name}/` |
| Put foundational studies in `/analysis/` | Use `/research/{study-name}/` (no date prefix, permanent) |
| Create deeply nested directory trees | Keep nesting to 3 levels max |
| Reference `/scratch/` paths in permanent code or docs | Promote the file first, then reference |
| Mismatch config/output paths | Keep symmetric: `config/X/` ↔ `output/X/` |
| Ask open-ended "where should this go?" | Propose a specific path and ask for confirmation |
