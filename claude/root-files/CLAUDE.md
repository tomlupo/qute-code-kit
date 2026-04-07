# @CLAUDE.md

See also: @README.md

## Project Goal

<!-- What the project does. 1-3 sentences. -->

## Key Paths

<!-- Directories/files that aren't obvious from repo structure. -->

## Key Commands

<!-- Common workflows: build, test, deploy, etc. -->

## Work Phase Routing

<!-- Decision tree: determines which .claude/rules/ apply to your current task.
     Individual rules stay modular; this section ties them together. -->

| Phase | What you're doing | Key rules |
|-------|-------------------|-----------|
| Exploratory research | New study in `research/` on `dev` branch | work-organization (scratch-first, research as sub-projects), git-workflow (research on dev) |
| Production promotion | Moving research findings to production | git-workflow (feat/* branch), work-organization (config/output symmetry) |
| Data pipeline work | Building or modifying a data pipeline | documentation (4-doc pattern), datasets, work-organization (data layers) |
| Feature development | New production feature | git-workflow (feat/* → dev → main), code-quality |
| Documentation | Writing or updating docs | documentation (placement rules, reference hierarchy) |

## Domain Knowledge

<!-- Project-specific conventions, data quirks, gotchas. -->
