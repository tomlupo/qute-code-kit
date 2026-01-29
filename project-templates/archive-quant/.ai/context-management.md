# Context Management Strategies

Guidelines for managing token/context budget when working with large content sources (vaults, codebases, PDFs, documentation).

## Core Principle

Context is precious. Search before reading, extract before loading, summarize aggressively.

## Detecting Context Pressure

Watch for:
- Large sources (vaults with hundreds of files, codebases with many modules)
- Lengthy files (10,000+ words, 500+ lines)
- Multiple file reads in single session
- Deep exploration chains (5+ levels of links/references)

## Smart Retrieval Strategies

### Strategy 1: Search Before Reading

```bash
# Don't read blindly - search first
# Find relevant files BEFORE reading them
grep -r "kubernetes" docs/knowledge/  # Find matches
# Then read only relevant files
```

### Strategy 2: Targeted Search

- Use tags, folders, or metadata for categorical queries
- Search specific paths rather than entire repositories
- Use filename search for quick discovery

### Strategy 3: Build Lightweight Index

```bash
# Create index to avoid repeated reading
cat > .claude/index/file_catalog.json << 'EOF'
{
  "filename.md": {
    "tags": ["topic1", "topic2"],
    "sections": ["Section A", "Section B"],
    "summary": "Brief description"
  }
}
EOF
```

### Strategy 4: Progressive Reading

**Phase 1: Metadata Only** (minimal context)
- Read frontmatter, headers, first few lines

**Phase 2: Summary/Abstract** (if relevant)
- First 20-50 lines usually contain overview

**Phase 3: Specific Section** (targeted)
- Extract only the section you need

**Phase 4: Full Read** (only if critical)
- Read complete file only when absolutely necessary

## Handling Low Context During Exploration

When context warning appears:

```markdown
## Context Low Detected

**Exploration Status**:
- Files scanned: 45
- Files read fully: 8
- Key findings: Documented

**Options**:
A) Run `/compact` to continue
B) Focus on specific topic (read only relevant files)
C) Use summary file for remainder of session

**Saving Knowledge Extract**:
[Create digest file with key findings]
```

## File-Based Knowledge Extraction

### Create Digests

Instead of keeping all content in context, extract key information:

```bash
# Extract key points to digest file
cat > .claude/digests/topic_knowledge.md << 'EOF'
# Topic Knowledge Digest

## From: file1.md
**Key Points**:
- Point 1
- Point 2

## From: file2.md
**Key Points**:
- Point 1
- Point 2
EOF
```

### Maintain Reading History

```bash
# Track what's been read to avoid duplicates
echo "$(date) | filename.md | Key insight extracted" >> .claude/reading_log.txt

# Check before reading
grep "filename.md" .claude/reading_log.txt
```

## Smart Link/Reference Following

### Limit Depth

```markdown
**Level 0**: Main file
- Reading... done
- Links found: 4

**Level 1**: Following links...
- Key points extracted from each

**Level 2**: Found 12 more links

## Context Warning
Going deeper fills context. Options:
A) Create link map (visual overview)
B) Specify which links to explore
C) Save findings and continue fresh
```

### Selective Following

Don't automatically read every linked file. Build a map first:

```bash
# Map links without reading content
grep -o '\[\[.*\]\]' file.md | sort -u
# User chooses which to explore
```

## Context-Efficient Conversation Flow

### Large Source Exploration

```markdown
User: "Tell me everything in [large source]"

Response:
"Source has 127 files. To explore efficiently:

**Quick Overview** (context-light):
- Count files by topic/category
- Show structure without reading

**Results**:
- 45 files: category A
- 32 files: category B

**Context Used**: 15%

**Next Steps** (your choice):
A) Deep dive on one topic
B) Create topic summaries
C) Search for specific information
D) Build comprehensive index

Which approach fits your needs?"
```

### Targeted Search Flow

```markdown
User: "Find information about [topic]"

**Searching...**
Found in 8 files

**Most Relevant**: file_x.md

**Options**:
A) Read all 8 files (~70% context)
B) Read top 3 (balanced)
C) Read only most relevant (focused)

Recommendation: Option C keeps context healthy.
```

## Proactive Context Warnings

### Before Large Operations

```markdown
"About to follow a chain 6 levels deep.

**Estimated Impact**: ~85% context usage

**Smarter Approach**:
- Build map visually (10% context)
- You choose which branches to explore
- I read only selected paths deeply

This preserves context. Agree?"
```

### Auto-Summarize Large Files

For files over 500 lines:
1. Extract structure (headers)
2. Read first 50 lines
3. Create summary instead of full read
4. Offer full read only if specifically needed

## Best Practices Checklist

### Before Reading
- [ ] Search first, read second
- [ ] Check file size (>500 lines? summarize)
- [ ] Read sections, not full files when possible
- [ ] Already at 60% context? Extract to file

### During Exploration
- [ ] Monitor context every 5-7 files read
- [ ] Save key findings to digest files
- [ ] Build index instead of reading everything
- [ ] Limit reference/link following (3 levels max)

### When Context Low
- [ ] Stop reading, start summarizing
- [ ] Create knowledge digest file
- [ ] Build map for visual overview
- [ ] Offer `/compact` or focused next steps

### Always
- [ ] Provide file paths for reference
- [ ] Show summaries over full content
- [ ] Track what's been read (avoid duplicates)
- [ ] Warn before deep exploration
