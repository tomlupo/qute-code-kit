# qute-code-kit

Reusable Claude Code components — rules, skills, MCP configs, and plugins — deployed to projects via manual copy or setup script.

## Quick Start

```bash
# 1. Add marketplaces (one-time)
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin marketplace add anthropics/claude-code-plugins
claude plugin marketplace add anthropics/example-agent-skills
claude plugin marketplace add every-ai-dev/compound-engineering

# 2. Install plugins (one-time)
claude plugin install qute-essentials@qute-marketplace
claude plugin install context7@claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin install compound-engineering@every-marketplace

# 3. Copy global settings
cp claude/settings/global-generic.json ~/.claude/settings.json

# 4. Set up a project (pick one)
./scripts/setup-project.sh ~/project --bundle quant --init    # script
cp claude/rules/general-rules.md ~/project/.claude/rules/     # or manual
```

## What's Here

```
claude/
├── rules/              Path-scoped coding guidelines
├── skills/             Domain skills (copy to projects)
├── mcp/                MCP server configs
├── bundles/            Bundle manifests (minimal, quant, webdev)
├── root-files/         CLAUDE.md + AGENTS.md templates
├── settings/           Project settings profiles
├── commands/           Kit management commands
└── hooks/              Reusable hook scripts

plugins/
└── qute-essentials/    Merged plugin: hooks + universal skills

docs/
├── playbooks/          Step-by-step workflows
├── cheatsheets/        Quick reference lookups
├── prompts/            Copy-paste prompts for Claude
└── resources.md        External tools and links

scripts/                Setup and build tooling
templates/              pyproject.toml templates
project-templates/      Generated reference outputs
```

## Bundles

| Bundle | Rules | MCP Servers | Use for |
|--------|-------|-------------|---------|
| `minimal` | general, work-org, context-mgmt, docs | — | Any project |
| `quant` | minimal + python, datasets | firecrawl, postgres | Data science, ML |
| `webdev` | minimal + typescript | vercel, playwright, chrome-devtools, docker, figma | Web apps |

## Plugin

**qute-essentials** — one install for all kit hooks and universal skills:

| Type | Components |
|------|------------|
| Hooks | forced-eval, ruff-formatter, doc-reminder, skill-use-logger, notifications |
| Guards | destructive, malware, secrets, audit, lakera, langfuse |
| Skills | commits, worktrees, handoff, pickup, decision, readme, guard, config, ship, ship-setup, audit, test, gbu, wtf |

```bash
claude plugin install qute-essentials@qute-marketplace
```

## Skills

### Universal (qute-essentials plugin)

| Skill | Invocation | Notes |
|-------|------------|-------|
| generating-commit-messages | automatic | Conventional commits |
| worktrees | `/worktrees` | Git worktree management |
| handoff | `/handoff` | Session-end: captures context, ADRs, TASKS |
| pickup | `/pickup` | Session-start: loads handoff, audits ADR health |
| decision | `/decision [--supersedes NNNN] <title>` | Record ADRs with auto-numbering |
| readme | `/readme` | README generation (forked context) |
| guard | `/guard [<name> <on\|off>]` | Toggle any of 6 security guards |
| config | `/config [--set key=value]` | Plugin notification config |
| ship-setup | `/ship-setup` | One-time commitizen + CHANGELOG setup |
| ship | `/ship` | Bump version, tag, update CHANGELOG |
| audit | `/audit` | Dependency CVE scan (pip-audit) |
| test | `/test [filter]` | Run test suite, interpret failures |
| gbu | `/gbu` | Good/Bad/Ugly structured review |
| wtf | `/wtf` | Acknowledge failure, retry immediately |

### Research & Data (quant bundle)

| Skill | Invocation |
|-------|------------|
| paper-reading | `/paper-reading [path]` |
| investment-research | `/investment-research` |
| investment-research-formal | `/investment-research-formal` |
| investment-research-dashboard | `/investment-research-dashboard` |
| market-datasets | `/market-datasets [ticker]` |
| analizy-pl-data | `/analizy-pl-data` |
| sql-patterns | `/sql-patterns` |
| qrd | `/qrd` |
| pipeline-docs | `/pipeline-docs` |
| python-patterns | model-invocable |
| image-generator | `/image-generator` |
| llm-external-review | `/llm-external-review` |

### Web Development (webdev bundle)

| Skill | Invocation |
|-------|------------|
| ui-ux-pro-max | `/ui-ux-pro-max` |

### Output

| Skill | Invocation |
|-------|------------|
| gist-report | `/gist-report` |
| gist-transcript | `/gist-transcript` |
| excalidraw | `/excalidraw` |

### Standalone (not in bundles)

| Skill | Notes |
|-------|-------|
| bird-twitter | Twitter/X posting |
| brand-dm-evo | Project-specific branding |
| brand-rockbridge | Project-specific branding |

## Agents

| Agent | Trigger | Purpose |
|-------|---------|---------|
| research-synthesizer | "synthesize these papers", multiple sources to compare | Cross-reference findings, identify consensus/conflicts |
| data-pipeline-debugger | "data looks wrong", unexpected pipeline output | Trace data flow, isolate the transformation stage where data breaks |

## MCP Servers

| Server | Bundle | Auth |
|--------|--------|------|
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
| decisions | `docs/decisions/**` | minimal |
| python-rules | `**/*.py` | quant |
| typescript-rules | `**/*.{ts,tsx,js,jsx}` | webdev |
| datasets | `data/**`, `docs/datasets/**` | quant |

## Documentation

| Type | Location | Purpose |
|------|----------|---------|
| [Playbooks](docs/playbooks/) | `docs/playbooks/` | Step-by-step workflows |
| [Cheatsheets](docs/cheatsheets/) | `docs/cheatsheets/` | Quick reference lookups |
| [Prompts](docs/prompts/) | `docs/prompts/` | Copy-paste into Claude |
| [Resources](docs/resources.md) | `docs/resources.md` | External tools and links |

## Worth Having

- [gstack](https://github.com/garrytan/gstack) — virtual engineering team for Claude Code: 23 specialized roles (CEO, designer, QA lead, security officer, etc.) as slash-command skills for running a full product development sprint

## Kit Management

```bash
# Audit kit consistency
/audit-kit

# Audit a project's setup
/check-setup ~/project

# Rebuild marketplace manifest
python scripts/build-marketplace.py

# Regenerate project templates
/refresh-templates
```
