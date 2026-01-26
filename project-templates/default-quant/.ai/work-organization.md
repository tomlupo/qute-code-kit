# Work Organization

## Directory Structure

`/config/` - Configuration files
`/data/` - Datasets (see datasets.md for details)
`/output/` - Analysis results: `/{analysis-name}/` with report, figures, tables, artifacts
`/reports/` - Polished deliverables (small collection)
`/analysis/` - Human exploratory work: `/{YYYYMMDD-name}/` (NOT for AI files)
`/scratch/` - Temporary exploration (gitignored): `/scratch/{agent-name}/`
`/docs/` - Documentation (see documentation.md for subdirectories)
`/src/` - Production code used across other files (imported/shared modules)
`/scripts/` - Standalone reusable scripts

Root-level files: 
`IN_PROGRESS.md` - Active work
`BACKLOG.md` - Future tasks
`README.md` - Project overview

## Task Tracking

See **workflow.md** for complete task management guidelines.

**Quick reference:**
- `IN_PROGRESS.md` - Active project-level tasks
- `BACKLOG.md` - Future tasks and ideas
- `CHANGELOG.md` - User-facing changes (update on main branch only)
- `.claude/sessions/` - Session history (see `/session-help`)
- TodoWrite - Within-conversation task tracking 

## File Placement Decision Tree

Input data? → `/data/` (raw/intermediate/processed)
Analysis output? → `/output/{analysis-name}/`
Polished deliverable? → `/reports/`
Human exploratory work? → `/analysis/{date-name}/`
AI exploration/scripts? → `/scratch/{agent-name}/
Documentation? → `/docs/` (appropriate subdirectory)
Reusable code? → `/src/` (if used across files) or `/scripts/` (standalone)

When uncertain, ASK before creating files.

## Rule: Scratch First

ALL agent-generated files go in `scratch/{agent-name}/{artifact-name}/` first.

**Agent names**: Use the tool name - `claude`, `codex`, `cursor`, `gemini`, `copilot`, etc.

Examples:
- ✅ `scratch/claude/fiz-scraper/script.py`
- ❌ `scripts/script.py`
- ❌ `docs/notes.md`
- ❌ `scratch/my-work/file.py` (missing agent-name)

Only create outside scratch if:
1. User explicitly specifies path: "Create X at Y"
2. Editing existing files (not new content)
3. User explicitly requests cleanup/organization of existing code

**After creation**: Notify user where work is located for review.

## When to Promote Files

- Data: Output becomes input to other analyses → `/data/processed/{dataset-name}/`
- Code: Scratch becomes reusable → `/src/` (if used across files) or `/scripts/` (standalone)
- Output: Report ready to share → `/reports/`
- Reference: Output becomes reference material → `/docs/reference/`

## Common Mistakes

❌ Scripts in root, mixing raw/processed data, AI files in `/analysis/`, deep nesting, referencing `scratch/` from permanent docs