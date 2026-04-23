# Impeccable Design Workflow

> Design-aware code review and polish via the [Impeccable](https://impeccable.style/) plugin (v2.1, Apache 2.0, by [@pbakaus](https://github.com/pbakaus/impeccable)).

Companion plugin — not vendored into this kit. Install it alongside `qute-essentials` when you want Claude to reason about typography, color, spacing, motion, and UX writing instead of only correctness.

## What it is

A design skill set plus a deterministic detection engine. 18 slash commands teach Claude a concrete design vocabulary; 25 anti-pattern rules catch the usual AI-generated tells (gradient text, purple gradients, Inter everywhere, nested cards, low-contrast text, emoji-only nodes, etc.) before they ship.

Release timeline:
- **v2.1** — 2026-04-09 — 21 → 18 commands; `/arrange` → `/layout`, `/normalize` folded into `/polish`, `/onboard` folded into `/harden`, `/extract` became a sub-mode.
- **v2.0** — 2026-04-08 — data-driven rewrite against an internal eval framework that measures output monoculture; stronger font/color diversity; cross-model support.

## Install

Pick one. All leave a `.claude/` tree at project or user scope.

```bash
# Marketplace (recommended — updates cleanly)
/plugin marketplace add pbakaus/impeccable
/plugin                                    # enable "impeccable"

# Universal installer (auto-detects harness)
npx skills add pbakaus/impeccable

# CI / pre-commit scanner (no harness needed)
npm i -g impeccable
npx impeccable detect src/
```

Prefixed variant (`/i-polish`, `/i-audit`, …) exists if the default names collide with your other skills.

## One-time project setup

```
/impeccable teach
```

Writes `.impeccable.md` with your project's design context (brand, fonts, palette, tone). Every subsequent command reads it — skip this and results regress to generic defaults.

Commit `.impeccable.md`. Treat it like a design ADR.

## Core commands

Grouped by when you reach for them. Exact set per v2.1.

### Shape & polish

| Command | Use when |
|---------|----------|
| `/polish` | Default "make this better" pass — typography, spacing, color, hierarchy. Absorbs the old `/normalize`. |
| `/layout` | Restructure page or component layout (renamed from `/arrange`). |
| `/typeset` | Pure typography pass — type scale, line-height, tracking, font pairings. |
| `/overdrive` | Aggressive redesign — use when `/polish` is too timid. |

### Audit & detect

| Command | Use when |
|---------|----------|
| `/audit` | Run the 25-rule detection engine against the current view/file and report findings with fixes. |
| `/harden` | Accessibility + robustness pass (contrast, focus states, keyboard nav). Absorbs the old `/onboard`. |

### Supporting

The remaining commands cover motion, interaction states, responsive breakpoints, UX writing, color systems, and extraction of existing design tokens. Run `/plugin` after install to see the full list with in-harness descriptions.

## Typical flows

### A. New component from scratch

```
1. superpowers:brainstorming   → clarify what the component is for
2. Claude drafts the component
3. /polish                     → fixes obvious tells (gradient text, Inter, etc.)
4. /harden                     → a11y + keyboard
5. /audit                      → confirm detection engine is clean
6. architecture-diagram        → drop a diagram into the PR if it's structural
```

### B. Fixing LLM-generated slop in an existing repo

```
1. npx impeccable detect src/      # scan first — no harness needed
2. /impeccable teach               # if .impeccable.md doesn't exist yet
3. /audit <file>                   # per-file triage
4. /polish <file>                  # apply fixes; review diff
5. /gbu                            # qute-essentials review of the polish pass
```

### C. Design system extraction

```
1. /audit src/components/    → find what's already in use
2. /typeset                  → lock the type scale
3. Commit .impeccable.md     → now every future change inherits the system
```

### D. CI / pre-commit

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: impeccable
      name: impeccable detect
      entry: npx impeccable detect
      language: system
      pass_filenames: true
      files: \.(tsx?|jsx?|css|scss)$
```

Fails the commit on hard rules (gradient text, contrast < AA). Warnings-only for softer rules.

## Pairing with qute-code-kit

| Kit component | How it interacts with Impeccable |
|---------------|----------------------------------|
| `ui-ux-pro-max` skill (webdev bundle) | Strategic UX review; Impeccable is the tactical pass after it |
| `code-quality` skill | Runs on code correctness; Impeccable runs on design quality — use both |
| `architecture-diagram` skill | System-level diagrams; Impeccable polishes the UI surface those systems render |
| `/guard` from qute-essentials | Leave guards on — Impeccable only edits files, never shells or network |
| `/gbu`, `/wtf` from qute-essentials | Good review partners for a `/polish` or `/overdrive` diff |
| Chrome extension | Pairs with the `chrome-devtools` MCP (webdev bundle) — overlay detection while you debug live |

## Gotchas

- **No `.impeccable.md` = monoculture outputs.** Run `/teach` first, always.
- **`/overdrive` is not idempotent.** Re-running produces a different design each time — commit between runs.
- **Prefix variants are separate commands.** If you installed the prefixed zip, `/polish` won't exist — it's `/i-polish`. Don't mix.
- **The detection engine runs client-side.** No code or content leaves your machine; safe to use on private repos.
- **Cross-harness skill files.** The repo ships `.claude/`, `.cursor/skills`, `.gemini/skills`, etc. — only the `.claude/` tree matters for Claude Code; ignore the rest.

## Links

- Site: https://impeccable.style/
- Install docs: https://impeccable.style/install
- Source: https://github.com/pbakaus/impeccable
- Chrome extension: [Chrome Web Store](https://chromewebstore.google.com/detail/impeccable/bdkgmiklpdmaojlpflclinlofgjfpabf)
