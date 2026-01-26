# Notifications Plugin

Push notifications via [ntfy.sh](https://ntfy.sh/) for Claude events.

## Features

- **Push notifications** to phone/desktop via ntfy
- **Event-based triggers** - builds, tests, errors
- **Configurable filters** - minimum duration, specific commands
- **Manual notifications** - send custom messages

## Setup

1. **Install ntfy app** on your phone or desktop:
   - iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)
   - Android: [Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - Desktop: [ntfy.sh web](https://ntfy.sh/)

2. **Subscribe to your topic**:
   - Default: `claude-notifications`
   - Or set custom topic in config

3. **Test it**:
   ```
   /notify:test
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/notify:send "<msg>"` | Send a notification |
| `/notify:config` | View/edit configuration |
| `/notify:test` | Send test notification |

## Quick Start

```bash
### Send a notification
/notify:send "Deployment complete!" --priority high

### View config
/notify:config

### Change topic
/notify:config --set topic=my-custom-topic

### Test setup
/notify:test
```

## Configuration

Edit `config/ntfy.json`:

```json
{
  "server": "https://ntfy.sh",
  "topic": "claude-notifications",
  "priority": "default",
  "tags": ["robot"],
  "events": {
    "task_complete": true,
    "build_success": true,
    "build_failure": true,
    "error": true
  },
  "filters": {
    "min_duration_seconds": 30,
    "commands": ["npm", "python", "pytest"]
  }
}
```

## Event Types

| Event | Description | Default |
|-------|-------------|---------|
| `task_complete` | Long command finishes | ✅ |
| `build_success` | Build succeeds | ✅ |
| `build_failure` | Build fails | ✅ |
| `test_complete` | Tests finish | ✅ |
| `error` | Error occurs | ✅ |
| `commit` | Git commit | ❌ |
| `session_end` | Session ends | ❌ |

## Priority Levels

| Level | When to Use |
|-------|-------------|
| `min` | Background info |
| `low` | Non-urgent |
| `default` | Normal events |
| `high` | Important |
| `urgent` | Critical alerts |

## Self-Hosted ntfy

To use your own ntfy server:

```
/notify:config --set server=https://ntfy.example.com
```

## Installation

Part of qute-marketplace:

```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
```

## License

MIT
