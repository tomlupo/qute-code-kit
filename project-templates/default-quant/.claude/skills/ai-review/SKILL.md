---
name: ai-reviewer
description: Invoke external AI models (Codex, Gemini) for plan review, brainstorming, and validation. Use when Claude should get a second opinion, validate complex work, brainstorm alternatives, or review code/architecture before implementation. Triggers include explicit requests like "get codex to review", "ask gemini", "second opinion", "brainstorm with external model", or when Claude suggests external review for high-stakes decisions.
---

# AI Reviewer

Invoke Codex CLI or Gemini CLI to get external AI perspectives on plans, code, and ideas.

## When to Use

- **Code review**: Before committing complex changes
- **Plan validation**: Before implementing architecture decisions
- **Brainstorming**: Generate alternative approaches
- **Second opinion**: When uncertainty is high or stakes warrant it

## Model Selection

| Task | Model | Reason |
|------|-------|--------|
| Code review, bug hunting | Codex | GPT-5-Codex tuned for code |
| Architecture, plan review | Gemini | 1M context, strong reasoning |
| Brainstorming, alternatives | Gemini | Creative divergent thinking |
| Validation (compare views) | Both | Get multiple perspectives |

User can override with explicit model request.

## Invocation

### Explicit triggers (invoke immediately)
- "Get codex/gemini to review this"
- "Ask gemini for alternatives"
- "Get a second opinion"
- "Brainstorm with external model"

### Claude suggests (require user approval)
- Before implementing complex plans
- When uncertainty is high
- After completing draft needing validation

## Usage

### 1. Prepare context

Write task context to temp file (Windows/Unix):
```bash
# Unix/Mac
cat > /tmp/ai_review_context.md << 'EOF'
# Context
{Brief description of goal, constraints, current state}

# Question
{Specific ask - what to review/validate/brainstorm}

# Relevant files
{List key files the external model should examine}
EOF

# Windows (PowerShell)
@"
# Context
{Brief description of goal, constraints, current state}

# Question
{Specific ask - what to review/validate/brainstorm}

# Relevant files
{List key files the external model should examine}
"@ | Out-File -FilePath "$env:TEMP\ai_review_context.md" -Encoding UTF8
```

### 2. Run review script (cross-platform)

```bash
# Basic usage
uv run python .claude/skills/ai-review/review.py \
  --model codex|gemini|both \
  --task review|brainstorm|validate|plan \
  --context /tmp/ai_review_context.md \
  --workdir .

# With reasoning effort control (Codex only)
uv run python .claude/skills/ai-review/review.py \
  --model codex \
  --task review \
  --context context.md \
  --effort high  # low|medium|high (default: medium)

# Suppress thinking tokens (Codex only)
uv run python .claude/skills/ai-review/review.py \
  --model codex \
  --task review \
  --context context.md \
  --suppress-thinking

# Resume last Codex session
uv run python .claude/skills/ai-review/review.py \
  --resume \
  --context "follow up question here"
```

### CLI Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--model` | codex, gemini, both | required | Which AI model to use |
| `--task` | review, brainstorm, validate, plan, bug_hunting | required | Type of review task |
| `--context` | path or text | required | Context file or inline text |
| `--workdir` | path | . | Project working directory |
| `--timeout` | seconds | 120 | Timeout in seconds |
| `--effort` | low, medium, high | medium | Reasoning effort level (Codex only) |
| `--suppress-thinking` | flag | false | Hide thinking tokens from stderr |
| `--resume` | flag | false | Resume last Codex session |

### 3. Parse response

Script returns JSON:
```json
{
  "model": "codex",
  "task_type": "review",
  "status": "success",
  "response": {
    "summary": "One-line finding",
    "key_points": ["..."],
    "concerns": ["..."],
    "suggestions": ["..."],
    "alternatives": ["..."]
  },
  "metadata": {
    "duration_ms": 5000,
    "effort": "medium",
    "resumed": false,
    "tokens_used": 1234  // Gemini only
  }
}
```

### Session Resume (Codex only)

After a successful Codex call, session info is saved to `~/.claude/skills/ai-review/.last_session.json`.

To resume and continue the conversation:
```bash
# Resume with a follow-up question
uv run python .claude/skills/ai-review/review.py \
  --resume \
  --context "What about error handling in that approach?"

# Resume inherits: model, task, effort, workdir from last session
```

This enables multi-turn conversations with Codex without re-specifying all parameters.

### 4. Synthesize for user

After receiving response:
- Note agreements/disagreements with Claude's approach
- Highlight actionable suggestions
- Adjust approach if warranted
- Present synthesis to user

## Direct CLI Usage (Advanced)

If you need to invoke models directly without the Python orchestrator:

**Codex:**
```bash
codex exec --full-auto --json --cd /project/path "PROMPT"
```

**Gemini:**
```bash
cd /project/path && gemini -p "PROMPT" --output-format json
```

**Note**: The `invoke_codex.sh` and `invoke_gemini.sh` wrapper scripts are Unix-only and not needed. Use `review.py` directly for cross-platform compatibility.

See `references/prompts.md` for prompt templates.

## Error Handling

- **CLI not found**: Inform user which CLI needs installation
  - Codex: `npm i -g @openai/codex` (requires Node.js)
  - Gemini: Install from https://github.com/google-gemini/gemini-cli
  - On Windows: Ensure CLI tools are in your PATH
- **Auth error**: Suggest user run `codex login` or `gemini /auth`
- **Timeout**: Default 120s, configurable via `--timeout`
- **Parse error**: Return raw response in `raw_response` field

## Platform Notes

- **Python script** (`review.py`): Fully cross-platform (Windows/Mac/Linux)
- **Bash scripts** (`invoke_*.sh`): Unix-only, not required (use `review.py` directly)
- **External CLIs**: `codex` and `gemini` must be installed and in PATH
  - Windows users: Use PowerShell or Git Bash for CLI installation
  - Verify with: `codex --version` or `gemini --version`

## Notes

- External models can read project files (Codex uses AGENTS.md, Gemini uses @./path)
- Pass minimal context; let them explore codebase
- For sensitive projects, use `--sandbox read-only` with Codex
