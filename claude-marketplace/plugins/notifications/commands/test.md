# /notify:test

Send a test notification to verify configuration.

## Usage

```
/notify:test
```

## Behavior

1. **Read configuration** from `config/ntfy.json`

2. **Send test notification**:
   ```
   Title: Claude Test
   Message: 🧪 Test notification from Claude Code
   Priority: default
   Tags: robot, test_tube
   ```

3. **Display result**:
   ```
   🧪 Sending test notification...

   Server: https://ntfy.sh
   Topic: claude-notifications

   ✅ Test notification sent successfully!

   Check your ntfy app or visit:
   https://ntfy.sh/claude-notifications
   ```

## Example

```
/notify:test

# Output:
🧪 Sending test notification...

Server: https://ntfy.sh
Topic: claude-notifications

✅ Test notification sent successfully!

If you didn't receive it:
1. Check topic name matches your subscription
2. Verify ntfy app is installed and configured
3. Check server URL is correct

Subscribe URL: https://ntfy.sh/claude-notifications
```

## Troubleshooting

If test fails:

1. **Check internet connection**
2. **Verify server URL** - Default is https://ntfy.sh
3. **Check topic name** - Must match subscription
4. **Try curl manually**:
   ```bash
   curl -d "Test" https://ntfy.sh/your-topic
   ```
