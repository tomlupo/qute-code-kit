# qute-code-kit

Tom's **personal skills & templates library** for Claude Code — a curated tree
of skills, agents, settings profiles, doc templates, and playbooks
that you browse and **copy by hand** into target repos. Nothing here installs,
releases, or self-updates.

> **The plugins are not here.** `qute-essentials` (guards, hooks, the session
> loop, `/pr`, `/ship`) and `qute-research` (the research lifecycle) live in
> [`tomlupo/qute-plugins`](https://github.com/tomlupo/qute-plugins) and install
> from its marketplace; qute-essentials brings Matt Pocock's skills along as a
> dependency. This repo has **no plugin, no marketplace manifest, and no release
> cadence**.

## The kit: `claude/`

12 generic skills (quant/data, engineering, visual/UX), 2 agents, 3 settings
profiles, 2 root-file starters. Browse [`INVENTORY.md`](INVENTORY.md) for the
full map. A skill bound to one project does not live here: its master is that
project's repo (TOM-1235, 2026-09-28).

**New generic skills start here** — the kit is the incubator; the rule and the
promotion path are in [`CLAUDE.md`](CLAUDE.md).

Pick what you need and copy it by hand. A copied skill carries a
`PROVENANCE.yaml` (source path, source commit, each file `tracked` or
`forked from <sha>, reason: …`) so its drift from the kit can be checked:

```bash
# Skill — copy the directory, then stamp PROVENANCE.yaml in the copy
cp -r ~/workspace/projects/qute-code-kit/claude/skills/quant/market-datasets ~/projects/myrepo/.claude/skills/

# Agent — single file
cp ~/workspace/projects/qute-code-kit/claude/agents/research-synthesizer.md ~/projects/myrepo/.claude/agents/

# Settings profile
cp ~/workspace/projects/qute-code-kit/claude/settings/project-quant.json ~/projects/myrepo/.claude/settings.json
```

## Templates: `templates/`

Doc starters (ADR, PRD, tech spec, user flows, issue-tracker binding),
`pyproject.toml` starters (quant / webdev, uv + ruff + pyright + pytest), a
`WORKFLOW.md` orchestrator contract, and settings profiles. The research
scaffold — pin gate, line template, research-workflow — lives in the
qute-research plugin (`templates/research-scaffold/`), stamped by `onboard repo`.

## Browse

- [`INVENTORY.md`](INVENTORY.md) — full kit contents (skills / agents / settings / templates)
- [`docs/playbooks/`](docs/playbooks/) — multi-step workflows (compound engineering, multi-agent review, investment research, session continuity, …)
- [`docs/cheatsheets/`](docs/cheatsheets/) — Claude CLI, prompt engineering, XML prompting
- [`docs/prompts/`](docs/prompts/) — reusable prompt patterns
- [`docs/playbooks/skill-router.md`](docs/playbooks/skill-router.md) — which skill, when (the discipline one-pager)
- [`docs/adr/`](docs/adr/) — pointer to the plugin ADRs (history stays in git)
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

See [`CLAUDE.md`](CLAUDE.md) for repo conventions.
