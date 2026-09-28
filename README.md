# qute-code-kit

Tom's **personal skills & templates library** for Claude Code — a curated tree
of skills, agents, MCP configs, settings profiles, doc templates, and playbooks
that you browse and **copy by hand** into target repos. Nothing here installs,
releases, or self-updates.

> **The plugins are not here.** `qute-essentials` (guards, hooks, the session
> loop, `/pr`, `/ship`) and `qute-research` (the research lifecycle) live in
> [`tomlupo/qute-plugins`](https://github.com/tomlupo/qute-plugins) and install
> from its marketplace; qute-essentials brings Matt Pocock's skills along as a
> dependency. This repo has **no plugin, no marketplace manifest, and no release
> cadence**.

## The kit: `claude/`

19 generic skills (quant/data, multi-agent research workflows, engineering,
visual/UX), 2 agents, 7 MCP server configs, 3 settings profiles, 2 root-file
starters. Browse [`INVENTORY.md`](INVENTORY.md) for the full map. A skill bound
to one project does not live here: its master is that project's repo
(TOM-1235, 2026-09-28).

Pick what you need and copy it by hand. A copied skill carries a
`PROVENANCE.yaml` (source path, source commit, each file `tracked` or
`forked from <sha>, reason: …`) so its drift from the kit can be checked:

```bash
# Skill — copy the directory, then stamp PROVENANCE.yaml in the copy
cp -r ~/workspace/projects/qute-code-kit/claude/skills/quant/market-datasets ~/projects/myrepo/.claude/skills/

# Agent — single file
cp ~/workspace/projects/qute-code-kit/claude/agents/research-synthesizer.md ~/projects/myrepo/.claude/agents/

# MCP config
mkdir -p ~/projects/myrepo/.mcp/firecrawl
cp ~/workspace/projects/qute-code-kit/claude/mcp/firecrawl.json ~/projects/myrepo/.mcp/firecrawl/.mcp.json

# Settings profile
cp ~/workspace/projects/qute-code-kit/claude/settings/project-quant.json ~/projects/myrepo/.claude/settings.json
```

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
- [`docs/adr/`](docs/adr/) — pointer to the plugin ADRs (history stays in git)
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

See [`CLAUDE.md`](CLAUDE.md) for repo conventions.
