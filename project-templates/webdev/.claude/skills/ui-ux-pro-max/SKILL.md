---
name: ui-ux-pro-max
description: |
  UI/UX design intelligence for web and mobile. Use when tasks involve visual design decisions,
  component creation, style/color/font selection, layout, accessibility, or UX quality control.
  Covers 50+ styles, 161 color palettes, 57 font pairings, 99 UX guidelines, and 25 chart types
  across 10 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind,
  shadcn/ui, HTML/CSS). Actions: plan, build, design, review, fix, improve UI/UX code.
user-invocable: true
argument-hint: "[design request or review target]"
---

# UI/UX Pro Max — Design Intelligence

Comprehensive design guide for web and mobile applications. Based on [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) and the anti-slop guardrails from [impeccable.style](https://impeccable.style) ([pbakaus/impeccable](https://github.com/pbakaus/impeccable)).

## When to Apply

Use when the task involves **UI structure, visual design decisions, interaction patterns, or user experience quality control**.

### Must Use

- Designing new pages (Landing Page, Dashboard, Admin, SaaS, Mobile App)
- Creating or refactoring UI components (buttons, modals, forms, tables, charts)
- Choosing color schemes, typography systems, spacing standards, or layout systems
- Reviewing UI code for user experience, accessibility, or visual consistency
- Implementing navigation structures, animations, or responsive behavior
- Making product-level design decisions (style, information hierarchy, brand expression)

### Skip

- Pure backend logic, API/database design, DevOps, non-visual scripts

**Decision criteria**: If the task changes how a feature **looks, feels, moves, or is interacted with**, use this skill.

## Setup: PRODUCT.md + DESIGN.md

Before generating or refactoring UI, load (or write) two project docs — no design work happens without them:

- **PRODUCT.md** — audience, brand personality, anti-references, aesthetic direction
- **DESIGN.md** — color tokens, type scale, spacing scale, motion defaults, component rules

If either is missing, interview the user for the minimum set (audience + 3 adjectives + 2 anti-references) and write it before touching components. If the project already has running UI, reverse-engineer DESIGN.md from the code before editing.

## Register: Brand vs Product

Classify every screen before applying rules. The defaults change by register.

| Register | Examples | Dominant goals | Leans toward |
|----------|----------|----------------|--------------|
| Brand | Landing pages, marketing, docs home | Persuasion, emotion, memorability | Larger type, asymmetric layouts, bolder color, richer motion |
| Product | App UI, dashboards, admin, settings | Task completion, scanability, density | Restrained color, tabular figures, minimal motion, system controls |

Mismatched register is itself an anti-pattern (marketing flourishes inside a dashboard, or a flat product shell on a landing hero).

## Anti-Slop Guardrails

Generic LLM output has a recognizable fingerprint. Refuse these patterns by default — only use them with an explicit, documented reason.

### Absolute bans (no exceptions)

- **Side-stripe borders** on cards/sections (the 2–4px accent bar on the left edge)
- **Gradient text** for body, headings, or CTAs
- **Decorative glassmorphism** — blur is for scrim/dismissal, not ornament
- **Hero-metric template** — "big number + label + trend arrow" grids used as a landing pattern
- **Identical card grids** — N uniform cards as the entire page composition

### AI-slop fingerprints (replace on sight)

- **Inter / Arial / system-ui everywhere** — pick a distinctive pairing; reserve system-ui for product chrome only
- **Purple/indigo gradient backgrounds** as the default hero
- **Gray text on colored backgrounds** — fails contrast, looks cheap
- **Pure `#000` / `#fff` / neutral `#888`** — always tint neutrals (cool/warm) toward the brand hue
- **Cards nested in cards** — pick one container layer; use spacing and dividers inside it
- **Bounce / elastic easing** on UI transitions — dated; use exponential or spring
- **Dark glows** around cards/buttons to fake depth
- **Emoji as icons** in navigation, chrome, or data
- **Skipped heading levels** (`h1` → `h3`) to get a size
- **Cramped padding** (<12px on touch surfaces) or **excessive line length** (>75ch body)

## Color: OKLCH + Tinted Neutrals

- Author colors in **OKLCH** (or convert to it mentally). It separates perceptual lightness from chroma so scales stay even.
- **Reduce chroma at lightness extremes** (L > 0.9 or L < 0.15) — otherwise colors muddy or clip.
- **Tint the neutral ramp** toward the brand hue (e.g. cool grays for a blue brand, warm grays for an orange brand). Pure neutral `hsl(0 0% x)` is a slop tell.
- **Dark mode ≠ inverted light mode.** Lift surfaces by lightness, desaturate accents, raise border chroma slightly.
- **4.5:1 / 3:1 contrast** is the floor, not the target.

### Color strategy (pick one per surface)

| Strategy | Description | Good for |
|----------|-------------|----------|
| Restrained | Neutral canvas, one accent for primary action only | Dashboards, tools, admin |
| Committed | One brand hue used confidently across surfaces + one neutral | Most product UIs |
| Full palette | 3–5 intentional hues with defined roles | Data-viz, editorial, marketing |
| Drenched | Single hue saturates the whole surface; neutrals are tinted variants | Bold landing, brand moments |

Document the chosen strategy in DESIGN.md. Mixing strategies within one surface is an anti-pattern.

## Typography Defaults

- **Type scale ratio ≥ 1.25** between adjacent hierarchy levels. Smaller ratios read as noise.
- **Body 16–18px** web / **17pt** iOS / **16sp** Android; line-height 1.5–1.75; measure 60–75ch.
- **Pair personalities, not weights** — a geometric display with a humanist text, or a serif display with a grotesque text. Same-family super-families are safe but forgettable.
- Use **OpenType features** (tabular figures for data, small caps for labels, proper fractions) rather than faking them.

## Motion Defaults

- **Exponential / cubic-out easing** for entering, **cubic-in** for exiting. No linear, no bounce, no elastic on UI.
- **Never animate layout properties** (`width`, `height`, `top`, `left`, `margin`). Animate `transform` and `opacity` only; use FLIP for size changes.
- **Exit 60–70% of enter duration.** Total budget 150–300ms for micro, ≤400ms for transitions.
- **Respect `prefers-reduced-motion`** — replace motion with instant state change or opacity-only.
- **Interruptible** — user input cancels in-progress animation; never block input for motion.

## Rule Categories by Priority

| Priority | Category | Impact | Key Checks (Must Have) | Anti-Patterns (Avoid) |
|----------|----------|--------|------------------------|------------------------|
| 1 | Accessibility | CRITICAL | Contrast 4.5:1, Alt text, Keyboard nav, Aria-labels | Removing focus rings, Icon-only buttons without labels |
| 2 | Touch & Interaction | CRITICAL | Min size 44×44px, 8px+ spacing, Loading feedback | Reliance on hover only, Instant state changes (0ms) |
| 3 | Performance | HIGH | WebP/AVIF, Lazy loading, Reserve space (CLS < 0.1) | Layout thrashing, Cumulative Layout Shift |
| 4 | Style Selection | HIGH | Match product type, Consistency, SVG icons (no emoji) | Mixing flat & skeuomorphic randomly, Emoji as icons |
| 5 | Layout & Responsive | HIGH | Mobile-first breakpoints, Viewport meta, No horizontal scroll | Horizontal scroll, Fixed px container widths, Disable zoom |
| 6 | Typography & Color | MEDIUM | Base 16px, Line-height 1.5, Semantic color tokens | Text < 12px body, Gray-on-gray, Raw hex in components |
| 7 | Animation | MEDIUM | Duration 150–300ms, Motion conveys meaning, Spatial continuity | Decorative-only animation, Animating width/height, No reduced-motion |
| 8 | Forms & Feedback | MEDIUM | Visible labels, Error near field, Helper text, Progressive disclosure | Placeholder-only label, Errors only at top, Overwhelm upfront |
| 9 | Navigation Patterns | HIGH | Predictable back, Bottom nav ≤5, Deep linking | Overloaded nav, Broken back behavior, No deep links |
| 10 | Charts & Data | LOW | Legends, Tooltips, Accessible colors | Relying on color alone to convey meaning |

## Quick Reference

### 1. Accessibility (CRITICAL)

- `color-contrast` — Minimum 4.5:1 ratio for normal text (large text 3:1)
- `focus-states` — Visible focus rings on interactive elements (2–4px)
- `alt-text` — Descriptive alt text for meaningful images
- `aria-labels` — aria-label for icon-only buttons; accessibilityLabel in native
- `keyboard-nav` — Tab order matches visual order; full keyboard support
- `form-labels` — Use label with for attribute
- `skip-links` — Skip to main content for keyboard users
- `heading-hierarchy` — Sequential h1→h6, no level skip
- `color-not-only` — Don't convey info by color alone (add icon/text)
- `dynamic-type` — Support system text scaling; avoid truncation as text grows
- `reduced-motion` — Respect prefers-reduced-motion; reduce/disable animations when requested
- `voiceover-sr` — Meaningful accessibilityLabel/accessibilityHint; logical reading order
- `escape-routes` — Provide cancel/back in modals and multi-step flows
- `keyboard-shortcuts` — Preserve system and a11y shortcuts; offer keyboard alternatives for drag-and-drop

### 2. Touch & Interaction (CRITICAL)

- `touch-target-size` — Min 44×44pt (Apple) / 48×48dp (Material); extend hit area if needed
- `touch-spacing` — Minimum 8px/8dp gap between touch targets
- `hover-vs-tap` — Use click/tap for primary interactions; don't rely on hover alone
- `loading-buttons` — Disable button during async operations; show spinner or progress
- `error-feedback` — Clear error messages near problem
- `cursor-pointer` — Add cursor-pointer to clickable elements (Web)
- `gesture-conflicts` — Avoid horizontal swipe on main content; prefer vertical scroll
- `tap-delay` — Use touch-action: manipulation to reduce 300ms delay (Web)
- `standard-gestures` — Use platform standard gestures consistently
- `system-gestures` — Don't block system gestures (Control Center, back swipe, etc.)
- `press-feedback` — Visual feedback on press (ripple/highlight)
- `haptic-feedback` — Use haptic for confirmations and important actions; avoid overuse
- `gesture-alternative` — Always provide visible controls for critical actions
- `safe-area-awareness` — Keep primary touch targets away from notch, Dynamic Island, gesture bar
- `no-precision-required` — Avoid requiring pixel-perfect taps on small icons or thin edges
- `swipe-clarity` — Swipe actions must show clear affordance or hint
- `drag-threshold` — Use a movement threshold before starting drag to avoid accidental drags

### 3. Performance (HIGH)

- `image-optimization` — Use WebP/AVIF, responsive images (srcset/sizes), lazy load non-critical assets
- `image-dimension` — Declare width/height or use aspect-ratio to prevent layout shift (CLS)
- `font-loading` — Use font-display: swap/optional to avoid invisible text (FOIT)
- `font-preload` — Preload only critical fonts
- `critical-css` — Prioritize above-the-fold CSS
- `lazy-loading` — Lazy load non-hero components via dynamic import / route-level splitting
- `bundle-splitting` — Split code by route/feature to reduce initial load and TTI
- `third-party-scripts` — Load third-party scripts async/defer
- `reduce-reflows` — Avoid frequent layout reads/writes; batch DOM reads then writes
- `content-jumping` — Reserve space for async content to avoid layout jumps (CLS)
- `virtualize-lists` — Virtualize lists with 50+ items
- `main-thread-budget` — Keep per-frame work under ~16ms for 60fps
- `progressive-loading` — Use skeleton screens / shimmer instead of long blocking spinners
- `input-latency` — Keep input latency under ~100ms for taps/scrolls
- `debounce-throttle` — Use debounce/throttle for high-frequency events (scroll, resize, input)
- `offline-support` — Provide offline state messaging and basic fallback (PWA / mobile)

### 4. Style Selection (HIGH)

- `style-match` — Match style to product type
- `consistency` — Use same style across all pages
- `no-emoji-icons` — Use SVG icons (Heroicons, Lucide), not emojis
- `color-palette-from-product` — Choose palette from product/industry
- `effects-match-style` — Shadows, blur, radius aligned with chosen style
- `platform-adaptive` — Respect platform idioms (iOS HIG vs Material)
- `state-clarity` — Make hover/pressed/disabled states visually distinct while staying on-style
- `elevation-consistent` — Use a consistent elevation/shadow scale
- `dark-mode-pairing` — Design light/dark variants together
- `icon-style-consistent` — Use one icon set/visual language across the product
- `system-controls` — Prefer native/system controls over fully custom ones
- `blur-purpose` — Use blur to indicate background dismissal, not as decoration
- `primary-action` — Each screen should have only one primary CTA

### 5. Layout & Responsive (HIGH)

- `viewport-meta` — width=device-width initial-scale=1 (never disable zoom)
- `mobile-first` — Design mobile-first, then scale up
- `breakpoint-consistency` — Use systematic breakpoints (e.g. 375 / 768 / 1024 / 1440)
- `readable-font-size` — Minimum 16px body text on mobile (avoids iOS auto-zoom)
- `line-length-control` — Mobile 35–60 chars per line; desktop 60–75 chars
- `horizontal-scroll` — No horizontal scroll on mobile
- `spacing-scale` — Use 4pt/8dp incremental spacing system
- `container-width` — Consistent max-width on desktop
- `z-index-management` — Define layered z-index scale
- `fixed-element-offset` — Fixed navbar/bottom bar must reserve safe padding
- `scroll-behavior` — Avoid nested scroll regions that interfere with main scroll
- `viewport-units` — Prefer min-h-dvh over 100vh on mobile
- `orientation-support` — Keep layout readable in landscape mode
- `content-priority` — Show core content first on mobile
- `visual-hierarchy` — Establish hierarchy via size, spacing, contrast — not color alone

### 6. Typography & Color (MEDIUM)

- `line-height` — Use 1.5–1.75 for body text
- `line-length` — Limit to 65–75 characters per line
- `font-pairing` — Match heading/body font personalities
- `font-scale` — Consistent type scale (e.g. 12 14 16 18 24 32)
- `contrast-readability` — Darker text on light backgrounds
- `text-styles-system` — Use platform type system (iOS Dynamic Type / Material type roles)
- `weight-hierarchy` — Bold headings (600–700), Regular body (400), Medium labels (500)
- `color-semantic` — Define semantic color tokens (primary, secondary, error, surface) not raw hex
- `color-dark-mode` — Dark mode uses desaturated / lighter tonal variants, not inverted colors
- `color-accessible-pairs` — Foreground/background pairs must meet 4.5:1 (AA) or 7:1 (AAA)
- `color-not-decorative-only` — Functional color must include icon/text
- `truncation-strategy` — Prefer wrapping over truncation; when truncating use ellipsis with tooltip
- `number-tabular` — Use tabular/monospaced figures for data columns, prices, timers
- `whitespace-balance` — Use whitespace intentionally to group related items and separate sections

### 7. Animation (MEDIUM)

- `duration-timing` — 150–300ms for micro-interactions; complex transitions ≤400ms; avoid >500ms
- `transform-performance` — Use transform/opacity only; avoid animating width/height/top/left
- `loading-states` — Show skeleton or progress indicator when loading exceeds 300ms
- `excessive-motion` — Animate 1–2 key elements per view max
- `easing` — Use ease-out for entering, ease-in for exiting; avoid linear for UI transitions
- `motion-meaning` — Every animation must express cause-effect, not just be decorative
- `state-transition` — State changes should animate smoothly, not snap
- `continuity` — Page/screen transitions should maintain spatial continuity
- `spring-physics` — Prefer spring/physics-based curves for natural feel
- `exit-faster-than-enter` — Exit animations shorter than enter (~60–70% of enter duration)
- `stagger-sequence` — Stagger list/grid item entrance by 30–50ms per item
- `shared-element-transition` — Use shared element / hero transitions between screens
- `interruptible` — Animations must be interruptible; user tap cancels in-progress animation
- `no-blocking-animation` — Never block user input during an animation
- `scale-feedback` — Subtle scale (0.95–1.05) on press for tappable cards/buttons
- `gesture-feedback` — Drag, swipe, and pinch must provide real-time visual response
- `modal-motion` — Modals/sheets should animate from their trigger source
- `navigation-direction` — Forward navigation animates left/up; backward right/down

### 8. Forms & Feedback (MEDIUM)

- `input-labels` — Visible label per input (not placeholder-only)
- `error-placement` — Show error below the related field
- `submit-feedback` — Loading then success/error state on submit
- `required-indicators` — Mark required fields (e.g. asterisk)
- `empty-states` — Helpful message and action when no content
- `toast-dismiss` — Auto-dismiss toasts in 3–5s
- `confirmation-dialogs` — Confirm before destructive actions
- `input-helper-text` — Provide persistent helper text below complex inputs
- `disabled-states` — Reduced opacity (0.38–0.5) + cursor change + semantic attribute
- `progressive-disclosure` — Reveal complex options progressively
- `inline-validation` — Validate on blur (not keystroke)
- `input-type-keyboard` — Use semantic input types (email, tel, number) for correct mobile keyboard
- `password-toggle` — Provide show/hide toggle for password fields
- `undo-support` — Allow undo for destructive or bulk actions
- `success-feedback` — Confirm completed actions with brief visual feedback
- `error-recovery` — Error messages must include a clear recovery path
- `multi-step-progress` — Multi-step flows show step indicator; allow back navigation
- `form-autosave` — Long forms should auto-save drafts
- `error-clarity` — Error messages must state cause + how to fix
- `field-grouping` — Group related fields logically
- `focus-management` — After submit error, auto-focus the first invalid field
- `destructive-emphasis` — Destructive actions use semantic danger color and are visually separated
- `toast-accessibility` — Toasts must not steal focus; use aria-live="polite"

### 9. Navigation Patterns (HIGH)

- `bottom-nav-limit` — Bottom navigation max 5 items; use labels with icons
- `drawer-usage` — Use drawer/sidebar for secondary navigation, not primary actions
- `back-behavior` — Back navigation must be predictable and consistent; preserve scroll/state
- `deep-linking` — All key screens must be reachable via deep link / URL
- `tab-bar-ios` — iOS: use bottom Tab Bar for top-level navigation
- `top-app-bar-android` — Android: use Top App Bar with navigation icon
- `nav-label-icon` — Navigation items must have both icon and text label
- `nav-state-active` — Current location must be visually highlighted in navigation
- `nav-hierarchy` — Primary nav vs secondary nav must be clearly separated
- `modal-escape` — Modals and sheets must offer a clear close/dismiss affordance
- `search-accessible` — Search must be easily reachable; provide recent/suggested queries
- `breadcrumb-web` — Web: use breadcrumbs for 3+ level deep hierarchies
- `state-preservation` — Navigating back must restore previous scroll position and filter state
- `gesture-nav-support` — Support system gesture navigation without conflict
- `overflow-menu` — When actions exceed available space, use overflow/more menu
- `adaptive-navigation` — Large screens prefer sidebar; small screens use bottom/top nav
- `back-stack-integrity` — Never silently reset the navigation stack
- `navigation-consistency` — Navigation placement must stay the same across all pages
- `modal-vs-navigation` — Modals must not be used for primary navigation flows
- `focus-on-route-change` — After page transition, move focus to main content region for screen readers
- `persistent-nav` — Core navigation must remain reachable from deep pages
- `destructive-nav-separation` — Dangerous actions must be visually and spatially separated from normal nav items

### 10. Charts & Data (LOW)

- `chart-type` — Match chart type to data type (trend→line, comparison→bar, proportion→pie/donut)
- `color-guidance` — Use accessible color palettes; avoid red/green only pairs
- `data-table` — Provide table alternative for accessibility
- `pattern-texture` — Supplement color with patterns/textures/shapes
- `legend-visible` — Always show legend; position near the chart
- `tooltip-on-interact` — Provide tooltips on hover (Web) or tap (mobile) showing exact values
- `axis-labels` — Label axes with units and readable scale
- `responsive-chart` — Charts must reflow or simplify on small screens
- `empty-data-state` — Show meaningful empty state when no data exists
- `loading-chart` — Use skeleton/shimmer placeholder while chart data loads
- `large-dataset` — For 1000+ data points, aggregate or sample; provide drill-down
- `number-formatting` — Use locale-aware formatting for numbers, dates, currencies
- `touch-target-chart` — Interactive chart elements must have ≥44pt tap area
- `no-pie-overuse` — Avoid pie/donut for >5 categories; switch to bar chart
- `contrast-data` — Data lines/bars vs background ≥3:1; data text labels ≥4.5:1
- `legend-interactive` — Legends should be clickable to toggle series visibility
- `tooltip-keyboard` — Tooltip content must be keyboard-reachable
- `sortable-table` — Data tables must support sorting with aria-sort
- `focusable-elements` — Interactive chart elements must be keyboard-navigable
- `screen-reader-summary` — Provide a text summary or aria-label describing the chart's key insight

## Design System Workflow

When designing a new project or page, follow this workflow:

### Step 1: Analyze Requirements

Extract from user request (and PRODUCT.md if present):
- **Register**: Brand or Product (see Register table above)
- **Product type**: Entertainment, Tool, Productivity, E-commerce, SaaS, Portfolio, etc.
- **Target audience**: Age group, usage context (commute, leisure, work)
- **Style keywords**: playful, vibrant, minimal, dark mode, content-first, immersive, etc.
- **Anti-references**: What the product should *not* look like
- **Stack**: React, Next.js, Vue, Svelte, React Native, Flutter, Tailwind, etc.

### Step 2: Generate Design System (writes DESIGN.md)

Recommend a complete design system covering:
1. **Pattern** — Page structure and layout approach matching register + product type
2. **Style** — Visual style (minimalism, editorial, brutalism, etc.) — avoid default glassmorphism
3. **Color strategy** — Restrained / Committed / Full palette / Drenched (pick one)
4. **Colors** — OKLCH tokens with tinted neutrals, chroma reduced at lightness extremes
5. **Typography** — Font pairing (distinctive display + readable text), scale ratio ≥ 1.25
6. **Effects** — Shadows, radius, motion tokens (exponential easing) matching the chosen style
7. **Anti-patterns** — Anti-slop guardrails + product-specific avoidances

### Step 3: Apply Rules by Priority

Work through the priority table (§1–§10), focusing on:
1. CRITICAL rules first (Accessibility, Touch & Interaction)
2. HIGH impact rules next (Performance, Style, Layout, Navigation)
3. MEDIUM rules for polish (Typography, Animation, Forms)
4. LOW rules as applicable (Charts & Data)

## Common Rules for Professional UI

### Icons & Visual Elements

| Rule | Standard | Avoid |
|------|----------|-------|
| No Emoji as Icons | Use vector icons (Heroicons, Lucide, react-native-vector-icons) | Emojis (🎨 🚀 ⚙️) for navigation or system controls |
| Vector-Only Assets | SVG or platform vector icons that scale cleanly | Raster PNG icons that blur or pixelate |
| Stable Interaction States | Color, opacity, or elevation transitions for press states | Layout-shifting transforms that move surrounding content |
| Correct Brand Logos | Official brand assets following usage guidelines | Guessing logo paths or recoloring unofficially |
| Consistent Icon Sizing | Define icon sizes as design tokens (icon-sm, icon-md=24pt, icon-lg) | Mixing arbitrary values randomly |
| Stroke Consistency | Consistent stroke width within the same visual layer | Mixing thick and thin stroke styles |
| Filled vs Outline | One icon style per hierarchy level | Mixing filled and outline at the same level |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
|------|----|----- |
| Surface readability | Cards/surfaces clearly separated from background | Overly transparent surfaces that blur hierarchy |
| Text contrast (light) | Body text contrast ≥4.5:1 against light surfaces | Low-contrast gray body text |
| Text contrast (dark) | Primary text ≥4.5:1, secondary ≥3:1 on dark surfaces | Dark mode text blending into background |
| Border visibility | Separators visible in both themes | Theme-specific borders disappearing in one mode |
| State contrast parity | Pressed/focused/disabled equally distinguishable in both modes | Defining interaction states for one theme only |
| Token-driven theming | Semantic color tokens mapped per theme | Hardcoded per-screen hex values |

### Layout & Spacing

| Rule | Do | Don't |
|------|----|----- |
| Safe-area compliance | Respect top/bottom safe areas for fixed headers, tab bars, CTAs | Placing UI under notch, status bar, gesture area |
| System bar clearance | Add spacing for status/navigation bars and gesture indicator | Tappable content colliding with OS chrome |
| 8dp spacing rhythm | Consistent 4/8dp spacing system | Random spacing increments |
| Readable text measure | Keep long-form text readable on large devices | Full-width paragraphs on tablets |
| Scroll + fixed coexistence | Add content insets so lists aren't hidden behind fixed bars | Scroll content obscured by sticky headers/footers |

## Pre-Delivery Checklist

### Anti-Slop Audit
- [ ] No side-stripe accent borders on cards/sections
- [ ] No gradient text (headings, body, or CTAs)
- [ ] No decorative glassmorphism (blur only for dismissal/scrim)
- [ ] No "hero-metric" or uniform-card-grid page compositions
- [ ] No purple/indigo gradient default heroes
- [ ] No Inter / Arial / system-ui as display face unless explicitly chosen
- [ ] No cards nested in cards
- [ ] No bounce/elastic easing on UI transitions
- [ ] Neutrals are tinted, not pure `#000`/`#fff`/`#888`
- [ ] Register (brand vs product) is correct for the screen

### Visual Quality
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from a consistent icon family and style
- [ ] Official brand assets with correct proportions
- [ ] Pressed-state visuals do not shift layout bounds
- [ ] Semantic theme tokens used consistently
- [ ] Color strategy (Restrained / Committed / Full / Drenched) documented in DESIGN.md
- [ ] Chroma reduced at lightness extremes (L > 0.9, L < 0.15)
- [ ] Type scale ratio ≥ 1.25 between hierarchy levels

### Interaction
- [ ] All tappable elements provide clear pressed feedback
- [ ] Touch targets meet minimum size (≥44×44pt iOS, ≥48×48dp Android)
- [ ] Micro-interaction timing 150–300ms with native-feeling easing
- [ ] Disabled states visually clear and non-interactive
- [ ] Screen reader focus order matches visual order
- [ ] Only `transform`/`opacity` are animated (no layout properties)
- [ ] Exit animations run at 60–70% of enter duration
- [ ] `prefers-reduced-motion` path tested

### Light/Dark Mode
- [ ] Primary text contrast ≥4.5:1 in both modes
- [ ] Secondary text contrast ≥3:1 in both modes
- [ ] Dividers/borders distinguishable in both modes
- [ ] Both themes tested before delivery

### Layout
- [ ] Safe areas respected for headers, tab bars, bottom CTAs
- [ ] Scroll content not hidden behind fixed/sticky bars
- [ ] Verified on small phone, large phone, and tablet (portrait + landscape)
- [ ] 4/8dp spacing rhythm maintained
- [ ] Long-form text measure readable on larger devices

### Accessibility
- [ ] All meaningful images/icons have accessibility labels
- [ ] Form fields have labels, hints, and clear error messages
- [ ] Color is not the only indicator
- [ ] Reduced motion and dynamic text size supported
- [ ] Accessibility traits/roles/states announced correctly
