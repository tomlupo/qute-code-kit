# qute-code-kit

This repo serves two roles in one tree:

1. **Personal kit** — reusable Claude Code components under `claude/`
   (skills, agents, MCP configs, settings, root-file templates). Browse and
   copy what you need into target repos.
2. **Distributable plugin** — `plugins/qute-essentials/` is the
   Claude Code plugin published via `.claude-plugin/marketplace.json` and
   installed with `claude plugin install qute-essentials@qute-marketplace`.

There is no bundle, scaffold, or setup-script flow. The plugin half ships
itself via the marketplace; the kit half is plain files you copy by hand.

## Hybrid philosophy

qute is complementary to Matt Pocock-style skills.

Do not grow qute into a competing planning framework. Use qute as the agent runtime and operating layer:

- guards and safety enforcement
- observability and notifications
- task tracking and repo status
- handoff/pickup
- tests and audits
- ADR creation
- independent review
- release/version/tag hygiene

Use Matt-style skills for the organizing engineering loop:

- grilling / clarification
- domain modeling
- spec creation
- ticket decomposition
- implementation orchestration
- TDD
- architecture cleanup
- spec-aware code review

Canonical reference: `docs/architecture/matt-qute-hybrid-stack.md`.
Target-repo playbook: `docs/playbooks/matt-qute-hybrid-workflow.md`.

When adding a new qute skill, check whether it duplicates a Matt-style generic engineering role. If yes, prefer documenting how qute integrates with Matt instead of adding another qute skill.

## Layout

| Path | Contents |
|---|---|
| `claude/skills/` | Personal-kit skills (`<name>/SKILL.md` + assets) |
| `claude/agents/` | Personal-kit subagents |
| `claude/mcp/` | MCP server configs |
| `claude/settings/` | Claude Code project settings profiles |
| `claude/root-files/` | Root-level CLAUDE.md / AGENTS.md starters |
| `plugins/qute-essentials/` | Distributable plugin (its own README + SKILL.md files) |
| `.claude-plugin/marketplace.json` | Marketplace manifest (regenerated from plugin manifest) |
| `templates/docs/`, `templates/pyproject/` | Doc / pyproject templates (used by `/ship`'s first-time-setup) |
| `docs/playbooks/`, `docs/cheatsheets/`, `docs/prompts/`, `docs/architecture/` | Workflows, references, reusable prompts, architecture notes |
| `scripts/build-marketplace.py`, `scripts/release-plugin.sh` | Release tooling |
| `.githooks/pre-commit` | Plugin-version drift detector (enable: `git config core.hooksPath .githooks`) |

## Conventions

- Conventional Commits with scope (e.g. `feat(skill): ...`, `fix(plugin): ...`).
- One canonical manifest per plugin — `plugins/<name>/.claude-plugin/plugin.json`. The pre-commit hook + `release-plugin.sh` enforce drift-free version updates.
- `marketplace.json` is generated, not hand-edited. Edit the plugin manifest; run `python3 scripts/build-marketplace.py`.
- Skills are directories containing `SKILL.md`. Agents can be single `.md` files or directories with `AGENT.md`.
- No hardcoded secrets — use `${ENV_VAR}` placeholders in MCP configs.
- For hybrid target repos, prefer `docs/agents/*.md` over ever-growing `CLAUDE.md` files.

## Releasing the plugin

```bash
scripts/release-plugin.sh qute-essentials <patch|minor|major|X.Y.Z>
git push --follow-tags
```

This bumps `plugins/qute-essentials/.claude-plugin/plugin.json`, regenerates `marketplace.json`, writes a CHANGELOG entry from Conventional Commits since the last tag, commits, and tags. Or use the plugin's own `/ship` skill — it dispatches to this script automatically when the repo root has `.claude-plugin/marketplace.json`.

## Adding a kit component

This is a curated tree, not a generated one. To add a skill / agent / MCP config:

1. Create the file(s) under the appropriate `claude/<type>/` directory.
2. Add a row to the relevant table in `README.md` or `INVENTORY.md`.
3. Commit with Conventional Commits (`feat(skill-name): ...`).

Promotion path: when a personal-kit component proves universally useful, move it into `plugins/qute-essentials/skills/` and bump the plugin via `scripts/release-plugin.sh`.

Do not promote repo/domain-specific planning workflows into `qute-essentials` if they are better represented as Matt skills plus repo-local `docs/agents/` rules.

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

- `disable-model-invocation: true` — user-initiated only (e.g. `gist-report`).
- `user-invocable: false` — model-only skills (e.g. `context-management`).
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
