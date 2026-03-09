# /notify:config

View or update notification configuration.

## Usage

```
/notify:config [--set <key>=<value>] [--enable <event>] [--disable <event>]
```

## Arguments

- `--set` - Set a configuration value
- `--enable` - Enable notifications for an event
- `--disable` - Disable notifications for an event

## Behavior

### View Configuration (no args)

```
/notify:config

# Output:
📱 Notification Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
- Min duration: 30s
- Commands: npm, python, pytest, make, cargo
```

### Set Configuration

```
/notify:config --set topic=my-custom-topic
/notify:config --set priority=high
/notify:config --set server=https://my-ntfy.example.com
```

### Enable/Disable Events

```
/notify:config --enable commit
/notify:config --disable build_success
```

## Configuration Options

| Key | Description | Default |
|-----|-------------|---------|
| `server` | ntfy server URL | https://ntfy.sh |
| `topic` | Notification topic | claude-notifications |
| `priority` | Default priority | default |
| `tags` | Default tags | robot |

## Event Types

| Event | Description |
|-------|-------------|
| `task_complete` | Long-running task finishes |
| `build_success` | Build completes successfully |
| `build_failure` | Build fails |
| `test_complete` | Tests finish running |
| `commit` | Git commit created |
| `error` | Error occurs |
| `session_end` | Claude session ends |

## Filters

- `min_duration_seconds` - Only notify for commands taking longer than this
- `commands` - List of commands to monitor
