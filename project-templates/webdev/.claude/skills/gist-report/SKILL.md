---
name: gist-report
description: |
  Create a shareable HTML report and return a preview link.
  Use when the user says "create a report", "share as HTML", "make a gist report",
  "gist report", or wants to convert files/sessions to shareable HTML gists.
disable-model-invocation: true
allowed-tools: Bash
---

# Gist Report

Create a shareable HTML report and return a preview link.

## Usage Modes

### Mode 1: File Provided
If user provides a file path:
1. Read the file content
2. Convert to a styled HTML report:
   - For code files: syntax-highlighted HTML
   - For markdown: render to HTML
   - For data files (JSON, CSV, etc.): formatted/tabular HTML
   - For HTML files: use as-is
3. Create public gist and return preview link

### Mode 2: Description Provided
If user provides a description (not a file path):
1. Generate an HTML report based on the description
2. Use clean, readable styling (e.g., simple CSS, good typography)
3. Create public gist and return preview link

### Mode 3: No Arguments
If no specific input provided:
1. Generate an HTML report of the current conversation/session
2. Create public gist and return preview link

## Steps (all modes)
1. Generate or prepare HTML content
2. Save to a temporary file if needed
3. Run `gh gist create <file> --public` and capture the output URL
4. Extract USERNAME and GIST_ID from URL (format: https://gist.github.com/USERNAME/GIST_ID)
5. Construct preview link: `https://htmlpreview.github.io/?https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/FILENAME`
6. Return only the clickable preview link

## Styling Guidelines
- Include minimal embedded CSS for readability
- Clean typography (system fonts, good line height)
- Syntax highlighting for code blocks
- Responsive layout
