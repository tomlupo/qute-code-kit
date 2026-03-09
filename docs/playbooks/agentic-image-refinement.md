# Agentic Image Refinement

> Create and iteratively refine images from your terminal using generate-annotate-refine loops.

Based on [Agentic Context Engineering](https://academy.dair.ai/blog/agentic-context-engineering) by DAIR.AI.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| image-generator | `qute-marketplace` plugin | Generate/edit images via Gemini API |
| playground | `claude-plugins-official` plugin | Build interactive annotation interfaces |
| gemini-imagegen | `compound-engineering` skill | Gemini image generation knowledge |

## Setup

```bash
# Gemini API key (free from Google AI Studio)
export GEMINI_API_KEY="your_key_here"  # add to ~/.bashrc

# Plugins (already installed if using qute-code-kit)
claude plugin install image-generator@qute-marketplace
```

## The Generate → Annotate → Refine Loop

### 1. Generate

Be descriptive. Mention context, aesthetic, and where the image will be used:

```
Generate a professional infographic about transformer attention mechanisms.
Use --style notebooklm. Save to output/attention-infographic.jpg
```

**Prompt tips:**
- Specify use context: "for a blog header", "for a slide deck", "for social media"
- Use photography terms: "85mm lens, bokeh", "studio lighting", "bird's eye view"
- Reference art styles: "flat vector, pastel palette", "dark mode UI", "watercolor"
- Include dimensions: "16:9 landscape", "1:1 square for Instagram", "9:16 story"

### 2. Annotate (visual feedback)

Open the image, then build a review tool:

```
Create a playground that shows output/attention-infographic.jpg
with click-to-add numbered markers and text descriptions.
Add a "Generate revision prompt" button that compiles all annotations.
```

The playground creates a self-contained HTML tool where you:
- Click areas that need changes
- Type what you want different
- Hit the button to get a structured revision prompt

### 3. Refine

Paste the compiled prompt back:

```
Edit output/attention-infographic.jpg with these changes:
[paste structured prompt from playground]
```

Repeat 2-3 until satisfied. Each round gets more precise.

## Creative Use Cases

### Blog & Content
```
Create a 16:9 cover image for my post about RAG pipelines,
minimalist style with blue and white palette
```

### Product Mockups
```
Generate a MacBook Pro mockup showing our dashboard UI,
studio lighting, perspective angle, save as mockup.png
```

### Logos & Brand
```
Design a minimalist logo for "Nexus AI" — geometric shapes,
blue and white, transparent background, 1:1 square
```

### Social Media
```
Create a 9:16 image of a clean developer workspace
for an Instagram story about productivity tools
```

### Architecture Diagrams
```
Generate a clean system architecture diagram showing
data flow: API → Queue → Workers → DB → Cache
Dark background, neon accent colors, --style technical-diagram
```

### Photo Editing
```
Take ./assets/team-photo.jpg and:
- Remove the cluttered background
- Replace with a clean gradient
- Improve lighting on faces
```

### Data Visualization
```
Create a publication-quality chart showing model performance
across 5 metrics, radar plot style, Nature journal aesthetic
```

## Style Presets

| Preset | Best for |
|--------|----------|
| `--style notebooklm` | Clean data visualizations, educational content |
| `--style dark-infographic` | Technical content, developer audiences |
| `--style technical-diagram` | System architecture, flow diagrams |
| (no preset) | Photos, mockups, creative visuals |

## Advanced Techniques

### Multi-image composition
Generate components separately, then combine:
```
Generate a header banner, a sidebar illustration, and 3 section icons
for a landing page. Same color palette. Save each separately.
```

### Resolution ladder
Start at 1K for fast iteration, upscale final version:
```
Generate at 1K for review... [iterate]... Final version at 4K
```

### Batch generation
```
Generate 5 variations of a hero image for A/B testing,
each with a different color mood. Save to output/variants/
```

## Tips

- Start rough, refine later — don't over-specify on first generation
- The playground annotation eliminates manual prompt writing between iterations
- Keep style consistent across a project by reusing the same style descriptions
- Use `--png` for anything that needs transparency or lossless quality
- Combine with `/gist-report` to share visual work via URL
