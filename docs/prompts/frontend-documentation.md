# Frontend Documentation Extractor

When: you have HTML files and need to extract a complete design system from them. Produces two outputs: design guidelines (markdown) and interactive style guide (HTML).

## Prompt

Analyze the attached HTML files and create two documents:

### Document 1: Design Guidelines (Markdown)
Extract and document:
- All CSS variables and design tokens (colors, spacing, shadows, radius)
- Typography patterns (families, sizes, weights, line heights)
- Component patterns (buttons, cards, forms, navigation) with complete CSS
- Layout patterns (grids, containers, responsive breakpoints)
- Utility classes
- Accessibility guidelines

### Document 2: Interactive Style Guide (HTML)
Self-contained HTML file with:
- Color palette swatches with hex codes
- Live typography examples
- Working examples of every component (buttons, cards, forms)
- Interactive states (hover, focus, disabled)
- Responsive layout demos

Requirements:
- Style guide must be self-contained (all CSS inline)
- Every component from source files must be demonstrated
- Include usage examples for copy-paste implementation

Source: https://www.nathanonn.com/claude-skill-design-system-reusable-frontend/
