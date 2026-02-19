# Image Generator Plugin

Generate and edit images using Google's Gemini API directly from Claude Code.

## Requirements

- `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable
- Python packages: `google-genai`, `pillow`

## Installation

```bash
pip install google-genai pillow
```

## Commands

| Command | Description |
|---------|-------------|
| `/image-generator:generate <prompt>` | Generate an image from text |
| `/image-generator:edit <path> <instructions>` | Edit an existing image |

## Examples

```
/image-generator:generate A professional infographic about AI agents, dark theme, 9:16 portrait, 2K
/image-generator:generate A kawaii sticker of a cat programmer
/image-generator:edit ./photo.jpg Remove the background and add a gradient
```

## Style Presets

The CLI script supports `--style` for consistent visual styles:

| Style | Description |
|-------|-------------|
| `notebooklm` | Light, clean, Google Material Design with soft cards and whitespace |
| `dark` | Dark navy/charcoal with teal/coral/gold accents |
| `technical` | Architecture diagram style with labeled boxes and arrows |
| `sticker` | Kawaii-style bold outlines, cel-shading, white background |

```bash
python scripts/generate.py "Memory system architecture" --style notebooklm --aspect 9:16 --size 2K --png
python scripts/generate.py "AI agent workflow" --style dark --aspect 16:9 --size 2K
```

## Capabilities

- **Text-to-image**: Generate from detailed prompts
- **Image editing**: Modify existing images with natural language
- **Multi-turn refinement**: Iteratively improve via chat
- **Multi-reference**: Combine up to 14 input images
- **Custom dimensions**: 10 aspect ratios, 3 resolution tiers (1K-4K)
- **Search grounding**: Generate based on real-time web data
- **Style presets**: NotebookLM, dark, technical, sticker
- **Dual output**: Save as both JPEG and PNG with `--png` flag

## Model

Uses `gemini-3-pro-image-preview` (Google Gemini 3 Pro) for all generation.
Outputs JPEG by default with SynthID watermarks.

## Known Gotchas

- **Gemini Image ≠ PIL Image**: `part.as_image().save()` does NOT support `format=` kwarg.
  Always route through PIL for PNG conversion.
- **JPEG default**: Gemini always returns JPEG. If you save as `.png` directly with
  Gemini's save, you get a JPEG file with a PNG extension. Use PIL instead.
- **Large prompts work better**: For infographics, provide detailed layout structure
  (sections, columns, colors, flow direction) rather than vague descriptions.

## CLI Script

```bash
python scripts/generate.py "A sunset over mountains" --aspect 16:9 --size 2K
python scripts/generate.py "System diagram" --style technical --png -o diagram.jpg
python scripts/generate.py "Add rain" --input photo.jpg -o photo_rain.jpg
```
