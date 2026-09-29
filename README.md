# qute-code-kit

Tom's **personal skills & templates library** for Claude Code — a curated tree
of skills, an agent, doc templates, and playbooks
that you browse and **copy by hand** into target repos. Nothing here installs,
releases, or self-updates.

> **The plugins are not here.** `qute-essentials` (guards, hooks, the session
> loop, `/pr`, `/ship`) and `qute-research` (the research lifecycle) live in
> [`tomlupo/qute-plugins`](https://github.com/tomlupo/qute-plugins) and install
> from its marketplace; qute-essentials brings Matt Pocock's skills along as a
> dependency. This repo has **no plugin, no marketplace manifest, and no release
> cadence**.

## The kit: `claude/`

Generic skills (quant/data, engineering, visual/UX), a subagent and an
`AGENTS.md` starter. Browse [`INVENTORY.md`](INVENTORY.md) for the
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
cp ~/workspace/projects/qute-code-kit/claude/agents/data-pipeline-debugger.md ~/projects/myrepo/.claude/agents/
```

`pyproject.toml` and `.claude/settings.json` starters are not here: `onboard
repo` (qute-essentials) offers them where a repo has none (TOM-1235).

## Templates: `templates/`

Doc starters (PRD, tech spec, user flows) and a `WORKFLOW.md` orchestrator
contract. ADRs take their shape from `/decision`, and the tracker binding is
stamped by `onboard repo` — both qute-essentials. The research
scaffold — pin gate, line template, research-workflow — lives in the
qute-research plugin (`templates/research-scaffold/`), stamped by `onboard repo`.

## Browse

- [`INVENTORY.md`](INVENTORY.md) — full kit contents (skills / agents / templates)
- [`docs/playbooks/`](docs/playbooks/) — multi-step workflows (compound engineering, multi-agent review, investment research, session continuity, …)
- [`docs/cheatsheets/`](docs/cheatsheets/) — Claude CLI, prompt engineering, XML prompting
- [`docs/prompts/`](docs/prompts/) — reusable prompt patterns
- [`docs/playbooks/skill-router.md`](docs/playbooks/skill-router.md) — which skill, when (the discipline one-pager)
- [`docs/adr/`](docs/adr/) — pointer to the plugin ADRs (history stays in git)
- [`docs/resources.md`](docs/resources.md) — curated external links (interesting repos, tools, reading)

See [`CLAUDE.md`](CLAUDE.md) for repo conventions. Before committing here, install
[pre-commit](https://pre-commit.com) and [gitleaks](https://github.com/gitleaks/gitleaks), then run
`pre-commit install` — this repo is public.
