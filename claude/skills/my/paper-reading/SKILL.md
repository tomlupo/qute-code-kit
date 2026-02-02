---
name: paper-reading
description: |
  Active reading and analysis of research papers. Use when reading academic papers, extracting insights,
  summarizing findings, or evaluating research quality. Triggers: "read this paper", "analyze paper",
  "summarize paper", "what does this paper say", "extract insights", "paper review", "literature review"
agent: Explore
---

# Paper Reading & Analysis

Active reading strategies and analysis frameworks for research papers. Focus on extracting actionable insights efficiently.

## Reading Strategy

### Three-Pass Approach

**Pass 1: Quick Assessment (5-10 min)**
- Read title, abstract, introduction, conclusion
- Skim figures and tables
- **Goal**: Determine relevance and main contribution
- **Output**: Quick summary + relevance score

**Pass 2: Selective Deep Dive (20-30 min)**
- Read methodology section (if relevant to implementation)
- Examine key results and figures in detail
- Review related work for context
- **Goal**: Understand approach and validate claims
- **Output**: Technical summary + key findings

**Pass 3: Critical Analysis (30-60 min, only if needed)**
- Full careful reading
- Verify experimental setup
- Check reproducibility details
- Assess limitations and future work
- **Goal**: Deep understanding for implementation or critique
- **Output**: Comprehensive analysis

### When to Use Each Pass

| Relevance | Use Pass | Time | Output |
|-----------|----------|------|--------|
| Low/Unknown | 1 only | 5-10 min | Quick assessment |
| Medium | 1 + 2 | 25-40 min | Technical summary |
| High/Critical | All 3 | 60-90 min | Full analysis |

## Context Management for Papers

Papers are large content sources (often 20-50+ pages). Apply context management principles to read efficiently without exhausting context. See also `@.claude/skills/context-management` for general strategies.

### Progressive Reading Phases

Match reading depth to context budget:

| Phase | Context Cost | What to Read | Output |
|-------|--------------|--------------|--------|
| **Metadata** | Minimal | Title, authors, venue, year | Quick relevance check |
| **Abstract** | Low | Abstract, introduction (first page) | Quick summary |
| **Selective** | Medium | Key sections (methods, results) | Technical summary |
| **Full** | High | Complete paper | Comprehensive analysis |

**Rule**: Only proceed to next phase if paper is relevant. Most papers stop at Abstract phase.

### Save Summaries to Files

**Always save paper summaries to files** rather than keeping full paper content in context:

```markdown
✅ GOOD: Save summary to file
"Saved summary to docs/papers/summaries/investsuite-ivar-summary.md
Key points: [brief list]"

❌ BAD: Keep full paper in context
[Full paper content filling context...]
```

**Summary File Location**: `docs/papers/summaries/{paper-slug}-summary.md`

**When to Save**:
- After Pass 1 (Quick Assessment) → Save quick summary
- After Pass 2 (Technical Summary) → Save technical summary
- After Pass 3 (Critical Analysis) → Save comprehensive analysis
- Before reading next paper → Save current findings

### Context Checkpoints

When reading multiple papers:

```markdown
**Context Check**: ~60% used
- Papers read: 3 ✓
- Summaries saved: 3 ✓
- Remaining: 2 papers

**Action**: Continuing normally
```

```markdown
**Context Check**: ⚠️ ~85% used

**Saving state**:
- Paper summaries → saved to docs/papers/summaries/
- Key insights → saved to docs/papers/insights.md

**Options**:
A) Read remaining papers with Pass 1 only (quick assessment)
B) Focus on most relevant paper (deep dive)
C) Wrap up with synthesis document
```

### Search Before Reading

**Before reading a new paper**:
1. Check `docs/papers/_index.md` for existing entry
2. Check `docs/papers/summaries/` for existing summary
3. If summary exists, read it first (saves context)
4. Only read full paper if summary is insufficient

### Proactive Warnings

Before reading multiple papers:

```markdown
"About to read 5 papers (~150 pages total).

**Estimated Context Impact**: ~90% usage

**Smarter Approach**:
- Read abstracts first (Pass 1) → ~20% context
- Save quick summaries to files
- You choose which papers need deep dive
- I read only selected papers fully

This preserves context. Proceed with Pass 1 only?"
```

### Literature Review Context Strategy

When doing literature reviews (multiple papers):

1. **Phase 1: Discovery** (Low context)
   - Read abstracts of all papers
   - Save quick assessments to files
   - Rank by relevance

2. **Phase 2: Selective Deep Dive** (Medium context)
   - Read technical summaries of top 3-5 papers
   - Save summaries to files
   - Build synthesis document

3. **Phase 3: Targeted Analysis** (High context, only if needed)
   - Full read of 1-2 most critical papers
   - Save comprehensive analysis

**Never read all papers fully in one session.**

## Analysis Frameworks

### Quick Assessment Template

For initial evaluation (~2 min read):

```markdown
## Paper: [Title]

**Metadata**
- Authors: [List]
- Year: [Publication Year]
- Venue: [Conference/Journal]
- DOI/ArXiv: [Link]

**Quick Summary**
[1-2 sentence overview of the paper's main contribution]

**Relevance Score**: [High/Medium/Low] for [current task]
**Key Insight**: [One sentence takeaway]
**Action**: [Read more / Archive / Deep dive]
```

### Technical Summary Template

For papers requiring understanding:

```markdown
## Technical Summary: [Paper Title]

### Problem Statement
[What problem does this address?]

### Core Contribution
[Main novelty or advance]

### Methodology
- **Approach**: [High-level description]
- **Key Innovation**: [What's new vs prior work]
- **Technical Details**: [Architecture/algorithm/framework]

### Experimental Setup
- **Datasets**: [What data was used]
- **Baselines**: [Compared against what]
- **Metrics**: [How success was measured]

### Key Results
- **Main Findings**: [Quantitative results with numbers]
- **Performance**: [Comparison to baselines]
- **Ablation Studies**: [What components matter]

### Practical Takeaways
- **Actionable Insights**: [What can we use?]
- **Implementation Notes**: [How to apply?]
- **Caveats**: [Limitations to consider]
```

### Executive Summary Template

For non-technical stakeholders:

```markdown
## Executive Summary: [Title]

**What They Did**: [Plain language explanation]

**Why It Matters**: [Significance and impact]

**Key Finding**: [Main result in simple terms]

**Bottom Line**: [Practical implication for our work]
```

### Critical Analysis Template

For deep evaluation:

```markdown
## Critical Analysis: [Paper Title]

### Strengths
- [What this paper does well]
- [Novel contributions]
- [Sound methodology]

### Limitations
- [Acknowledged by authors]
- [Potential issues identified]
- [Missing experiments]

### Reproducibility
- [ ] Code available?
- [ ] Data available?
- [ ] Clear enough to implement?

### Future Work
- [Authors' suggestions]
- [Open questions]
- [Research gaps]

### Relevance to Our Work
- [How does this relate?]
- [What can we adopt?]
- [What should we test?]
```

## Active Reading Techniques

### Question-Driven Reading

Before reading, ask:
1. **What problem does this solve?** (Introduction)
2. **How is it different from prior work?** (Related Work)
3. **What's the core idea?** (Methodology)
4. **Does it actually work?** (Results)
5. **What are the limitations?** (Discussion/Conclusion)

### Extract-As-You-Read

While reading, capture:
- **Key definitions**: Technical terms, metrics, concepts
- **Formulas/algorithms**: Mathematical expressions, pseudocode
- **Numbers**: Performance metrics, dataset sizes, hyperparameters
- **Citations**: Important related papers to follow up
- **Open questions**: What's not addressed?

### Cross-Reference Strategy

When reading multiple papers:
1. **Build concept map**: How papers relate to each other
2. **Compare approaches**: Different solutions to same problem
3. **Track evolution**: How ideas developed over time
4. **Identify consensus**: What do most papers agree on?

## Quality Assessment

### Credibility Checklist

- [ ] **Venue**: Top-tier conference/journal?
- [ ] **Authors**: Recognized researchers?
- [ ] **Reproducibility**: Code/data available?
- [ ] **Methodology**: Sound experimental design?
- [ ] **Results**: Statistically significant?
- [ ] **Peer Review**: Rigorous venue?

### Red Flags

⚠️ **Warning signs:**
- Unrealistic claims without evidence
- Missing experimental details
- No comparison to baselines
- Cherry-picked results
- Lack of ablation studies
- Poor writing/clarity (often indicates poor thinking)

### When to Trust Results

✅ **High confidence:**
- Reproducible code available
- Multiple independent validations
- Consistent with related work
- Clear methodology
- Honest about limitations

## Literature Review Synthesis

For comparing multiple papers:

```markdown
## Literature Review: [Topic]

**Papers Analyzed**: [Count]
**Date Range**: [Years covered]

### Evolution of Ideas
1. **Early Work ([years])**
   - Focus: [approach]
   - Key papers: [List]
   - Limitations: [Issues]

2. **Current State ([years])**
   - Refined techniques: [Modern approaches]
   - SOTA results: [Best performance]
   - Key papers: [List]

### Consensus Findings
- [Agreement across papers]
- [Well-established techniques]
- [Proven approaches]

### Controversial Areas
- [Disagreements]
- [Conflicting results]
- [Open debates]

### Research Gaps
- [Under-explored areas]
- [Future directions]
- [Opportunities]
```

## Integration with Project

### When Reading Papers for This Project

1. **Check existing knowledge**: Look in `docs/papers/_index.md` first
2. **Extract actionable insights**: Focus on what can be implemented
3. **Link to codebase**: Note where concepts are used (e.g., "iVaR from InvestSuite paper")
4. **Update index**: Add new papers to `docs/papers/_index.md` with brief description
5. **Document connections**: Link papers to research findings in `docs/research/`

### Paper Storage

- **Location**: `docs/papers/` (flat structure)
- **Index**: `docs/papers/_index.md` (maintain with short descriptions)
- **References**: Use relative paths in documentation (e.g., `docs/papers/paper-name.pdf`)

## Remember

**Focus on extracting actionable insights rather than comprehensive summaries.** Match the analysis depth to the paper's relevance to your current task. Use the three-pass strategy to efficiently triage papers, then deep-dive only when needed.

**Key principle**: Read to understand, not to archive. Extract what matters for the current work, document connections to the codebase, and move on.
