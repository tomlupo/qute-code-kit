# LLM External Review Plugin

Get code reviews from external AI models for second opinions and comprehensive analysis.

## Features

- **Multi-model reviews** - Compare feedback from different AI models
- **Security scanning** - OWASP-based vulnerability detection
- **Architecture review** - Project structure analysis
- **Focused analysis** - Target specific concerns (bugs, performance, security)

## Commands

| Command | Description |
|---------|-------------|
| `/llm-external-review:code <file>` | Review code with external AI model |
| `/llm-external-review:compare <file>` | Get reviews from multiple models |
| `/llm-external-review:architecture` | Review project architecture |
| `/llm-external-review:security <file>` | Security-focused code analysis |

## Quick Start

1. **Configure API keys**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export GOOGLE_API_KEY="..."
   ```

2. **Review a file**:
   ```
   /llm-external-review:code src/api/handler.py --focus security
   ```

3. **Compare models**:
   ```
   /llm-external-review:compare src/critical/payment.py
   ```

## Configuration

Edit `config/models.json` to enable/disable models:

```json
{
  "models": [
    {
      "name": "codex",
      "provider": "openai",
      "enabled": true
    },
    {
      "name": "gemini",
      "provider": "google",
      "enabled": false
    }
  ],
  "default": "codex"
}
```

## Output Example

```
🤖 AI Review (model: codex)
━━━━━━━━━━━━━━━━━━━━━━━━━━

## Summary
The handler has good structure but needs security hardening.

## Issues Found

### 🔴 Critical
- Line 45: SQL injection vulnerability

### 🟡 Warning
- Line 23: Unused variable

### 🔵 Suggestion
- Line 12: Consider type hints

## Recommendations
1. Use parameterized queries
2. Add input validation
```

## Supported Models

| Model | Provider | API Key Env |
|-------|----------|-------------|
| Codex/GPT-4 | OpenAI | `OPENAI_API_KEY` |
| Gemini Pro | Google | `GOOGLE_API_KEY` |
| Claude | Anthropic | `ANTHROPIC_API_KEY` |

## Installation

Part of qute-marketplace:

```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
```

## License

MIT
