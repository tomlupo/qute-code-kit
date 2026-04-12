---
name: config
description: View or update qute-essentials plugin configuration — currently covers notification settings (ntfy.sh server, topic, priority, event filters) and is the intended home for future qute-essentials plugin-wide settings. Use when the user asks to change notification settings, view current config, enable/disable specific events for notifications, or configure the plugin. Do NOT use for toggling Lakera Guard or Langfuse (use the `guard` skill for those).
argument-hint: "[--set key=value] [--enable event] [--disable event]"
---

# /config

View or update qute-essentials plugin configuration. Currently scoped to
notification settings; intended to grow into the central entry point for all
qute-essentials plugin-wide configuration over time.

**Out of scope**: Lakera Guard and Langfuse toggles — those live in the `guard`
skill. A future refactor may fold guard into this skill for a single `/config`
entry point.

## Usage

```
/config                                   # show current config
/config --set <key>=<value>               # update a config value
/config --enable <event>                  # enable notification for an event
/config --disable <event>                 # disable notification for an event
```

## Behavior

### View configuration (no args)

```
📱 qute-essentials Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Notifications (ntfy.sh)
  Server: https://ntfy.sh
  Topic: claude-notifications
  Priority: default
  Tags: 🤖

## Enabled Events
✅ task_complete
✅ build_success
✅ build_failure
✅ test_complete
✅ error

## Disabled Events
❌ commit
❌ session_end

## Filters
  Min duration: 30s
  Monitored commands: npm, python, pytest, make, cargo
```

### Update a value

```
/config --set topic=my-custom-topic
/config --set priority=high
/config --set server=https://my-ntfy.example.com
```

### Enable/disable events

```
/config --enable commit
/config --disable build_success
```

## Configuration keys

| Key | Description | Default |
|---|---|---|
| `server` | ntfy server URL | `https://ntfy.sh` |
| `topic` | Notification topic | `claude-notifications` |
| `priority` | Default priority | `default` |
| `tags` | Default tags | `robot` |

## Notification events

| Event | Description |
|---|---|
| `task_complete` | Long-running task finishes |
| `build_success` | Build completes successfully |
| `build_failure` | Build fails |
| `test_complete` | Tests finish running |
| `commit` | Git commit created |
| `error` | Error occurs |
| `session_end` | Claude session ends |

## Filters

- `min_duration_seconds` — only notify for commands taking longer than this
- `commands` — list of commands to monitor

## Implementation

Configuration is persisted at `${CLAUDE_PLUGIN_ROOT}/config/ntfy.json`.
Read and write this file directly using `Read` and `Edit`/`Write` tools.
Notifications themselves are sent by the `notify.py` helper script and
triggered by PostToolUse / Notification hooks — they are **not** manually
invoked. This skill only manages the configuration values, not notification
delivery.

## Gotchas

- **ntfy.sh is public** — anyone who knows your topic string can subscribe and read all notifications; use a hard-to-guess topic or a self-hosted server for sensitive projects
- **ntfy.sh free-tier rate limit** is 250 messages/day — for projects with frequent builds, set `min_duration_seconds` high (e.g., 60) or switch to a self-hosted ntfy instance
- **Changing `topic` only affects future notifications** — past notifications remain on the old topic; subscribers to the old topic stop receiving updates immediately
- **The config file does not exist until first run or manual creation** — if `/config` shows an error, the file may not have been created yet; `/config --set topic=my-topic` will create it
- **Guards (lakera, langfuse) are NOT managed here** — use `/guard` for those; `/config` is for notification settings only
