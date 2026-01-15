# Workflow Integration

## Pre-Implementation Research

Before starting development:
- "What papers describe similar approaches?"
- "What's the theoretical foundation for this method?"
- "What hyperparameters do papers typically use?"
- "Are there known failure modes documented?"

## Methodology Validation

During implementation:
- "How did paper X implement this component?"
- "What preprocessing steps are standard?"
- "What evaluation metrics should we use?"
- "How do we compare against baselines?"

## Results Interpretation

After experiments:
- "Are our results consistent with literature?"
- "How do our metrics compare to published work?"
- "What papers achieved similar performance?"
- "What could explain the differences?"

## Literature Review Generation

For documentation:
- Generate related work sections
- Compile comprehensive bibliographies
- Create comparison tables across papers
- Summarize state-of-the-art approaches

## Paper Discovery Strategies

### File Organization Patterns

```bash
# Common paper storage structures
docs/knowledge/papers/
├── by-topic/
│   ├── machine-learning/
│   ├── nlp/
│   └── computer-vision/
├── by-year/
│   ├── 2024/
│   └── 2023/
├── by-author/
├── by-conference/
│   ├── neurips/
│   ├── icml/
│   └── cvpr/
└── reading-notes/
```

### Smart Search

```bash
# Find papers by topic
find docs/knowledge/papers -name "*.pdf" -o -name "*.md" | xargs grep -l "transformer"

# Search by year in filename
find docs/knowledge/papers -name "*2024*"

# Full-text search in PDFs
pdfgrep -r "attention mechanism" docs/knowledge/papers/

# Search in markdown notes
grep -r "key contribution" docs/knowledge/papers/ --include="*.md"
```

## Error Handling

### Missing Papers

```markdown
❌ **Paper Not Found**: "Transformer Architecture Survey"

**Search Results**: No exact match found

**Similar Papers Available**:
- "Attention is All You Need" (2017) - Original transformer paper
- "BERT: Pre-training of Deep Bidirectional Transformers" (2018)
- "The Illustrated Transformer" (2018) - Tutorial

**Suggestion**: Would you like me to:
1. Search for this paper online?
2. Analyze one of the similar papers above?
3. Create a placeholder note for when you add it?
```

### Incomplete Metadata

```markdown
⚠️ **Limited Information Available**

**Paper**: [Filename]
**Issue**: PDF text extraction incomplete or markdown notes minimal

**What I Found**:
- Title: [If extractable]
- Partial abstract: [If available]

**Recommendations**:
1. Add structured markdown notes with metadata
2. Ensure PDF is text-searchable (not scanned image)
3. Add manual annotations in frontmatter
```

### Conflicting Information

```markdown
⚠️ **Conflicting Findings Detected**

**Topic**: [Subject]

**Paper A** (Smith et al., 2023):
- Finding: [Result A]
- Method: [Approach A]

**Paper B** (Jones et al., 2024):
- Finding: [Result B - contradicts A]
- Method: [Approach B]

**Analysis**:
- Possible reasons for discrepancy: [Methodology differences, datasets, etc.]
- More recent work suggests: [If available]
- Consensus view: [If identifiable]

**Recommendation**: [Which to trust and why]
```

## Best Practices

### Paper Organization Tips

For each paper, create a markdown note:

**Filename**: `author-year-short-title.md`

**Content**:
```markdown
---
title: "Full Paper Title"
authors: ["First Author", "Second Author"]
year: 2024
venue: "NeurIPS"
pdf: "../pdfs/author-2024.pdf"
arxiv: "2401.12345"
code: "https://github.com/author/repo"
tags: [machine-learning, transformers, nlp]
read_date: 2024-03-15
status: read  # to-read, reading, read
rating: 5  # 1-5 stars
---

## Summary
[Your summary]

## Key Contributions
1. [First contribution]
2. [Second contribution]

## Important Figures
- Figure 3: [Description and insights]

## Quotes
> "Important quote from paper"

## Personal Notes
[Your thoughts, questions, connections]

## Related Papers
- [[related-paper-1]]
- [[related-paper-2]]
```

### Efficient Reading Strategy

1. **First Pass**: Title, abstract, figures
2. **Second Pass**: Introduction, conclusion
3. **Third Pass**: Methods, results (if relevant)
4. **Deep Dive**: Full careful reading (only if critical)

### Note-Taking Template

```markdown
## Quick Notes: [Paper]

**TL;DR**: [One sentence]

**Why This Matters**: [Relevance]

**Key Idea**: [Main insight]

**Useful For**: [When to apply]

**Remember**: [Most important takeaway]
```
