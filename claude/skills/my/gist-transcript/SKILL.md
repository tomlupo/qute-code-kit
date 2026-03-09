---
name: gist-transcript
description: |
  Create a GitHub gist from the current Claude Code session transcript.
  Use when the user says "save transcript", "share session", "gist transcript",
  "upload session", or wants to share the current conversation as a gist.
disable-model-invocation: true
allowed-tools: Bash
---

# Gist Transcript

Create a GitHub gist from the current Claude Code session transcript.

## Usage

```bash
uvx claude-code-transcripts json --gist "$(ls -t ~/.claude/projects/$(pwd | tr '/' '-')/*.jsonl | head -1)"
```

This uploads the most recent session transcript as a secret GitHub Gist and returns a preview URL.

## What Gets Uploaded

- Full conversation (user messages + assistant responses)
- Tool calls and their outputs
- Timestamps for each message
- Session metadata (project path, model used)

Sensitive content (env vars, secrets in tool output) is included as-is — review the transcript before sharing if the session touched credentials.

## Output

The command prints a single gist URL. The gist contains a formatted JSON transcript viewable in any browser.

## Requirements

- `gh` CLI authenticated (`gh auth login`)
- `uvx` available (via `uv`)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No such file" | No session files found — ensure you're in a project directory |
| gh auth error | Run `gh auth login` to authenticate |
| Empty transcript | Session just started — need at least one exchange |
