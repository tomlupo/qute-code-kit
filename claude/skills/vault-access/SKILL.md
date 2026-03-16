---
name: vault-access
description: "Read product specs and project context from the Obsidian vault. Resolves vault path by hostname. Use when you need to fetch latest specs, read project _meta.md, or search vault notes."
user-invocable: true
---

# Vault Access

Read product specs, project context, and knowledge from the Obsidian vault. The vault is synced to every machine via Syncthing — this skill resolves the correct local path.

## Step 1: Determine vault path

Run `hostname` to identify the machine, then use the matching path:

| Hostname | Vault path |
|----------|------------|
| `x13` | `C:\Users\twilc\Obsidian\notebook` |
| `bots` | `/srv/obsidian/notebook` |
| `core` | `/srv/obsidian/notebook` |

If hostname doesn't match, try fallbacks in order:
1. `$OBSIDIAN_VAULT_PATH` environment variable
2. `~/obsidian/notebook`
3. `/srv/obsidian/notebook`

If no local vault found, fetch from GitHub:
- Repo: `tomlupo/obsidian-vaults`
- Branch: `main`
- Root: `notebook/`

## Step 2: Read `_meta.md`

Every project has `_meta.md` in its vault folder:

```yaml
---
project: my-project
github_repo: owner/my-project
status: active
tags: [dev, app]
project_dir: user@host:/path/to/working/dir
---

One-line description.
```

Check CLAUDE.md for the vault project path (e.g., `projects/alphaops/collaboo/`).

## Step 3: Read specs

Read files directly from the resolved vault path:

```bash
# Linux/Mac
cat "$VAULT_PATH/projects/my-project/prd.md"

# Windows
type "%VAULT_PATH%\projects\my-project\prd.md"
```

## Step 4: Search (optional)

```bash
# Find files by name
find "$VAULT_PATH" -name "*.md" -path "*/projects/*" | sort

# Search content
grep -r "keyword" "$VAULT_PATH" --include="*.md" -l
```

## Vault structure

| Folder | Purpose |
|--------|---------|
| `areas/` | Life domains (diet, fitness, health, work) |
| `systems/` | Infrastructure specs |
| `knowledge/` | Synthesized understanding |
| `resources/` | Tools, references, prompts |
| `projects/` | Active finite work — each has `_meta.md` |
| `inbox/` | Captures, daily notes, reports |

## Rules

- The vault is **read-only**. Never write to it.
- Prefer `docs/specs/` in the repo for day-to-day work (committed copies).
- Use vault access for the latest version or broader context.
