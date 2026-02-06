# /adaptive-learning:export

Export instincts to a portable JSON bundle for sharing or backup.

## Arguments

- `$ARGUMENTS` — Optional: output filename (default: `instincts-export-<date>.json`)

## Behavior

1. **Read all instincts** from `~/.claude/adaptive-learning/instincts/personal/` and `inherited/`
   - Parse frontmatter and body from each `.md` file

2. **Bundle into JSON**:
   ```json
   {
     "version": "1.0",
     "exported": "<ISO timestamp>",
     "instincts": [
       {
         "id": "prefer-type-hints",
         "trigger": "python function definitions",
         "confidence": 0.70,
         "domain": "python",
         "source": "personal",
         "created": "2026-02-06T10:00:00Z",
         "body": "# Prefer Type Hints\n\n## Pattern\n..."
       }
     ]
   }
   ```

3. **Write to** `~/.claude/adaptive-learning/exports/<filename>`

4. **Report**: Number of instincts exported and file path

## Example

```
/adaptive-learning:export

Exported 5 instincts to ~/.claude/adaptive-learning/exports/instincts-export-2026-02-06.json
  - prefer-type-hints (0.70)
  - test-before-commit (0.60)
  - prefer-pathlib (0.45)
  - run-pytest-after-edit (0.30)
  - read-after-bash-error (0.30)
```
