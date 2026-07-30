# qute-code-kit

Tom's **personal skills & templates library** for Claude Code — a curated tree
of skills, agents, MCP configs, settings profiles, doc templates, and playbooks
that you browse and **copy by hand** into target repos. Nothing here installs,
releases, or self-updates.

> **The `qute-essentials` plugin moved out.** As of **2026-07-29** the plugin
> (guards, hooks, `/ship`, `/qute-review`, the research-regime skills) lives in
> [`tomlupo/qute-platform`](https://github.com/tomlupo/qute-platform) under
> `agent-kit/plugins/qute-essentials/`, published via the agent-kit
> marketplace. Its ADRs moved with it (see [`docs/adr/`](docs/adr/)). This repo
> has **no plugin, no marketplace manifest, and no release cadence** anymore —
> install and update the plugin from qute-platform, not from here.

## The kit: `claude/`

33 skills across five categories (quant/research, engineering, multi-agent
research workflows, visual/UX, brand) plus the `workflow` bundle, 2 agents,
7 MCP server configs, 3 settings profiles, 2 root-file starters. Browse
[`INVENTORY.md`](INVENTORY.md) for the full map.

Pick what you need; copy (or symlink) by hand:

```bash
# Skill — copy directory
cp -r ~/workspace/projects/qute-code-kit/claude/skills/quant/paper-reading ~/projects/myrepo/.claude/skills/

# Skill — or symlink into your global skills (edits here are instantly live)
ln -s ~/workspace/projects/qute-code-kit/claude/skills/visual/ui-ux-pro-max ~/.claude/skills/

# Agent — single file
cp ~/workspace/projects/qute-code-kit/claude/agents/research-synthesizer.md ~/projects/myrepo/.claude/agents/

# MCP config
mkdir -p ~/projects/myrepo/.mcp/firecrawl
cp ~/workspace/projects/qute-code-kit/claude/mcp/firecrawl.json ~/projects/myrepo/.mcp/firecrawl/.mcp.json

# Settings profile
cp ~/workspace/projects/qute-code-kit/claude/settings/project-quant.json ~/projects/myrepo/.claude/settings.json
```

Several skills here are wired into `~/.claude/skills/` by symlink today
(`research-*`, `architecture-diagram`, `ui-ux-pro-max`) — edits in this repo
are live immediately for those.

## Templates: `templates/`

Doc starters (ADR, PRD, tech spec, user flows, research-workflow and
issue-tracker bindings), `pyproject.toml` starters (quant / webdev, uv + ruff +
pyright + pytest), a `WORKFLOW.md` orchestrator contract, settings profiles,
and the canonical research gate `templates/research/check_research_pins.py`
(unit-tested in `tests/`).

## Browse

- [`INVENTORY.md`](INVENTORY.md) — full kit contents (skills / agents / MCP / settings / templates)
- [`docs/playbooks/`](docs/playbooks/) — multi-step workflows (compound engineering, multi-agent review, investment research, session continuity, …)
- [`docs/cheatsheets/`](docs/cheatsheets/) — Claude CLI, prompt engineering, XML prompting
- [`docs/prompts/`](docs/prompts/) — reusable prompt patterns
- [`docs/playbooks/skill-router.md`](docs/playbooks/skill-router.md) — which skill, when (the discipline one-pager)
- [`docs/adr/`](docs/adr/) — pointer to the plugin's ADRs in qute-platform (history stays in git)
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

See [`CLAUDE.md`](CLAUDE.md) for repo conventions.
