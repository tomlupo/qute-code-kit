# qute-code-kit

Reusable Claude Code components, bundled and deployed via `setup-project.sh`. See `README.md` for full inventory and quick-start.

## Architecture

```
claude/              Source components (rules, skills, agents, commands, hooks, MCP configs, settings)
claude/bundles/      Bundle manifests — text files listing which components belong together
templates/           Non-Claude scaffolding (pyproject templates, .gitignore)
scripts/setup-project.sh  Engine — resolves bundles, copies/links components to a target project
project-templates/   Generated reference outputs (minimal/, quant/, webdev/)
```

The workflow: **source components** are authored in `claude/`, grouped by **bundles**, and deployed to target projects by `setup-project.sh`. The `project-templates/` directory contains regenerated example outputs for each bundle.

## Component types

| Prefix | Source path | Target path |
|--------|-------------|-------------|
| `rules/name.md` | `claude/rules/` | `.claude/rules/` |
| `root/CLAUDE.md` | `claude/root-files/` | project root |
| `root/AGENTS.md` | `claude/root-files/` | project root |
| `settings/name.json` | `claude/settings/` | `.claude/settings.json` |
| `pyproject/name.toml` | `templates/pyproject/` | `pyproject.toml` |
| `commands/name.md` | `claude/commands/` | `.claude/commands/` |
| `hooks/name.py` | `claude/hooks/` | `.claude/hooks/` |
| `skill-name` | `claude/skills/skill-name/` | `.claude/skills/` |
| `agent-name` | `claude/agents/agent-name.md` | `.claude/agents/` |
| `mcp:name` | `claude/mcp/name.json` | `.mcp/name/.mcp.json` |
| `@bundle` | `claude/bundles/bundle.txt` | (expands to listed components) |

## Plugins

Plugins live in `plugins/` and provide runtime hooks/commands. Unlike bundle components (deployed to projects), plugins are installed globally via `claude plugin install`.

### Plugin structure

```
plugins/plugin-name/
├── plugin.json           # Manifest (name, description, version)
├── hooks/
│   └── hooks.json        # Lifecycle hooks
├── commands/             # Slash commands
├── skills/               # Domain knowledge
└── scripts/              # Hook implementations
```

### Managing plugins

```bash
python scripts/build-marketplace.py    # Rebuild marketplace manifest
python scripts/create-plugin.py name   # Scaffold new plugin
```

### Available plugins

| Plugin | Description |
|--------|-------------|
| qute-essentials | Hooks (forced-eval, ruff, doc-enforcer, skill-logger, notifications) + universal skills (commits, worktrees, handoff, readme, gbu, wtf) |

## Skills and slash commands

Slash commands and skills are now unified in Claude Code. Every skill can be invoked with `/` syntax, and every slash command can be called as a skill. **Prefer creating skills over commands** for new components — skills support progressive disclosure, subagent integration, and new invocation controls.

### Skill frontmatter properties

| Property | Values | Default | Purpose |
|----------|--------|---------|---------|
| `name` | string | directory name | Skill identifier (lowercase, hyphens, max 64 chars) |
| `description` | string | first paragraph | When to use this skill (include trigger phrases) |
| `argument-hint` | string | (none) | Hint shown during autocomplete (e.g., `[issue-number]`) |
| `user-invocable` | `true` / `false` | `true` | Whether users can invoke via `/skill-name` |
| `disable-model-invocation` | `true` / `false` | `false` | Prevent model from auto-invoking |
| `allowed-tools` | tool names | (all) | Restrict tools when skill is active (e.g., `Read, Grep, Glob`) |
| `model` | model name | (inherit) | Model to use when skill is active |
| `agent` | agent name (e.g. `Explore`) | (none) | Subagent type when `context: fork` is set |
| `context` | `fork` | (none) | Fork context for isolated subagent execution |
| `hooks` | hook config | (none) | Lifecycle hooks scoped to this skill (see Hooks section) |

**When to use each property:**

- `disable-model-invocation: true` — For user-initiated actions only (e.g., `gist-report`, `gist-transcript`)
- `user-invocable: false` — For model-only skills (e.g., `context-management` which the model should auto-apply)
- `agent: <name>` — For search/research skills where a subagent protects the main context window (e.g., `paper-reading` with `agent: Explore`)
- `context: fork` — For skills that produce side-output in parallel (e.g., `readme` generation, memory/summarization)
- `allowed-tools` — For read-only or restricted skills (e.g., a safe-reader with `Read, Grep, Glob`)
- `model` — When a specific model is better suited (e.g., `haiku` for lightweight agents)
- `argument-hint` — For skills invoked with arguments (e.g., `/fix-issue [issue-number]`)
- `hooks` — For skills that need validation before tool calls (e.g., security checks on Bash commands)

### Skill dynamic features

**String substitutions** in skill content:

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` | Specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |

**Dynamic context injection:** Use `` !`command` `` to run shell commands before skill content is sent to Claude. The command output replaces the placeholder.

### Existing commands

The `claude/commands/` directory still works for backward compatibility. Existing `commands/` refs in bundles are still supported by `setup-project.sh`. However, new user-invocable actions should be created as skills instead.

## Adding a new component

### Skill

1. Create `claude/skills/skill-name/` with a `SKILL.md` file inside
2. Add frontmatter with `name`, `description`, and any controls (`disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `agent`, `context`, `hooks`)
3. Add `skill-name` to the appropriate bundle `.txt` file(s) in `claude/bundles/`
4. Add a row to the Skills table in `README.md`
5. Regenerate affected templates (see below)

### Agent

1. Create `claude/agents/agent-name.md` (single file) or `claude/agents/agent-name/` (directory with `AGENT.md`)
2. Add frontmatter with `name`, `description`, and any controls (see table below)
3. Add `agent-name` to bundle file(s)
4. Update `README.md`
5. Regenerate templates

#### Agent frontmatter properties

| Property | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Unique identifier (lowercase, hyphens) |
| `description` | Yes | When Claude should delegate to this agent |
| `tools` | No | Allowed tools (inherits all if omitted) |
| `disallowedTools` | No | Tools to deny from inherited list |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `skills` | No | Skills preloaded into agent context at startup |
| `hooks` | No | Lifecycle hooks scoped to this agent |

### MCP server

1. Create `claude/mcp/servername.json` — use `${ENV_VAR}` for secrets, never hardcode keys
2. Add `mcp:servername` to bundle file(s)
3. Add a row to the MCP Servers table in `README.md`
4. Regenerate templates — `setup-project.sh` auto-populates `.env.example` with required env vars

### Hook

Hooks can be defined in two ways:

**Standalone scripts** (deployed via bundles):
1. Create `claude/hooks/hook-name.py`
2. Add `hooks/hook-name.py` to bundle file(s)
3. Configure the hook event in `settings.json` (see below)
4. Regenerate templates

**In skill/agent frontmatter** (scoped to component lifecycle):
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
```

Hook types: `command` (shell script), `prompt` (LLM evaluation), `agent` (multi-turn subagent verification).

Hook events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `SessionEnd`.

Options: `once: true` (run once per session, skills only), `async: true` (non-blocking, command hooks only).

### Command (legacy — prefer skills)

1. Create `claude/commands/command-name.md`
2. Add `commands/command-name.md` to bundle file(s)
3. Regenerate templates
4. **Note:** Consider creating a skill instead — skills support subagents, invocation controls, and progressive disclosure

### Rule

1. Create `claude/rules/rule-name.md`
2. Add `rules/rule-name.md` to bundle file(s)
3. Regenerate templates

## Bundles

Bundle files live in `claude/bundles/`. Format: one component ref per line, `#` for comments, `@name` to inherit another bundle.

```
# Example bundle
@minimal                    # inherit all minimal components
settings/project-quant.json
paper-reading
mcp:firecrawl
```

### Creating a new bundle

1. Create `claude/bundles/newbundle.txt`
2. List component refs (one per line); use `@minimal` to inherit the base
3. Add a row to the Bundles table in `README.md`
4. Optionally generate a template: `./scripts/setup-project.sh project-templates/newbundle --bundle newbundle`

## Refreshing templates

After any component or bundle change, regenerate the affected templates:

```bash
./scripts/setup-project.sh project-templates/minimal --bundle minimal --update
./scripts/setup-project.sh project-templates/quant --bundle quant --update
./scripts/setup-project.sh project-templates/webdev --bundle webdev --update
```

## Auditing an existing project

Preview what would change without modifying anything:

```bash
./scripts/setup-project.sh ~/projects/existing-project --bundle quant --diff
```

Check what was previously installed:

```bash
cat ~/projects/existing-project/.claude/.toolkit-manifest.json
```

Bring a project up to date with the latest kit:

```bash
./scripts/setup-project.sh ~/projects/existing-project --bundle quant --update
```

Add individual components to an existing project:

```bash
./scripts/setup-project.sh ~/projects/existing-project --add paper-reading
```

## Conventions

- No hardcoded secrets — use `${ENV_VAR}` placeholders in MCP configs
- No personal paths in committed files
- MCP configs use cross-platform `npx` (not `cmd /c`)
- Skills are directories containing `SKILL.md`; agents can be single `.md` files or directories with `AGENT.md`
- Prefer skills over commands for new user-invocable actions
- Use skill frontmatter properties (`allowed-tools`, `model`, `agent`, `context`, `hooks`, `disable-model-invocation`, `user-invocable`) to control behavior
- Use agent frontmatter properties (`tools`, `disallowedTools`, `model`, `permissionMode`, `skills`, `hooks`) for subagent configuration
- Keep `README.md` tables in sync with bundle contents
- Always regenerate templates after component or bundle changes
