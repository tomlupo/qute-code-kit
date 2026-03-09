# Evo Dom Maklerski Design Tokens

Complete design token reference for implementing evo dm brand identity in web projects.

## Color Tokens

### Primary Colors

```
primary:          #0C2340  rgb(12, 35, 64)
primary-dark:     #02091A  rgb(2, 9, 26)
primary-light:    #1F3A5F  rgb(31, 58, 95)
primary-hover:    #10294F  rgb(16, 41, 79)
```

### Accent Colors

```
accent:           #2563EB  rgb(37, 99, 235)
accent-soft:      #DBEAFE  rgb(219, 234, 254)
accent-hover:     #1D4ED8  rgb(29, 78, 216)
```

### Background Colors

```
background:       #FFFFFF  rgb(255, 255, 255)
background-alt:   #F9FAFB  rgb(249, 250, 251)
surface:          #F1F5F9  rgb(241, 245, 249)
```

### Text Colors

```
text:             #0F172A  rgb(15, 23, 42)
text-muted:       #6B7280  rgb(107, 114, 128)
text-on-primary:  #FFFFFF  rgb(255, 255, 255)
text-on-accent:   #FFFFFF  rgb(255, 255, 255)
```

### Border Colors

```
border:           #E5E7EB  rgb(229, 231, 235)
border-strong:    #CBD5F5  rgb(203, 213, 245)
```

### Semantic Colors

```
error:            #DC2626  rgb(220, 38, 38)
success:          #16A34A  rgb(22, 163, 74)
warning:          #D97706  rgb(217, 119, 6)
info:             #0284C7  rgb(2, 132, 199)
```

## Typography Tokens

### Font Family

```
font-base:    -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
font-heading: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
```

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
shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.08)
shadow-md: 0 4px 12px rgba(15, 23, 42, 0.10)
shadow-lg: 0 10px 30px rgba(15, 23, 42, 0.15)
```

## Component Token Mappings

### Button - Primary

```
background:       var(--color-primary)       #0C2340
color:            var(--color-text-on-primary) #FFFFFF
hover-background: #10294F
border-radius:    var(--radius-pill)         999px
padding-x:        20px
padding-y:        10px
font-size:        15px
font-weight:      600
```

### Button - Accent

```
background:       var(--color-accent)        #2563EB
color:            var(--color-text-on-accent) #FFFFFF
hover-background: #1D4ED8
border-radius:    var(--radius-pill)         999px
```

### Button - Outline

```
background:       transparent
color:            var(--color-primary)       #0C2340
border:           1px solid var(--color-primary)
hover-background: rgba(12, 35, 64, 0.05)
border-radius:    var(--radius-pill)         999px
```

### Button - Ghost

```
background:       transparent
color:            var(--color-primary)       #0C2340
hover-background: rgba(15, 23, 42, 0.04)
```

### Card

```
background:    var(--color-surface)    #F1F5F9
border:        1px solid var(--color-border) #E5E7EB
border-radius: var(--radius-lg)        16px
padding:       var(--space-lg)         24px
box-shadow:    var(--shadow-sm)
```

### Input

```
background:       #FFFFFF
border:           1px solid var(--color-border) #E5E7EB
border-radius:    var(--radius-md)     8px
padding-x:        12px
padding-y:        10px
font-size:        14px
focus-border:     var(--color-accent)  #2563EB
focus-shadow:     0 0 0 1px rgba(37, 99, 235, 0.4)
```

### Chip/Tag

```
background:    var(--color-accent-soft) #DBEAFE
color:         var(--color-accent)      #2563EB
border-radius: var(--radius-pill)       999px
padding-x:     10px
padding-y:     4px
font-size:     12px
```

### Link

```
color:            var(--color-accent)  #2563EB
hover-color:      #1D4ED8
underline-offset: 2px
```

## Tailwind Class Mappings

### Colors

| Token | Tailwind Class |
|-------|----------------|
| primary | `bg-primary` `text-primary` |
| primary-dark | `bg-primary-dark` |
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

### Primary Button (Tailwind)

```html
<button class="bg-primary text-white px-5 py-2.5 rounded-full font-semibold hover:bg-primary-dark transition-colors">
  Click me
</button>
```

### Card (Tailwind)

```html
<div class="bg-surface border border-border rounded-lg p-6 shadow-sm">
  <h3 class="text-h4 font-semibold text-foreground">Card Title</h3>
  <p class="text-muted mt-2">Card content goes here.</p>
</div>
```

### Input (Tailwind)

```html
<input
  type="text"
  class="w-full px-3 py-2.5 border border-border rounded-md text-sm focus:border-accent focus:ring-1 focus:ring-accent/40 outline-none"
  placeholder="Enter value..."
/>
```

### Chip (Tailwind)

```html
<span class="inline-flex px-2.5 py-1 bg-accent-soft text-accent text-xs rounded-full">
  Tag
</span>
```
