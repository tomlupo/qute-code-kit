# Toolkit Quick Reference

## Skills

### Universal (qute-essentials plugin)

| Skill | Invocation | Notes |
|-------|------------|-------|
| generating-commit-messages | mandatory | Conventional commits format |
| worktrees | `/worktrees` | Git worktree management |
| readme | `/readme` | README generation (forked context) |
| handoff | `/handoff` | Session transition documents |

### Foundational (minimal bundle)

| Skill | Invocation | Notes |
|-------|------------|-------|
| llm-external-review | `/llm-external-review` | Second opinions from Codex/Gemini |

### Research & Data (quant bundle)

| Skill | Invocation | Notes |
|-------|------------|-------|
| paper-reading | `/paper-reading [path]` | PDFs, papers, fund cards (Explore agent) |
| investment-research | `/investment-research` | Research lifecycle framework |
| investment-research-formal | `/investment-research-formal` | Auditable hypothesis/experiment tracking |
| investment-research-dashboard | `/investment-research-dashboard` | Plotly.js HTML dashboards |
| market-datasets | `/market-datasets [ticker]` | Auto-routes to best data source |
| analizy-pl-data | `/analizy-pl-data` | Polish fund data (2,133 funds) |
| sql-patterns | `/sql-patterns` | SQL query templates |
| qrd | `/qrd` | Quant R&D specification |
| pipeline-docs | `/pipeline-docs` | 4-doc pipeline documentation |
| python-patterns | model-invocable | Idiomatic Python reference |

### ML (quant bundle, @skills/ml-core)

| Skill | Notes |
|-------|-------|
| scikit-learn | ML patterns and workflows |
| shap | Model explainability |
| exploratory-data-analysis | Auto-detect file formats, quality reports |
| polars | DataFrame library |
| openalex-database | Academic paper database |

### Output (quant + webdev)

| Skill | Invocation | Notes |
|-------|------------|-------|
| gist-report | `/gist-report` | Styled HTML → GitHub gist (user-only) |
| gist-transcript | `/gist-transcript` | Session transcript → gist (user-only) |
| image-generator | `/image-generator` | Gemini API image generation (quant only) |
| excalidraw | `/excalidraw` | Hand-drawn diagrams as JSON |

## Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| security-auditor | Sonnet | Codebase security audit with report |

## MCP Servers

| Server | Bundle | Auth |
|--------|--------|------|
| memory | minimal | — |
| firecrawl | quant | `FIRECRAWL_API_KEY` |
| postgres | quant | `POSTGRES_CONNECTION_STRING` |
| vercel | webdev | — |
| chrome-devtools | webdev | — |
| playwright | webdev | — |
| docker | webdev | — |
| figma | webdev | `FIGMA_ACCESS_TOKEN` |

## Rules

| Rule | Applies to | Bundle |
|------|-----------|--------|
| general-rules | all files | minimal |
| work-organization | all files | minimal |
| context-management | all files | minimal |
| documentation | `docs/**`, `**/*.md` | minimal |
| python-rules | `**/*.py` | quant |
| typescript-rules | `**/*.{ts,tsx,js,jsx}` | webdev |
| datasets | `data/**`, `docs/datasets/**` | quant |

## Plugins (global)

Install marketplaces first, then plugins:

```bash
# Marketplaces
claude plugin marketplace add tomlupo/qute-code-kit        # qute-marketplace
claude plugin marketplace add anthropics/claude-code-skills # anthropic-agent-skills
claude plugin marketplace add nichochar/compound-engineering # every-marketplace

# Essential plugins
claude plugin install context7@claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin install compound-engineering@every-marketplace
claude plugin install document-skills@anthropic-agent-skills

# Kit plugin (hooks + universal skills)
claude plugin install qute-essentials@qute-marketplace
```

| Plugin | Source | What you get |
|--------|--------|--------------|
| qute-essentials | qute-marketplace | Hooks: ruff, doc-enforcer, skill-eval, notifications. Skills: commits, worktrees, handoff, readme |
| context7 | claude-plugins-official | Framework doc lookup |
| superpowers | claude-plugins-official | Planning, TDD, debugging |
| compound-engineering | every-marketplace | Full dev lifecycle |
| document-skills | anthropic-agent-skills | PDF, PPTX, XLSX, canvas |

## Headless Mode

```bash
claude -p "instruction" --allowedTools "Bash,Read,Write,Edit"
claude -p "instruction" --dangerously-skip-permissions  # trusted env only
claude -p "instruction" --output-format json > output.json
```

## Playbooks

```
docs/playbooks/
├── superpowers-workflow.md
├── compound-engineering-workflow.md
├── investment-research-workflow.md
├── multi-agent-code-review.md
├── research-to-production.md
├── session-continuity.md
├── visual-documentation.md
└── agentic-image-refinement.md
```

## Cheatsheets

```
docs/cheatsheets/
├── toolkit-reference.md    ← this file
├── claude-cli.md
├── prompt-engineering.md
└── xml-prompting.md
```
