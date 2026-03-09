---
name: investment-research-formal
description: Structured, auditable investment research with tracked hypotheses, experiments, and findings. Use when research needs an evidence chain for compliance, regulatory documentation (MiFID II suitability), published methodology, white papers, or peer review. Triggers — "formal research", "document methodology", "audit trail", "compliance evidence", "white paper".
---

# Formal Investment Research

Structured research with full traceability: every decision links back to evidence, every finding links forward to application. For iterative exploration, use `investment-research` instead.

## When to Use This vs `investment-research`

| Signal | `investment-research` | `investment-research-formal` |
|--------|----------------------|------------------------------|
| Audience | You + immediate team | Compliance, regulators, external reviewers |
| Lifespan | Until next calibration cycle | Permanent record |
| Review | Visual (dashboard) | Written (methodology doc) |
| Tracking | README + git | Hypothesis → Experiment → Finding chain |

**Common pattern**: Start with `investment-research` for exploration, then formalize key findings with this skill when producing regulatory or publication deliverables.

## Research Lifecycle

```
Question → Hypothesis → Experiment → Finding → Application → Review
              ↑              ↓           ↓
              └── rejected ──┘     updates hypothesis
```

### Status Tracking

| Artifact | Statuses |
|----------|----------|
| Hypothesis | TESTING → VALIDATED / REJECTED / INCONCLUSIVE |
| Experiment | RUNNING → COMPLETE / FAILED |
| Finding | DRAFT → REVIEWED → APPLIED |
| Study | IN PROGRESS → UNDER REVIEW → PUBLISHED |

## Directory Structure

```
research/{study-name}/
├── README.md                     # Study overview, status, pipeline
├── METHODOLOGY.md                # Formal methodology document
├── hypotheses/
│   ├── H01-{slug}.md             # Numbered for cross-referencing
│   └── H02-{slug}.md
├── experiments/
│   ├── E01-{slug}.md
│   └── E02-{slug}.md
├── findings/
│   ├── F01-{slug}.md
│   └── F02-{slug}.md
├── literature/
│   └── {author-year}-{slug}.md   # Paper notes
├── data/                         # raw/, intermediate/, processed/
├── scripts/                      # Or build_*.py at root
├── output/
└── archive/
```

## Document Templates

All templates are in `references/templates.md`. Use them for:

| Document | File Pattern | Purpose |
|----------|-------------|---------|
| Hypothesis | `hypotheses/H{nn}-{slug}.md` | Testable claim with success criteria |
| Experiment | `experiments/E{nn}-{slug}.md` | Setup, parameters, results, limitations |
| Finding | `findings/F{nn}-{slug}.md` | Evidence chain, implications, application status |
| Literature | `literature/{author-year}-{slug}.md` | Paper notes with actionable ideas |
| Methodology | `METHODOLOGY.md` | Formal versioned methodology (publication-grade) |

## Cross-Referencing Convention

Use consistent IDs for traceability:

```
H01 → tested by → E01, E02
E01 → supports → F01
F01 → applied to → config/profiles.json
F01 → documented in → METHODOLOGY.md §6
```

**Numbering**: H{nn}, E{nn}, F{nn} — sequential, never reused. If H03 is rejected, H04 is next.

## Workflow Integration

### Starting from Iterative Research

When formalizing results from an `investment-research` study:

1. Identify key decisions (from README, git history, dashboard)
2. Reconstruct hypotheses retroactively (what did we actually test?)
3. Write experiments from existing scripts (what did we run?)
4. Extract findings from dashboard/output (what did we conclude?)
5. Write METHODOLOGY.md as the synthesis

### Feeding Back to Production

```
Finding validated
    → Update config JSON
    → Update dashboard data (rebuild pipeline)
    → Mark finding as APPLIED with date
    → Update METHODOLOGY.md version
```

## Regulatory Context (MiFID II)

| Requirement | How This Addresses It |
|-------------|----------------------|
| Suitability assessment basis | METHODOLOGY.md documents profile construction |
| Acting in client's best interest | Evidence chain shows data-driven decisions |
| Record keeping | Timestamped findings with version history |
| Periodic review | Findings re-validated against new data |
| Transparency | Methodology document is client-shareable |

## Guidelines

- **Formal does not mean slow** — templates are fast to fill. The overhead is in thinking, not writing.
- **Retroactive formalization is fine** — most research starts informal. Formalize when the audience requires it.
- **One finding per decision** — if a finding supports multiple decisions, split it.
- **Version METHODOLOGY.md** — bump version and add review history when parameters change.
- **Archive rejected hypotheses** — they're evidence too. "We tested X and it didn't work" is valuable.

## Reference Documentation

| Reference | When to Load |
|-----------|-------------|
| [templates.md](references/templates.md) | All document templates (hypothesis, experiment, finding, literature, methodology) |

## Complementary Skills

| Skill | Role |
|-------|------|
| `investment-research` | Iterative exploration (use first, formalize later) |
| `investment-research-dashboard` | Interactive deliverables referenced by findings |
