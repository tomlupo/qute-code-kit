# Multi-Agent Code Review

> Comprehensive code review using parallel specialist agents.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| /workflows:review | `compound-engineering` plugin | 13+ specialist review agents |
| /triage | `compound-engineering` plugin | Accept/reject findings |
| /resolve_todo_parallel | `compound-engineering` plugin | Fix approved findings in parallel |
| kieran-python-reviewer | `compound-engineering` plugin | Strict Python conventions |
| visual-explainer | `claude-plugins-official` plugin | Visualize review findings |

## Review Depth Levels

| Depth | Tool | Cost | When |
|-------|------|------|------|
| Quick | `/requesting-code-review` | Low | Routine changes, small PRs |
| Standard | `/code-review:code-review` | Medium | Feature PRs, before merge |
| Deep | `/workflows:review` | High | Major features, architecture changes |

## The Deep Review Flow

```
Review → Triage → Resolve → Verify
```

### 1. Launch multi-agent review

```
/workflows:review
```

This spawns 13+ specialist agents in parallel, each reviewing from their domain:

| Agent | Looks for |
|-------|----------|
| Security sentinel | Vulnerabilities, injection, auth issues |
| Performance oracle | N+1 queries, memory leaks, scaling issues |
| Architecture strategist | Component boundaries, coupling, cohesion |
| Data integrity guardian | Migration safety, transaction boundaries |
| Code simplicity reviewer | Over-engineering, YAGNI violations |
| Pattern recognition | Anti-patterns, code duplication |
| Agent-native reviewer | API parity for agent access |
| Schema drift detector | Unrelated schema.rb changes |
| And more... | |

### 2. Triage findings

```
/triage
```

Walk through findings one by one. Runs on Haiku (cheap). For each finding:
- **Accept** — add to fix list
- **Reject** — dismiss with reason
- **Defer** — acknowledge but not now

**Tip:** Be ruthless. Not every finding needs action. The triage step prevents over-fixing.

### 3. Resolve accepted findings

```
/resolve_todo_parallel
```

Fixes all accepted findings using parallel agents. Each fix runs in isolation.

### 4. Verify

Run your test suite, then optionally:

```
/requesting-code-review
```

Quick single-agent pass to verify the fixes didn't introduce new issues.

## Variations

### Python-specific review

For Python codebases, use the `kieran-python-reviewer` agent from compound-engineering:

```
Use the kieran-python-reviewer agent to review src/
```

### Visual review summary

After review, create a shareable summary:

```
/visual-explainer
```

Produces a styled HTML page with findings by severity, affected files, and recommendations.

### Autonomous full cycle

For maximum automation:

```
/lfg           # or /slfg for swarm mode
```

Runs the full compound-engineering cycle: plan → implement → review → triage → resolve. Use when you trust the process and want to go hands-off.

## Tips

- `/workflows:review` is expensive (13+ agents) — reserve for major features
- Quick review (`/requesting-code-review`) is the right default for daily work
- Run review after implementation, before `/handoff` or commit
- The triage step is critical — skip it and you'll waste time on false positives
- For PRs touching data migrations, the data-integrity-guardian alone is worth the cost
