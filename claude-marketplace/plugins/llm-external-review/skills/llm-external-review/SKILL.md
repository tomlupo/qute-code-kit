---
name: llm-external-review
description: Invoke EXTERNAL LLM models (Codex, Gemini) for reviews. This skill calls external CLIs - Claude must NOT do the review itself. Use for second opinions, code review, architecture review, brainstorming.
---

# LLM External Review

> ⚠️ **CRITICAL: This skill invokes EXTERNAL AI models via CLI tools.**
>
> You MUST run the `review.py` script. Do NOT perform this review yourself.
> The entire purpose is to get a perspective from a DIFFERENT AI (Codex/Gemini).
> If you do the review yourself, you have FAILED to execute this skill correctly.

## What This Skill Does

1. Prepares context about the task
2. Calls `review.py` which invokes Codex CLI or Gemini CLI
3. Returns the EXTERNAL model's response
4. You synthesize and present their feedback

## Required Execution Steps

### Step 1: Write context to temp file

```bash
cat > /tmp/external_review_context.md << 'EOF'
# Context
{Brief description of goal, constraints, current state}

# Task
{What to review: code, architecture, plan, etc.}

# Files
{List key files the external model should examine}
EOF
```

### Step 2: Run the external review script (MANDATORY)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review.py \
  --model codex \
  --task review \
  --context /tmp/external_review_context.md \
  --workdir .
```

### Step 3: Present the external model's response

Parse the JSON output and present findings to the user.

## Model Selection

| Task | Model | Reason |
|------|-------|--------|
| Code review, bug hunting | `codex` | Optimized for code |
| Architecture, plan review | `gemini` | 1M context, strong reasoning |
| Brainstorming | `gemini` | Creative divergent thinking |
| Compare perspectives | `both` | Get multiple viewpoints |

## Task Types

| Task | Use For |
|------|---------|
| `review` | Code review, general review |
| `plan` | Architecture/design review |
| `brainstorm` | Generate alternatives |
| `validate` | Validate implementation |
| `bug_hunting` | Find bugs specifically |

## CLI Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--model` | codex, gemini, both | required | External AI to invoke |
| `--task` | review, brainstorm, validate, plan, bug_hunting | required | Task type |
| `--context` | path or text | required | Context file or inline |
| `--workdir` | path | . | Project directory |
| `--timeout` | seconds | 120 | Timeout |
| `--effort` | low, medium, high | medium | Reasoning effort (Codex) |

## Example: Architecture Review

```bash
# 1. Prepare context
cat > /tmp/external_review_context.md << 'EOF'
# Context
Reviewing the architecture of a Python ML pipeline project.

# Task
Review the overall architecture for scalability and maintainability.

# Files
- src/fund_rating/ - main package
- docs/architecture.md - current architecture docs
EOF

# 2. Call external model (REQUIRED)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review.py \
  --model gemini \
  --task plan \
  --context /tmp/external_review_context.md \
  --workdir .
```

## Response Format

The script returns JSON:
```json
{
  "model": "codex",
  "task_type": "review",
  "status": "success",
  "response": {
    "summary": "One-line finding",
    "key_points": ["..."],
    "concerns": ["..."],
    "suggestions": ["..."]
  }
}
```

## Error Handling

- **CLI not found**: User needs to install:
  - Codex: `npm i -g @openai/codex`
  - Gemini: https://github.com/google-gemini/gemini-cli
- **Auth error**: Run `codex login` or `gemini /auth`
- **Timeout**: Increase with `--timeout 300`

## Remember

> ⚠️ You are Claude. This skill exists to get opinions from OTHER AI models.
>
> **CORRECT**: Run `review.py` → Get Codex/Gemini response → Present to user
>
> **WRONG**: Read the codebase yourself and provide your own review
>
> If Codex/Gemini CLIs are not installed, tell the user how to install them.
> Do NOT fall back to doing the review yourself.
