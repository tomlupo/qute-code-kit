# /adaptive-learning:status

Show the current state of the adaptive learning system.

## Behavior

1. **Check the observations file** at `~/.claude/adaptive-learning/observations.jsonl`
   - Report: line count, file size, date range of entries
   - If no file exists, report "No observations yet"

2. **List instincts** from `~/.claude/adaptive-learning/instincts/`
   - Group by `personal/` and `inherited/`
   - For each instinct, parse the YAML frontmatter and show:

   | ID | Domain | Confidence | Trigger | Confirmations | Contradictions |
   |----|--------|------------|---------|---------------|----------------|

   - Show confidence as a visual bar: `[######....]` (0.6)
   - Sort by confidence descending

3. **Show stats** from `~/.claude/adaptive-learning/stats.json` if it exists
   - Total observations, sessions tracked, instincts created

4. **Show config** — display merged config (defaults + user overrides)

## Arguments

- None

## Example

```
/adaptive-learning:status

Observations: 1,247 entries (2.3 MB) — 2026-02-01 to 2026-02-06
Sessions tracked: 14

Personal Instincts (3):
  [########..] prefer-type-hints (python) — "python function definitions" — 5 confirms, 0 contradicts
  [######....] test-before-commit (git) — "git commit" — 3 confirms, 1 contradicts
  [####......] prefer-pathlib (python) — "file path operations" — 2 confirms, 0 contradicts

Inherited Instincts: none

Config: max_observation_size_mb=10, max_instincts=5, min_confidence=0.3
```
