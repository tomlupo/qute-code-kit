# qute-code-kit

Home for **qute-essentials** — a Claude Code plugin providing the agent **runtime layer** (security guards, observability, task-store ops, review, release tooling) plus **research-regime skills** for quant/lab repos — and a curated personal library of skills, agents, MCP configs, and settings that you can copy into target repos.

qute is **Matt-compatible by design**: [Matt Pocock's skills](https://github.com/mattpocock/skills) own the planning spine (grill → spec → tickets → implement → TDD → code review) and the repo-binding conventions (`docs/agents/*.md`, `docs/adr/`, `CONTEXT.md`); qute keeps that work safe, tracked, reviewed, and shippable — and works standalone when Matt isn't installed. See [ADR-0001](docs/adr/0001-matt-planning-spine-qute-runtime.md).

## The plugin: `qute-essentials`

Essential hooks, guards, and skills for Claude Code. Six toggleable security guards (block destructive commands, scan writes for secrets, screen tool output for prompt injection via Lakera, trace every tool call to Langfuse, auto-run pip-audit after dependency installs, tag automated shared-record writes with an identity marker), a notification layer (ntfy push for blocks/detections), and universal skills covering the release-and-handoff lifecycle plus the standard research regime.

```bash
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace
```

### What you get

| | Components |
|---|---|
| **Hooks** | ruff-formatter, skill-use-logger, ntfy notifications, auto-audit, langfuse-trace |
| **Security guards** (toggleable via `/guard`) | destructive (blocks `rm -rf /`, `git reset --hard`, etc.), secrets (blocks writes containing API keys / private keys / tracked `.env`), audit (pip-audit on dependency changes), lakera (prompt-injection screening on untrusted tool output), langfuse (every-tool-call observability), provenance (auto-injects the `[agent:]`/`[session:]` identity tag on automated Linear-MCP / `gh pr` writes) |
| **Release & lifecycle** | `/ship` (Plugin-mode + Python-mode auto-detect; commitizen + CHANGELOG + tag), `/handoff`, `/pickup`, `/task`, `/board` (Linear write-identity conventions), `/repo-status` (git dashboard + Open tasks glance) |
| **Workflow** | `/audit`, `/test`, `/decision` (ADRs → `docs/adr/`), `/readme`, `/worktrees`, `/gbu`, `/wtf`, `/qute-review`, `/guard`, `generating-commit-messages` |
| **Research regime** ([ADR-0002](docs/adr/0002-standard-research-regime.md)) | `/research-line` (open/register a line), `/finding` (verdict-forced results + atomic index update), `/research-status` (drift detector + index regenerator), `/promote` (finding → ADR + prod PR / wiki / plugin) |
| **Regime setup** | `/setup-qute-repo` (guided onboarding wizard: repo type → tracker → conductor.yml → worktrees → shipping → research regime; supersedes adopt-matt-workflow), `/check-agent-regime` (audit for competing regimes / duplicate task stores) |
| **PR flow** ([ADR-0005](docs/adr/0005-qute-jimek-boundary-governance-modes.md) / [ADR-0006](docs/adr/0006-essentials-platform-contract-realignment.md)) | optional tier-aware `review-gate.yml` CI template; independent review is `/qute-review` (in essentials, it absorbed the retired `qute-reviewer`); the bot transport verbs `/qute-coder`, `/jimek-onboard` ship from the jimek repo (auto-installed globally by the bot) |

Full plugin reference (including the guard architecture diagram and per-hook event table): [`plugins/qute-essentials/README.md`](plugins/qute-essentials/README.md).

### Why it exists

- **Default-safe agent operation.** Three PreToolUse guards refuse destructive commands, block secret writes, and tag automated shared-record writes with an identity marker before they run. Three PostToolUse guards screen dependency vulnerabilities, prompt injection, and trace every tool call.
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
- [`docs/playbooks/skill-router.md`](docs/playbooks/skill-router.md) — which skill, when (the discipline one-pager)
- [`docs/adr/`](docs/adr/) — architecture decision records (Matt spine, research regime, tracking tiers)
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

## Releasing the plugin

```bash
scripts/release-plugin.sh qute-essentials <patch|minor|major|X.Y.Z>
git push --follow-tags
```

Or use the plugin's own `/ship` skill — it dispatches to this script when run from the marketplace repo.

See [`CLAUDE.md`](CLAUDE.md) for repo conventions and the canonical-manifest model.
