# Research Workflow Skill

A comprehensive skill for managing ML/data science research workflows.

## When to Use

Use this skill when the user needs to:
- Track research hypotheses and their validation status
- Document experiments with reproducible setups
- Record validated findings with evidence
- Extract and analyze academic papers
- Maintain a research index

## Commands

| Command | Purpose |
|---------|---------|
| `/research:start <topic>` | Initialize research structure |
| `/research:hypothesis "<statement>"` | Document a testable hypothesis |
| `/research:experiment <name>` | Log an experiment |
| `/research:finding "<title>"` | Document a validated finding |
| `/research:paper <url>` | Read and extract paper insights |
| `/research:index` | Show research overview |

## Research Lifecycle

```
1. Hypothesis → 2. Experiment(s) → 3. Finding → 4. Application

🔬 Testing    →    🏃 Running    →    🟢 High    →    Production
                   ✅ Complete        🟡 Medium
                   ❌ Failed          🔴 Low
```

## Document Locations

All research documents are stored in `docs/research/`:

```
docs/research/
├── index.md           # Auto-maintained index
├── hypotheses/        # Testable statements
├── experiments/       # Reproducible setups & results
├── findings/          # Validated conclusions
└── papers/            # Literature notes
```

## Best Practices

### Hypotheses
- Make them **specific and testable**
- Include **success criteria** upfront
- Link to **supporting papers** or observations

### Experiments
- Document **environment** completely (versions, hardware)
- Record **all parameters**, not just the ones you changed
- Save **artifacts** (models, logs, configs)
- Note **unexpected observations**

### Findings
- Only document **validated** findings (not hunches)
- Include **statistical significance** where applicable
- Note **limitations** and edge cases
- Define **next steps** for application

### Papers
- Focus on **relevance to your research**
- Extract **actionable ideas**
- Note **limitations for your use case**
- Track **references to follow**

## Integration with MLflow

If your project uses MLflow, link experiments to runs:

```markdown
## Artifacts
- MLflow run: `runs:/abc123`
- Metrics dashboard: [link]
```

## Templates

Templates are available in the plugin's `templates/` directory:
- `hypothesis.md`
- `experiment.md`
- `finding.md`
- `paper-notes.md`
