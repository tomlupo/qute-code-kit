# /llm-external-review:compare

> **This command invokes EXTERNAL AI models (Codex, Gemini) for reviews. Claude must NOT do this review itself.**

Get code reviews from multiple EXTERNAL AI models and compare their feedback.

## Usage

```
/llm-external-review:compare <file> [--models <model1,model2,...>]
```

## Arguments

- `<file>` - File path to review
- `--models` - (Optional) Comma-separated list of models (default: all enabled)

## Behavior

1. **Read the code** from specified file

2. **Send to multiple models** in parallel:
   - Codex
   - Gemini
   - GPT-4
   - (other configured models)

3. **Collect responses** and compare

4. **Display comparison matrix**:
   ```
   🤖 Multi-Model Review Comparison
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   File: src/api/handler.py

   ## Issue Comparison

   | Issue | Codex | Gemini | GPT-4 |
   |-------|-------|--------|-------|
   | SQL injection (L45) | 🔴 | 🔴 | 🔴 |
   | Missing auth (L78) | 🔴 | 🟡 | 🔴 |
   | Unused var (L23) | 🟡 | - | 🟡 |
   | Type hints missing | 🔵 | 🔵 | - |

   ## Consensus Issues (all models agree)
   - 🔴 SQL injection vulnerability on line 45

   ## Contested Issues (models disagree)
   - Missing auth check: Codex/GPT-4 say critical, Gemini says warning

   ## Unique Findings
   - **Codex only**: Suggested async refactor
   - **Gemini only**: Noted memory leak potential
   - **GPT-4 only**: Recommended design pattern

   ## Summary Scores
   | Model | Critical | Warnings | Suggestions |
   |-------|----------|----------|-------------|
   | Codex | 2 | 3 | 5 |
   | Gemini | 1 | 4 | 3 |
   | GPT-4 | 2 | 2 | 4 |
   ```

## Example

```
/llm-external-review:compare src/ml/model.py --models codex,gemini

# Output:
🤖 Multi-Model Review Comparison
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: src/ml/model.py

## Consensus Issues
- 🔴 Memory leak in training loop (both models)
- 🟡 Missing gradient clipping (both models)

## Disagreements
- Codex: Use torch.compile() for speed
- Gemini: Keep eager mode for debugging

## Recommendation
Fix consensus issues first, then consider model-specific suggestions.
```

## Use Cases

- **Critical code**: Get multiple perspectives before deployment
- **Learning**: See how different models analyze the same code
- **Comprehensive review**: Catch issues that one model might miss
