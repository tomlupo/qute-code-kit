---
name: pdf-reader
description: PDF document processing with text extraction, image extraction, table recognition, and NLP analysis. Use when you need to extract content from PDF files, analyze document structure, or process PDF content (text, images, tables, entities, summaries, keywords, classification).
---

# PDF Reader

Extract and analyze PDF content: text, images, tables, metadata, plus NLP capabilities (entity recognition, summarization, keyword extraction, document classification).

## Scripts

| Script | Purpose |
|--------|---------|
| `extract_text.py` | Text extraction (full or page range) |
| `extract_images.py` | Image extraction with base64 encoding |
| `extract_tables.py` | Structured table extraction (CSV/JSON/DataFrame) |
| `analyze_content.py` | NLP analysis: `entities`, `summary`, or `keywords` mode |
| `get_metadata.py` | Title, author, dates, page count |
| `classify_document.py` | Zero-shot document classification |
| `calculate_similarity.py` | Semantic similarity between two PDFs |
| `detect_languages.py` | Language detection |
| `advanced_analysis.py` | Detailed linguistic analysis |

## Common Workflows

### Extract and Analyze
```bash
python scripts/extract_text.py document.pdf
python scripts/analyze_content.py document.pdf summary
python scripts/analyze_content.py document.pdf entities
```

### Extract Tables
```bash
python scripts/extract_tables.py report.pdf
# Output: structured table data convertible to CSV/JSON
```

### Batch Processing
```bash
for f in *.pdf; do
  python scripts/extract_text.py "$f"
  python scripts/get_metadata.py "$f"
done
```

## Handling Image-Based PDFs

Some PDFs contain scanned images instead of selectable text.

**Detection**: If `extract_text.py` returns empty or minimal text (<100 chars), the PDF is likely image-based.

**Workflow**:
1. Attempt text extraction
2. If result is empty/minimal — notify user it's image-based
3. Offer image extraction: `python scripts/extract_images.py document.pdf --output ./images`
4. Suggest OCR alternatives: EasyOCR, Google Cloud Vision, Amazon Textract, Adobe Acrobat

```
PDF → extract_text() → meaningful? → YES → process normally
                                   → NO  → notify user → extract images or suggest OCR
```

## Dependencies

```bash
pip install -r requirements.txt
```

Key packages: PyMuPDF (fitz), pdfminer.six, tabula-py, spacy, transformers, sentence-transformers.

## Performance Notes

- **Large PDFs (1000+ pages)**: Process page ranges, not the whole document
- **Scanned PDFs**: Text extraction works on text-based PDFs only; scanned PDFs need OCR
- **GPU**: Advanced analysis features use CUDA if available

## References

See `references/api_reference.md` for complete API documentation.
