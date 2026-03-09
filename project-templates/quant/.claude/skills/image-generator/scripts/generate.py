#!/usr/bin/env python3
"""Generate an image using Google Gemini API.

Usage:
    python generate.py "prompt" [--aspect RATIO] [--size SIZE] [--output PATH]

Examples:
    python generate.py "A sunset over mountains" --aspect 16:9 --size 2K
    python generate.py "Logo for TechCo" --output logo.jpg
    python generate.py "Edit: add clouds" --input photo.jpg --output photo_edited.jpg
    python generate.py "Dark infographic about AI" --aspect 9:16 --size 2K --png
"""

import argparse
import io
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Generate images with Gemini")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("--aspect", default="1:1",
                        choices=["1:1", "2:3", "3:2", "3:4", "4:3",
                                 "4:5", "5:4", "9:16", "16:9", "21:9"],
                        help="Aspect ratio (default: 1:1)")
    parser.add_argument("--size", default="1K", choices=["1K", "2K", "4K"],
                        help="Image resolution (default: 1K)")
    parser.add_argument("--output", "-o", default="output.jpg",
                        help="Output file path (default: output.jpg)")
    parser.add_argument("--input", "-i", default=None,
                        help="Input image for editing (optional)")
    parser.add_argument("--png", action="store_true",
                        help="Also save a PNG version alongside the JPEG")
    parser.add_argument("--style", default=None,
                        choices=["notebooklm", "dark", "technical", "sticker"],
                        help="Prepend a style preset to the prompt")
    parser.add_argument("--model", default="gemini-3-pro-image-preview",
                        help="Model name (default: gemini-3-pro-image-preview)")
    args = parser.parse_args()

    # Resolve API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable",
              file=sys.stderr)
        sys.exit(1)

    # Import SDK
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: Install google-genai: pip install google-genai pillow",
              file=sys.stderr)
        sys.exit(1)

    # Style presets
    STYLE_PRESETS = {
        "notebooklm": (
            "Create this in Google NotebookLM style — light #f8f9fa background, "
            "soft rounded cards with subtle drop shadows, Material Design aesthetic, "
            "clean sans-serif typography, muted pastel colors, generous whitespace, "
            "thin gray connecting lines. NO dark backgrounds, NO heavy borders. "
        ),
        "dark": (
            "Create this with a dark navy/charcoal background, modern design, "
            "clean typography, teal/coral/gold accents on dark background. "
            "Sharp contrast, readable text, no clutter. "
        ),
        "technical": (
            "Create a clean technical architecture diagram, light background, "
            "labeled boxes with directional arrows, color-coded components, "
            "professional engineering documentation style. "
        ),
        "sticker": (
            "Create a kawaii-style sticker with bold outlines, cel-shading, "
            "white background. Simple, bold, instantly recognizable. "
        ),
    }

    # Build prompt
    prompt = args.prompt
    if args.style and args.style in STYLE_PRESETS:
        prompt = STYLE_PRESETS[args.style] + prompt

    # Build contents
    contents = [prompt]
    if args.input:
        from PIL import Image as PILImage
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        img = PILImage.open(args.input)
        contents = [prompt, img]

    # Generate
    client = genai.Client(api_key=api_key)
    print(f"Generating ({args.size}, {args.aspect})...", file=sys.stderr)

    response = client.models.generate_content(
        model=args.model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=args.aspect,
                image_size=args.size,
            ),
        ),
    )

    # Process response
    saved = False
    for part in response.parts:
        if part.text:
            print(part.text)
        elif part.inline_data:
            # Ensure output has .jpg extension (Gemini returns JPEG)
            out_path = args.output
            if not out_path.lower().endswith((".jpg", ".jpeg")):
                out_path = os.path.splitext(out_path)[0] + ".jpg"

            # Save via PIL for format-safe handling
            from PIL import Image as PILImage
            pil_img = PILImage.open(io.BytesIO(part.inline_data.data))
            pil_img.save(out_path, format="JPEG", quality=95)
            print(f"Saved: {out_path}")

            # Optional PNG
            if args.png:
                png_path = os.path.splitext(out_path)[0] + ".png"
                pil_img.save(png_path, format="PNG")
                print(f"Saved: {png_path}")

            saved = True

    if not saved:
        print("Warning: No image was generated in the response", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
