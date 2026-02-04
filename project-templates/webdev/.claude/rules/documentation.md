---
paths:
  - "docs/**/*"
  - "**/*.md"
---

# Documentation Guidelines

## Document Length
- **Target**: 100-250 lines for most documents
- **Exception**: Complex topics may require longer docs (300-500 lines)
- **Always**: Include a note at the top if exceeding 250 lines explaining why
- **Focus**: Prioritize clarity and actionability over exhaustiveness

## Documentation Style
- Use clear headings and structure
- Include code examples where relevant
- Add dates to time-sensitive content
- Keep language concise and direct
- Use bullet points and tables for scannability

## Documentation Directory Structure

See work-organization.md for full directory structure. Two organizational patterns:

### Pattern 1: By Type (cross-cutting)

This is the primary pattern used in practice.

**`/docs/instructions/`** - Operational guides (for humans and AI agents)
- Examples: `setup_guide.md`, `deployment_steps.md`, `troubleshooting.md`, `quick-start.md`

**`/docs/methodology/`** - Technical/academic approaches (could share externally)
- Examples: `research_design.md`, `evaluation_framework.md`, `statistical_methods.md`

**`/docs/reference/`** - Reference material (data dictionaries, benchmarks)
- Examples: `schema_reference.md`, `features.md`, `metrics.md`, `config-format.md`

**`/docs/research/`** - Dated research findings and experiments
- Examples: `2025-01-feature-comparison.md`, `2025-02-model-experiment.md`
- Use `/experiment-document` command or `research-docs` skill to create structured findings

**`/docs/models/`** - Design specifications for models and frameworks
- Examples: `tactical-3p-model.md`, `portfolio-construction-framework.md`

**`/docs/datasets/`** - Dataset documentation
- Examples: `customer_orders.md`, `weather_data.md` (see datasets skill for details)

**`/docs/papers/`** - External research papers and domain notes
- Examples: academic papers, industry white papers

**`/docs/tasks/`** - Task planning and archival (integrates with session workflow)
- Active tasks: `{task-slug}.md` - planning, architecture, acceptance criteria
- Completed: `completed/{task-slug}.md` - archived with completion notes
- See workflow.md for Task-Session Integration details

### Reference Hierarchy

Documentation layers follow a one-way reference pattern:

```
instructions/  →  reference/    (link TO)
instructions/  →  methodology/  (link TO)
reference/     ✗  instructions/ (no back-link)
methodology/   ✗  instructions/ (no back-link)
models/        →  instructions/ (link TO)
models/        →  research/     (link TO)
```

**Source of truth:** `reference/` and `methodology/`
**Operational docs:** `instructions/`

This ensures progressive disclosure: start with instructions, drill into reference/methodology as needed.

### Pattern 2: By Artifact (self-contained, optional)

**`/docs/{artifact}/`** - All documentation for a specific feature, module, or deliverable
- Structure: `README.md` + subfolders as needed
- Common subfolders: `instructions/`, `methodology/`, `reference/`, `research/`, `ideas/`
- Example: `docs/fund_ratings/` with `README.md`, `instructions/`, `research/`

Use artifact-based structure when:
- Feature has substantial documentation (5+ files)
- Documentation spans multiple types (methodology + instructions + reference)
- Team needs a single entry point for the feature

Note: This pattern is available but the by-type pattern is more commonly used in practice.

### Templates

This plugin bundles a dataset documentation template at `templates/dataset_template.md`. Use it when creating `docs/datasets/{name}.md` files.

Projects may also keep templates in `/.ai/templates/` for other document types.

Create new subdirectories as needed. Keep files in root `/docs/` for smaller projects.

## Best Practices

### Writing Effective Documentation
- **Start with purpose**: State what the document covers and who it's for
- **Use examples**: Show, don't just tell - include concrete examples
- **Be specific**: Use actual values, dates, and results rather than placeholders
- **Link appropriately**: Cross-reference related docs, but never reference `scratch/` content
- **Update dates**: Mark when content was last updated, especially for time-sensitive info
- **Code examples**: Include working code snippets with context
- **Visual aids**: Use tables, lists, and diagrams when they clarify structure

### Documentation Structure
- **Introduction**: Brief overview and purpose
- **Main content**: Organized with clear headings
- **Examples**: Practical illustrations
- **Reference**: Quick lookup sections (if applicable)
- **Related docs**: Links to related documentation

### Common Patterns
- **Setup guides**: Prerequisites → Installation → Configuration → Verification
- **API docs**: Endpoint → Parameters → Response → Examples → Errors
- **Dataset docs**: Source → Schema → Processing → Usage → Quality metrics
- **Troubleshooting**: Problem → Symptoms → Solution → Prevention
