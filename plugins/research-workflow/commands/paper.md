# /research:paper

Read and extract key information from an academic paper.

## Usage

```
/research:paper <url|file> [--focus <aspect>]
```

## Arguments

- `<url|file>` - URL to paper (arXiv, SSRN, etc.) or local PDF path
- `--focus` - (Optional) Specific aspect to focus on: methods, results, architecture

## Behavior

1. **Fetch/Read the paper**
   - If URL: Use WebFetch to retrieve content
   - If PDF: Read and extract text

2. **Extract key information**:
   - Title and authors
   - Abstract
   - Key contributions
   - Methodology
   - Results
   - Relevance to current research

3. **Generate filename**
   - Format: `YYYY-MM-DD_<paper-slug>.md`

4. **Create paper notes** at `docs/research/papers/<filename>`:
   ```markdown
   # Paper: <title>

   **Date Read**: YYYY-MM-DD
   **Authors**: ...
   **Published**: YYYY, <venue>
   **URL**: <link>

   ## Abstract
   <original abstract>

   ## Key Contributions
   1. ...
   2. ...
   3. ...

   ## Methodology
   <!-- Summary of approach -->

   ## Key Results
   | Metric | Value | Baseline |
   |--------|-------|----------|
   | ... | ... | ... |

   ## Relevance to Our Research
   <!-- How does this apply to our work? -->

   ### Applicable Ideas
   - [ ] Idea 1: ...
   - [ ] Idea 2: ...

   ### Limitations for Our Use Case
   - ...

   ## Quotes
   > "Notable quote from paper" (p. X)

   ## References to Follow
   - [Ref 1]: ...
   - [Ref 2]: ...

   ## My Notes
   <!-- Personal observations and questions -->
   ```

5. **Update index.md**
   - Add entry under "Papers Reviewed"

## Example

```
/research:paper https://arxiv.org/abs/2301.00001 --focus methods

# Output:
📄 Reading paper: "Attention Is All You Need"

✅ Paper notes created: docs/research/papers/2026-01-13_attention-is-all-you-need.md

Extracted:
  - Title: Attention Is All You Need
  - Authors: Vaswani et al.
  - Key contributions: 3 identified
  - Methodology: Transformer architecture

Added to research index under "Papers Reviewed"
```

## Supported Sources

- arXiv (arxiv.org)
- SSRN (ssrn.com)
- OpenReview (openreview.net)
- Local PDF files
- Google Scholar links
- Direct publisher links (IEEE, ACM, etc.)
