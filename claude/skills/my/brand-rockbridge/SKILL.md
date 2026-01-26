---
name: brand-rockbridge
description: Applies Rockbridge TFI brand identity to web/frontend projects and PDF documents. This skill should be used when creating React components, Tailwind configurations, CSS, or generating branded PDF documents for Rockbridge TFI (Towarzystwo Funduszy Inwestycyjnych). Use for any frontend work or document generation requiring the Rockbridge visual style.
---

# Rockbridge TFI Brand Guidelines

## Overview

This skill provides the official brand identity for Rockbridge TFI (Towarzystwo Funduszy Inwestycyjnych), a Polish investment fund company established in 1998. Apply these guidelines for consistent branding across web projects and PDF documents.

**Keywords**: rockbridge, tfi, branding, corporate identity, visual identity, financial services, investment fund, tailwind, css variables, react styling, design tokens, pdf generation

**Tagline**: "Lokalni eksperci, globalna wizja" (Local experts, global vision)

## Brand Colors

### Primary Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary | `#00A19A` | rgb(0, 161, 154) | Teal - main brand color, headlines, CTAs |
| Primary Dark | `#008A84` | rgb(0, 138, 132) | Darker teal for hover states |
| Primary Light | `#33B5AF` | rgb(51, 181, 175) | Lighter variant for secondary elements |

### Secondary Palette

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Dark Teal | `#1D3D36` | rgb(29, 61, 54) | Dark backgrounds, headers, footers |
| Dark Teal Light | `#2A5249` | rgb(42, 82, 73) | Hover states on dark backgrounds |
| Navy | `#1A2B3C` | rgb(26, 43, 60) | Alternative dark color |

### Accent Colors

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Gold | `#C9A45C` | rgb(201, 164, 92) | Awards, trophies, premium highlights |
| Gold Light | `#D4B978` | rgb(212, 185, 120) | Gold hover/lighter variant |
| Gold Soft | `#F5EDD8` | rgb(245, 237, 216) | Subtle gold backgrounds |

### Background & Surface

| Name | Hex | Usage |
|------|-----|-------|
| Background | `#FFFFFF` | Main page background |
| Background Alt | `#F5F7F6` | Alternating sections |
| Surface | `#EEF2F0` | Cards, elevated surfaces |
| Surface Dark | `#1D3D36` | Dark sections |

### Text Colors

| Name | Hex | Usage |
|------|-----|-------|
| Text | `#1A1A1A` | Primary text |
| Text Muted | `#6B7280` | Secondary text, captions |
| Text On Primary | `#FFFFFF` | Text on teal backgrounds |
| Text On Dark | `#FFFFFF` | Text on dark backgrounds |
| Text Teal | `#00A19A` | Emphasized text, links |

### Semantic Colors

| Name | Hex | Usage |
|------|-----|-------|
| Error | `#DC2626` | Error states, negative returns |
| Success | `#16A34A` | Success states, positive returns |
| Warning | `#D97706` | Warning states, cautions |
| Info | `#00A19A` | Informational messages (uses primary) |

### Border Colors

| Name | Hex | Usage |
|------|-----|-------|
| Border | `#E5E7EB` | Default borders |
| Border Strong | `#00A19A` | Emphasized borders |
| Border Dark | `#2A5249` | Borders on dark backgrounds |

### Chart Colors

For financial charts and data visualization:

| Name | Hex | Usage |
|------|-----|-------|
| Chart Primary | `#00A19A` | Primary data series |
| Chart Secondary | `#1D3D36` | Secondary data series |
| Chart Accent | `#C9A45C` | Highlighted data points |
| Chart Positive | `#16A34A` | Positive values/growth |
| Chart Negative | `#DC2626` | Negative values/decline |

## Typography

### Font Family

```css
/* Primary font - Roboto (if available) or system fonts */
font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;

/* For PDF documents */
font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
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
| h2 | 32px / 2rem | 1.2 | Section headers |
| h3 | 24px / 1.5rem | 1.25 | Subsection headers |
| h4 | 20px / 1.25rem | 1.3 | Card titles |
| h5 | 18px / 1.125rem | 1.3 | Small headings |
| body | 16px / 1rem | 1.5 | Body text |
| small | 14px / 0.875rem | 1.5 | Secondary text |
| xs | 12px / 0.75rem | 1.5 | Captions, labels, disclaimers |
| xxs | 10px / 0.625rem | 1.4 | Legal text |

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
| none | 0px | Sharp corners (tables) |
| sm | 4px | Small elements |
| md | 8px | Default radius |
| lg | 16px | Cards |
| xl | 24px | Large cards |
| pill | 999px | Buttons, chips |

## Shadows

```css
--shadow-sm: 0 1px 2px rgba(29, 61, 54, 0.08);
--shadow-md: 0 4px 12px rgba(29, 61, 54, 0.12);
--shadow-lg: 0 10px 30px rgba(29, 61, 54, 0.16);
```

## Component Patterns

### Buttons

**Primary Button:**
- Background: `#00A19A`
- Text: `#FFFFFF`
- Hover: `#008A84`
- Border Radius: pill (999px)
- Padding: 12px 24px

**Secondary Button:**
- Background: `#1D3D36`
- Text: `#FFFFFF`
- Hover: `#2A5249`
- Border Radius: pill (999px)

**Outline Button:**
- Background: transparent
- Border: 2px solid `#00A19A`
- Text: `#00A19A`
- Hover Background: rgba(0, 161, 154, 0.08)

**Gold Button (Premium/Awards):**
- Background: `#C9A45C`
- Text: `#1A1A1A`
- Hover: `#D4B978`

### Cards

- Background: `#FFFFFF` or `#EEF2F0`
- Border: 1px solid `#E5E7EB`
- Border Radius: 16px (lg)
- Padding: 24px
- Shadow: shadow-sm

### Dark Sections (Headers/Footers)

- Background: `#1D3D36`
- Text: `#FFFFFF`
- Accent Text: `#00A19A`
- Border: 1px solid `#2A5249`

### Risk Indicator (1-7 Scale)

```css
.risk-indicator {
  display: flex;
  gap: 2px;
}

.risk-box {
  width: 32px;
  height: 32px;
  border: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.risk-box.active {
  background: #00A19A;
  color: white;
  border-color: #00A19A;
}
```

### Data Tables

- Header Background: `#1D3D36`
- Header Text: `#FFFFFF`
- Row Background: alternating `#FFFFFF` and `#F5F7F6`
- Border: 1px solid `#E5E7EB`
- Font Size: 14px

## PDF Document Guidelines

### Page Setup

- Page Size: A4 (210mm x 297mm)
- Margins: 20mm top/bottom, 15mm left/right
- Background: White (`#FFFFFF`)

### PDF Header

- Height: 60px
- Background: `#1D3D36`
- Logo: Top right corner
- Title: White text, left-aligned

### PDF Footer

- Height: 40px
- Background: `#00A19A`
- Contact info: White text
- Page numbers: Right-aligned

### PDF Typography

```css
/* Headlines */
h1 { font-size: 24pt; color: #00A19A; font-weight: 700; }
h2 { font-size: 18pt; color: #1D3D36; font-weight: 600; }
h3 { font-size: 14pt; color: #1A1A1A; font-weight: 600; }

/* Body */
p { font-size: 10pt; color: #1A1A1A; line-height: 1.5; }

/* Captions */
.caption { font-size: 8pt; color: #6B7280; }

/* Legal/Disclaimers */
.legal { font-size: 7pt; color: #6B7280; line-height: 1.3; }
```

### PDF Fund Card Layout

Based on official Rockbridge fund cards:

1. **Header Bar**: Dark teal with awards/rankings
2. **Fund Name**: Large teal text
3. **Performance Chart**: Green bars on white background
4. **Returns Table**: Clean table with alternating rows
5. **Fund Info Section**: Two-column layout
6. **Risk Indicator**: 1-7 scale boxes
7. **Legal Disclaimer**: Small text at bottom

### PDF Color Usage

```javascript
// For PDF generation libraries (e.g., pdfkit, jspdf, react-pdf)
const rockbridgePdfColors = {
  primary: '#00A19A',
  dark: '#1D3D36',
  gold: '#C9A45C',
  text: '#1A1A1A',
  textMuted: '#6B7280',
  background: '#FFFFFF',
  backgroundAlt: '#F5F7F6',
  positive: '#16A34A',
  negative: '#DC2626',
};
```

## Usage

### Tailwind Configuration

To apply Rockbridge branding to a Tailwind project, copy the configuration from `assets/tailwind.config.js` or extend the theme:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00A19A',
          dark: '#008A84',
          light: '#33B5AF',
        },
        dark: {
          DEFAULT: '#1D3D36',
          light: '#2A5249',
        },
        gold: {
          DEFAULT: '#C9A45C',
          light: '#D4B978',
          soft: '#F5EDD8',
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
  --color-primary: #00A19A;
  --color-dark: #1D3D36;
  --color-gold: #C9A45C;
  /* ... see assets/css-variables.css for complete list */
}
```

### PDF Generation (React-PDF Example)

```jsx
import { Document, Page, Text, View, StyleSheet } from '@react-pdf/renderer';

const styles = StyleSheet.create({
  page: {
    backgroundColor: '#FFFFFF',
    padding: 20,
  },
  header: {
    backgroundColor: '#1D3D36',
    padding: 15,
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    color: '#00A19A',
    fontWeight: 'bold',
  },
  // ... see assets/pdf-styles.md for complete styles
});

const RockbridgeDocument = () => (
  <Document>
    <Page size="A4" style={styles.page}>
      <View style={styles.header}>
        <Text style={{ color: '#FFFFFF' }}>Rockbridge TFI</Text>
      </View>
      <Text style={styles.title}>Fund Report</Text>
    </Page>
  </Document>
);
```

### PDF Generation (Python - ReportLab Example)

```python
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

# Rockbridge brand colors
ROCKBRIDGE_PRIMARY = HexColor('#00A19A')
ROCKBRIDGE_DARK = HexColor('#1D3D36')
ROCKBRIDGE_GOLD = HexColor('#C9A45C')
ROCKBRIDGE_TEXT = HexColor('#1A1A1A')

# See assets/pdf-styles.md for complete implementation
```

For detailed token documentation, see `references/design-tokens.md`.
For PDF-specific styles, see `assets/pdf-styles.md`.
