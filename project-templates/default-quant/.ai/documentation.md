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

See work-organization.md for full directory structure. Keep documentation organized, use subdirectories when appropriate. Examples:

**`/docs/methodology/`** - Technical/academic approaches (could share externally)
- Examples: `research_design.md`, `evaluation_framework.md`, `statistical_methods.md`

**`/docs/instructions/`** - Operational guides (for humans and AI agents)
- Examples: `setup_guide.md`, `deployment_steps.md`, `troubleshooting.md`, `api_usage.md`

**`/docs/knowledge/`** - Domain expertise and context (business logic, quirks)
- Examples: `domain_glossary.md`, `business_rules.md`, `system_quirks.md`, `historical_context.md`

**`/docs/datasets/`** - Dataset documentation
- Examples: `customer_orders.md`, `weather_data.md` (see datasets.md for details)

**`/docs/reference/`** - Reference material (data dictionaries, benchmarks)
- Examples: `schema_reference.md`, `api_endpoints.md`, `performance_benchmarks.md`, `config_options.md`

**`/.ai/templates/`** - Documentation templates
- Examples: `dataset_template.md`, `analysis_template.md`

You can create new subdirectories as needed or kepp files in the root directory for smaller projects or/and when it makes sense.

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


