# Context Management & Performance

Universal patterns for managing token budget and model performance in long conversations.

## Core Principles

1. **Search before read** - Find what you need, don't read everything
2. **Progressive disclosure** - Overview -> Sample -> Targeted deep-dive
3. **Summarize as you go** - Extract key points, discard verbose content
4. **Save large outputs to files** - Keep conversation context lean
5. **Proactive awareness** - Monitor usage, warn before limits

## Smart Reading Strategy

### For Any Large Content

```
Step 1: List/Search -> Identify what exists
Step 2: Quick scan -> Read headers/summaries only
Step 3: Relevance ranking -> Prioritize what matters
Step 4: Targeted reading -> Deep dive only on relevant sections
Step 5: Synthesize -> Create concise summary, reference files for details
```

### Progressive Disclosure Pattern

| Phase | Context Cost | Action |
|-------|--------------|--------|
| Discovery | Low | List files, search keywords |
| Sampling | Medium | Read first N lines, headers only |
| Targeted | Medium-High | Read specific sections of interest |
| Full | High | Only if absolutely necessary |

## File-Based Output Strategy

When outputs would be large (>100 lines, >1000 rows):

```markdown
GOOD: Save to file, show summary
"Saved 1,500 results to output/analysis.csv
Summary: Top 10 items by revenue..."

BAD: Dump everything into conversation
[1,500 rows of data filling context...]
```

## Context Checkpoints

Periodically assess context usage:

```markdown
**Context Check**: ~60% used
- Explored: 15 files
- Key findings: documented
- Remaining work: 3 tasks

**Action**: Continuing normally
```

```markdown
**Context Check**: ~85% used

**Saving state**:
- Analysis summary -> saved to scratch/analysis_summary.md

**Options**:
A) Use /clear or /compact to continue
B) Focus on specific remaining question
C) Wrap up with executive summary
```

## Proactive Warnings

Before large operations, warn:

```markdown
"This query will return ~50,000 rows.

**Context Management Plan**:
- Execute query
- Save full results to CSV
- Show summary statistics in chat
- Display top 20 rows as preview

This keeps our conversation efficient. Proceed?"
```

## Model Selection Strategy

**Haiku 4.5** (90% of Sonnet capability, 3x cost savings):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet 4.5** (Best coding model):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus 4.5** (Deepest reasoning):
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks

## Context Window Awareness

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Plan Mode

For complex tasks requiring deep reasoning:
1. Enable **Plan Mode** for structured approach
2. "Rev the engine" with multiple critique rounds
3. Use split role sub-agents for diverse analysis

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix

## Remember

Context is a precious resource. Be surgical: search to find, sample to assess, read only what matters. Save verbose outputs to files and keep the conversation focused on insights and decisions, not raw data.
