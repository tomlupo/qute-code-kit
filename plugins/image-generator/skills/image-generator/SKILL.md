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
| Output Format | JPEG (.jpg) | Convert to PNG if needed |

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
        image.save("output.jpg")
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

## Prompting Best Practices

### Photorealistic
Include camera details: lens type, lighting, angle, mood.
> "A photorealistic close-up portrait, 85mm lens, soft golden hour light, shallow depth of field"

### Stylized Art
Specify style explicitly:
> "A kawaii-style sticker of a happy red panda, bold outlines, cel-shading, white background"

### Text in Images
Be explicit about font style and placement:
> "Create a logo with text 'Daily Grind' in clean sans-serif, black and white, coffee bean motif"

### Infographics
Describe layout, sections, color scheme, and data:
> "Professional infographic, dark background, teal/coral accents, 9:16 portrait, sections for: [list topics]"

### Product Mockups
Describe lighting setup and surface:
> "Studio-lit product photo on polished concrete, three-point softbox setup, 45-degree angle"

## Critical Notes

- **File format**: Gemini returns JPEG by default. Always use `.jpg` extension.
- **PNG conversion**: Use `img.save("output.png", format="PNG")` if PNG is needed.
- **SynthID**: All generated images include invisible SynthID watermarks.
- **Dependencies**: `pip install google-genai pillow`
- **Model**: Always use `gemini-3-pro-image-preview` unless user specifies otherwise.

## Workflow: Generate → Review → Refine

1. Write a Python script using the API pattern above
2. Run it to generate the initial image
3. View the output with the Read tool
4. If refinement needed, use multi-turn chat or edit the prompt
5. Save final output to user's desired location
