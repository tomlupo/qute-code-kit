---
name: image-generator
description: Generate and edit images using Google Gemini API. Use when the user asks to create images, infographics, logos, mockups, diagrams, or edit existing images.
---

# Image Generator (Gemini)

Generate and edit images using Google's Gemini API. Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable.

## When to Use

Use this skill when the user needs to:
- Generate images from text descriptions
- Create infographics, diagrams, or data visualizations
- Design logos, icons, or brand assets
- Create product mockups or social media graphics
- Edit or modify existing images
- Remove backgrounds or composite multiple images
- Iteratively refine an image through conversation

## Default Settings

| Setting | Default | Options |
|---------|---------|----------|
| Model | `gemini-3-pro-image-preview` | Always use Pro |
| Resolution | 1K | 1K, 2K, 4K |
| Aspect Ratio | 1:1 | 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 |
| Output Format | JPEG (.jpg) | Convert to PNG via PIL |

## Core API Pattern

```python
import os
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Your prompt here"],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
    ),
)

for part in response.parts:
    if part.text:
        print(part.text)
    elif part.inline_data:
        image = part.as_image()
        image.save("output.jpg")  # Always .jpg — Gemini returns JPEG
```

## Custom Resolution & Aspect Ratio

```python
config=types.GenerateContentConfig(
    response_modalities=['TEXT', 'IMAGE'],
    image_config=types.ImageConfig(
        aspect_ratio="16:9",  # Wide format
        image_size="2K"       # Higher resolution
    ),
)
```

## PNG Conversion (IMPORTANT)

Gemini's `part.as_image()` returns a Gemini Image object, NOT a PIL Image.
Its `.save()` method does NOT support `format=` kwargs. To get PNG:

```python
# WRONG — will crash with TypeError
image = part.as_image()
image.save("output.png", format="PNG")  # TypeError!

# CORRECT — save as JPEG first, then convert with PIL
image = part.as_image()
image.save("output.jpg")

from PIL import Image as PILImage
pil_img = PILImage.open("output.jpg")
pil_img.save("output.png", format="PNG")
```

Or in one step without intermediate file:

```python
import io
from PIL import Image as PILImage

for part in response.parts:
    if part.inline_data:
        pil_img = PILImage.open(io.BytesIO(part.inline_data.data))
        pil_img.save("output.jpg")  # JPEG
        pil_img.save("output.png")  # PNG (PIL auto-detects from extension)
```

## Editing Existing Images

```python
from PIL import Image

img = Image.open("input.png")
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Add a sunset to this scene", img],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
    ),
)
```

## Multi-Turn Refinement

```python
chat = client.chats.create(
    model="gemini-3-pro-image-preview",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
)

response = chat.send_message("Create a logo for 'Acme Corp'")
# Save first image...

response = chat.send_message("Make the text bolder and add a blue gradient")
# Save refined image...
```

## Multiple Reference Images (Up to 14)

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[
        "Create a group photo of these people in an office",
        Image.open("person1.png"),
        Image.open("person2.png"),
    ],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
    ),
)
```

## Google Search Grounding

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["Visualize today's weather in Tokyo as an infographic"],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        tools=[{"google_search": {}}]
    )
)
```

## Style Presets

Prepend these style directives to your prompt for consistent results:

### NotebookLM / Google Material (light, clean)
```
Create a clean, modern infographic in Google NotebookLM style — light #f8f9fa
background, soft rounded cards with subtle drop shadows, Google Material Design
aesthetic, clean sans-serif typography, muted pastel colors (soft blue, purple,
green, coral), generous whitespace, thin gray connecting lines with small labels.
NO dark backgrounds, NO heavy borders, NO neon colors.
```

### Dark Tech Infographic
```
Create a professional infographic with dark navy/charcoal background, modern
design aesthetic, clean typography, cohesive color palette (teal, coral, gold
accents on dark background). Sharp contrast, readable text, no clutter.
Think McKinsey report meets modern tech blog.
```

### Technical Architecture Diagram
```
Create a clean technical architecture diagram with a light background, clearly
labeled boxes connected by directional arrows, color-coded by component type,
legend in the corner. Professional engineering documentation style.
```

### Sticker / Icon
```
A kawaii-style sticker with bold outlines, cel-shading, white/transparent
background. Simple, bold, and instantly recognizable.
```

## Prompting Best Practices

### Photorealistic
Include camera details: lens type, lighting, angle, mood.
> "A photorealistic close-up portrait, 85mm lens, soft golden hour light, shallow depth of field"

### Text in Images
Be explicit about font style and placement:
> "Create a logo with text 'Daily Grind' in clean sans-serif, black and white, coffee bean motif"

### Infographics
Describe layout structure explicitly — sections, color scheme, columns, flow direction:
> "9:16 portrait infographic, 3-column layout (left/center/right), top-to-bottom flow, connecting arrows between cards"

### Product Mockups
Describe lighting setup and surface:
> "Studio-lit product photo on polished concrete, three-point softbox setup, 45-degree angle"

## Critical Notes

- **File format**: Gemini returns JPEG by default. Always save as `.jpg` first.
- **PNG conversion**: Use PIL (`from PIL import Image`), NOT Gemini's `.save(format=)` which doesn't exist.
- **SynthID**: All generated images include invisible SynthID watermarks.
- **Dependencies**: `pip install google-genai pillow`
- **Model**: Always use `gemini-3-pro-image-preview` unless user specifies otherwise.
- **Aspect ratios for infographics**: Use `9:16` for portrait posters, `16:9` for presentations.
- **Resolution**: Use `2K` for final output. `1K` for drafts/iteration. `4K` only when explicitly needed.

## Workflow: Generate → Review → Refine

1. Write a Python script using the core API pattern above
2. Apply a style preset if the user mentions a visual style
3. Run it to generate the initial image (save as .jpg)
4. Convert to .png with PIL if the user needs PNG
5. View the output with the Read tool
6. If refinement needed, adjust the prompt and regenerate
7. Save final output to user's desired location
