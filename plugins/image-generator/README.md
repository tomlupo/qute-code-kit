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

## Capabilities

- **Text-to-image**: Generate from detailed prompts
- **Image editing**: Modify existing images with natural language
- **Multi-turn refinement**: Iteratively improve via chat
- **Multi-reference**: Combine up to 14 input images
- **Custom dimensions**: 10 aspect ratios, 3 resolution tiers (1K-4K)
- **Search grounding**: Generate based on real-time web data

## Model

Uses `gemini-3-pro-image-preview` (Google Gemini 3 Pro) for all generation.
Outputs JPEG by default with SynthID watermarks.

## CLI Script

A standalone script is included at `scripts/generate.py`:

```bash
python scripts/generate.py "A sunset over mountains" --aspect 16:9 --size 2K -o sunset.jpg
python scripts/generate.py "Add rain" --input photo.jpg -o photo_rain.jpg
```
