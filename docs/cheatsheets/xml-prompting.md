# XML Prompting Cheatsheet

XML tags in prompts leverage how Anthropic models were trained — structured reasoning, context isolation, enforced constraints.

## Basic Template

```xml
<task>Describe the main objective</task>
<context>Provide background info</context>
<constraints>List limitations or rules</constraints>
<output_format>Specify response structure</output_format>
```

## Key Techniques

### Chain-of-Thought

```xml
<reasoning>
Think through this step-by-step:
1. First, consider X
2. Then evaluate Y
3. Finally, conclude Z
</reasoning>
```

### Content Isolation

```xml
<good_example>This is how to do it well</good_example>
<bad_example>Avoid this approach</bad_example>
<your_task>Now apply the good example</your_task>
```

### Validation Rules

```xml
<validation_rules>
- Output must be under 200 words
- Include exactly 3 bullet points
- Cite 2 sources
</validation_rules>
```

### Document Analysis

```xml
<source_document>Paste long text here</source_document>
<analysis_framework>
- Key findings
- Methodology critique
- Practical applications
</analysis_framework>
<output>Executive summary</output>
```

### Nested Hierarchy

```xml
<primary_goal>
Write a technical blog post
  <audience>Senior engineers</audience>
  <tone>Authoritative but accessible</tone>
</primary_goal>
```

Outer tags = higher priority. Nest for specifics.

## Tips

- Start simple, add nesting as needed
- Don't overload — keep tags focused
- Structure everything, avoid conversational style
- Larger models handle complex hierarchies better
