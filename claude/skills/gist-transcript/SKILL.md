---
name: gist-transcript
description: |
  Upload the current Claude Code session transcript as a GitHub Gist.
  Use when the user says "save transcript", "share session", "gist transcript", "upload session".
disable-model-invocation: true
allowed-tools: Bash
---

# Gist Transcript

> **Merged into `gist-report`** — use `/gist-report` for both HTML reports and transcript uploads.
> The transcript command is documented under "Transcript Mode" in that skill.

```bash
uvx claude-code-transcripts json --gist "$(ls -t ~/.claude/projects/$(pwd | tr '/' '-')/*.jsonl | head -1)"
```
