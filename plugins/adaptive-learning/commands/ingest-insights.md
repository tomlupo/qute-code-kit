# /adaptive-learning:ingest-insights

Parse the insights report and convert high-value patterns into persistent instinct files.

## Arguments

- `$ARGUMENTS` — Optional flags:
  - `--dry-run` — Show what instincts would be created without writing files

## Behavior

1. **Read the insights report** at `~/.claude/usage-data/report.html`
   - If the file does not exist, tell the user to run `/insights` first and stop

2. **Extract patterns** from the HTML. Focus on these sections:

   | Section | CSS class | Instinct value |
   |---------|-----------|----------------|
   | Friction patterns | `.friction-category` | High — title, description, examples |
   | CLAUDE.md suggestions | `.claude-md-item` | High — the rule text and rationale |
   | Key insight | `.key-insight` | Medium — overall usage pattern summary |
   | New usage patterns | `.pattern-card` | Medium — title, summary, detail |

   Skip feature suggestions (`.feature-card`) — those are user-facing, not Claude-facing.

3. **Check for duplicates** — For each extracted item, scan `~/.claude/adaptive-learning/instincts/personal/` for existing instincts with a matching `id` or semantically similar `trigger`. Skip duplicates.

4. **Create instinct files** at `~/.claude/adaptive-learning/instincts/personal/<id>.md` using this format:

   ```markdown
   ---
   id: <kebab-case-id>
   trigger: "<when this pattern applies>"
   confidence: <see table below>
   domain: workflow
   source: insights
   created: <ISO timestamp>
   last_confirmed: <ISO timestamp>
   confirmations: 0
   contradictions: 0
   ---

   # <Title>

   ## Pattern
   <Description from the insights report — what was observed>

   ## When to Apply
   <Specific trigger conditions derived from the pattern>

   ## Source
   Extracted from insights report on <date>. Original section: <section name>.
   ```

   **Confidence levels by section:**
   - Friction patterns: `0.6` (strong signal — derived from actual failure analysis)
   - CLAUDE.md suggestions: `0.5` (concrete rules with rationale)
   - Usage patterns: `0.4` (behavioral observations, less prescriptive)
   - Key insight: `0.4` (broad context)

5. **If `--dry-run`**: Print what would be created without writing any files. Show each instinct with its id, trigger, confidence, and source section.

6. **Report summary**:

## Example

```
/adaptive-learning:ingest-insights --dry-run

Reading ~/.claude/usage-data/report.html...

Extracted 7 patterns from insights report:

Friction patterns (3):
  [DRY RUN] always-update-docs (workflow, 0.60)
    trigger: "implementing code changes from a plan"
  [DRY RUN] verify-all-plan-steps (workflow, 0.60)
    trigger: "executing a structured plan with multiple steps"
  [DRY RUN] secondary-artifacts (workflow, 0.60)
    trigger: "completing primary implementation task"

CLAUDE.md suggestions (2):
  [DRY RUN] docs-alongside-code (workflow, 0.50)
    trigger: "code changes that affect documented behavior"
  [DRY RUN] run-tests-after-changes (workflow, 0.50)
    trigger: "modifying source code"

Usage patterns (2):
  ~ plan-checklist-enforcement — similar instinct already exists (verify-all-plan-steps)
  [DRY RUN] incremental-verification (workflow, 0.40)
    trigger: "multi-step implementation tasks"

Would create 5 instincts, skip 1 duplicate. Run without --dry-run to write files.
```

```
/adaptive-learning:ingest-insights

Reading ~/.claude/usage-data/report.html...

Created 5 instincts from insights report:

Friction patterns:
  + always-update-docs (workflow, 0.60) — "implementing code changes from a plan"
  + verify-all-plan-steps (workflow, 0.60) — "executing a structured plan with multiple steps"
  + secondary-artifacts (workflow, 0.60) — "completing primary implementation task"

CLAUDE.md suggestions:
  + docs-alongside-code (workflow, 0.50) — "code changes that affect documented behavior"
  + run-tests-after-changes (workflow, 0.50) — "modifying source code"

Usage patterns:
  ~ plan-checklist-enforcement — skipped (duplicate of verify-all-plan-steps)
  + incremental-verification (workflow, 0.40) — "multi-step implementation tasks"

5 created, 1 skipped. Run /adaptive-learning:status to verify.
```
