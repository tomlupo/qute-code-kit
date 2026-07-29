# Atlas — Personal Knowledge Compilation System

**Date:** 2026-04-03
**Status:** Design approved
**Repo:** `tomlupo/atlas` (to be created)
**Deploy:** `/home/tom/workspace/dev/atlas/`

## Overview

Atlas is a personal knowledge system that ingests content from external sources (starting with Raindrop), uses an LLM to compile it into an interlinked wiki, indexes all Obsidian vaults for unified search, and supports Q&A against the compiled knowledge. Inspired by Karpathy's LLM Knowledge Bases approach.

Atlas is the **vault master** — it indexes and searches across all Obsidian vaults but only writes to its own managed spaces.

## Architecture

**Three layers:**

1. **Core library** (`atlas/core/`) — all logic: ingest, compile, index, search, Q&A
2. **CLI** (`atlas/cli/`) — thin Typer wrapper for day-to-day use
3. **API** (`atlas/api/`) — FastAPI, added in Phase 4 for separate VPS deployment

**Stack:** Python 3.12, uv, Typer, SQLite + FTS5, Claude API (Anthropic SDK), Raindrop API

## Vault Hierarchy

Atlas manages and indexes the full Obsidian vault ecosystem at `/srv/obsidian/`:

| Vault | Path | Owner | Purpose |
|-------|------|-------|---------|
| `notebook` | `/srv/obsidian/notebook/` | Human | Personal notes, projects, areas, systems |
| `atlas` | `/srv/obsidian/atlas/` | Atlas (LLM) | Compiled wiki, raw ingests, Q&A outputs |
| `agents` | `/srv/obsidian/agents/` | Other agents | Shared agent read/write space |
| `diet` | `/srv/obsidian/diet/` | Human | Nutrition tracking |
| `quarkbook` | `/srv/obsidian/quarkbook/` | Human | Quark workspace |

**Write policy:** Atlas only writes to `/srv/obsidian/atlas/`. It reads everything.

The `agents` vault is a shared scratchpad — other agents (Telegram bot, agent-orchestrator) can drop content there, Atlas indexes it, and subsequent agent sessions have the context.

All vaults sync via Syncthing across devices and back up to GitHub via the existing 5-min git cron.

## Atlas Vault Structure

```
/srv/obsidian/atlas/
├── raw/                    # Ingested source material
│   ├── {collection}/       # Organized by Raindrop collection
│   │   └── {slug}.md       # Individual articles as markdown
│   └── manual/             # Future: manually dropped files
├── wiki/                   # LLM-compiled interlinked knowledge
│   ├── _index.md           # Master index with 1-line summaries
│   ├── concepts/           # Concept articles (synthesized from sources)
│   ├── summaries/          # Per-source summaries with key takeaways
│   └── connections.md      # Cross-cutting themes and surprising links
├── outputs/                # Q&A results, reports, lint reports
├── .atlas/                 # Atlas internal state
│   ├── index.db            # SQLite + FTS5 search index
│   └── state.json          # Sync timestamps, compilation hashes
└── .obsidian/              # Minimal Obsidian config
```

## Ingest Pipeline

**Source:** Raindrop API (primary, v1). Generic interface for future sources.

**Flow:**
1. Fetch bookmarks from a Raindrop collection via API
2. For each bookmark: fetch parsed content, convert to clean markdown with frontmatter
3. Save to `raw/{collection}/{slugified-title}.md`
4. Skip articles already ingested (dedup by Raindrop ID)

**Incremental:** Tracks last sync timestamp per collection in `state.json`. Subsequent runs only fetch new/updated bookmarks.

**Raw file format:**
```markdown
---
title: "Carry Strategies in Crypto Markets"
url: "https://example.com/article"
source: raindrop
collection: quant
tags: [crypto, carry, trading]
ingested: 2026-04-03
raindrop_id: 12345
---

# Carry Strategies in Crypto Markets

[full article content as markdown]
```

**Future ingest sources** (not built in v1):
- Obsidian Web Clipper drops into `raw/manual/`
- PDFs into `raw/papers/`
- GitHub repo READMEs into `raw/repos/`

## Wiki Compilation

LLM reads raw sources and compiles a structured, interlinked wiki.

**Flow:**
1. Read all files in `raw/` (or a specific collection)
2. Read current state of `wiki/` (if any)
3. Send batches to Claude API with compilation prompt:
   - Summarize each new raw source → `wiki/summaries/`
   - Identify concepts across sources → `wiki/concepts/`
   - Write/update concept articles with `[[wikilinks]]`
   - Maintain `wiki/_index.md` with brief descriptions
   - Add backlinks between articles
   - Update `wiki/connections.md` with cross-cutting themes

**Incremental:** Tracks content hash per raw file in SQLite. Only new/changed sources trigger recompilation. Full recompile available to find new cross-connections.

**Model selection:**
- Summaries: `claude-sonnet-4-6` (high throughput, good quality)
- Concept articles and connection-finding: `claude-opus-4-6` (deeper synthesis)
- Configurable in config file

**Concept article format:**
```markdown
---
type: concept
sources: [carry-strategies-in-crypto, funding-rate-explained]
related: [[funding-rate]], [[basis-trade]]
last_compiled: 2026-04-03
---

# Carry Trade

[LLM-written synthesis from multiple sources]

## Sources
- [[carry-strategies-in-crypto]] — [key insight]
- [[funding-rate-explained]] — [key insight]

## See Also
- [[funding-rate]]
- [[basis-trade]]
```

**Compilation prompt** stored as a template file in the project repo, iterable and versionable.

## Index & Search

**SQLite + FTS5** over all configured vaults.

**Schema:**
- `documents`: path, title, type (raw/concept/summary/note), source_vault, collection, tags, body, content_hash, last_indexed
- `documents_fts`: FTS5 virtual table over title + body + tags
- `links`: source_path, target_slug (extracted from `[[wikilinks]]`)

**Index stored at:** `/srv/obsidian/atlas/.atlas/index.db`

**Incremental:** Checks content hash, only re-indexes changed files.

**Configurable sources:**
```toml
[index]
sources = [
  { path = "/srv/obsidian/atlas", label = "atlas" },
  { path = "/srv/obsidian/notebook", label = "notebook" },
  { path = "/srv/obsidian/agents", label = "agents" },
]
```

## Q&A

Ask questions against the knowledge base, with search-backed context retrieval.

**Flow:**
1. Query goes through FTS5 search to find relevant articles
2. Top results loaded as context
3. Sent to Claude API with question + context
4. Response to stdout (default) or saved to `wiki/outputs/` with `--save`

Saved outputs get frontmatter and become part of the searchable wiki — the "queries add up" loop.

## Wiki Maintenance

**Lint** (`atlas lint`):
- Inconsistent claims across articles
- Orphan articles (no inbound links)
- Missing concepts (referenced in wikilinks but no article exists)
- Stale summaries (raw source updated, summary hasn't)
- Suggested new connections
- Report to `wiki/outputs/lint-{date}.md`
- `--fix` to auto-remediate

**Enhance** (`atlas enhance`):
- LLM reads wiki state, suggests new concept articles, deeper connections
- `--apply` to write improvements directly

## CLI Interface

```bash
# Ingest
atlas ingest --collection "quant"       # Fetch from Raindrop collection
atlas ingest --all                      # All collections

# Compile
atlas compile                           # Compile new raw sources into wiki
atlas compile --full                    # Full recompile
atlas compile --collection "quant"      # Specific collection

# Index
atlas index                             # Update search index

# Search & Q&A
atlas search "carry trade"              # Full-text search, all vaults
atlas search "carry" --type concept     # Wiki concepts only
atlas search "crypto" --source notebook # Only personal vault
atlas ask "what are the main carry strategies?" --save
atlas links "carry-trade"               # Backlink query

# Maintenance
atlas lint                              # Health check
atlas lint --fix                        # Auto-fix
atlas enhance                           # Suggest improvements
atlas enhance --apply                   # Apply improvements

# Info
atlas status                            # Stats and health overview
```

## Configuration

**File:** `~/.config/atlas/config.toml`

```toml
[vault]
path = "/srv/obsidian/atlas"

[raindrop]
# token in env: RAINDROP_API_TOKEN

[llm]
# key in env: ANTHROPIC_API_KEY
compile_model = "claude-sonnet-4-6"
qa_model = "claude-sonnet-4-6"
enhance_model = "claude-opus-4-6"

[index]
db_path = "/srv/obsidian/atlas/.atlas/index.db"
sources = [
  { path = "/srv/obsidian/atlas", label = "atlas" },
  { path = "/srv/obsidian/notebook", label = "notebook" },
  { path = "/srv/obsidian/agents", label = "agents" },
]
```

**Secrets** stored as environment variables (consistent with existing `~/.config/monitoring.env` pattern).

## Cron Integration

| Time | Job | Purpose |
|------|-----|---------|
| 06:00 | `atlas ingest --all && atlas compile && atlas index` | Daily: pull, compile, reindex |

Uses existing `run-job` wrapper + healthchecks.io monitoring.

## qute-code-kit Integration

- **Skill:** `claude/skills/my/atlas/SKILL.md` — lets Claude Code agents search and query the knowledge base via CLI
- **Replaces:** existing `obsidian-knowledge` agent (Atlas subsumes its functionality)
- **Bundle:** added to `minimal` bundle (all projects benefit from knowledge access)

## Project Structure

```
atlas/
├── atlas/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py      # Settings, paths, env vars
│   │   ├── ingest.py      # Raindrop → raw/ markdown
│   │   ├── compiler.py    # LLM: raw/ → wiki/
│   │   ├── indexer.py     # SQLite + FTS5
│   │   ├── search.py      # Query interface
│   │   ├── qa.py          # LLM Q&A with retrieval
│   │   ├── lint.py        # Wiki health checks
│   │   └── enhance.py     # Wiki enhancement
│   ├── cli/
│   │   └── app.py         # Typer CLI
│   ├── api/               # Empty — FastAPI added in Phase 4
│   └── prompts/           # LLM prompt templates
│       ├── compile.md
│       ├── summarize.md
│       ├── qa.md
│       ├── lint.md
│       └── enhance.md
├── pyproject.toml
├── tests/
└── README.md
```

## Build Phases

### Phase 1 — Foundation (MVP)
- Project scaffold (uv, pyproject.toml)
- Config loading (TOML + env vars)
- Raindrop ingest → `raw/` markdown files
- SQLite + FTS5 indexer over all configured vaults
- `atlas search`, `atlas status` CLI
- Atlas vault init at `/srv/obsidian/atlas/`
- Agents vault init at `/srv/obsidian/agents/`

### Phase 2 — Compilation
- LLM compiler: `raw/` → `wiki/` (summaries + concepts + index)
- Incremental compilation with hash tracking
- `atlas compile` CLI
- Cron job setup via `run-job`

### Phase 3 — Intelligence
- `atlas ask` — Q&A with search-backed context
- `atlas lint` — wiki health checks
- `atlas enhance` — suggest/apply improvements
- `--save` flag to file outputs back into wiki

### Phase 4 — Integration
- `atlas` skill for qute-code-kit (replaces `obsidian-knowledge` agent)
- FastAPI API layer for separate VPS deployment
- Additional ingest sources (PDFs, web clipper, GitHub repos)
