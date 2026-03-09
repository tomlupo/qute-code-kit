# Claude CLI Cheatsheet

## Work Modes

Pre-inject a behavioral prompt to change how Claude operates for the session.

```bash
# Interactive — tell Claude to read a mode prompt
claude
> Read docs/prompts/mode-dev.md and follow it. Now fix the auth bug.

# Headless — pipe mode prompt + task
claude -p "$(cat docs/prompts/mode-research.md) Analyze momentum factor in Polish funds."

# Shell aliases (add to ~/.bashrc or ~/.zshrc)
alias claude-dev='claude -a "$(cat docs/prompts/mode-dev.md)"'
alias claude-research='claude -a "$(cat docs/prompts/mode-research.md)"'
alias claude-review='claude -a "$(cat docs/prompts/mode-review.md)"'
```

Available modes: `mode-dev`, `mode-research`, `mode-review` in `docs/prompts/`.

## Headless Mode

Run Claude non-interactively for automation, pipelines, and batch jobs.

```bash
# Basic
claude -p "instruction"

# With tool permissions
claude -p "Run tests and summarize failures" --allowedTools "Bash,Read"

# Skip all permission prompts (trusted/sandboxed env only)
claude -p "Fix all lint errors" --dangerously-skip-permissions

# JSON output (pipe to file)
claude -p "Analyze src/" --output-format json > report.json

# Streaming JSON (requires --verbose with -p)
claude -p "instruction" --output-format stream-json --verbose
```

## Key Flags

| Flag | Purpose |
|------|---------|
| `-p "..."` | Headless mode — pass prompt, no interactive session |
| `-a "..."` | Append text to system prompt (good for mode injection) |
| `-c` | Continue last session |
| `--allowedTools "..."` | Grant specific tool permissions (comma-separated) |
| `--dangerously-skip-permissions` | Skip ALL permission prompts |
| `--output-format json` | JSON output |
| `--output-format stream-json` | Streaming JSON (add `--verbose` with `-p`) |
| `--model sonnet` | Use specific model |

## Common Patterns

```bash
# Continue previous session
claude -c

# Batch refactoring
claude -p "Replace all uses of old_func with new_func in src/" \
  --allowedTools "Read,Edit,Grep"

# CI integration
claude -p "Run tests and fix failures" \
  --allowedTools "Bash,Read,Edit" \
  --output-format json > test-results.json

# Quick code review (read-only)
claude -p "$(cat docs/prompts/mode-review.md) Review changes on this branch." \
  --allowedTools "Bash,Read,Grep,Glob"
```
