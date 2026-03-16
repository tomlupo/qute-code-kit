Audit the qute-code-kit repo for consistency. This is a read-only diagnostic — do not modify any files.

## Steps

### 1. Inventory all source components

Scan these directories and collect every component reference that exists on disk:

- `claude/rules/*.md` → `rules/<name>.md`
- `claude/root-files/CLAUDE.md` → `root/CLAUDE.md`
- `claude/root-files/AGENTS.md` → `root/AGENTS.md`
- `claude/settings/*.json` → `settings/<name>.json`
- `claude/commands/*.md` → `commands/<name>.md`
- `claude/hooks/*` → `hooks/<name>`
- `claude/skills/*/` → `<name>` (skill directories)
- `claude/agents/*` → `<name>` (agent files or directories)
- `claude/mcp/*.json` → `mcp:<name>`
- `templates/pyproject/*.toml` → `pyproject/<name>.toml`

### 2. Inventory all bundle references

Read every `.txt` file in `claude/bundles/`. For each file, collect all non-comment, non-blank, non-`@` lines — these are component refs.

### 3. Cross-reference

Produce three lists:

**Broken refs** — refs that appear in a bundle file but have no matching source file on disk. This is an error.

**Orphaned components** — source files that exist on disk but are not referenced by any bundle. This is a warning (some components like maintenance commands are intentionally unbundled).

**Unused bundles** — bundle files in `claude/bundles/` that are not referenced by any other bundle via `@name`. Top-level bundles (minimal, quant, webdev) are expected to be unused.

### 4. Plugin manifest validation

For each plugin in `plugins/*/plugin.json`:

- **author** must be an object (`{"name": "..."}`) not a string
- **No deprecated fields** — `commands`, `skills`, `hooks`, `rules` arrays should NOT be present (Claude Code auto-discovers these from directory structure)
- File must be valid JSON

Also check `templates/plugin-template/plugin.json` follows the same rules.

### 5. README table check

Read `README.md` and compare the tables (Skills, Agents, MCP Servers, etc.) against the on-disk inventory from step 1. Report any components that are on disk but missing from the README, or listed in the README but not on disk.

### 6. Stale references check

Search source components (`claude/rules/`, `claude/agents/`) for references to agents or components that no longer exist on disk. Report any stale references with file path and line number.

### 7. Report

Print a structured report with sections for each check. Use clear headings and bullet points. End with a summary line: `✓ N checks passed, M issues found` (or `✓ All checks passed`).
