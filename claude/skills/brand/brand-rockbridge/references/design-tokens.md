# Rockbridge TFI Design Tokens

Complete design token reference for implementing Rockbridge TFI brand identity in web projects and PDF documents.

## Color Tokens

### Primary Colors (Teal)

```
primary:          #00A19A  rgb(0, 161, 154)
primary-dark:     #008A84  rgb(0, 138, 132)
primary-light:    #33B5AF  rgb(51, 181, 175)
primary-hover:    #008A84  rgb(0, 138, 132)
```

### Secondary / Dark Colors

```
dark:             #1D3D36  rgb(29, 61, 54)
dark-light:       #2A5249  rgb(42, 82, 73)
dark-hover:       #2A5249  rgb(42, 82, 73)
navy:             #1A2B3C  rgb(26, 43, 60)
```

### Accent / Gold Colors

```
gold:             #C9A45C  rgb(201, 164, 92)
gold-light:       #D4B978  rgb(212, 185, 120)
gold-soft:        #F5EDD8  rgb(245, 237, 216)
gold-hover:       #D4B978  rgb(212, 185, 120)
```

### Background Colors

```
background:       #FFFFFF  rgb(255, 255, 255)
background-alt:   #F5F7F6  rgb(245, 247, 246)
surface:          #EEF2F0  rgb(238, 242, 240)
surface-dark:     #1D3D36  rgb(29, 61, 54)
```

### Text Colors

```
text:             #1A1A1A  rgb(26, 26, 26)
text-muted:       #6B7280  rgb(107, 114, 128)
text-on-primary:  #FFFFFF  rgb(255, 255, 255)
text-on-dark:     #FFFFFF  rgb(255, 255, 255)
text-teal:        #00A19A  rgb(0, 161, 154)
```

### Border Colors

```
border:           #E5E7EB  rgb(229, 231, 235)
border-strong:    #00A19A  rgb(0, 161, 154)
border-dark:      #2A5249  rgb(42, 82, 73)
```

### Semantic Colors

```
error:            #DC2626  rgb(220, 38, 38)
success:          #16A34A  rgb(22, 163, 74)
warning:          #D97706  rgb(217, 119, 6)
info:             #00A19A  rgb(0, 161, 154)
```

### Chart Colors

```
chart-primary:    #00A19A  rgb(0, 161, 154)
chart-secondary:  #1D3D36  rgb(29, 61, 54)
chart-accent:     #C9A45C  rgb(201, 164, 92)
chart-positive:   #16A34A  rgb(22, 163, 74)
chart-negative:   #DC2626  rgb(220, 38, 38)
```

## Typography Tokens

### Font Family

```
font-base:    'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
font-heading: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif
font-pdf:     'Helvetica Neue', Helvetica, Arial, sans-serif
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
text-h5:    18px / 1.125rem
text-body:  16px / 1rem
text-small: 14px / 0.875rem
text-xs:    12px / 0.75rem
text-xxs:   10px / 0.625rem
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
radius-none: 0
radius-sm:   4px
radius-md:   8px
radius-lg:   16px
radius-xl:   24px
radius-pill: 999px
```

## Shadow Tokens

```
shadow-sm: 0 1px 2px rgba(29, 61, 54, 0.08)
shadow-md: 0 4px 12px rgba(29, 61, 54, 0.12)
shadow-lg: 0 10px 30px rgba(29, 61, 54, 0.16)
```

## Component Token Mappings

### Button - Primary

```
background:       var(--color-primary)       #00A19A
color:            var(--color-text-on-primary) #FFFFFF
hover-background: #008A84
border-radius:    var(--radius-pill)         999px
padding-x:        24px
padding-y:        12px
font-size:        16px
font-weight:      600
```

### Button - Secondary

```
background:       var(--color-dark)          #1D3D36
color:            var(--color-text-on-dark)  #FFFFFF
hover-background: #2A5249
border-radius:    var(--radius-pill)         999px
```

### Button - Outline

```
background:       transparent
color:            var(--color-primary)       #00A19A
border:           2px solid var(--color-primary)
hover-background: rgba(0, 161, 154, 0.08)
border-radius:    var(--radius-pill)         999px
```

### Button - Gold

```
background:       var(--color-gold)          #C9A45C
color:            var(--color-text)          #1A1A1A
hover-background: #D4B978
border-radius:    var(--radius-pill)         999px
```

### Card

```
background:    var(--color-background)  #FFFFFF
border:        1px solid var(--color-border) #E5E7EB
border-radius: var(--radius-lg)         16px
padding:       var(--space-lg)          24px
box-shadow:    var(--shadow-sm)
```

### Card - Surface

```
background:    var(--color-surface)     #EEF2F0
border:        1px solid var(--color-border) #E5E7EB
border-radius: var(--radius-lg)         16px
padding:       var(--space-lg)          24px
```

### Dark Section

```
background:    var(--color-dark)        #1D3D36
color:         var(--color-text-on-dark) #FFFFFF
padding:       var(--space-xl)          32px
accent-color:  var(--color-primary-light) #33B5AF
```

### Input

```
background:       #FFFFFF
border:           1px solid var(--color-border) #E5E7EB
border-radius:    var(--radius-md)      8px
padding-x:        16px
padding-y:        12px
font-size:        14px
focus-border:     var(--color-primary)  #00A19A
focus-shadow:     0 0 0 2px rgba(0, 161, 154, 0.2)
```

### Chip/Tag

```
background:    rgba(0, 161, 154, 0.1)
color:         var(--color-primary)     #00A19A
border-radius: var(--radius-pill)       999px
padding-x:     12px
padding-y:     4px
font-size:     12px
```

### Chip - Gold

```
background:    var(--color-gold-soft)   #F5EDD8
color:         var(--color-gold)        #C9A45C
```

### Risk Indicator Box

```
width:         32px
height:        32px
border:        1px solid var(--color-border) #E5E7EB
font-weight:   600
font-size:     14px

active:
  background:  var(--color-primary)     #00A19A
  color:       var(--color-text-on-primary) #FFFFFF
  border:      var(--color-primary)     #00A19A
```

### Data Table

```
header-background: var(--color-dark)    #1D3D36
header-color:      var(--color-text-on-dark) #FFFFFF
row-even:          var(--color-background-alt) #F5F7F6
row-odd:           var(--color-background) #FFFFFF
border:            1px solid var(--color-border) #E5E7EB
font-size:         14px
padding:           12px 16px
```

### Link

```
color:            var(--color-primary)  #00A19A
hover-color:      #008A84
underline-offset: 2px
```

## Tailwind Class Mappings

### Colors

| Token | Tailwind Class |
|-------|----------------|
| primary | `bg-primary` `text-primary` |
| primary-dark | `bg-primary-dark` |
| primary-light | `bg-primary-light` |
| dark | `bg-dark` `text-dark` |
| dark-light | `bg-dark-light` |
| gold | `bg-gold` `text-gold` |
| gold-soft | `bg-gold-soft` |
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
| radius-none | `rounded-none` |
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
<button class="bg-primary text-white px-6 py-3 rounded-full font-semibold hover:bg-primary-dark transition-colors">
  Zainwestuj teraz
</button>
```

### Secondary Button (Tailwind)

```html
<button class="bg-dark text-white px-6 py-3 rounded-full font-semibold hover:bg-dark-light transition-colors">
  Dowiedz si?? wi??cej
</button>
```

### Gold/Award Button (Tailwind)

```html
<button class="bg-gold text-foreground px-6 py-3 rounded-full font-semibold hover:bg-gold-light transition-colors">
  Zobacz nagrody
</button>
```

### Card (Tailwind)

```html
<div class="bg-white border border-border rounded-lg p-6 shadow-sm">
  <h3 class="text-h4 font-semibold text-foreground">Tytu?? karty</h3>
  <p class="text-muted mt-2">Tre???? karty.</p>
</div>
```

### Dark Section (Tailwind)

```html
<section class="bg-dark text-white py-12 px-8">
  <h2 class="text-h2 font-bold">Nag????wek sekcji</h2>
  <p class="text-primary-light mt-4">Tre???? z akcentem.</p>
</section>
```

### Risk Indicator (Tailwind)

```html
<div class="flex gap-0.5">
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">1</div>
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">2</div>
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">3</div>
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">4</div>
  <div class="w-8 h-8 bg-primary text-white border-primary flex items-center justify-center font-semibold text-sm">5</div>
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">6</div>
  <div class="w-8 h-8 border border-border flex items-center justify-center font-semibold text-sm">7</div>
</div>
```

### Data Table (Tailwind)

```html
<table class="w-full text-sm">
  <thead class="bg-dark text-white">
    <tr>
      <th class="p-3 text-left">Okres</th>
      <th class="p-3 text-right">Stopa zwrotu</th>
    </tr>
  </thead>
  <tbody>
    <tr class="bg-white border-b border-border">
      <td class="p-3">1M</td>
      <td class="p-3 text-right text-success">+1.72%</td>
    </tr>
    <tr class="bg-background-alt border-b border-border">
      <td class="p-3">3M</td>
      <td class="p-3 text-right text-success">+3.74%</td>
    </tr>
  </tbody>
</table>
```

### Chip (Tailwind)

```html
<span class="inline-flex px-3 py-1 bg-primary/10 text-primary text-xs rounded-full font-medium">
  Fundusz akcji
</span>
```

### Input (Tailwind)

```html
<input
  type="text"
  class="w-full px-4 py-3 border border-border rounded-md text-sm focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
  placeholder="Wpisz kwot??..."
/>
```
