# Workflows

Organized by use case. Each section shows when to use it, what skills/agents are involved, and the typical flow.

---

## Feature Development

**Mode**: `claude-dev`

### Quick approach (Superpowers)

```
brainstorm → write-plan → execute-plan → review → commit
```

1. `/brainstorming` — explore the idea, clarify requirements
2. `/writing-plans` — break into bite-sized tasks
3. `/worktrees [branch]` — isolate work in a git worktree
4. `/executing-plans` — implement with review checkpoints
5. `/requesting-code-review` — validate before merge
6. `/commit` — atomic commit with structured message

### Full lifecycle (Compound Engineering)

```
brainstorm → plan → deepen → work → review → triage → resolve → compound
```

| Step | Command | What happens |
|------|---------|-------------|
| Brainstorm | `/workflows:brainstorm` | Clarify WHAT to build. Output: `docs/brainstorms/` |
| Plan | `/workflows:plan` | Detail HOW. Spawns research agents. Output: `docs/plans/` |
| Deepen | `/deepen-plan` | 30-50+ parallel research agents enhance the plan |
| Work | `/workflows:work` | Execute in worktree, incremental commits, tests |
| Review | `/workflows:review` | 13+ specialist agents review in parallel |
| Triage | `/triage` | Accept/reject findings one by one (runs on Haiku) |
| Resolve | `/resolve_todo_parallel` | Fix approved findings in parallel |
| Compound | `/workflows:compound` | Capture learnings to `docs/solutions/` |

**Shortcuts**: `/lfg` (full autonomous loop), `/slfg` (swarm mode)

### Combining both

```
superpowers:brainstorming     → clarify what to build
/workflows:plan               → detailed implementation plan
/deepen-plan                  → enhance with research agents
superpowers:subagent-driven   → execute with fresh agents
/workflows:review             → multi-agent review
/workflows:compound           → capture learnings
```

---

## Quantitative Research

**Mode**: `claude-research` → `claude-dev`

Full pipeline from literature to production:

| Step | Tool | Notes |
|------|------|-------|
| Literature review | `/paper-reading [path]` | Three-pass reading via Explore subagent |
| Research spec | `/qrd` | Interactive questionnaire → structured QRD document |
| Market data | `/market-data-fetcher [ticker]` | Auto-routes: Stooq (Polish), Yahoo (US), FRED (macro), Binance (crypto) |
| Database queries | `database-explorer` agent | Natural language → SQL, schema discovery |
| SQL templates | `/sql-patterns` | Time-series, cohort analysis, window functions, CTEs |
| EDA | `exploratory-data-analysis` | Auto-detect 200+ formats, generate quality reports |
| Statistical modeling | `statsmodels` / `pymc` | OLS, GLM, ARIMA, Bayesian inference |
| ML training | `scikit-learn` / `pytorch-lightning` | Pipelines, multi-GPU, callbacks |
| Time series ML | `aeon` | Classification, forecasting, anomaly detection |
| Explainability | `shap` | SHAP values for any model type |
| Experiment tracking | `mlflow-analyzer` agent | Compare runs, hyperparameter sensitivity |
| Visualization | `matplotlib` / `plotly` | Static (publication) / interactive (dashboards) |
| Data processing | `polars` | Fast DataFrames, lazy evaluation, 1-100GB |
| Documentation | `/readme` | Project README (forked context) |

**Research workflow plugin** (structured research tracking):

```
/research:start <topic>           → initialize docs/research/ structure
/research:hypothesis "<statement>" → document testable hypothesis
/research:experiment <name>       → log experiment setup
/research:finding "<title>"       → document validated finding
/research:index                   → show research overview
```

---

## Code Review

**Mode**: `claude-review`

### Giving reviews

- `/requesting-code-review` — single-agent review with checklist
- `/workflows:review` — 13+ specialist agents in parallel (security, performance, architecture, simplicity, data integrity, etc.)
- `/llm-external-review` — delegate to Codex CLI (bugs) or Gemini CLI (architecture)

### Receiving reviews

- `/receiving-code-review` — verify feedback before implementing. Push back on incorrect suggestions.

### Pre-implementation gate

The `forced-eval` plugin intercepts every prompt and forces evaluation of available skills/agents before coding starts. Increases skill activation from ~50% to ~84%.

---

## Debugging

1. `/systematic-debugging` — structured root cause analysis
2. Diagnose → hypothesize → verify → fix
3. `/verification-before-completion` — confirm the fix works

---

## Documentation

- `/readme` — generate comprehensive project README (runs in forked context)
- `/gist-report` — convert files/analysis to styled HTML → GitHub gist
- `/gist-transcript` — save session transcript to GitHub gist

---

## Session Management

| Action | Command |
|--------|---------|
| Summarize context | `/compact` |
| Create handoff doc | `/strategic-compact:handoff <goal>` |
| List saved sessions | `/session-persistence:list` |
| Restore session | `/session-persistence:load` |
| Resume from handoff | `Read .claude/handoffs/<file>.md and continue` |

---

## Learning & Self-Improvement

### Behavioral learning (adaptive-learning plugin)

```
Tool usage → observations.jsonl → /adaptive-learning:analyze → instincts
                                                                    ↓
Next session start → top instincts surfaced → Claude adapts
```

Commands: `/adaptive-learning:status`, `:analyze`, `:ingest-insights`, `:export`, `:import`

### Project knowledge (compound-engineering)

```
Problem solved → /workflows:compound → docs/solutions/{category}/
                                              ↓
Next /workflows:plan → learnings-researcher reads past solutions → better plan
```
