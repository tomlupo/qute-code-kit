# qute-code-kit (retired)

Retired 2026-11-14 (TOM-3843, TOM-3853). Its skills, agent and templates now live in
[`tomlupo/qute-plugins`](https://github.com/tomlupo/qute-plugins) under `library/`, byte-equal, and this repo
holds no second copy:

- `claude/skills/{quant,engineering,visual}/*` → `library/skills/{quant,engineering,visual}/*`
- `claude/agents/data-pipeline-debugger.md` → `library/agents/`
- `claude/root-files/AGENTS.md`, `templates/*` → `library/templates/`

A repo that stamped a kit skill (`source_repo: qute-code-kit`) re-stamps it against `library/` in qute-plugins.
The plugins (qute-basic, qute-factory, qute-research) were never here. `docs/` (playbooks, prompts, cheatsheets, resources), `CONTEXT.md`, `conductor.yml`, `CHANGELOG.md`
and the history stay as they were, to be read only. The old `INVENTORY.md` is in git history.
