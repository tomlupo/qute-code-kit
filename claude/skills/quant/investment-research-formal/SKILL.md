---
name: investment-research-formal
description: Structured, auditable investment research with tracked hypotheses, experiments, and findings. Use when research needs an evidence chain for compliance, regulatory documentation (MiFID II suitability), published methodology, white papers, or peer review. Use when the user says "formal research", "document methodology", "audit trail", "compliance evidence", or "white paper". Complements investment-research (iterative) with traceability.
---

# Formal Investment Research

Structured research with full traceability: every decision links back to evidence, every finding links forward to application. For iterative exploration, use `investment-research` instead.

## When to Use This vs `investment-research`

| Signal | Use `investment-research` | Use `investment-research-formal` |
|--------|--------------------------|----------------------------------|
| Audience | You + immediate team | Compliance, regulators, external reviewers |
| Lifespan | Until next calibration cycle | Permanent record |
| Review | Visual (dashboard) | Written (methodology doc) |
| Tracking | README + git | Hypothesis → Experiment → Finding chain |
| Trigger phrases | "research", "backtest", "study" | "document methodology", "audit trail", "white paper" |

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
├── data/
│   ├── raw/
│   ├── intermediate/
│   └── processed/
├── scripts/                      # Or build_*.py at root
├── output/
└── archive/
```

## Cross-Referencing Convention

Use consistent IDs for traceability:

```
H01 → tested by → E01, E02
E01 → supports → F01
F01 → applied to → config/profiles.json, app parameter
F01 → documented in → METHODOLOGY.md §6
```

In any document, reference others with relative links:
```markdown
See [H01](../hypotheses/H01-gold-diversification.md) for the original hypothesis.
Evidence from [E01](../experiments/E01-gold-allocation-sweep.md).
```

**Numbering**: H{nn}, E{nn}, F{nn} — sequential, never reused. If H03 is rejected, H04 is next.

## Workflow Integration

### Starting from Iterative Research

When formalizing results from an `investment-research` study:

1. Identify the key decisions that were made (from README, git history, dashboard)
2. Reconstruct hypotheses retroactively (what did we actually test?)
3. Write experiments from existing scripts (what did we run?)
4. Extract findings from dashboard/output (what did we conclude?)
5. Write METHODOLOGY.md as the synthesis

### Feeding Back to Production

```
Finding validated
    → Update config JSON (profile_data.json, etc.)
    → Update dashboard data (rebuild pipeline)
    → Mark finding as APPLIED with date
    → Update METHODOLOGY.md version
```

## Regulatory Context (MiFID II)

For advisory firms, formal research documentation serves compliance:

| Requirement | How This Skill Addresses It |
|-------------|----------------------------|
| Suitability assessment basis | METHODOLOGY.md documents how profiles are constructed |
| Acting in client's best interest | Evidence chain shows data-driven decisions |
| Record keeping | Timestamped findings with version history |
| Periodic review | Findings can be re-validated against new data |
| Transparency | Methodology document is client-shareable |

## Guidelines

- **Formal does not mean slow** — templates are fast to fill. The overhead is in thinking, not writing.
- **Retroactive formalization is fine** — most research starts informal. Formalize when the audience requires it.
- **One finding per decision** — if a finding supports multiple decisions, split it.
- **Version METHODOLOGY.md** — when parameters change, bump version and add review history entry.
- **Don't duplicate the dashboard** — findings reference dashboard charts, not reproduce them.
- **Archive rejected hypotheses** — they're evidence too. "We tested X and it didn't work" is valuable for compliance.

---

## Document Templates

Use these templates when creating formal research artifacts. Each template is self-contained — copy the markdown block directly into the appropriate file.

### Hypothesis (H01-{slug}.md)

```markdown
# H01: {Testable Statement}

**Status**: TESTING
**Date**: YYYY-MM-DD
**Author**: {name}
**Study**: {study-name}

## Statement

{Clear, falsifiable claim. One sentence.}

Example: "Adding a 10% gold allocation to bond-heavy profiles (P1-P3)
reduces max drawdown by >2pp without reducing annualized return by >0.5pp."

## Rationale

Why we believe this might be true:
- {Theoretical basis or market intuition}
- {Supporting literature: see literature/author-year-slug.md}
- {Empirical observation from prior work}

## Success Criteria

Quantitative thresholds that determine validated vs rejected:
- [ ] Max DD reduction > 2pp for P1, P2, P3
- [ ] Ann. return reduction < 0.5pp
- [ ] Improvement consistent across full-period AND recent-period

## Test Plan

| # | Experiment | What It Tests |
|---|-----------|---------------|
| 1 | E01-{name} | {description} |
| 2 | E02-{name} | {description} |

## Results

| Experiment | Outcome | Key Metric |
|-----------|---------|------------|
| E01 | {PASS/FAIL} | {value} |

## Conclusion

**Status**: {VALIDATED / REJECTED / INCONCLUSIVE}

{One paragraph summarizing the verdict with key numbers.}

**If validated** → Finding: F{nn}-{slug}.md
**If rejected** → {Why, and what we learned}
**If inconclusive** → {What additional evidence is needed}
```

### Experiment (E01-{slug}.md)

```markdown
# E01: {Experiment Name}

**Status**: RUNNING
**Date**: YYYY-MM-DD
**Hypothesis**: H01-{slug}.md

## Objective

{What specific question does this experiment answer?}

## Setup

### Data
- Period: {start} to {end} ({N} months)
- Assets: {list}
- Source: {data source and validation status}
- Frequency: {monthly/daily}

### Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Rebalancing | Quarterly | {why} |
| Cost assumption | 0 bps | {why} |
| Weight step | 5% | {why} |
| Benchmark | {what} | {why} |

### Methodology
1. {Step 1}
2. {Step 2}
3. {Step 3}

### Reproducibility
```bash
uv run python scripts/{script}.py --config {config}
```
Output: `output/{run-dir}/`

## Results

### Primary Metrics
| Profile | Metric Before | Metric After | Delta |
|---------|--------------|-------------|-------|
| P1 | | | |
| P2 | | | |

### Key Observations
- {Observation 1}
- {Observation 2}

### Artifacts
- Data: `data/processed/{file}`
- Charts: `output/{run}/`
- Dashboard: `output/{run}/dashboard.html`

## Conclusion

{Does this support or refute H01? With what confidence?}

## Limitations
- {Limitation 1: e.g., no transaction costs}
- {Limitation 2: e.g., USD-only, no FX for PLN portfolios}
```

### Finding (F01-{slug}.md)

```markdown
# F01: {Finding Title}

**Status**: DRAFT
**Date**: YYYY-MM-DD
**Confidence**: HIGH / MEDIUM / LOW

## Summary

{One paragraph: what we found, with key numbers.}

## Evidence Chain

| Source | Reference | Key Result |
|--------|-----------|------------|
| Hypothesis | H01-{slug}.md | {original claim} |
| Experiment | E01-{slug}.md | {supporting result} |
| Experiment | E02-{slug}.md | {confirming result} |

## Quantitative Evidence

| Metric | Before | After | Significance |
|--------|--------|-------|-------------|
| Max DD (P1) | -12.3% | -10.2% | 2.1pp improvement |
| Ann. Return (P1) | 5.9% | 5.7% | 0.2pp cost |

## Implications

### For Production
- {What parameter changes should be made}
- {Which config files need updating}

### For Clients
- {How this affects risk profile communication}
- {Suitability documentation impact}

### For Future Research
- {What new questions this raises}

## Limitations & Caveats

- {When this finding might not hold}
- {Data limitations}
- {Assumptions that could be violated}

## Regulatory Notes

{If applicable: MiFID II suitability relevance, documentation requirements,
how this finding supports the "acting in client's best interest" obligation.}

## Application

**Applied**: YES / NO / PARTIAL
**Applied to**: {config file, dashboard, app parameter}
**Applied date**: YYYY-MM-DD
**Applied by**: {name}
```

### Literature Note ({author-year}-{slug}.md)

```markdown
# {Author} ({Year}) — {Short Title}

**Source**: {journal/working paper/blog}
**URL**: {link}
**Relevance**: {HIGH/MEDIUM/LOW}

## Key Claims
1. {Main finding relevant to our research}
2. {Secondary finding}

## Methodology
- {Data period and universe}
- {Approach}
- {Key assumptions}

## Relevance to Our Work
- {How it supports/challenges our approach}
- {What we can adapt}
- {What doesn't apply (different market, period, etc.)}

## Actionable Ideas
- [ ] {Specific thing to test based on this paper}
- [ ] {Parameter to consider}

## Related Hypotheses
- H{nn}-{slug}: {how it connects}
```

### METHODOLOGY.md (Formal Methodology Document)

```markdown
# {Study Title} — Methodology

**Version**: 1.0
**Date**: YYYY-MM-DD
**Authors**: {names}
**Status**: UNDER REVIEW / PUBLISHED

## 1. Objective
{What decision this methodology supports. One paragraph.}

## 2. Scope
- Asset classes: {list}
- Instruments: {types}
- Geography: {markets}
- Time horizon: {period}

## 3. Data Sources
| Source | Coverage | Frequency | Validation |
|--------|----------|-----------|------------|
| {name} | {period} | {freq} | {how validated} |

## 4. Methodology

### 4.1 {Step Name}
{Description with enough detail to reproduce.
Include formulas where relevant.}

### 4.2 {Step Name}
...

## 5. Assumptions & Limitations
1. {Assumption}: {justification}
2. {Limitation}: {impact}

## 6. Results Summary
{Key findings with references to Finding documents.}

| Finding | Reference | Confidence |
|---------|-----------|------------|
| {title} | F01-{slug}.md | HIGH |

## 7. Sensitivity Analysis
{How results change under different assumptions.}

## 8. Conclusions & Recommendations
{Actionable output: parameters, allocations, constraints.}

## 9. Review History
| Date | Reviewer | Action |
|------|----------|--------|
| YYYY-MM-DD | {name} | Initial draft |
| YYYY-MM-DD | {name} | Approved |

## Appendices
- A: Detailed tables
- B: Reproducibility instructions
- C: Regulatory mapping (MiFID II suitability requirements)
```

## Complementary Skills

| Skill | Role |
|-------|------|
| `investment-research` | Iterative exploration (use first, formalize later) |
| `investment-research-dashboard` | Interactive deliverables referenced by findings |
| `analizy-pl-data` | Polish fund data from analizy.pl |
