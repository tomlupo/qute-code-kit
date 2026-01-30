Create a GitHub gist from the current Claude Code session transcript.

Run this bash command to upload the current session to a gist:

```bash
uvx claude-code-transcripts json --gist "$(ls -t ~/.claude/projects/$(pwd | tr '/' '-')/*.jsonl | head -1)"
```

Note: Requires `gh` CLI to be authenticated (`gh auth login`).
