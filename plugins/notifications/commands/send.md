# /notify:send

Send a push notification via ntfy.

## Usage

```
/notify:send "<message>" [--title <title>] [--priority <level>] [--tags <tags>]
```

## Arguments

- `<message>` - Notification message (in quotes)
- `--title` - (Optional) Notification title (default: "Claude")
- `--priority` - (Optional) Priority: min, low, default, high, urgent
- `--tags` - (Optional) Comma-separated emoji tags

## Behavior

1. **Read configuration** from `config/ntfy.json`

2. **Send notification** via curl/requests:
   ```bash
   curl -d "message" \
     -H "Title: title" \
     -H "Priority: priority" \
     -H "Tags: tags" \
     https://ntfy.sh/topic
   ```

3. **Confirm delivery**:
   ```
   ✅ Notification sent to: claude-notifications

   Title: Claude
   Message: Build completed successfully
   Priority: default
   ```

## Example

```
/notify:send "Deployment to production complete!" --title "Deploy" --priority high --tags rocket,white_check_mark

# Output:
✅ Notification sent to: claude-notifications

Title: Deploy
Message: Deployment to production complete!
Priority: high
Tags: 🚀 ✅
```

## Priority Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| min | Lowest | Background info |
| low | Low | Non-urgent updates |
| default | Normal | Standard notifications |
| high | High | Important events |
| urgent | Highest | Critical alerts |

## Tags (Emoji)

Common tags:
- `robot` 🤖
- `white_check_mark` ✅
- `x` ❌
- `warning` ⚠️
- `rocket` 🚀
- `construction` 🚧
- `bug` 🐛
