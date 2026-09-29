# qute-code-kit

Tom's **personal skills & templates library** — reusable Claude Code components
under `claude/` (skills, agents, an AGENTS.md starter) and doc templates under
`templates/`. The research scaffold (pin gate,
line template, research-workflow) is qute-research's, not the kit's. Browse and copy what you need into
target repos; a copied skill carries a `PROVENANCE.yaml` stamp (source path,
source commit, each file `tracked` or `forked from <sha>, reason: …`).

**What belongs here: generic skills only.** A skill whose content is bound to
one project lives in that project's repo, which is its master (TOM-1235,
2026-09-28: the dm-evo fund chain moved to dm-evo-lab, `backtest` and
`evo-dm-brand` to dm-evo-core, `brand-rockbridge` to robo-lab).

**The plugins are NOT here.** `qute-essentials` and `qute-research` live in
`tomlupo/qute-plugins`, with their marketplace, release tooling and ADRs
(`docs/adr/` here is a pointer). This repo has no release cadence — do not add
plugin manifests, marketplace files, or `/ship` release wiring here. Changes to
guards, hooks, review/release regime, or plugin skills belong in qute-plugins.

## Layout

| Path | Contents |
|---|---|
| `claude/skills/` | Generic kit skills, grouped: `quant/`, `engineering/`, `visual/` (`<name>/SKILL.md` + assets) |
| `claude/agents/` | Personal-kit subagents |
| `claude/root-files/` | Root-level AGENTS.md starter |
| `templates/docs/` | Doc starters (PRD, tech spec, user flows) |
| `docs/playbooks/`, `docs/cheatsheets/`, `docs/prompts/` | Workflows, references, reusable prompts |
| `docs/adr/` | Pointer to the plugin ADRs (history in git) |

## Conventions

- Conventional Commits with scope (e.g. `feat(skill): ...`, `docs(playbook): ...`).
- Skills are directories containing `SKILL.md`. Agents can be single `.md` files or directories with `AGENT.md`.
- No hardcoded secrets — use `${ENV_VAR}` placeholders.
- This is a curated tree, not a generated one — no build step, no manifests.

## Adding a kit component

1. Create the file(s) under the appropriate `claude/<type>/` directory.
2. Add a row to the relevant table in `INVENTORY.md`.
3. Commit with Conventional Commits (`feat(skill-name): ...`).

**The kit is the incubator** (Tom, 2026-09-28). A NEW **generic** skill starts
here — not in a plugin — and is copied by hand into the repos that try it. When it has
become part of a process every repo or lab should run the same way, move it into
a plugin in **qute-plugins** (`qute-essentials`, or `qute-research` for the
research lifecycle), release it there, and delete it here — moving means moving.

MCP server configs are not kept here (removed 2026-09-28, TOM-1235): a copied
config drifts from the server it describes, and each server's own install docs
are the authority.

## Skill frontmatter properties

| Property | Values | Default | Purpose |
|----------|--------|---------|---------|
| `name` | string | directory name | Skill identifier (lowercase, hyphens, max 64 chars) |
| `description` | string | first paragraph | When to use (include trigger phrases) |
| `argument-hint` | string | (none) | Hint shown during autocomplete |
| `user-invocable` | `true` / `false` | `true` | Whether users can invoke via `/skill-name` |
| `disable-model-invocation` | `true` / `false` | `false` | Prevent model from auto-invoking |
| `allowed-tools` | tool names | (all) | Restrict tools when active |
| `model` | model name | (inherit) | Model to use when active |
| `agent` | agent name (e.g. `Explore`) | (none) | Subagent type when `context: fork` is set |
| `context` | `fork` | (none) | Fork context for isolated subagent execution |
| `hooks` | hook config | (none) | Lifecycle hooks scoped to this skill |

**When to use each:**

- `disable-model-invocation: true` — user-initiated only (pair it with `agents/openai.yaml` `policy.allow_implicit_invocation: false` so Codex agrees).
- `user-invocable: false` — model-only skills.
- `agent: <name>` — search/research skills where a subagent protects the main context window.
- `context: fork` — side-output produced in parallel (e.g. memory/summarization).
- `allowed-tools` — read-only or restricted skills.
- `argument-hint` — skills invoked with arguments.

### Skill dynamic features

**String substitutions** in skill content:

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` | Specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |

**Dynamic context injection:** Use `` !`command` `` to run shell commands before skill content is sent to Claude.

## Agent frontmatter properties

| Property | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Unique identifier (lowercase, hyphens) |
| `description` | Yes | When Claude should delegate to this agent |
| `tools` | No | Allowed tools (inherits all if omitted) |
| `disallowedTools` | No | Tools to deny from inherited list |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `skills` | No | Skills preloaded into agent context at startup |
| `hooks` | No | Lifecycle hooks scoped to this agent |

## Hook events

`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `SessionEnd`.

Options: `once: true` (run once per session, skills only), `async: true` (non-blocking, command hooks only).
