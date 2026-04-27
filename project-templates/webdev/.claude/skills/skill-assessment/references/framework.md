# Skill Assessment Framework

Based on Anthropic's internal skill engineering practices (April 2025). Use this as the scoring rubric when evaluating skills.

## The 9 Skill Categories

### 1. Library & API Reference
Skills explaining how to use a library, CLI, or SDK correctly. Include reference snippets and gotcha lists. Best when they cover internal or poorly-documented tools.

**Signals**: code examples, function signatures, edge cases, "don't do X" warnings.

### 2. Product Verification
Skills describing how to test/verify code is working. Often paired with external tools (Playwright, tmux, headless browsers). High-value when they enforce programmatic assertions.

**Signals**: test scripts, assertion patterns, verification workflows, video/screenshot capture.

### 3. Data Fetching & Analysis
Skills connecting to data/monitoring stacks. Include credentials patterns, dashboard IDs, common query workflows.

**Signals**: data source configs, query templates, helper libraries, fetch scripts.

### 4. Business Process & Team Automation
Skills automating repetitive workflows into one command. Often compose other skills or MCPs. Benefit from logging previous results for consistency.

**Signals**: workflow orchestration, log files, template outputs, multi-tool composition.

### 5. Code Scaffolding & Templates
Skills generating framework boilerplate. Combine scripts with natural language requirements. Most useful for org-specific conventions.

**Signals**: directory structure templates, file generators, annotation patterns, init scripts.

### 6. Code Quality & Review
Skills enforcing code quality. May include deterministic scripts for robustness. Good candidates for running via hooks or CI.

**Signals**: lint rules, review checklists, subagent critique patterns, style enforcement.

### 7. CI/CD & Deployment
Skills for fetching, pushing, and deploying code. May reference other skills for data.

**Signals**: build scripts, deploy workflows, rollback patterns, merge conflict resolution.

### 8. Runbooks
Skills taking a symptom → walking through investigation → producing structured report. Multi-tool diagnostic workflows.

**Signals**: symptom→tool mapping, diagnostic steps, structured output templates, escalation paths.

### 9. Infrastructure Operations
Skills for routine maintenance and operational procedures. May involve destructive actions needing guardrails.

**Signals**: cleanup scripts, approval workflows, cost queries, soak periods.

---

## The 8 Quality Dimensions

Score each 0-2 (0 = absent, 1 = partial, 2 = strong).

### D1. Description Targeting (0-2)
Does the `description` field tell the **model** when to trigger, not just describe what the skill does?

- **0**: Generic or missing description
- **1**: Describes functionality but not trigger conditions
- **2**: Includes trigger phrases, user intent patterns, and clear scope boundaries

### D2. Progressive Disclosure (0-2)
Does the skill use folder structure to layer information?

- **0**: Monolithic SKILL.md only, no supporting files
- **1**: Some supporting files but not well-organized or referenced
- **2**: Clear folder structure (references/, scripts/, assets/) with SKILL.md pointing to them at appropriate moments

### D3. Gotchas & Pitfalls (0-2)
Does the skill capture failure modes, edge cases, and "don't do X" warnings?

- **0**: No gotchas section or failure mode documentation
- **1**: Some warnings scattered in the text
- **2**: Dedicated gotchas/pitfalls section built from real failure experience, regularly updated

### D4. Non-Obvious Knowledge (0-2)
Does the skill push Claude beyond its default behavior? Does it contain information Claude wouldn't know?

- **0**: Mostly restates common knowledge Claude already has
- **1**: Mix of common and specialized knowledge
- **2**: Primarily contains org-specific, domain-specific, or counter-intuitive information

### D5. Actionable Scripts & Assets (0-2)
Does the skill provide runnable scripts, templates, or data files?

- **0**: Pure instructions, no executable assets
- **1**: Some code snippets in SKILL.md but not standalone scripts
- **2**: Standalone scripts, helper libraries, or template files that Claude can compose with

### D6. Flexibility vs. Railroading (0-2)
Does the skill give Claude information and flexibility rather than rigid step-by-step commands?

- **0**: Overly prescriptive, no room for adaptation
- **1**: Mostly prescriptive with some flexibility
- **2**: Provides context and constraints, lets Claude adapt to the situation

### D7. Setup & Configuration (0-2)
Does the skill handle first-time setup gracefully?

- **0**: Assumes everything is configured, fails silently if not
- **1**: Documents prerequisites but doesn't guide setup
- **2**: Detects missing config, guides user through setup, stores preferences (e.g., config.json pattern)

### D8. Composition & References (0-2)
Does the skill reference or compose with other skills, tools, or MCPs?

- **0**: Completely standalone, no awareness of ecosystem
- **1**: Mentions related tools but doesn't integrate
- **2**: Explicitly references other skills, composes workflows, or chains outputs

---

## External Tools & References

Tools that complement skill assessment or serve as exemplars for specific categories.

### Ultimate Bug Scanner (UBS)

**Repository**: https://github.com/Dicklesworthstone/ultimate_bug_scanner
**Category relevance**: Code Quality & Review (6), Product Verification (2)

Static analysis tool detecting 1000+ bug patterns across 9 languages (JS/TS, Python, C/C++, Rust, Go, Java, Ruby, Swift, C#). Designed as "The AI Coding Agent's Secret Weapon" — targets bugs that commonly slip through AI-assisted development.

**Why it matters for skill assessment**:
- Exemplar of a **Code Quality** tool that could be wrapped as a skill — meta-runner architecture, per-language modules, unified reporting
- Outputs in TOON format (token-optimized, ~50% smaller than JSON) — purpose-built for LLM consumption, a pattern worth adopting in skills that produce structured output
- Git-aware scanning (`--staged`, `--diff`) — shows how skills can be scoped to only changed code
- Baseline comparison (`--comparison=<baseline.json>`) — demonstrates regression tracking, useful for skills that run repeatedly
- Strictness profiles (`--profile=strict|loose`) — good pattern for skills that need different modes
- `ubs doctor` self-diagnostic — exemplar for D7 (Setup & Configuration): detects broken deps, auto-repairs with `--fix`

**Assessment integration**: When evaluating Code Quality skills, compare their coverage and sophistication against UBS patterns. A good code quality skill should at minimum support: scoped scanning (not whole repo), machine-readable output, and suppression of known issues.

---

## Category Gap Assessment Guide

When evaluating a skill universe, check coverage across all 9 categories. Common gaps in developer toolkits:

- **Product Verification** is often missing — teams write code but don't skill-ify their testing
- **Runbooks** are usually in wikis, not skills — huge opportunity to make them actionable
- **Code Quality & Review** often exists as linter config but not as a review skill
- **Infrastructure Operations** is underserved — operations knowledge stays in people's heads
- **Business Process** skills have the highest ROI when they compose other skills
