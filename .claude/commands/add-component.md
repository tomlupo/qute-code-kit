Guided walkthrough for adding a new component to qute-code-kit.

## Step 1: Gather info

Ask the user for:

1. **Component type** — one of: rule, command, hook, skill, agent, mcp, pyproject
2. **Name** — the component name (e.g., `my-new-skill`, `eslint`, `data-validation.md`)
3. **Bundles** — which bundle(s) to add it to (minimal, quant, webdev)

Use $ARGUMENTS if the user already provided some of this info.

## Step 2: Create the source file(s)

Based on the type, create the scaffold:

| Type | Action |
|------|--------|
| `rule` | Create `claude/rules/<name>.md` with a placeholder heading |
| `command` | Create `claude/commands/<name>.md` with a placeholder heading |
| `hook` | Create `claude/hooks/<name>.py` with a minimal Python stub |
| `skill` | Create `claude/skills/<name>/SKILL.md` with a placeholder |
| `agent` | Ask: single file (`claude/agents/<name>.md`) or directory (`claude/agents/<name>/AGENT.md`). Create accordingly. |
| `mcp` | Create `claude/mcp/<name>.json` — ask the user for the command, args, and any `${ENV_VAR}` placeholders |
| `pyproject` | Create `templates/pyproject/<name>.toml` with a minimal `[project]` section |

After creating the file(s), tell the user the path(s) created and suggest they fill in the content.

## Step 3: Add to bundle(s)

For each bundle the user selected, append the component reference to the appropriate `.txt` file in `claude/bundles/`.

Use the correct ref format from CLAUDE.md (e.g., `skill-name`, `mcp:server`, `rules/name.md`).

## Step 4: Offer to regenerate templates

Ask: "Want me to regenerate the affected project-templates now?"

If yes, run the appropriate `./scripts/setup-project.sh project-templates/<bundle> --bundle <bundle> --update` command(s) for each affected bundle.

## Step 5: Summary

Print what was created:
- Source file(s) created
- Bundle(s) updated
- Whether templates were regenerated
- Remind the user to update the README.md tables
