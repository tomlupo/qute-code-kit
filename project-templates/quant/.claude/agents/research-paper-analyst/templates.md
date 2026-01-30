# Document Analysis Templates

Templates for different document types and analysis depths.

## Quick Assessment Templates

### Quick Assessment (Universal)

For initial evaluation of any document (~2 min):

```markdown
## Document: [Title/Filename]

**Metadata**
- Type: [Research Paper / Financial Report / Technical Doc / Legal / Other]
- Authors/Source: [List or Organization]
- Date: [Publication Date]
- Pages: [Count]
- Language: [Primary language]

**Quick Summary**
[1-2 sentence overview of the document's main content]

**Relevance Score**: [High/Medium/Low] for [stated purpose]
**Key Insight**: [One sentence takeaway]
**Action**: [Read more / Archive / Deep dive / Extract tables]
```

### Quick Assessment (Research Paper)

```markdown
## Paper: [Title]

**Metadata**
- Authors: [List]
- Year: [Publication Year]
- Venue: [Conference/Journal]
- Citations: [Count if available]
- DOI/ArXiv: [Link]

**Quick Summary**
[1-2 sentence overview of the paper's main contribution]

**Relevance Score**: [High/Medium/Low] for [current task]
**Key Insight**: [One sentence takeaway]
**Action**: [Read more / Archive / Deep dive]
```

## Technical Summary Templates

### Technical Summary (Research Paper)

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

### Technical Summary (General)

For technical documents and reports:

```markdown
## Technical Summary: [Document Title]

### Purpose
[What is this document for?]

### Key Components
1. [Component/Section 1]: [Description]
2. [Component/Section 2]: [Description]
3. [Component/Section 3]: [Description]

### Technical Details
- **Architecture/Design**: [Overview]
- **Requirements**: [Key requirements if applicable]
- **Dependencies**: [External dependencies]

### Data/Metrics
[Key numbers, performance data, or specifications]

### Conclusions
[Main takeaways]

### Action Items
- [What to do with this information]
```

## Financial Document Templates

### Financial Document (Fund Card/Factsheet)

For fund cards, factsheets, and investment summaries:

```markdown
## Fund Analysis: [Fund Name]

### Fund Overview
- **Fund Type**: [Equity/Bond/Mixed/ETF/etc.]
- **Manager**: [Asset Manager Name]
- **Inception Date**: [Date]
- **Currency**: [Base currency]
- **ISIN**: [If available]

### Performance Metrics
| Period | Fund Return | Benchmark | Difference |
|--------|-------------|-----------|------------|
| YTD | [%] | [%] | [%] |
| 1Y | [%] | [%] | [%] |
| 3Y | [%] | [%] | [%] |
| 5Y | [%] | [%] | [%] |

### Key Statistics
- **NAV**: [Value and date]
- **AUM**: [Assets under management]
- **TER**: [Total Expense Ratio]
- **Volatility**: [Standard deviation]
- **Sharpe Ratio**: [If available]

### Portfolio Composition
**Top Holdings**:
1. [Holding 1] - [%]
2. [Holding 2] - [%]
3. [Holding 3] - [%]

**Sector Allocation**:
- [Sector 1]: [%]
- [Sector 2]: [%]
- [Sector 3]: [%]

**Geographic Allocation**:
- [Region 1]: [%]
- [Region 2]: [%]

### Risk Profile
- **Risk Level**: [1-7 scale or description]
- **Benchmark**: [Index name]
- **Investment Horizon**: [Recommended period]

### Key Observations
1. [Observation about performance]
2. [Observation about composition]
3. [Observation about risk/opportunity]

### Source
- **Document**: [Filename]
- **Date**: [Report date]
```

### Financial Document (Prospectus)

For fund prospectuses and offering documents:

```markdown
## Prospectus Analysis: [Fund/Product Name]

### Fund Structure
- **Legal Form**: [SICAV/FCP/UCITS/etc.]
- **Domicile**: [Country]
- **Regulator**: [Regulatory body]
- **Custodian**: [Bank name]

### Investment Objective
[Stated investment objective]

### Investment Policy
- **Asset Classes**: [What the fund invests in]
- **Geographic Focus**: [Regions/countries]
- **Restrictions**: [Key limitations]

### Fee Structure
| Fee Type | Amount |
|----------|--------|
| Management Fee | [%] |
| Performance Fee | [% and hurdle] |
| Entry Fee | [%] |
| Exit Fee | [%] |
| TER | [%] |

### Risk Factors
1. [Major risk 1]
2. [Major risk 2]
3. [Major risk 3]

### Key Dates
- **Valuation**: [Frequency]
- **Subscription**: [Deadlines/process]
- **Redemption**: [Notice period]

### Important Notes
[Critical information for investors]
```

## General Report Templates

### General Report

For business reports, analysis documents, and general PDFs:

```markdown
## Report Analysis: [Title]

### Document Overview
- **Type**: [Annual Report / Analysis / Study / White Paper / etc.]
- **Author/Organization**: [Source]
- **Date**: [Publication date]
- **Audience**: [Intended readers]

### Executive Summary
[2-3 sentence overview of the report's main message]

### Key Sections
1. **[Section 1 Title]**: [Brief description of content]
2. **[Section 2 Title]**: [Brief description of content]
3. **[Section 3 Title]**: [Brief description of content]

### Main Findings
1. [Finding 1 with supporting data]
2. [Finding 2 with supporting data]
3. [Finding 3 with supporting data]

### Data Highlights
| Metric | Value | Context |
|--------|-------|---------|
| [Metric 1] | [Value] | [Comparison/benchmark] |
| [Metric 2] | [Value] | [Comparison/benchmark] |

### Recommendations (if present)
1. [Recommendation 1]
2. [Recommendation 2]

### Relevance Assessment
- **For Current Task**: [How does this relate to what we're doing?]
- **Action Items**: [What should we do with this information?]
```

### Executive Summary (Non-Technical)

For stakeholder communication:

```markdown
## Executive Summary: [Title]

**What This Document Is**
[One sentence describing the document type and purpose]

**What They Found/Did**
[Plain language explanation of main content]

**Why It Matters**
[Significance and impact for the reader]

**Key Numbers**
- [Most important metric]: [Value]
- [Second important metric]: [Value]
- [Third important metric]: [Value]

**Bottom Line**
[One sentence practical implication or recommendation]

**Next Steps**
[What action to take based on this document]
```

## Critical Analysis Templates

### Critical Analysis (Research Paper)

For deep evaluation of academic papers:

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

### Critical Analysis (General Document)

For evaluating any document's quality and reliability:

```markdown
## Critical Analysis: [Document Title]

### Source Credibility
- **Organization**: [Reputation assessment]
- **Authors**: [Qualifications if known]
- **Methodology**: [How was data gathered?]
- **Date**: [How current is this?]

### Strengths
1. [Strong point 1]
2. [Strong point 2]

### Weaknesses/Gaps
1. [Missing information]
2. [Potential bias]
3. [Outdated data]

### Data Quality
- [ ] Sources cited?
- [ ] Methodology explained?
- [ ] Numbers verifiable?
- [ ] Assumptions stated?

### Alternative Perspectives
[What viewpoints might be missing?]

### Reliability Assessment
**Overall Confidence**: [High/Medium/Low]
**Reason**: [Why this rating]

### Usage Recommendations
[How should this document be used given its limitations?]
```

## Literature Review Templates

### Literature Review Synthesis

For comparing multiple papers:

```markdown
## Literature Review: [Topic]

**Papers Analyzed**: [Count]
**Date Range**: [Years covered]
**Key Authors**: [Frequently appearing authors]

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

### Practical Implications
[What does this mean for our work?]
```

## Quality Assessment Checklists

### Paper Credibility Evaluation

- [ ] **Venue**: Top-tier conference/journal?
- [ ] **Authors**: Recognized researchers?
- [ ] **Citations**: Highly cited? (if metadata available)
- [ ] **Reproducibility**: Code/data available?
- [ ] **Methodology**: Sound experimental design?
- [ ] **Results**: Statistically significant?
- [ ] **Peer Review**: Rigorous venue?

### Red Flags

- Unrealistic claims without evidence
- Missing experimental details
- No comparison to baselines
- Cherry-picked results
- Lack of ablation studies
- Unclear methodology
- Irreproducible experiments

### Financial Document Quality Check

- [ ] **Source**: Reputable institution?
- [ ] **Date**: Current data?
- [ ] **Audit**: Audited figures?
- [ ] **Completeness**: All required disclosures?
- [ ] **Consistency**: Numbers add up?
- [ ] **Benchmark**: Appropriate comparison?

## Template Selection Guide

| Document Type | Quick | Technical | Domain-Specific | Critical |
|---------------|-------|-----------|-----------------|----------|
| Research Paper | Quick Assessment (Research) | Technical Summary (Research) | - | Critical Analysis (Research) |
| Fund Card | Quick Assessment (Universal) | - | Financial Document (Fund) | - |
| Prospectus | Quick Assessment (Universal) | - | Financial Document (Prospectus) | Critical Analysis (General) |
| Technical Report | Quick Assessment (Universal) | Technical Summary (General) | - | Critical Analysis (General) |
| Business Report | Quick Assessment (Universal) | General Report | - | Critical Analysis (General) |
| Legal Document | Quick Assessment (Universal) | - | [Use Legal template if created] | Critical Analysis (General) |
