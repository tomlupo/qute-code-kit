# Document Analysis Workflows

Step-by-step workflows for different document types and analysis scenarios.

## Universal Document Workflow

Use this workflow for any PDF document.

### Step 1: Initial Assessment

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

# 1.1 Get metadata (always first - minimal cost)
python $PDF_SKILL/get_metadata.py <document.pdf>

# 1.2 Classify document type
python $PDF_SKILL/classify_document.py <document.pdf> "research,report,financial,legal,technical"
```

**Decision Point**: Based on classification, choose the appropriate workflow below.

### Step 2: Quick Assessment (Pass 1)

```bash
# Extract first 1-2 pages
python $PDF_SKILL/extract_text.py <document.pdf> --page 0
python $PDF_SKILL/extract_text.py <document.pdf> --page 1  # if needed
```

**Output**: Apply **Quick Assessment (Universal)** template from `templates.md`

**Decision Point**:
- Relevance Low → Archive, move to next document
- Relevance Medium → Continue to Pass 2
- Relevance High → Continue to Pass 2 or 3

### Step 3: Deep Analysis (Pass 2)

Based on document type:

| Type | Focus Actions |
|------|---------------|
| Research | Extract methodology, results sections |
| Financial | Extract all tables |
| Technical | Extract diagrams, specifications |
| General | Extract key sections |

```bash
# For financial documents
python $PDF_SKILL/extract_tables.py <document.pdf>

# For documents with diagrams
python $PDF_SKILL/extract_images.py <document.pdf> --output ./figures/

# For NLP insights
python $PDF_SKILL/advanced_analysis.py <document.pdf>
```

**Output**: Apply appropriate **Technical Summary** or **Domain-Specific** template

### Step 4: Critical Analysis (Pass 3, if needed)

Full document reading for high-priority documents only.

```bash
# Full text extraction (use sparingly)
python $PDF_SKILL/extract_text.py <document.pdf> --output full_text.txt
```

**Output**: Apply **Critical Analysis** template

### Step 5: Save Results

Always save summaries to files:
```
docs/papers/summaries/<document-slug>-summary.md
```

---

## Research Paper Workflow

For academic papers with standard structure (Abstract, Introduction, Methods, Results, Discussion).

### Pass 1: Quick Assessment (5-10 min)

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

# Get metadata
python $PDF_SKILL/get_metadata.py paper.pdf

# Read abstract and introduction
python $PDF_SKILL/extract_text.py paper.pdf --page 0
python $PDF_SKILL/extract_text.py paper.pdf --page 1
```

**Questions to answer**:
1. What problem does this paper solve?
2. What is the main contribution?
3. Is this relevant to our current task?

**Output**: Quick Assessment (Research Paper) template

**Decision**:
- Not relevant → Archive
- Relevant → Continue to Pass 2

### Pass 2: Technical Summary (20-30 min)

```bash
# Extract methodology (typically pages 3-6)
python $PDF_SKILL/extract_text.py paper.pdf --page 3
python $PDF_SKILL/extract_text.py paper.pdf --page 4

# Extract results section (typically pages 6-10)
python $PDF_SKILL/extract_text.py paper.pdf --page 6
python $PDF_SKILL/extract_text.py paper.pdf --page 7

# Extract key figures
python $PDF_SKILL/extract_images.py paper.pdf --output ./figures/

# NLP analysis for key entities and phrases
python $PDF_SKILL/advanced_analysis.py paper.pdf
```

**Output**: Technical Summary (Research Paper) template

### Pass 3: Critical Analysis (30-60 min, if needed)

For papers critical to implementation:

```bash
# Full extraction
python $PDF_SKILL/extract_text.py paper.pdf --output paper_full.txt
```

**Focus on**:
- Experimental setup details
- Hyperparameters and settings
- Code/data availability
- Limitations acknowledged
- Related work for further reading

**Output**: Critical Analysis (Research Paper) template

---

## Financial Document Workflow

For fund cards, factsheets, prospectuses, and investment documents.

### Step 1: Identify Document Type

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

# Get metadata
python $PDF_SKILL/get_metadata.py fund_doc.pdf

# Classify
python $PDF_SKILL/classify_document.py fund_doc.pdf "fund_card,factsheet,prospectus,annual_report,kiid"
```

### Step 2: Extract Key Data

**Tables are critical for financial documents**:

```bash
# Extract all tables
python $PDF_SKILL/extract_tables.py fund_doc.pdf --output tables.json

# First page overview
python $PDF_SKILL/extract_text.py fund_doc.pdf --page 0
```

### Step 3: Identify Key Metrics

Look for in extracted tables:
- NAV (Net Asset Value)
- Returns (YTD, 1Y, 3Y, 5Y, Since Inception)
- TER (Total Expense Ratio)
- AUM (Assets Under Management)
- Top Holdings
- Sector/Geographic allocation
- Risk indicators (volatility, Sharpe ratio)

### Step 4: Apply Template

- Fund Card → **Financial Document (Fund Card/Factsheet)** template
- Prospectus → **Financial Document (Prospectus)** template

### Example: Rockbridge Fund Card Analysis

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"
PDF="temp/12_2025_rockbridge-akcji-globalnych-karta-funduszu.pdf"

# Step 1: Metadata
python $PDF_SKILL/get_metadata.py "$PDF"

# Step 2: Classification
python $PDF_SKILL/classify_document.py "$PDF" "fund_card,prospectus,factsheet"

# Step 3: Tables (key performance data)
python $PDF_SKILL/extract_tables.py "$PDF" --output tables.json

# Step 4: First page overview
python $PDF_SKILL/extract_text.py "$PDF" --page 0

# Step 5: Apply Financial Document (Fund Card) template
```

---

## Technical Report Workflow

For specifications, requirements documents, design documents.

### Step 1: Initial Assessment

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

python $PDF_SKILL/get_metadata.py report.pdf
python $PDF_SKILL/classify_document.py report.pdf "specification,requirements,design,architecture,manual"
```

### Step 2: Executive Summary

```bash
# First 2-3 pages usually contain executive summary
python $PDF_SKILL/extract_text.py report.pdf --page 0
python $PDF_SKILL/extract_text.py report.pdf --page 1
```

### Step 3: Technical Details

```bash
# Extract diagrams and figures
python $PDF_SKILL/extract_images.py report.pdf --output ./diagrams/

# Extract tables (if data-heavy)
python $PDF_SKILL/extract_tables.py report.pdf
```

### Step 4: Apply Template

Use **Technical Summary (General)** template.

---

## Literature Review Workflow

For analyzing multiple papers on a topic.

### Phase 1: Discovery (Low Context)

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

# For each paper:
for pdf in docs/papers/*.pdf; do
    echo "=== $pdf ==="
    python $PDF_SKILL/get_metadata.py "$pdf"
    python $PDF_SKILL/extract_text.py "$pdf" --page 0
done
```

**Output**: Quick Assessment for each paper
**Save**: To `docs/papers/summaries/<paper>-quick.md`
**Rank**: By relevance to research question

### Phase 2: Selective Deep Dive (Medium Context)

Select top 3-5 papers for deeper analysis:

```bash
# For each selected paper:
python $PDF_SKILL/extract_text.py paper.pdf --page 0  # Abstract
python $PDF_SKILL/extract_text.py paper.pdf --page 3  # Methods
python $PDF_SKILL/extract_text.py paper.pdf --page 6  # Results
python $PDF_SKILL/advanced_analysis.py paper.pdf
```

**Output**: Technical Summary for each
**Save**: To `docs/papers/summaries/<paper>-technical.md`

### Phase 3: Synthesis

Build synthesis document:

```markdown
## Literature Review: [Topic]

### Papers Analyzed
1. [Paper 1] - [Key contribution]
2. [Paper 2] - [Key contribution]
...

### Common Themes
- [Theme 1]
- [Theme 2]

### Conflicting Findings
- [Disagreement 1]

### Gaps Identified
- [Gap 1]
```

**Save**: To `docs/papers/literature-review-<topic>.md`

### Context Budget Management

```markdown
**Context Check** before each phase:

Phase 1: ~20% context budget
Phase 2: ~50% context budget
Phase 3: ~30% context budget

If approaching limit:
- Save current state to files
- Summarize aggressively
- Ask user which papers to prioritize
```

---

## Multi-Document Comparison Workflow

For comparing similar documents (e.g., multiple fund cards).

### Step 1: Parallel Extraction

```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"

# Extract tables from all documents
for pdf in fund*.pdf; do
    name=$(basename "$pdf" .pdf)
    python $PDF_SKILL/extract_tables.py "$pdf" --output "${name}_tables.json"
done
```

### Step 2: Normalize Metrics

Create comparison table with standardized metrics:

```markdown
| Fund | NAV | 1Y Return | TER | Volatility |
|------|-----|-----------|-----|------------|
| Fund A | 100.5 | 12.3% | 1.2% | 15.2% |
| Fund B | 98.2 | 10.1% | 0.9% | 12.8% |
```

### Step 3: Similarity Analysis (Optional)

```bash
python $PDF_SKILL/calculate_similarity.py fund1.pdf fund2.pdf
```

---

## Error Handling Workflows

### Image-Based PDF Detected

If `extract_text.py` returns empty or garbled text:

```bash
# Check if image-based
python $PDF_SKILL/extract_text.py document.pdf --page 0

# If empty/garbled, extract as images
python $PDF_SKILL/extract_images.py document.pdf --output ./pages/

# Report to user
echo "Document appears to be image-based (scanned).
Options:
1. Use external OCR (tesseract)
2. Read the PDF manually using the Read tool
3. Skip this document"
```

### Encrypted PDF

```bash
# get_metadata.py will show is_encrypted: true
python $PDF_SKILL/get_metadata.py document.pdf
```

If encrypted, report to user that password is needed.

### No Tables Found

```bash
# extract_tables.py returns empty tables array
python $PDF_SKILL/extract_tables.py document.pdf

# If no tables, fall back to text extraction
python $PDF_SKILL/extract_text.py document.pdf --page 0
```

---

## Context Management Best Practices

### Before Reading

1. Check for existing summaries in `docs/papers/summaries/`
2. Get metadata first (minimal cost)
3. Classify document to pick right workflow

### During Reading

1. Extract pages incrementally, not all at once
2. Summarize each section before moving to next
3. Save summaries to files frequently

### After Reading

1. Always save final summary to file
2. Update paper index if maintaining one
3. Clear temporary extractions

### Warning Signs

```markdown
**Context Warning**: ~80% used

**Actions**:
1. Save current summaries to files
2. Ask user: "Continue with remaining documents?"
3. Offer: "Read remaining with Pass 1 only?"
```

---

## Quick Reference: When to Use Each Workflow

| Scenario | Workflow |
|----------|----------|
| Single PDF, unknown type | Universal Document Workflow |
| Academic paper | Research Paper Workflow |
| Fund card, factsheet | Financial Document Workflow |
| Technical specification | Technical Report Workflow |
| Multiple papers on topic | Literature Review Workflow |
| Comparing similar docs | Multi-Document Comparison |
