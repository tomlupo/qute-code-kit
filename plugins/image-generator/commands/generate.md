---
name: generate
description: Generate an image from a text prompt using Gemini
user_invocable: true
arguments:
  - name: prompt
    description: Description of the image to generate
    required: true
---

Generate an image using the Gemini API.

## Instructions

1. Check that `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set in the environment
2. Write a Python script to `/tmp/gemini_generate.py` using the image-generator skill's API pattern
3. Use the user's prompt as the image description
4. Default settings: 1K resolution, 1:1 aspect ratio
5. If the user specifies dimensions (e.g., "wide", "portrait", "16:9"), set the appropriate aspect ratio
6. If the user specifies quality (e.g., "high res", "4K"), set the appropriate resolution
7. Save output to a sensible location (current directory or user-specified path) with `.jpg` extension
8. Run the script and display the resulting image using the Read tool
9. Ask if refinements are needed

## Argument Parsing

- `$ARGUMENTS` contains the full prompt text
- Extract any aspect ratio hints: "wide" → 16:9, "portrait" → 9:16, "square" → 1:1, "ultrawide" → 21:9
- Extract any resolution hints: "high res" or "4K" → 4K, "preview" → 1K
- Everything else is the image prompt

Generate the image for: $ARGUMENTS
