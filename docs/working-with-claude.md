# Working Effectively with Claude

Practical guidance on using qute-code-kit tools for effective AI-assisted development.

## Work Modes

The toolkit supports different work modes via CLI aliases, each optimizing Claude's behavior for specific tasks:

| Mode | Alias | Behavior |
|------|-------|----------|
| Development | `claude-dev` | Code first, explain after. Working solutions, tests, atomic commits. |
| Research | `claude-research` | Read widely before concluding. Document findings. No code until clear. |
| Review | `claude-review` | Read thoroughly. Prioritize by severity. Check security. |

### Setting Up Work Modes

Create context files and shell aliases:

```bash
# Create context directory
mkdir -p ~/.claude/contexts

# Create mode-specific context files
cat > ~/.claude/contexts/dev.md << 'EOF'
# Development Mode
Prioritize working code over explanation. Write tests. Make atomic commits.
When in doubt, ship something working and iterate.
EOF

cat > ~/.claude/contexts/research.md << 'EOF'
# Research Mode
Read widely before concluding. Document sources and findings.
No code until requirements are crystal clear.
EOF

cat > ~/.claude/contexts/review.md << 'EOF'
# Review Mode
Read thoroughly before commenting. Prioritize issues by severity.
Check for security vulnerabilities. Be constructive.
EOF

# Add aliases to your shell config (~/.bashrc or ~/.zshrc)
alias claude-dev='claude --context ~/.claude/contexts/dev.md'
alias claude-research='claude --context ~/.claude/contexts/research.md'
alias claude-review='claude --context ~/.claude/contexts/review.md'
```

### When to Use Each Mode

- **`claude-dev`**: Feature implementation, bug fixes, refactoring
- **`claude-research`**: Architecture decisions, technology evaluation, understanding unfamiliar codebases
- **`claude-review`**: Code review, security audits, PR feedback

## How Everything Works Together

Plugins coordinate across your session lifecycle, creating a seamless development experience.

### Session Start
- `session-persistence` reports unfinished work from previous sessions
- Context loaded, skills available for invocation

### Continuous (Silent)
These plugins run automatically without interrupting your flow:

| Plugin | Purpose |
|--------|---------|
| `doc-enforcer` | Reminds when docs may need updating |
| `strategic-compact` | Suggests `/compact` at token thresholds |
| `skill-use-logger` | Tracks skill invocations for analytics |
| `forced-eval` | Ensures skill evaluation before implementation |

### Active Work
The typical cycle: **brainstorm → plan → work → review → document**

Skills are invoked on-demand. Subagents provide isolation for research and exploration.

## When to Use What

| Task | Recommended Approach |
|------|---------------------|
| New feature, unclear requirements | `superpowers:brainstorming` → planning |
| Bug fix | `superpowers:systematic-debugging` |
| Full development cycle | `/workflows:plan` → `/workflows:work` → `/workflows:review` |
| Quick implementation | Direct coding with `superpowers:test-driven-development` |
| Research/exploration | `Explore` subagent or `paper-reading` skill |
| Code review | `superpowers:requesting-code-review` or `/workflows:review` |
| Feature isolation | `superpowers:using-git-worktrees` |

## Skill Activation Patterns

### Reliable Invocation

Skills activate through:
1. **Explicit invocation**: `/skill-name` or mentioning the skill name
2. **Trigger phrases**: Keywords in the skill's description
3. **Model recognition**: Claude identifies relevant skills from context

### Why `forced-eval` Matters

The `forced-eval` plugin increases skill activation from ~50% to ~84%. It intercepts before implementation and checks: "Should any skill be used here?"

Without it, Claude may jump to coding without using available structured approaches.

### Chaining Skills

Complex work often chains skills:

```
brainstorm → write-plan → worktree → execute → review
```

Each skill's output feeds the next phase.

## Context Management

### Search Before Read

Don't read files blindly. Search first:
1. `Grep` for specific patterns
2. `Glob` for file discovery
3. Read only what's relevant

### Progressive Disclosure

1. **Overview**: High-level structure (ls, tree, README)
2. **Sample**: Representative files to understand patterns
3. **Targeted**: Specific files for the task at hand

### Save-to-Files Strategy

Keep the conversation lean by offloading large outputs:

- **Save outputs >100 lines to files** instead of displaying in chat
- **Show summaries** with file paths for reference
- **Periodic checkpoints** at ~60% and ~85% context usage
- **Proactive warnings** before large operations that might bloat context

Example flow:
```
Claude: Analysis complete. Full results saved to ./analysis-results.md (847 lines).
        Summary: 12 critical issues, 34 warnings. See file for details.
```

### When to Use Subagents

Use subagents (`Task` tool) to:
- Protect main context from exploratory searches
- Run parallel investigations
- Isolate research that may not be relevant

### Strategic Compacting

The `strategic-compact` plugin monitors tool call frequency and suggests compaction:

| Threshold | Action |
|-----------|--------|
| 50 tool calls | First reminder to consider `/compact` |
| Every 25 after | Subsequent reminders |
| ~85% context | Urgent warning |

#### `/compact` - In-Place Summarization

Compresses context while preserving essential information:

```
/compact
```

Good times to compact:
- After completing a major task
- Before starting unrelated work
- When responses seem to lose earlier context

#### `/strategic-compact:handoff` - Explicit Session Transition

When you need to end a session cleanly and prepare for continuation:

```
/strategic-compact:handoff <goal-for-next-session>
```

This creates a structured handoff document (see Session Transitions below).

## Session Transitions

When context runs low or you need to switch focus, use explicit handoffs instead of losing work.

### The Handoff Command

```
/strategic-compact:handoff implement the remaining API endpoints
```

Creates a structured document at `.claude/handoffs/<timestamp>-<slug>.md`:

```markdown
# Session Handoff

## Goal for Next Session
Implement the remaining API endpoints

## Context Summary
- Working on user authentication system
- JWT implementation complete, refresh tokens pending
- Database schema finalized

## Key Decisions and Rationale
- Chose JWT over sessions for stateless scaling
- Using bcrypt (cost=12) for password hashing
- Refresh tokens stored in Redis with 7-day TTL

## Relevant Files to Load
- src/auth/jwt.ts - JWT utilities
- src/routes/auth.ts - Auth endpoints
- docs/api-spec.md - API specification

## Next Steps
1. Implement refresh token endpoint
2. Add token revocation
3. Write integration tests

## Notes/Caveats
- Redis connection pooling not yet configured
- Rate limiting deferred to next sprint
```

### Continuing from a Handoff

Start a new session and load the handoff:

```bash
claude
> Read .claude/handoffs/2024-01-15-api-endpoints.md and continue the work
```

The handoff provides context without the full transcript overhead.

### Session Handoff Format (Manual)

If not using the plugin, structure handoffs manually:

```markdown
# Session Handoff

## Completed
- [List of finished items]

## Key Findings
- [Important discoveries, decisions, blockers]

## Remaining Work
- [What's left to do]

## Files to Reference
- [Key files for context]
```

## Common Patterns

### Planning a Feature

```
1. superpowers:brainstorming    → Clarify requirements
2. superpowers:writing-plans    → Create implementation plan
3. superpowers:using-git-worktrees → Isolated branch
4. Execute task-by-task with checkpoints
5. superpowers:requesting-code-review
6. Merge
```

### Debugging

```
1. superpowers:systematic-debugging → Structured approach
2. Form hypothesis
3. Test hypothesis
4. Verify fix
5. Document in CLAUDE.md if pattern is reusable
```

### Full Development Cycle (Compound)

```
1. /workflows:plan     → Turn ideas into detailed plans
2. /workflows:work     → Execute with worktrees and tracking
3. /workflows:review   → Multi-agent code review
4. /workflows:compound → Capture learnings for future work
```

### Research Session

```
1. paper-reading skill (runs in Explore subagent)
2. Extract key findings
3. Document in project knowledge base
```

## Adaptive Learning (Homunculus)

The `homunculus` plugin (external) is "a plugin that's alive" — it observes your work, learns instincts, and evolves its capabilities over time.

### How It Works

Homunculus watches patterns in your sessions:
- Which skills you invoke frequently
- Common correction patterns (what you ask Claude to redo)
- Preferred coding styles and conventions
- Domain-specific knowledge accumulation

### Commands

| Command | Purpose |
|---------|---------|
| `/homunculus:status` | Check current learning state and accumulated instincts |
| `/homunculus:evolve` | Trigger learning from recent sessions |
| `/homunculus:export` | Export learned patterns for backup or sharing |

### When to Evolve

Run `/homunculus:evolve` after:
- Completing a significant project milestone
- Establishing new patterns you want remembered
- Correcting Claude multiple times on the same issue

The plugin learns from corrections, so consistent feedback produces better instincts.

## Headless Mode

For non-interactive execution of long-running or automated tasks, use the `-p` flag:

```bash
claude -p "instruction" --allowedTools "Bash,Read,Write,Edit"
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `-p "instruction"` | Pass prompt directly, no interactive mode |
| `--allowedTools "..."` | Grant tool permissions (comma-separated) |
| `--dangerously-skip-permissions` | Skip all permission prompts (use with caution) |
| `--output-format json` | Output as JSON (pipe to file) |
| `--output-format stream-json` | Streaming JSON output |

### Use Cases

**Pipeline integration:**
```bash
claude -p "Run tests and summarize failures" \
  --allowedTools "Bash,Read" \
  --output-format json > test-report.json
```

**Batch documentation updates:**
```bash
claude -p "Update all docstrings in src/ to match the new API" \
  --allowedTools "Read,Edit,Glob,Grep"
```

**Refactoring sweeps:**
```bash
claude -p "Replace all uses of deprecated_func with new_func" \
  --allowedTools "Read,Edit,Grep"
```

### Important Notes

- No interactive prompts — pre-grant permissions via `--allowedTools` or `--dangerously-skip-permissions`
- `--dangerously-skip-permissions` bypasses ALL prompts — use only in trusted, sandboxed environments
- **Gotcha**: `--output-format stream-json` requires `--verbose` when using `-p`
- Output goes to stdout; use redirection for files
- Combine with cron or CI for scheduled tasks
- Consider context limits for large operations

## Quick Reference

### Core Skills

| Skill | Purpose |
|-------|---------|
| `superpowers:brainstorming` | Clarify requirements before building |
| `superpowers:writing-plans` | Create bite-sized implementation plans |
| `superpowers:systematic-debugging` | Structured debugging approach |
| `superpowers:test-driven-development` | TDD workflow |
| `superpowers:using-git-worktrees` | Feature branch isolation |
| `superpowers:requesting-code-review` | Pre-merge review |

### Workflow Commands

| Command | Purpose |
|---------|---------|
| `/workflows:plan` | Plan features |
| `/workflows:work` | Execute with tracking |
| `/workflows:review` | Multi-agent review |
| `/workflows:compound` | Capture learnings |

### Session Management Commands

| Command | Purpose |
|---------|---------|
| `/compact` | In-place context summarization |
| `/strategic-compact:handoff <goal>` | Create handoff document for session transition |
| `/gist-report` | Create shareable HTML report |
| `/gist-transcript` | Save session transcript |

### Utility Commands

| Command | Purpose |
|---------|---------|
| `/worktrees` | Manage git worktrees |
| `/homunculus:status` | Check adaptive learning state |
| `/homunculus:evolve` | Trigger learning from recent sessions |
| `/homunculus:export` | Export learned patterns |

### Work Mode Aliases

| Alias | Purpose |
|-------|---------|
| `claude-dev` | Development mode — code first, explain after |
| `claude-research` | Research mode — read widely, no code until clear |
| `claude-review` | Review mode — thorough reading, severity-based feedback |

### Headless Mode

```bash
# Basic headless execution
claude -p "instruction" --allowedTools "Bash,Read,Write,Edit"

# Skip all permissions (sandboxed environments only)
claude -p "instruction" --dangerously-skip-permissions

# With JSON output
claude -p "instruction" --output-format json > result.json

# Streaming JSON (requires --verbose with -p)
claude -p "instruction" --verbose --output-format stream-json
```

## Troubleshooting

### Skills Not Activating

**Symptoms**: Claude jumps to implementation without using relevant skills.

**Solutions**:
1. Enable `forced-eval` plugin
2. Use explicit invocation: `/skill-name`
3. Check skill frontmatter has correct triggers
4. Mention the skill name directly

### Context Exhaustion

**Symptoms**: Claude loses track of earlier discussion, responses become generic.

**Solutions**:
1. Use `/compact` to summarize and free space
2. Delegate research to subagents
3. Break large tasks into separate sessions
4. Use progressive disclosure (don't read everything upfront)

### Lost Work

**Symptoms**: Session ended, unsure what was completed.

**Solutions**:
1. Check `session-persistence` plugin output at session start
2. Use `/gist-transcript` before ending important sessions
3. Review git log for committed changes

### Skill Shows Wrong Behavior

**Symptoms**: Skill does something unexpected or outdated.

**Solutions**:
1. Re-read the skill with `Skill` tool (skills evolve)
2. Check if user instructions conflict with skill
3. Use explicit `/skill-name` to force fresh load

## See Also

- [Getting Started](getting-started.md) - Initial setup
- [Bundles Explained](bundles-explained.md) - Component packaging
- [Plugins Explained](plugins-explained.md) - Runtime hooks and commands
- [Workflow Patterns](workflow-patterns.md) - Superpowers vs Compound workflows, branching strategies
