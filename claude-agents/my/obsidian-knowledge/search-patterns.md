# Search Patterns

## Obsidian MCP Search

### By Content
```
mcp__obsidian__search-vault(vault="knowledge", query="kubernetes deployment")
```

### By Tag
```
mcp__obsidian__search-vault(vault="knowledge", query="tag:devops/kubernetes")
mcp__obsidian__search-vault(vault="knowledge", query="tag:project/advisory")
```

### By Path
```
mcp__obsidian__search-vault(vault="knowledge", query="deployment", path="projects/advisory")
```

### Combined
```
mcp__obsidian__search-vault(vault="knowledge", query="API tag:backend", path="technical")
```

## docs/knowledge/ Search

### Find All Markdown Files
```
Glob(pattern="docs/knowledge/**/*.md")
```

### Search by Content
```
Grep(pattern="kubernetes", path="docs/knowledge/")
Grep(pattern="deployment config", path="docs/knowledge/technical/")
```

### Find by Filename Pattern
```
Glob(pattern="docs/knowledge/**/setup*.md")
Glob(pattern="docs/knowledge/**/2024*.md")
```

## Obsidian Syntax Parsing

### Wikilinks
- `[[note-name]]` - Link to note
- `[[note-name#heading]]` - Link to heading
- `[[note-name|display text]]` - Aliased link

### Tags
- `#tag` - Simple tag
- `#parent/child` - Nested tag
- Tags in frontmatter: `tags: [tag1, tag2]`

### Frontmatter
```yaml
---
title: "Note Title"
tags: [project, technical]
created: 2024-01-15
status: active
---
```

### Block References
- `![[note#^blockid]]` - Embedded block
- `^blockid` - Block identifier

## Search Strategy by Query Type

### "What do we know about X?"
1. Search Obsidian: `query="X"`
2. Search docs: `Grep(pattern="X", path="docs/knowledge/")`
3. Read top 3-5 matches
4. Synthesize findings

### "Find notes tagged with X"
1. Search Obsidian: `query="tag:X"`
2. Search docs frontmatter: `Grep(pattern="tags:.*X")`

### "What did we decide about X?"
1. Search Obsidian: `query="decision X" OR query="decided X"`
2. Look in project notes and meeting notes
3. Check for ADR (Architecture Decision Records) patterns

### "Show me documentation for X"
1. Search docs/knowledge/ first: `Grep(pattern="X", path="docs/knowledge/")`
2. Then Obsidian: `query="X documentation" OR query="X guide"`

## Link Following Strategy

### When to Follow Links
- Linked note is directly relevant to query
- Understanding requires context from linked note
- User asks for comprehensive coverage

### Depth Limits
- **Depth 1**: Always follow direct links in relevant notes
- **Depth 2**: Follow if link title matches query terms
- **Depth 3**: Only for comprehensive research requests
- **Beyond 3**: Rarely - risk of context overflow

### Building Link Maps
```markdown
## Link Map: [Starting Note]

### Direct Links (Depth 1)
- [[Link 1]] - [Relevance: High/Medium/Low]
- [[Link 2]] - [Relevance: High/Medium/Low]

### Secondary Links (Depth 2)
- From [[Link 1]]:
  - [[Sub-link 1]]
  - [[Sub-link 2]]

### Recommendation
Follow: [[Link 1]], [[Sub-link 1]]
Skip: Low relevance links
```

## Output Formatting

### Source Citations
Always cite sources clearly:

```markdown
## Found in Vault: [Topic]

### Primary Source
**Vault**: knowledge
**Note**: [[path/to/note]]
**Tags**: #tag1 #tag2

[Key information extracted]

### Also Found In
- [[Related Note 1]] - Brief description
- `docs/knowledge/file.md` - Brief description
```

### When Information Not Found
```markdown
❌ **Not Found**: "[Query]"

**Searched**:
- Obsidian vault "knowledge" - No matches
- docs/knowledge/ - No matches

**Suggestions**:
1. Try alternative terms: [suggestions]
2. Create new note to capture this knowledge
3. Check if information exists elsewhere

**Would you like me to**:
- Create a placeholder note for this topic?
- Search with different terms?
```
