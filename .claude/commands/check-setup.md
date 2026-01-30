Audit a project's setup or user/global settings against the current kit. This is a read-only diagnostic — do not modify any files.

## Usage

```
/check-setup                                → prompt for path (or "user"/"global")
/check-setup user                           → audit ~/.claude/settings.json
/check-setup global                         → (same as "user")
/check-setup ~/projects/myproject           → audit a project
/check-setup ~/projects/myproject quant     → audit project, override bundle name
```

The target comes from $ARGUMENTS. If $ARGUMENTS is empty, ask the user what to audit: a project path, or "user" for global settings.

---

## Part A: User/Global audit

**When:** $ARGUMENTS is "user" or "global".

### A1. Read user settings

Read `~/.claude/settings.json`. Extract the `enabledPlugins` array and `permissions` object.

If the file doesn't exist, report that and stop.

### A2. Read kit reference

Read `claude/settings/global-generic.json` from the kit repo (relative to cwd).

### A3. Compare plugins

Compare the `enabledPlugins` arrays:

- **Missing plugins** — in the kit reference but not in user settings
- **Extra plugins** — in user settings but not in the kit reference
- **Present plugins** — in both (good)

### A4. Compare permissions

Compare the `permissions.allow` arrays (if present in both):

- **Missing permissions** — in kit but not in user settings
- **Extra permissions** — in user settings but not in kit

### A5. Report

Print a structured report:
- Section: "User/Global Settings Audit"
- Plugin comparison (missing / extra / present counts and lists)
- Permission comparison (missing / extra counts and lists)
- Summary line

---

## Part B: Project audit

**When:** $ARGUMENTS is a path (or after prompting for one).

### B1. Read project manifest (if exists)

Read `<target>/.claude/.toolkit-manifest.json`.

- **If found:** extract `bundle`, `installed`, `mode`, and `components[]` (use the `src` field from each entry). Proceed to B2.
- **If not found:** note "No manifest found — using filesystem scan." Proceed to B2.

### B2. Determine bundle

Pick the bundle name from the first available source:
1. Second word in $ARGUMENTS (e.g., `/check-setup ~/project quant` → "quant")
2. The `bundle` field from the manifest (if manifest exists)
3. Ask the user which bundle to compare against

### B3. Resolve current bundle

Read `claude/bundles/<bundle>.txt` from the kit repo. Recursively expand:
- `@name` → read `claude/bundles/name.txt`
- `@skills/name` → read `claude/bundles/skills/name.txt`

Collect the full deduplicated list of component refs the bundle currently specifies. Ignore comment lines (`#`) and blank lines.

If the bundle file doesn't exist, report this and list only the installed/discovered components.

### B4. Discover installed components

**If manifest exists** — use its component list (the `src` field of each entry).

**If no manifest** — scan the project filesystem to discover installed components:

| Project path pattern | Component ref |
|---------------------|---------------|
| `.claude/rules/<name>.md` | `rules/<name>.md` |
| `.claude/skills/<name>/` (directory) | Match against kit's `my:<name>` and `external:<name>` skills by directory name |
| `.claude/agents/<name>` (file or dir) | Match against kit's agent refs by name |
| `.claude/commands/<name>.md` | `commands/<name>.md` |
| `.claude/hooks/<name>` | `hooks/<name>` |
| `.mcp/<name>/` | `mcp:<name>` |
| Root `CLAUDE.md` exists | `root/CLAUDE.md` |
| Root `AGENTS.md` exists | `root/AGENTS.md` |

For skill/agent matching: read the kit's `claude/skills/my/`, `claude/skills/external/`, `claude/agents/my/`, and `claude/agents/external/` directories. Match discovered project directories/files against known kit component names.

### B5. Compare bundle vs installed

Produce three lists:

**Missing components** — in the current bundle but not installed/discovered. These need to be added.

**Extra components** — installed/discovered but not in the current bundle. These may have been removed from the bundle or added manually.

**Present components** — in both (good).

### B6. Check for outdated components

For each present component, compare the kit source file against the project's installed file by reading both and comparing content. Report which components have diverged.

Skip this step if:
- The project uses symlink mode (symlinks are always current)
- There is no manifest and the component type doesn't have a clear 1:1 file mapping

### B7. Settings comparison

Read the project's `.claude/settings.json` (if it exists).

Determine the kit's project settings template based on the bundle name:
- Look for `claude/settings/project-<bundle>.json`
- If not found, skip this step

If both exist, compare:
- **enabledPlugins**: list missing and extra plugins
- **permissions.allow**: list missing permissions from the template

Note: settings are templates, not exact copies — differences are advisory, not errors. If `.claude/settings.local.json` exists, note its presence (it's project-specific and not audited).

### B8. Propose fix commands

For missing components:
```
./setup-project.sh <target> --add <ref>
```

To sync everything at once:
```
./setup-project.sh <target> --bundle <bundle> --update
```

For settings/plugin differences, note that these need manual review since settings are templates adapted per project.

### B9. Report

Print a structured report with:
- **Header**: Project path, bundle name, install date and mode (or "no manifest — filesystem scan")
- **Component counts**: installed/discovered, expected from bundle, missing, extra, outdated
- **Detailed lists**: missing, extra, outdated components
- **Settings comparison**: plugin and permission diffs (if applicable)
- **Fix commands**: actionable commands to resolve gaps
- **Summary line**: e.g., "3 missing, 1 outdated, 2 extra — run --update to sync"
