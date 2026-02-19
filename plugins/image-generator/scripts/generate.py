#!/usr/bin/env python3
"""Generate an image using Google Gemini API.

Usage:
    python generate.py "prompt" [--aspect RATIO] [--size SIZE] [--output PATH]

Examples:
    python generate.py "A sunset over mountains" --aspect 16:9 --size 2K
    python generate.py "Logo for TechCo" --output logo.jpg
    python generate.py "Edit: add clouds" --input photo.jpg --output photo_edited.jpg
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Generate images with Gemini")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("--aspect", default="1:1",
                        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                        help="Aspect ratio (default: 1:1)")
    parser.add_argument("--size", default="1K", choices=["1K", "2K", "4K"],
                        help="Image resolution (default: 1K)")
    parser.add_argument("--output", "-o", default="output.jpg",
                        help="Output file path (default: output.jpg)")
    parser.add_argument("--input", "-i", default=None,
                        help="Input image for editing (optional)")
    parser.add_argument("--model", default="gemini-3-pro-image-preview",
                        help="Model name (default: gemini-3-pro-image-preview)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: Install google-genai: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    contents = [args.prompt]

    if args.input:
        from PIL import Image
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        img = Image.open(args.input)
        contents = [args.prompt, img]

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

    saved = False
    for part in response.parts:
        if part.text:
            print(part.text)
        elif part.inline_data:
            image = part.as_image()
            image.save(args.output)
            print(f"Saved: {args.output}")
            saved = True

    if not saved:
        print("Warning: No image was generated in the response", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
