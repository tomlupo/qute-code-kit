# Marketplace Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge qute-marketplace into qute-code-kit as a unified repository with bundles, plugins, and documentation.

**Architecture:** Move marketplace plugins to `plugins/`, external repos to `external/`, scripts to `scripts/`, and create `docs/` for guides. Update paths in build scripts. Keep both bundle and plugin systems functional.

**Tech Stack:** Bash, Python, Git

---

## Task 1: Create directory structure

**Files:**
- Create: `scripts/` (directory)
- Create: `docs/` (directory)
- Create: `docs/workflows/` (directory)
- Create: `docs/tutorials/` (directory)

**Step 1: Create directories**

```bash
mkdir -p scripts docs/workflows docs/tutorials
```

**Step 2: Verify**

```bash
ls -la scripts docs
```
Expected: Both directories exist

**Step 3: Commit**

```bash
git add scripts docs
git commit -m "chore: create scripts/ and docs/ directories for unified structure"
```

---

## Task 2: Move setup-project.sh to scripts/

**Files:**
- Move: `setup-project.sh` → `scripts/setup-project.sh`
- Move: `setup-project.bat` → `scripts/setup-project.bat`
- Create: `setup-project.sh` (symlink at root for backward compatibility)

**Step 1: Move scripts**

```bash
mv setup-project.sh scripts/
mv setup-project.bat scripts/
```

**Step 2: Create backward-compatible symlink**

```bash
ln -s scripts/setup-project.sh setup-project.sh
```

**Step 3: Verify symlink works**

```bash
./setup-project.sh --help 2>&1 | head -5
```
Expected: Shows usage or runs without error

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move setup scripts to scripts/ with backward-compatible symlink"
```

---

## Task 3: Move marketplace plugins to plugins/

**Files:**
- Move: `repos/qute-marketplace/plugins/*` → `plugins/`

**Step 1: Move plugins directory**

```bash
mv repos/qute-marketplace/plugins plugins
```

**Step 2: Verify structure**

```bash
ls plugins/
```
Expected: doc-enforcer, forced-eval, notifications, research-workflow, session-persistence, skill-use-logger, strategic-compact

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: move marketplace plugins to top-level plugins/"
```

---

## Task 4: Move external plugins directory

**Files:**
- Move: `repos/qute-marketplace/external/` → `external/`
- Modify: `.gitignore` (add external/ ignore)

**Step 1: Move external directory**

```bash
mv repos/qute-marketplace/external external
```

**Step 2: Update .gitignore**

Replace `repos/` line with `external/` in `.gitignore`:

Find and replace:
```
repos/
```
With:
```
# External plugins (cloned from GitHub)
external/
```

**Step 3: Verify**

```bash
ls external/
```
Expected: compound-engineering-plugin, homunculus (if previously fetched)

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move external plugins to top-level external/"
```

---

## Task 5: Copy and update marketplace scripts

**Files:**
- Copy: `repos/qute-marketplace/scripts/build.py` → `scripts/build-marketplace.py`
- Copy: `repos/qute-marketplace/scripts/fetch.py` → `scripts/fetch-external.py`
- Copy: `repos/qute-marketplace/scripts/update.py` → `scripts/update-externals.py`
- Copy: `repos/qute-marketplace/scripts/create.py` → `scripts/create-plugin.py`
- Modify: All scripts to use new paths

**Step 1: Copy scripts with new names**

```bash
cp repos/qute-marketplace/scripts/build.py scripts/build-marketplace.py
cp repos/qute-marketplace/scripts/fetch.py scripts/fetch-external.py
cp repos/qute-marketplace/scripts/update.py scripts/update-externals.py
cp repos/qute-marketplace/scripts/create.py scripts/create-plugin.py
```

**Step 2: Update build-marketplace.py paths**

In `scripts/build-marketplace.py`, update:

```python
# Old:
MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
PLUGINS_DIR = MARKETPLACE_ROOT / "plugins"
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"
MARKETPLACE_JSON = MARKETPLACE_ROOT / ".claude-plugin" / "marketplace.json"

# New (same logic, but now relative to qute-code-kit root):
MARKETPLACE_ROOT = Path(__file__).parent.parent.resolve()
PLUGINS_DIR = MARKETPLACE_ROOT / "plugins"
EXTERNAL_DIR = MARKETPLACE_ROOT / "external"
MARKETPLACE_JSON = MARKETPLACE_ROOT / ".claude-plugin" / "marketplace.json"
```

The paths are actually the same since we moved plugins/ and external/ to root. Just verify MARKETPLACE_ROOT resolves to qute-code-kit/.

**Step 3: Update fetch-external.py paths**

In `scripts/fetch-external.py`, find the EXTERNAL_DIR and update if needed:

```python
EXTERNAL_DIR = Path(__file__).parent.parent / "external"
```

**Step 4: Update update-externals.py paths**

```python
EXTERNAL_DIR = Path(__file__).parent.parent / "external"
```

**Step 5: Update create-plugin.py paths**

```python
PLUGINS_DIR = Path(__file__).parent.parent / "plugins"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "plugin-template"
```

**Step 6: Test build script**

```bash
python scripts/build-marketplace.py
```
Expected: Builds successfully, creates .claude-plugin/marketplace.json

**Step 7: Commit**

```bash
git add scripts/
git commit -m "feat: add marketplace management scripts"
```

---

## Task 6: Copy plugin template

**Files:**
- Copy: `repos/qute-marketplace/templates/plugin-template/` → `templates/plugin-template/`

**Step 1: Copy template**

```bash
cp -r repos/qute-marketplace/templates/plugin-template templates/
```

**Step 2: Verify**

```bash
ls templates/plugin-template/
```
Expected: Template files exist

**Step 3: Commit**

```bash
git add templates/plugin-template/
git commit -m "feat: add plugin template for creating new plugins"
```

---

## Task 7: Create .claude-plugin directory and rebuild

**Files:**
- Create: `.claude-plugin/` (directory)
- Generate: `.claude-plugin/marketplace.json`

**Step 1: Run build script**

```bash
python scripts/build-marketplace.py
```

**Step 2: Verify marketplace.json created**

```bash
cat .claude-plugin/marketplace.json | head -20
```
Expected: Valid JSON with plugin entries

**Step 3: Commit**

```bash
git add .claude-plugin/
git commit -m "feat: generate marketplace manifest"
```

---

## Task 8: Create docs scaffold

**Files:**
- Create: `docs/getting-started.md`
- Create: `docs/bundles-explained.md`
- Create: `docs/plugins-explained.md`

**Step 1: Create getting-started.md**

```markdown
# Getting Started

qute-code-kit is a comprehensive Claude Code toolkit with:

- **Bundles**: Deploy skills, agents, rules, and MCP configs to projects
- **Plugins**: Runtime hooks and commands installed globally
- **Documentation**: Guides and tutorials for workflows

## Quick Start

### Install as a plugin (global)

```bash
claude plugin install github:tomlupo/qute-code-kit
```

### Deploy to a project (bundle)

```bash
./setup-project.sh ~/myproject --bundle minimal
```

### Available bundles

- `minimal` - Core skills and rules
- `quant` - Data science and ML workflows
- `webdev` - Frontend development

## Next Steps

- [Understanding Bundles](bundles-explained.md)
- [Understanding Plugins](plugins-explained.md)
```

**Step 2: Create bundles-explained.md**

```markdown
# Understanding Bundles

Bundles are collections of Claude Code components deployed to projects.

## What bundles include

- **Skills**: Domain knowledge and workflows
- **Agents**: Specialized subagents for delegation
- **Rules**: Always-loaded guidelines
- **MCP configs**: External service integrations
- **Settings**: Project-specific configurations

## Using bundles

```bash
# Deploy a bundle to a new project
./setup-project.sh ~/myproject --bundle quant

# Update an existing project
./setup-project.sh ~/myproject --bundle quant --update

# Preview changes without applying
./setup-project.sh ~/myproject --bundle quant --diff
```

## Creating custom bundles

See `claude/bundles/` for bundle definitions.
```

**Step 3: Create plugins-explained.md**

```markdown
# Understanding Plugins

Plugins provide runtime hooks and commands that work across all projects.

## What plugins include

- **Hooks**: Lifecycle events (session start, tool use, etc.)
- **Commands**: Slash commands like `/plugin:command`
- **Skills**: Domain knowledge loaded on demand
- **Rules**: Always-active guidelines

## Installing plugins

```bash
# Install the full marketplace
claude plugin install github:tomlupo/qute-code-kit

# Individual plugins are available via the marketplace
```

## Available plugins

| Plugin | Description |
|--------|-------------|
| doc-enforcer | Reminds when code changes need doc updates |
| forced-eval | Forces skill/tool evaluation before implementation |
| strategic-compact | Suggests /compact at token thresholds |
| notifications | Push notifications via ntfy.sh |
| session-persistence | Save/restore session state |

## Creating plugins

```bash
python scripts/create-plugin.py my-plugin
```
```

**Step 4: Commit**

```bash
git add docs/
git commit -m "docs: add initial documentation scaffold"
```

---

## Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add plugins section to CLAUDE.md**

Add after the "Component types" section:

```markdown
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
python scripts/fetch-external.py url   # Clone external plugin
python scripts/update-externals.py     # Update all externals
```
```

**Step 2: Update directory structure references**

Update any references to `setup-project.sh` location if needed.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add plugins section to CLAUDE.md"
```

---

## Task 10: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Update README with new structure**

Add sections for:
- Plugins (listing available plugins)
- Docs (linking to guides)
- Updated installation instructions

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with plugins and docs sections"
```

---

## Task 11: Clean up old marketplace directory

**Files:**
- Delete: `repos/qute-marketplace/` (after verification)

**Step 1: Verify nothing needed from old location**

```bash
ls repos/qute-marketplace/
```
Check: plugins/, external/, scripts/, templates/ should all be moved

**Step 2: Remove old directory**

```bash
rm -rf repos/qute-marketplace
```

**Step 3: Update .gitignore if repos/ is now empty**

If no other repos remain, can remove the `repos/` entry or leave it for future use.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old qute-marketplace directory (merged into main repo)"
```

---

## Task 12: Test both systems

**Step 1: Test plugin install (local)**

```bash
claude plugin install /home/twilc/projects/qute-code-kit
```
Expected: Plugin installs successfully

**Step 2: Test bundle deployment**

```bash
./setup-project.sh /tmp/test-project --bundle minimal
ls /tmp/test-project/.claude/
```
Expected: Skills, rules, settings deployed

**Step 3: Clean up test**

```bash
rm -rf /tmp/test-project
```

---

## Summary

After completion:
- `plugins/` contains all marketplace plugins
- `external/` contains cloned external plugins (gitignored)
- `scripts/` contains all tooling (setup + marketplace management)
- `docs/` contains guides and tutorials
- Both `./setup-project.sh` (bundles) and `claude plugin install` (plugins) work
- Single repository to maintain
