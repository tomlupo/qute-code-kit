---
name: brand-dm-evo
description: Applies Evo Dom Maklerski brand identity to web/frontend projects. This skill should be used when creating React components, Tailwind configurations, or CSS for projects requiring the evo dm visual style. Use for any frontend work that needs professional financial services branding.
---

# Evo Dom Maklerski Brand Guidelines

## Overview

This skill provides the official brand identity for Evo Dom Maklerski, a Polish brokerage house. To apply consistent branding to web and frontend projects, use these guidelines.

**Keywords**: evo dm, branding, corporate identity, visual identity, financial services, tailwind, css variables, react styling, design tokens

## Brand Colors

### Primary Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary | `#0C2340` | rgb(12, 35, 64) | Dark navy - headers, primary buttons, dark backgrounds |
| Primary Dark | `#02091A` | rgb(2, 9, 26) | Darker variant for hover states |
| Primary Light | `#1F3A5F` | rgb(31, 58, 95) | Lighter variant for secondary elements |

### Accent Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Accent | `#2563EB` | rgb(37, 99, 235) | Bright blue - CTAs, links, highlights |
| Accent Soft | `#DBEAFE` | rgb(219, 234, 254) | Light blue - chips, tags, subtle highlights |

### Background & Surface

| Name | Hex | Usage |
|------|-----|-------|
| Background | `#FFFFFF` | Main page background |
| Background Alt | `#F9FAFB` | Alternating sections |
| Surface | `#F1F5F9` | Cards, elevated surfaces |

### Text Colors

| Name | Hex | Usage |
|------|-----|-------|
| Text | `#0F172A` | Primary text |
| Text Muted | `#6B7280` | Secondary text, captions |
| Text On Primary | `#FFFFFF` | Text on dark backgrounds |
| Text On Accent | `#FFFFFF` | Text on accent buttons |

### Semantic Colors

| Name | Hex | Usage |
|------|-----|-------|
| Error | `#DC2626` | Error states, destructive actions |
| Success | `#16A34A` | Success states, confirmations |
| Warning | `#D97706` | Warning states, cautions |
| Info | `#0284C7` | Informational messages |

### Border Colors

| Name | Hex | Usage |
|------|-----|-------|
| Border | `#E5E7EB` | Default borders |
| Border Strong | `#CBD5F5` | Emphasized borders |

## Typography

### Font Family

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
```

### Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| Regular | 400 | Body text |
| Medium | 500 | Emphasized text |
| Semibold | 600 | Subheadings, buttons |
| Bold | 700 | Headings |

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
| pill | 999px | Buttons, chips |

## Shadows

```css
--shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.08);
--shadow-md: 0 4px 12px rgba(15, 23, 42, 0.10);
--shadow-lg: 0 10px 30px rgba(15, 23, 42, 0.15);
```

## Component Patterns

### Buttons

**Primary Button:**
- Background: `#0C2340`
- Text: `#FFFFFF`
- Hover: `#10294F`
- Border Radius: pill (999px)
- Padding: 20px horizontal, 10px vertical

**Accent Button:**
- Background: `#2563EB`
- Text: `#FFFFFF`
- Hover: `#1D4ED8`
- Border Radius: pill (999px)

**Outline Button:**
- Background: transparent
- Border: 1px solid `#0C2340`
- Text: `#0C2340`
- Hover Background: rgba(12, 35, 64, 0.05)

### Cards

- Background: `#F1F5F9`
- Border: 1px solid `#E5E7EB`
- Border Radius: 16px (lg)
- Padding: 24px
- Shadow: shadow-sm

### Inputs

- Background: `#FFFFFF`
- Border: 1px solid `#E5E7EB`
- Border Radius: 8px
- Padding: 12px horizontal, 10px vertical
- Focus Border: `#2563EB`
- Focus Shadow: 0 0 0 1px rgba(37, 99, 235, 0.4)

### Chips/Tags

- Background: `#DBEAFE`
- Text: `#2563EB`
- Border Radius: pill (999px)
- Padding: 10px horizontal, 4px vertical
- Font Size: 12px

### Links

- Color: `#2563EB`
- Hover: `#1D4ED8`
- Underline Offset: 2px

## Usage

### Tailwind Configuration

To apply evo dm branding to a Tailwind project, copy the configuration from `assets/tailwind.config.js` or extend the theme:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0C2340',
          dark: '#02091A',
          light: '#1F3A5F',
        },
        accent: {
          DEFAULT: '#2563EB',
          soft: '#DBEAFE',
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
  --color-primary: #0C2340;
  --color-accent: #2563EB;
  /* ... see assets/css-variables.css for complete list */
}
```

### React Component Styling

When styling React components with evo dm branding:

1. Use Tailwind classes with the extended theme
2. Or apply CSS variables directly
3. Follow the component patterns above for consistent UX

For detailed token documentation, see `references/design-tokens.md`.
