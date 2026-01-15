# /llm-external-review:code

> **This command invokes EXTERNAL AI (Codex/Gemini) for code review. Claude must NOT do this review itself.**

Get a code review from an EXTERNAL AI model (not Claude).

## Usage

```
/llm-external-review:code <file|selection> [--model <model-name>] [--focus <aspect>]
```

## Arguments

- `<file|selection>` - File path or code selection to review
- `--model` - (Optional) Model to use: codex, gemini, gpt4 (default: from config)
- `--focus` - (Optional) Focus area: bugs, performance, style, security, all

## Behavior

1. **Read the code**
   - If file path: read entire file
   - If selection: use provided code block

2. **Prepare review prompt**
   - Include code context
   - Specify focus area
   - Request structured feedback

3. **Call external model**
   - Use configured API endpoint
   - Pass code and review prompt
   - Receive structured review

4. **Format and display review**:
   ```
   🤖 AI Review (model: codex)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━

   ## Summary
   Overall assessment of the code.

   ## Issues Found

   ### 🔴 Critical
   - Line 45: Potential SQL injection vulnerability

   ### 🟡 Warning
   - Line 23: Unused variable 'temp'
   - Line 67: Consider extracting to function

   ### 🔵 Suggestion
   - Line 12: Could use list comprehension

   ## Positive Aspects
   - Good error handling
   - Clear naming conventions

   ## Recommendations
   1. Fix SQL injection on line 45
   2. Add input validation
   3. Consider caching for performance
   ```

## Example

```
/llm-external-review:code src/api/handler.py --focus security

# Output:
🤖 AI Review (model: codex)
━━━━━━━━━━━━━━━━━━━━━━━━━━

## Summary
The handler has good structure but needs security hardening.

## Issues Found

### 🔴 Critical
- Line 45: User input passed directly to SQL query
- Line 78: Missing authentication check

### 🟡 Warning
- Line 23: Sensitive data logged to console

## Recommendations
1. Use parameterized queries
2. Add @auth_required decorator
3. Remove debug logging
```

## Configuration

Models are configured in `config/models.json`. Set your API keys as environment variables:
- `OPENAI_API_KEY` for Codex/GPT-4
- `GOOGLE_API_KEY` for Gemini
