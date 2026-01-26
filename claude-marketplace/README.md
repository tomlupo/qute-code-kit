# Qute Marketplace

## Overview

A personal Claude Code plugin marketplace. Register once, add plugins easily.

## Installation

### Install the Marketplace

```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
```

### Install from GitHub

```bash
claude plugin install github:twilc/claude-marketplace
```

## Quick Start

```
┌─────────────────────────────────────────────────────────┐
│  Register marketplace once:                              │
│  claude plugin install ~/projects/qute-ai-tools/claude-marketplace │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  To add a plugin:                                       │
│  1. Drop plugin folder into plugins/                    │
│  2. Run: python scripts/build.py                        │
│  3. Restart Claude → new commands available!            │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
claude-marketplace/
├── .claude-plugin/
│   └── plugin.json            # AUTO-GENERATED: aggregates all plugins
├── hooks/
│   └── merged-hooks.json      # AUTO-GENERATED: merged hooks
├── plugins/                   # All plugins
│   ├── workflow-plugin/       # Session & context management
│   ├── research-workflow/     # Research documentation
│   ├── llm-external-review/   # Multi-model code review
│   └── notifications/         # ntfy.sh push notifications
├── external/                  # Plugins cloned from GitHub
├── scripts/                   # Management scripts
│   ├── build.py               # Rebuild manifest after changes
│   ├── create.py              # Create new plugin from template
│   ├── fetch.py               # Clone plugin from GitHub
│   └── update.py              # Update external plugins
└── templates/
    └── plugin-template/       # Template for new plugins
```

## Scripts

### Build Manifest

Run after adding/removing/modifying plugins:

```bash
python scripts/build.py
```

### Create New Plugin

```bash
python scripts/create.py my-new-plugin
python scripts/build.py
# Restart Claude → /my-new-plugin:* commands available
```

### Fetch Plugin from GitHub

```bash
python scripts/fetch.py github:username/repo-name
python scripts/build.py
# Restart Claude → new commands available
```

### Update External Plugins

```bash
# Update all
python scripts/update.py

# Update specific
python scripts/update.py plugin-name
```

## Included Plugins

### workflow-plugin

Session, task, and context management for Claude Code. Prevents context degradation through auto-handoffs and maintains a structured ledger system.

**Commands:**
| Command | Description |
|---------|-------------|
| `/workflow:init` | Initialize workflow infrastructure in a project |
| `/workflow:session [name]` | Start new or bind to existing session |
| `/workflow:session-update [notes]` | Add progress notes to active session |
| `/workflow:session-finish` | End session with outcome tracking |
| `/workflow:sessions` | View status overview (ledger, tasks, sessions) |

**Skills:** workflow-management, context-management, worktrees

---

### research-workflow

Comprehensive research workflow for ML/data science projects. Track hypotheses, experiments, findings, and academic papers.

**Commands:**
| Command | Description |
|---------|-------------|
| `/research:start <topic>` | Initialize research structure for a topic |
| `/research:hypothesis "<statement>"` | Document a testable hypothesis |
| `/research:experiment <name>` | Log an experiment with setup & results |
| `/research:finding "<title>"` | Document a validated finding |
| `/research:paper <url\|file>` | Read and extract paper insights |
| `/research:index` | Display research index overview |

**Skills:** research

**Output:** Creates `docs/research/` with hypotheses, experiments, findings, and papers.

---

### llm-external-review

Multi-model code review plugin. Get second opinions from external AI models (GPT-5, Gemini, etc.).

**Commands:**
| Command | Description |
|---------|-------------|
| `/llm-external-review:code <file>` | Review code with external AI model |
| `/llm-external-review:compare <file>` | Get reviews from multiple models, compare |
| `/llm-external-review:architecture` | Review project architecture |
| `/llm-external-review:security <file>` | Security-focused code analysis (OWASP) |

**Skills:** llm-external-review

**Configuration:** Set API keys in environment variables (`OPENAI_API_KEY`, `GOOGLE_API_KEY`).

---

### notifications

Push notifications via [ntfy.sh](https://ntfy.sh/) for Claude events. Get notified on your phone/desktop when long tasks complete, builds finish, or errors occur.

**Commands:**
| Command | Description |
|---------|-------------|
| `/notify:send "<message>"` | Send a push notification |
| `/notify:config` | View/edit notification settings |
| `/notify:test` | Send test notification to verify setup |

**Configuration:** Edit `plugins/notifications/config/ntfy.json` to set your topic and enable/disable events.

**Setup:**
1. Install ntfy app on phone/desktop
2. Subscribe to your topic (default: `claude-notifications`)
3. Run `/notify:test` to verify

---

## Adding Your Own Plugin

1. Create plugin structure:
   ```
   plugins/my-plugin/
   ├── plugin.json
   ├── commands/
   │   └── my-command.md
   ├── skills/
   ├── hooks/
   └── scripts/
   ```

2. Define `plugin.json`:
   ```json
   {
     "name": "my-plugin",
     "version": "1.0.0",
     "description": "My awesome plugin",
     "commands": ["commands/my-command.md"],
     "skills": [],
     "hooks": ""
   }
   ```

3. Run `python scripts/build.py`

4. Restart Claude

## Sharing via GitHub

Push to GitHub and anyone can install:

```bash
# Publish
git init && git add . && git commit -m "Initial" && git push

# Install (others)
claude plugin install github:twilc/claude-marketplace
```

## License

MIT
