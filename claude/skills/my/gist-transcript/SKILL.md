---
name: gist-transcript
description: |
  Create a GitHub gist from the current Claude Code session transcript.
  Use when the user says "save transcript", "share session", "gist transcript",
  "upload session", or wants to share the current conversation as a gist.
disable-model-invocation: true
---

# Gist Transcript

Create a GitHub gist from the current Claude Code session transcript.

## Usage

Run this bash command to upload the current session to a gist:

```bash
uvx claude-code-transcripts json --gist "$(ls -t ~/.claude/projects/$(pwd | tr '/' '-')/*.jsonl | head -1)"
```

## Requirements

- `gh` CLI must be authenticated (`gh auth login`)
- `uvx` must be available (installed via `uv`)
