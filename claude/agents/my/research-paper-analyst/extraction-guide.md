# PDF Extraction Guide

How to use pdf-skill scripts for document extraction and analysis.

## Scripts Location

All scripts are located at: `claude/skills/my/pdf-skill/scripts/`

Set this variable for convenience:
```bash
PDF_SKILL="claude/skills/my/pdf-skill/scripts"
```

## Core Extraction Scripts

### Text Extraction (`extract_text.py`)

Extract text content from PDF files.

```bash
# Full document (USE SPARINGLY - high token cost)
python $PDF_SKILL/extract_text.py document.pdf

# Single page (0-indexed) - PREFERRED
python $PDF_SKILL/extract_text.py document.pdf --page 0

# Save to file
python $PDF_SKILL/extract_text.py document.pdf --page 0 --output abstract.txt
```

**Page Range Patterns**:
| Goal | Command |
|------|---------|
| Abstract/Intro | `--page 0` (first page) |
| First 2 pages | Run twice: `--page 0`, `--page 1` |
| Methodology (typical) | `--page 3` to `--page 6` |
| Conclusions (typical) | Last 2 pages |

**Output**: Plain text, printed to stdout or saved to file.

### Table Extraction (`extract_tables.py`)

Extract tables as structured JSON data.

```bash
# All tables from document
python $PDF_SKILL/extract_tables.py document.pdf

# Tables from specific page (0-indexed)
python $PDF_SKILL/extract_tables.py document.pdf --page 0

# Save as JSON
python $PDF_SKILL/extract_tables.py document.pdf --output tables.json

# Save as CSV (creates separate files per table)
python $PDF_SKILL/extract_tables.py document.pdf --output tables.csv --format csv
```

**Output JSON Structure**:
```json
{
  "success": true,
  "total_tables": 3,
  "tables": [
    {
      "table_number": 1,
      "rows": 10,
      "columns": 4,
      "column_names": ["Date", "NAV", "Return", "Benchmark"],
      "data": [["2024-01", "100.5", "2.3%", "2.1%"], ...]
    }
  ]
}
```

**Best For**: Financial documents, fund cards, data-heavy reports.

### Image Extraction (`extract_images.py`)

Extract images and diagrams from PDF.

```bash
# List images (no download)
python $PDF_SKILL/extract_images.py document.pdf

# Extract from specific page
python $PDF_SKILL/extract_images.py document.pdf --page 0

# Save to directory
python $PDF_SKILL/extract_images.py document.pdf --output ./extracted_images/
```

**Output**: Creates PNG files in output directory with naming pattern `page_N_img_M.png`.

**Best For**: Research papers with diagrams, presentations, visual documents.

### Metadata Extraction (`get_metadata.py`)

Get document metadata without reading content.

```bash
python $PDF_SKILL/get_metadata.py document.pdf
python $PDF_SKILL/get_metadata.py document.pdf --output metadata.json
```

**Output JSON Structure**:
```json
{
  "success": true,
  "file_info": {
    "name": "document.pdf",
    "size_bytes": 1234567,
    "created_timestamp": 1234567890.0,
    "modified_timestamp": 1234567890.0
  },
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "subject": "Subject",
    "keywords": "keyword1, keyword2",
    "creator": "Application",
    "producer": "PDF Library",
    "creation_date": "D:20240101120000",
    "modification_date": "D:20240115120000"
  },
  "document_info": {
    "page_count": 25,
    "is_encrypted": false,
    "is_pdf": true
  }
}
```

**Always run first** - low cost, provides page count and basic info.

## Analysis Scripts

### Document Classification (`classify_document.py`)

Classify document into categories using zero-shot classification.

```bash
# Standard categories
python $PDF_SKILL/classify_document.py document.pdf "research,report,financial,legal,technical"

# Custom categories
python $PDF_SKILL/classify_document.py document.pdf "fund_card,prospectus,annual_report,factsheet"

# Save results
python $PDF_SKILL/classify_document.py document.pdf "research,report" --output classification.json
```

**Output**:
```json
{
  "success": true,
  "labels": ["financial", "report", "research", "legal", "technical"],
  "scores": [0.85, 0.72, 0.45, 0.12, 0.08],
  "top_label": "financial",
  "top_score": 0.85
}
```

**Use for**: Picking the right analysis template.

### Advanced Analysis (`advanced_analysis.py`)

NLP analysis: readability, entities, key phrases.

```bash
python $PDF_SKILL/advanced_analysis.py document.pdf
python $PDF_SKILL/advanced_analysis.py document.pdf --output analysis.json
```

**Output**:
```json
{
  "success": true,
  "text_statistics": {
    "total_characters": 50000,
    "total_words": 8500,
    "meaningful_words": 5000,
    "total_sentences": 400,
    "total_paragraphs": 50
  },
  "readability_metrics": {
    "avg_sentence_length": 21.25,
    "avg_word_length": 5.2,
    "flesch_kincaid_grade": 12.5
  },
  "pos_distribution": {
    "NN": 1200,
    "VB": 800,
    "JJ": 600
  },
  "top_noun_phrases": [
    {"phrase": "portfolio management", "count": 15},
    {"phrase": "risk assessment", "count": 12}
  ],
  "entity_types": {
    "PERSON": 5,
    "ORG": 25,
    "GPE": 10,
    "DATE": 30,
    "OTHER": 15
  }
}
```

**Note**: Analyzes first 10k characters for performance. Higher token cost.

### Language Detection (`detect_languages.py`)

Detect languages in document.

```bash
python $PDF_SKILL/detect_languages.py document.pdf
```

**Use for**: Multi-language documents, choosing appropriate NLP models.

### Document Similarity (`calculate_similarity.py`)

Compare two documents for similarity.

```bash
python $PDF_SKILL/calculate_similarity.py doc1.pdf doc2.pdf
```

**Use for**: Finding duplicate or related documents.

## Extraction Patterns by Document Type

### Research Papers

```bash
# Step 1: Metadata
python $PDF_SKILL/get_metadata.py paper.pdf

# Step 2: Abstract + Intro (Pass 1)
python $PDF_SKILL/extract_text.py paper.pdf --page 0
python $PDF_SKILL/extract_text.py paper.pdf --page 1

# Step 3: Key figures (if relevant)
python $PDF_SKILL/extract_images.py paper.pdf --output ./figures/

# Step 4: Full analysis (Pass 2, if needed)
python $PDF_SKILL/advanced_analysis.py paper.pdf
```

### Financial Documents (Fund Cards, Prospectuses)

```bash
# Step 1: Metadata
python $PDF_SKILL/get_metadata.py fund_card.pdf

# Step 2: Classification
python $PDF_SKILL/classify_document.py fund_card.pdf "fund_card,prospectus,factsheet,report"

# Step 3: Tables (key data!)
python $PDF_SKILL/extract_tables.py fund_card.pdf --output tables.json

# Step 4: First page overview
python $PDF_SKILL/extract_text.py fund_card.pdf --page 0
```

### Technical Reports

```bash
# Step 1: Metadata + Classification
python $PDF_SKILL/get_metadata.py report.pdf
python $PDF_SKILL/classify_document.py report.pdf "technical,specification,requirements,design"

# Step 2: Executive summary (usually page 0-1)
python $PDF_SKILL/extract_text.py report.pdf --page 0

# Step 3: Diagrams
python $PDF_SKILL/extract_images.py report.pdf --output ./diagrams/

# Step 4: NLP analysis
python $PDF_SKILL/advanced_analysis.py report.pdf
```

## Handling Image-Based PDFs

If `extract_text.py` returns empty or garbled text, the PDF may be image-based (scanned).

**Detection**:
```bash
# If this returns empty or very little text:
python $PDF_SKILL/extract_text.py document.pdf --page 0
```

**Alternatives**:
1. **Extract images**: `python $PDF_SKILL/extract_images.py document.pdf --output ./pages/`
2. **Use OCR externally**: `tesseract page.png output -l eng`
3. **Report to user**: "This appears to be a scanned document. OCR may be needed."

## Error Handling

All scripts return JSON with `success` field:

```json
// Success
{"success": true, "data": ...}

// Failure
{"success": false, "error": "Error message here"}
```

**Common errors**:
- `"No text content found in PDF"` - Image-based PDF
- `"Page N out of range"` - Invalid page number
- `"Error extracting tables"` - No tables or complex layout
- `"File not found"` - Check path

## Performance Considerations

| Script | Token Cost | When to Use |
|--------|------------|-------------|
| `get_metadata.py` | Minimal | Always first |
| `classify_document.py` | Low | After metadata |
| `extract_text.py --page N` | Low-Medium | Selective reading |
| `extract_text.py` (full) | High | Avoid if possible |
| `extract_tables.py` | Medium | Financial docs |
| `extract_images.py` | Low (metadata only) | Diagrams needed |
| `advanced_analysis.py` | High | Deep analysis |

**Rule**: Start cheap, go expensive only if needed.
