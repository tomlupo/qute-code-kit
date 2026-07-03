# qute-code-kit

Home for **qute-essentials** — a Claude Code plugin focused on security guards, observability, and release tooling — plus a curated personal library of skills, agents, MCP configs, and settings that you can copy into target repos.

## The plugin: `qute-essentials`

Essential hooks, guards, and skills for Claude Code. Five toggleable security guards (block destructive commands, scan writes for secrets, screen tool output for prompt injection via Lakera, trace every tool call to Langfuse, auto-run pip-audit after dependency installs), a notification layer (ntfy push for blocks/detections), and 16 universal skills covering the full release-and-handoff lifecycle.

```bash
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace
```

### What you get

| | Components |
|---|---|
| **Hooks** | ruff-formatter, skill-use-logger, ntfy notifications, auto-audit, langfuse-trace |
| **Security guards** (toggleable via `/guard`) | destructive (blocks `rm -rf /`, `git reset --hard`, etc.), secrets (blocks writes containing API keys / private keys / tracked `.env`), audit (pip-audit on dependency changes), lakera (prompt-injection screening on untrusted tool output), langfuse (every-tool-call observability) |
| **Release & lifecycle** | `/ship` (Plugin-mode + Python-mode auto-detect; commitizen + CHANGELOG + tag), `/handoff`, `/pickup`, `/task`, `/repo-status` (git dashboard + Open tasks glance) |
| **Workflow** | `/audit`, `/test`, `/decision`, `/readme`, `/worktrees`, `/gbu`, `/wtf`, `/qute-review`, `/guard`, `generating-commit-messages` |

Full plugin reference (including the guard architecture diagram and per-hook event table): [`plugins/qute-essentials/README.md`](plugins/qute-essentials/README.md).

### Why it exists

- **Default-safe agent operation.** Two PreToolUse guards refuse destructive commands and secret writes before they run. Three PostToolUse guards screen dependency vulnerabilities, prompt injection, and trace every tool call.
- **Single-command releases.** `/ship` detects whether the repo is a plugin marketplace or a Python project and dispatches accordingly. First-run setup is idempotent — no separate `/ship-setup` step.
- **Cross-platform.** Hooks tested on Linux/macOS/Windows (Git Bash). No `jq`, `md5sum`, or `curl` dependencies in shell scripts (stdlib python everywhere).
- **Observable.** Every tool call traces to Langfuse with session/project/host tags; long-running commands and waiting prompts push to ntfy.

API keys for the optional integrations (`LAKERA_GUARD_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) go in your `~/.claude/settings.json` env block; the plugin works without them (those two guards just disable themselves).

## The personal kit: `claude/`

23 skills (quant research, engineering quality, visual/UX, workflow), 2 agents, 7 MCP server configs, 3 settings profiles. Browse [`INVENTORY.md`](INVENTORY.md) for the full map.

Pick what you need; copy by hand:

```bash
# Skill — copy directory
cp -r ~/projects/qute-code-kit/claude/skills/paper-reading ~/projects/myrepo/.claude/skills/

# Agent — single file
cp ~/projects/qute-code-kit/claude/agents/research-synthesizer.md ~/projects/myrepo/.claude/agents/

# MCP config
mkdir -p ~/projects/myrepo/.mcp/firecrawl
cp ~/projects/qute-code-kit/claude/mcp/firecrawl.json ~/projects/myrepo/.mcp/firecrawl/.mcp.json

# Settings profile
cp ~/projects/qute-code-kit/claude/settings/project-quant.json ~/projects/myrepo/.claude/settings.json
```

For new repos that need release tooling, install the plugin and use `/ship` (it bootstraps commitizen + CHANGELOG + GitHub Actions workflow on first run).

## Browse

- [`INVENTORY.md`](INVENTORY.md) — full kit contents (skills / agents / MCP / settings / templates)
- [`plugins/qute-essentials/README.md`](plugins/qute-essentials/README.md) — plugin reference (guards, hooks, skills)
- [`docs/playbooks/`](docs/playbooks/) — multi-step workflows (compound engineering, multi-agent review, investment research, session continuity, …)
- [`docs/cheatsheets/`](docs/cheatsheets/) — Claude CLI, prompt engineering, XML prompting
- [`docs/prompts/`](docs/prompts/) — reusable prompt patterns
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

## Releasing the plugin

```bash
scripts/release-plugin.sh qute-essentials <patch|minor|major|X.Y.Z>
git push --follow-tags
```

Or use the plugin's own `/ship` skill — it dispatches to this script when run from the marketplace repo.

See [`CLAUDE.md`](CLAUDE.md) for repo conventions and the canonical-manifest model.
