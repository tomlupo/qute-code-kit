# /adaptive-learning:import

Import instincts from an exported JSON bundle.

## Arguments

- `$ARGUMENTS` — Path to the JSON bundle file to import

## Behavior

1. **Read the bundle file** — Parse JSON, validate `version` field

2. **For each instinct** in the bundle:
   - Check if an instinct with the same `id` already exists in `inherited/` or `personal/`
   - If it exists: **skip** (report as duplicate) — do not overwrite
   - If new: write as `~/.claude/adaptive-learning/instincts/inherited/<id>.md`
   - Use the template format with YAML frontmatter
   - Set `source: inherited`

3. **Report**: Number imported, number skipped (duplicates)

## Example

```
/adaptive-learning:import ~/.claude/adaptive-learning/exports/instincts-export-2026-02-06.json

Imported 3 instincts, skipped 2 duplicates:
  + prefer-pathlib (0.45) — imported to inherited/
  + run-pytest-after-edit (0.30) — imported to inherited/
  + read-after-bash-error (0.30) — imported to inherited/
  ~ prefer-type-hints — already exists in personal/
  ~ test-before-commit — already exists in personal/
```
