# Reference

Complete inventory of skills, agents, plugins, and MCP servers.

## Skills

Skills are deployed to projects via bundles/`setup-project.sh`. Source: `claude/skills/<name>/SKILL.md`.

| Skill | Bundle | Invocation | Notes |
|-------|--------|------------|-------|
| python-patterns | quant | Auto | Python idioms and patterns |
| paper-reading | quant | `/paper-reading [path]` | Three-pass analysis (`agent: Explore`) |
| sql-patterns | quant | `/sql-patterns` | SQL templates and best practices |
| market-datasets | quant | `/market-datasets [ticker]` | Multi-source market data |
| qrd | quant | `/qrd` | Quant R&D specification documents |
| pipeline-docs | quant | `/pipeline-docs` | Data pipeline documentation |
| investment-research | quant | `/investment-research` | Investment research workflow |
| investment-research-formal | quant | `/investment-research-formal` | Formal investment reports |
| investment-research-dashboard | quant | `/investment-research-dashboard` | Research dashboard |
| llm-external-review | quant | `/llm-external-review` | Second opinions from Codex/Gemini |
| analizy-pl-data | quant | `/analizy-pl-data` | Polish fund data |
| gist-report | quant, webdev | `/gist-report` | HTML reports via GitHub gist |
| gist-transcript | quant, webdev | `/gist-transcript` | Session transcript gist |
| image-generator | quant | `/image-generator` | Gemini-powered image generation |
| bird-twitter | standalone | `/bird-twitter` | Twitter/X posting |
| brand-dm-evo | standalone | — | Evo Dom Maklerski brand identity |
| brand-rockbridge | standalone | — | Rockbridge TFI brand identity |
| excalidraw | standalone | `/excalidraw` | Excalidraw diagram generation |

### Plugin Skills (qute-essentials)

Installed globally via plugin, not via bundles:

| Skill | Invocation | Notes |
|-------|------------|-------|
| generating-commit-messages | `/generating-commit-messages` | Mandatory before commits |
| worktrees | `/worktrees [branch]` | Git worktree management |
| handoff | `/handoff` | Session transition documents |
| readme | `/readme` | README generation (`context: fork`) |

## Agents

Agents are deployed to projects via bundles. Source: `claude/agents/<name>.md`.

| Agent | Description |
|-------|-------------|
| research-synthesizer | Cross-source analysis — synthesizes multiple papers/reports into consensus/conflict maps |
| data-pipeline-debugger | Traces data flow and isolates corruption in data pipelines |

## Plugin

One plugin in the qute-marketplace:

| Plugin | Version | Contents |
|--------|---------|----------|
| qute-essentials | 1.0.0 | 4 skills, 3 commands (notifications), hooks (ruff, doc-enforcer, skill-eval, notifications) |

### Hook Events (qute-essentials)

| Hook | Event | Purpose |
|------|-------|---------|
| skill-eval | UserPromptSubmit | Forces skill evaluation before responses |
| ruff-formatter | PostToolUse | Auto-formats Python after edits |
| doc-enforcer | PostToolUse | Reminds when docs may need updating |
| notifications | PostToolUse | Push notifications via ntfy.sh |

## MCP Servers

MCP configs deployed via bundles. Source: `claude/mcp/<name>.json`.

| Server | Auth | Bundle | Purpose |
|--------|:----:|--------|---------|
| firecrawl | `FIRECRAWL_API_KEY` | quant | Web scraping |
| postgres | `POSTGRES_CONNECTION_STRING` | quant | Database access |
| vercel | — | webdev | Deployment management |
| chrome-devtools | — | webdev | Browser debugging |
| playwright | — | webdev | Browser automation |
| docker | — | webdev | Container management |
| figma | `FIGMA_ACCESS_TOKEN` | webdev | Design file access |
| memory | — | standalone | Persistent fact storage |

## Bundles

| Bundle | Components | Inherits |
|--------|-----------|----------|
| minimal | 4 rules, CLAUDE.md, AGENTS.md | — |
| quant | 2 rules, 14 skills, 2 MCP, settings, pyproject | minimal |
| webdev | 1 rule, 2 skills, 5 MCP, settings, pyproject | minimal |
