---
name: edit
description: Edit an existing image using Gemini
user_invocable: true
arguments:
  - name: instructions
    description: Path to the image and editing instructions
    required: true
---

Edit an existing image using the Gemini API.

## Instructions

1. Parse `$ARGUMENTS` to extract:
   - The **image path** (first argument or path-like token)
   - The **editing instructions** (remaining text)
2. Verify the image file exists using the Read tool
3. Write a Python script to `/tmp/gemini_edit.py` using the image-generator skill's editing pattern
4. Pass both the image and the editing instructions to the API
5. Save the edited image next to the original with a `_edited` suffix (e.g., `photo_edited.jpg`)
6. Run the script and display the result
7. Ask if further edits are needed

Edit the image: $ARGUMENTS
