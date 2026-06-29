---
name: brand-sonte
description: Applies Sonte brand identity to web/frontend projects. This skill should be used when creating React components, Tailwind configurations, or CSS for projects requiring the Sonte visual style. Use for any frontend work that needs the clean, light-blue Sonte smart-film brand.
---

# Sonte Brand Guidelines

## Overview

This skill provides the official brand identity for Sonte — a smart-film-for-windows company (sonte.eu / sonte.com). The visual language is clean, bright, and transparent: a signature light Sonte blue paired with fresh cyan on white, evoking clarity, glass, and smart technology.

**Keywords**: sonte, branding, corporate identity, visual identity, smart film, smart glass, tailwind, css variables, react styling, design tokens

## Brand Colors

### Primary Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary | `#53A7DB` | rgb(83, 167, 219) | Sonte blue — headers, primary surfaces, brand moments |
| Primary Dark | `#005A99` | rgb(0, 90, 153) | Deep blue — primary buttons, emphasized CTAs |
| Primary Light | `#7FBCE4` | rgb(127, 188, 228) | Light blue — secondary elements, hover tints |
| Primary Hover | `#3D95CB` | rgb(61, 149, 203) | Primary button hover |

### Accent Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Accent | `#0CB4CE` | rgb(12, 180, 206) | Cyan — highlights, links, badges |
| Accent Soft | `#CDEFF4` | rgb(205, 239, 244) | Light cyan — chips, tags, soft highlights |
| Accent Hover | `#0998AE` | rgb(9, 152, 174) | Accent hover states |

### Background & Surface

| Name | Hex | Usage |
|------|-----|-------|
| Background | `#FFFFFF` | Main page background |
| Background Alt | `#FAFAFA` | Alternating sections |
| Surface | `#F7F7F7` | Cards, elevated surfaces |

### Text Colors

| Name | Hex | Usage |
|------|-----|-------|
| Text | `#141618` | Primary text |
| Text Muted | `#777777` | Secondary text, captions |
| Text On Primary | `#FFFFFF` | Text on primary/dark blue backgrounds |
| Text On Accent | `#FFFFFF` | Text on accent buttons |

### Semantic Colors

| Name | Hex | Usage |
|------|-----|-------|
| Error | `#FF3100` | Error states, destructive actions |
| Success | `#28DE72` | Success states, confirmations |
| Warning | `#FFC42E` | Warning states, cautions |
| Info | `#0CB4CE` | Informational messages (matches accent) |

### Border Colors

| Name | Hex | Usage |
|------|-----|-------|
| Border | `#EAEAEA` | Default borders |
| Border Strong | `#DDDDDD` | Emphasized borders |

## Typography

### Font Family

Sonte uses **Proxima Nova** as its brand typeface. Load via Adobe Fonts (Typekit), a self-hosted license, or fall back gracefully.

```css
font-family: 'proxima-nova', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
```

### Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| Regular | 400 | Body text |
| Medium | 500 | Emphasized text |
| Semibold | 600 | Subheadings, buttons |
| Bold | 700 | Headings, CTAs |

### Font Sizes

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| h1 | 40px / 2.5rem | 1.1 | Page titles |
| h2 | 32px / 2rem | 1.1 | Section headers |
| h3 | 24px / 1.5rem | 1.25 | Subsection headers |
| h4 | 20px / 1.25rem | 1.25 | Card titles |
| body | 16px / 1rem | 1.5 | Body text |
| small | 14px / 0.875rem | 1.5 | Secondary text |
| xs | 12px / 0.75rem | 1.5 | Captions, labels |

## Spacing Scale

| Name | Value | Usage |
|------|-------|-------|
| xs | 4px / 0.25rem | Tight spacing |
| sm | 8px / 0.5rem | Small gaps |
| md | 16px / 1rem | Default spacing |
| lg | 24px / 1.5rem | Section padding |
| xl | 32px / 2rem | Large sections |
| xxl | 48px / 3rem | Hero sections |

## Border Radius

| Name | Value | Usage |
|------|-------|-------|
| sm | 4px | Small elements |
| md | 8px | Default radius |
| lg | 16px | Cards |
| xl | 24px | Large cards |
| pill | 999px | Buttons, chips (Sonte uses pill-shape CTAs) |

## Shadows

```css
--shadow-sm: 0 1px 2px rgba(20, 22, 24, 0.06);
--shadow-md: 0 4px 12px rgba(20, 22, 24, 0.08);
--shadow-lg: 0 10px 30px rgba(20, 22, 24, 0.12);
```

## Component Patterns

### Buttons

**Primary Button (Sonte deep blue CTA):**
- Background: `#005A99`
- Text: `#FFFFFF`
- Hover: `#014978`
- Border Radius: pill (999px)
- Padding: 20px horizontal, 10px vertical
- Font Weight: 700

**Brand Button (Sonte signature light blue):**
- Background: `#53A7DB`
- Text: `#FFFFFF`
- Hover: `#3D95CB`
- Border Radius: pill (999px)

**Accent Button (cyan):**
- Background: `#0CB4CE`
- Text: `#FFFFFF`
- Hover: `#0998AE`
- Border Radius: pill (999px)

**Outline Button:**
- Background: transparent
- Border: 1px solid `#005A99`
- Text: `#005A99`
- Hover Background: rgba(0, 90, 153, 0.05)

### Cards

- Background: `#F7F7F7`
- Border: 1px solid `#EAEAEA`
- Border Radius: 16px (lg)
- Padding: 24px
- Shadow: shadow-sm

### Inputs

- Background: `#FFFFFF`
- Border: 1px solid `#EAEAEA`
- Border Radius: 8px
- Padding: 12px horizontal, 10px vertical
- Focus Border: `#53A7DB`
- Focus Shadow: 0 0 0 1px rgba(83, 167, 219, 0.4)

### Chips/Tags

- Background: `#CDEFF4`
- Text: `#0998AE`
- Border Radius: pill (999px)
- Padding: 10px horizontal, 4px vertical
- Font Size: 12px

### Links

- Color: `#005A99`
- Hover: `#0CB4CE`
- Underline Offset: 2px

## Usage

### Tailwind Configuration

To apply Sonte branding to a Tailwind project, copy the configuration from `assets/tailwind.config.js` or extend the theme:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#53A7DB',
          dark: '#005A99',
          light: '#7FBCE4',
          hover: '#3D95CB',
        },
        accent: {
          DEFAULT: '#0CB4CE',
          soft: '#CDEFF4',
          hover: '#0998AE',
        },
        // ... see assets/tailwind.config.js for complete config
      }
    }
  }
}
```

### CSS Variables

To use CSS custom properties, import `assets/css-variables.css` or copy the variables:

```css
:root {
  --color-primary: #53A7DB;
  --color-primary-dark: #005A99;
  --color-accent: #0CB4CE;
  /* ... see assets/css-variables.css for complete list */
}
```

### React Component Styling

When styling React components with Sonte branding:

1. Use Tailwind classes with the extended theme
2. Or apply CSS variables directly
3. Favor white/light surfaces — Sonte's brand breathes; avoid dense dark blocks
4. Use pill-shaped buttons as the default CTA shape
5. Follow the component patterns above for consistent UX

For detailed token documentation, see `references/design-tokens.md`.
