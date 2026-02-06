# /adaptive-learning:analyze

Analyze recent observations to discover patterns and create or update instincts.

## Arguments

- `$ARGUMENTS` — Optional flags:
  - `--since <date>` — Only analyze observations after this date (ISO format, e.g. `2026-02-01`)
  - `--dry-run` — Show what instincts would be created/updated without writing files

## Behavior

1. **Read observations** from `~/.claude/adaptive-learning/observations.jsonl`
   - If `--since` is provided, filter entries by timestamp
   - If the file is large, read the last 500 lines

2. **Analyze for patterns** — Look for:
   - **Repeated sequences**: Tool A always followed by Tool B (e.g., Read → Edit)
   - **Error-then-fix**: A tool fails, then a specific correction follows
   - **Consistent preferences**: Always using certain flags, file patterns, or approaches
   - **Project-specific habits**: Patterns that repeat within a project context

3. **Cross-reference existing instincts** in `~/.claude/adaptive-learning/instincts/personal/`
   - If a pattern matches an existing instinct, **boost confidence** by `+0.05`
   - If observations contradict an instinct, **penalize** by `-0.10`
   - Update `last_confirmed`, `confirmations`, and `contradictions` counts in frontmatter

4. **Create new instinct files** for novel patterns:
   - Save to `~/.claude/adaptive-learning/instincts/personal/<id>.md`
   - Use the template format from `templates/instinct.md`
   - Set initial confidence to `0.3`
   - Choose a descriptive `id` (kebab-case)

5. **If `--dry-run`**: Print what would happen without writing files

6. **Summary**: Report instincts created, updated, and confidence changes

## Example

```
/adaptive-learning:analyze --since 2026-02-04

Analyzing 342 observations since 2026-02-04...

Patterns found:
  1. After reading Python files, you consistently run tests with pytest (87% of cases)
  2. You prefer Edit over Write for existing files (93% of cases)
  3. When a Bash command fails, you typically Read the relevant file next

Instincts updated:
  - prefer-edit-over-write: confidence 0.55 → 0.60 (+1 confirmation)

Instincts created:
  - run-pytest-after-edit (python, confidence: 0.30) — "Run pytest after editing Python files"
  - read-after-bash-error (general, confidence: 0.30) — "Read relevant file after Bash failure"
```
