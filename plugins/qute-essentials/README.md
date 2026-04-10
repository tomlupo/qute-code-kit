# qute-essentials

Essential hooks, guards, and skills for Claude Code. Provides prompt injection screening, destructive command blocking, observability tracing, notifications, and utility skills.

## Guard System

Three security layers that run on every tool call, each toggleable via `/guard`:

```
                     ┌─────────────────────────┐
                     │   Discord / Interactive  │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │  Per-project permissions │  which tools the agent CAN use
                     │  (settings.local.json)   │
                     └────────────┬────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
    ┌──────────▼─────────┐ ┌─────▼──────┐ ┌─────────▼────────┐
    │ Destructive Guard  │ │  Lakera    │ │    Langfuse      │
    │ PreToolUse         │ │  PostTool  │ │    PostTool      │
    │ BLOCKS before exec │ │  WARNS on  │ │    TRACES for    │
    │ rm -rf, git reset  │ │  injection │ │    observability  │
    └────────────────────┘ └────────────┘ └──────────────────┘
               │                  │                  │
               └──────────┬──────┴──────────────────┘
                          │
                     ┌────▼────┐
                     │  ntfy   │  alerts to phone
                     │  push   │
                     └─────────┘
```

### Destructive Guard (PreToolUse)

Blocks dangerous commands before they execute. Context-aware: won't block `grep "rm -rf"` or dry-run flags.

| Category | Examples |
|----------|----------|
| Git | `reset --hard`, `push --force`, `clean -f`, `stash clear`, `branch -D` |
| Filesystem | `rm -rf /`, `rm -rf ~/`, `find -delete`, `mkfs`, `dd of=/dev/` |
| Database | `DROP TABLE`, `TRUNCATE`, `DELETE FROM x;` (no WHERE), `dropdb` |
| Docker | `system prune -a`, mass container removal |
| System | `sudo rm -rf`, `chmod -R 777`, `crontab -r`, `pkill -9 -u` |
| Custom | Obsidian vault paths, production quantlab, trading crons |

Logs to `~/.claude/permission-audit/destructive-blocks.jsonl`. Sends ntfy alert on every block.

### Lakera Guard (PostToolUse)

Screens tool outputs for prompt injection via the Lakera Guard API. Targets untrusted content sources:

- WebFetch, WebSearch (always screened)
- MCP tool responses (always screened)
- Bash output from curl/wget/python (selective)
- Read output from inbox/raw/tmp dirs (selective)
- Safe local commands (git, ls, find) are skipped to save API quota

When injection is detected, a warning is injected into the conversation context and an urgent ntfy alert is sent. Requires `LAKERA_GUARD_API_KEY` env var. Free tier: 10k requests/month.

Logs to `~/.claude/permission-audit/guard-detections.jsonl`.

### Langfuse Tracing (PostToolUse)

Traces every tool execution to Langfuse for observability and evaluation. Async hook, no latency impact.

Each trace includes:
- Tool name, input (redacted), output (truncated)
- `session_id` (groups tool calls per conversation)
- `project` (derived from cwd)
- `source` (`dispatcher` or `interactive`, detected via `$TMUX`)
- `hostname` (for multi-machine setups)
- Tags: `project:<name>`, `source:<type>`, `tool:<name>`, `host:<name>`

Failed commands (non-zero exit code) are auto-scored `tool_success: 0`.

Requires `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` env vars. Free tier: 50k traces/month.

## Toggle Guards

```
/guard                  # show status of all guards
/guard lakera off       # disable Lakera screening
/guard destructive off  # disable destructive command blocking
/guard langfuse off     # disable Langfuse tracing
/guard all on           # re-enable everything
```

Config stored in `config/guards.json`. Changes take effect immediately.

## Other Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `check-update.sh` | SessionStart | Daily version check against GitHub |
| `forced_eval.sh` | UserPromptSubmit | Skill evaluation on every prompt |
| `format_python.py` | PostToolUse (Edit/Write) | Auto-format Python with ruff |
| `track_edits.py` | PostToolUse (Edit/Write) | Track file modifications |
| `log_use.py` | PostToolUse (Skill/Agent), SubagentStart | Activity logging |
| `on_task_complete.py` | PostToolUse (Bash) | ntfy notification for long-running commands |
| `on_notification.py` | Notification | ntfy push when Claude is waiting for input |

## Notifications

Push notifications via [ntfy.sh](https://ntfy.sh). Config in `config/ntfy.json`.

Topic auto-generates from `{hostname}-{username}-claude` (e.g., `core-tom-claude`). Subscribe in the ntfy app to receive alerts for:
- Destructive command blocks
- Prompt injection detections
- Long-running command completions
- Permission prompts (agent waiting for input)

## Skills

| Skill | Description |
|-------|-------------|
| `/guard` | Toggle security guards on/off, check status |
| `/commit` | Generate conventional commit messages |
| `/ship` | Bump version, update CHANGELOG, create tag (Python, via commitizen) |
| `/ship-setup` | One-time setup for `/ship` in a project |
| `/worktrees` | Manage git worktrees for parallel development |
| `/handoff` | Prepare session handoff documents |
| `/readme` | Generate or update README files |
| `/wtf` | Quick debugging helper |
| `/gbu` | Good/bad/ugly code review |

## Setup

```bash
# Install via Claude Code plugin system
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace

# Add API keys to ~/.claude/settings.json env block
# LAKERA_GUARD_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
```
