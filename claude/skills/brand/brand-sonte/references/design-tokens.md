# Sonte Design Tokens

Complete design token reference for implementing the Sonte brand identity in web projects. Palette sourced from sonte.eu / sonte.com.

## Color Tokens

### Primary Colors

```
primary:          #53A7DB  rgb(83, 167, 219)   — signature Sonte blue
primary-dark:     #005A99  rgb(0, 90, 153)     — deep CTA blue
primary-light:    #7FBCE4  rgb(127, 188, 228)  — lighter tint
primary-hover:    #3D95CB  rgb(61, 149, 203)   — hover on primary
```

### Accent Colors

```
accent:           #0CB4CE  rgb(12, 180, 206)   — cyan
accent-soft:      #CDEFF4  rgb(205, 239, 244)  — light cyan
accent-hover:     #0998AE  rgb(9, 152, 174)    — hover on accent
```

### Background Colors

```
background:       #FFFFFF  rgb(255, 255, 255)
background-alt:   #FAFAFA  rgb(250, 250, 250)
surface:          #F7F7F7  rgb(247, 247, 247)
```

### Text Colors

```
text:             #141618  rgb(20, 22, 24)
text-muted:       #777777  rgb(119, 119, 119)
text-on-primary:  #FFFFFF  rgb(255, 255, 255)
text-on-accent:   #FFFFFF  rgb(255, 255, 255)
```

### Border Colors

```
border:           #EAEAEA  rgb(234, 234, 234)
border-strong:    #DDDDDD  rgb(221, 221, 221)
```

### Semantic Colors

```
error:            #FF3100  rgb(255, 49, 0)
success:          #28DE72  rgb(40, 222, 114)
warning:          #FFC42E  rgb(255, 196, 46)
info:             #0CB4CE  rgb(12, 180, 206)   — same as accent
```

## Typography Tokens

### Font Family

```
font-base:    'proxima-nova', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
font-heading: 'proxima-nova', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
```

Sonte's official typeface is **Proxima Nova** (via Adobe Fonts). Make sure it is loaded before render, or the stack falls back cleanly to the system sans-serif.

### Font Weights

```
font-regular:   400
font-medium:    500
font-semibold:  600
font-bold:      700
```

### Font Sizes (px / rem)

```
text-h1:    40px / 2.5rem
text-h2:    32px / 2rem
text-h3:    24px / 1.5rem
text-h4:    20px / 1.25rem
text-body:  16px / 1rem
text-small: 14px / 0.875rem
text-xs:    12px / 0.75rem
```

### Line Heights

```
leading-tight:   1.1
leading-snug:    1.25
leading-normal:  1.5
leading-relaxed: 1.7
```

## Spacing Tokens (px / rem)

```
space-none: 0
space-xs:   4px  / 0.25rem
space-sm:   8px  / 0.5rem
space-md:   16px / 1rem
space-lg:   24px / 1.5rem
space-xl:   32px / 2rem
space-xxl:  48px / 3rem
space-section: 80px / 5rem
```

### Content Width

```
content-max-width: 1200px
```

## Border Radius Tokens (px)

```
radius-sm:   4px
radius-md:   8px
radius-lg:   16px
radius-xl:   24px
radius-pill: 999px
```

## Shadow Tokens

```
shadow-sm: 0 1px 2px rgba(20, 22, 24, 0.06)
shadow-md: 0 4px 12px rgba(20, 22, 24, 0.08)
shadow-lg: 0 10px 30px rgba(20, 22, 24, 0.12)
```

## Component Token Mappings

### Button - Primary (deep-blue CTA)

```
background:       var(--color-primary-dark)     #005A99
color:            var(--color-text-on-primary)  #FFFFFF
hover-background: #014978
border-radius:    var(--radius-pill)            999px
padding-x:        20px
padding-y:        10px
font-size:        15px
font-weight:      700
```

### Button - Brand (signature light blue)

```
background:       var(--color-primary)          #53A7DB
color:            var(--color-text-on-primary)  #FFFFFF
hover-background: var(--color-primary-hover)    #3D95CB
border-radius:    var(--radius-pill)            999px
font-weight:      600
```

### Button - Accent (cyan)

```
background:       var(--color-accent)         #0CB4CE
color:            var(--color-text-on-accent) #FFFFFF
hover-background: var(--color-accent-hover)   #0998AE
border-radius:    var(--radius-pill)          999px
```

### Button - Outline

```
background:       transparent
color:            var(--color-primary-dark)   #005A99
border:           1px solid var(--color-primary-dark)
hover-background: rgba(0, 90, 153, 0.05)
border-radius:    var(--radius-pill)          999px
```

### Button - Ghost

```
background:       transparent
color:            var(--color-primary-dark)   #005A99
hover-background: rgba(20, 22, 24, 0.04)
```

### Card

```
background:    var(--color-surface)           #F7F7F7
border:        1px solid var(--color-border)  #EAEAEA
border-radius: var(--radius-lg)               16px
padding:       var(--space-lg)                24px
box-shadow:    var(--shadow-sm)
```

### Input

```
background:       #FFFFFF
border:           1px solid var(--color-border) #EAEAEA
border-radius:    var(--radius-md)              8px
padding-x:        12px
padding-y:        10px
font-size:        14px
focus-border:     var(--color-primary)          #53A7DB
focus-shadow:     0 0 0 1px rgba(83, 167, 219, 0.4)
```

### Chip/Tag

```
background:    var(--color-accent-soft)   #CDEFF4
color:         var(--color-accent-hover)  #0998AE
border-radius: var(--radius-pill)         999px
padding-x:     10px
padding-y:     4px
font-size:     12px
```

### Link

```
color:            var(--color-primary-dark) #005A99
hover-color:      var(--color-accent)       #0CB4CE
underline-offset: 2px
```

## Tailwind Class Mappings

### Colors

| Token | Tailwind Class |
|-------|----------------|
| primary | `bg-primary` `text-primary` |
| primary-dark | `bg-primary-dark` `text-primary-dark` |
| primary-light | `bg-primary-light` |
| accent | `bg-accent` `text-accent` |
| accent-soft | `bg-accent-soft` |
| surface | `bg-surface` |
| text | `text-foreground` |
| text-muted | `text-muted` |
| border | `border-border` |
| error | `text-error` `bg-error` |
| success | `text-success` `bg-success` |
| warning | `text-warning` `bg-warning` |

### Spacing

| Token | Tailwind Class |
|-------|----------------|
| space-xs | `p-1` `m-1` `gap-1` |
| space-sm | `p-2` `m-2` `gap-2` |
| space-md | `p-4` `m-4` `gap-4` |
| space-lg | `p-6` `m-6` `gap-6` |
| space-xl | `p-8` `m-8` `gap-8` |
| space-xxl | `p-12` `m-12` `gap-12` |

### Border Radius

| Token | Tailwind Class |
|-------|----------------|
| radius-sm | `rounded-sm` |
| radius-md | `rounded-md` |
| radius-lg | `rounded-lg` |
| radius-xl | `rounded-xl` |
| radius-pill | `rounded-full` |

### Shadows

| Token | Tailwind Class |
|-------|----------------|
| shadow-sm | `shadow-sm` |
| shadow-md | `shadow-md` |
| shadow-lg | `shadow-lg` |

## Usage Examples

### Primary CTA Button (Tailwind)

```html
<button class="bg-primary-dark text-white px-5 py-2.5 rounded-full font-bold hover:bg-[#014978] transition-colors">
  Zapytaj o ofertę
</button>
```

### Brand Button (Tailwind)

```html
<button class="bg-primary text-white px-5 py-2.5 rounded-full font-semibold hover:bg-primary-hover transition-colors">
  Dowiedz się więcej
</button>
```

### Card (Tailwind)

```html
<div class="bg-surface border border-border rounded-lg p-6 shadow-sm">
  <h3 class="text-h4 font-semibold text-foreground">Smart film</h3>
  <p class="text-muted mt-2">Kontrola prywatności jednym dotknięciem.</p>
</div>
```

### Input (Tailwind)

```html
<input
  type="text"
  class="w-full px-3 py-2.5 border border-border rounded-md text-sm focus:border-primary focus:ring-1 focus:ring-primary/40 outline-none"
  placeholder="Enter value..."
/>
```

### Chip (Tailwind)

```html
<span class="inline-flex px-2.5 py-1 bg-accent-soft text-accent-hover text-xs rounded-full font-medium">
  Nowość
</span>
```
