# AI Client Mappings

How the canonical `.agents` folder maps to each AI client's configuration.
Inspired by [dotagents](https://github.com/iannuttall/dotagents).

## Concept

Maintain **one** `.agents` directory as the source of truth. Use symlinks to
distribute configuration across all your AI coding tools.

```
.agents/                    # Canonical source of truth
├── AGENTS.md               # Universal prompt (fallback for all clients)
├── CLAUDE.md               # Claude-specific override (optional)
├── GEMINI.md               # Gemini-specific override (optional)
├── commands/               # Slash commands
├── hooks/                  # Event hooks
├── skills/                 # Domain skills (SKILL.md frontmatter)
└── backup/                 # Timestamped backups
```

## Global Scope Mappings

| Source | Target | Client |
|--------|--------|--------|
| `.agents/CLAUDE.md` | `~/.claude/CLAUDE.md` | Claude Code |
| `.agents/AGENTS.md` | `~/.claude/CLAUDE.md` | Claude Code (fallback) |
| `.agents/GEMINI.md` | `~/.gemini/GEMINI.md` | Gemini |
| `.agents/AGENTS.md` | `~/.gemini/GEMINI.md` | Gemini (fallback) |
| `.agents/AGENTS.md` | `~/.codex/AGENTS.md` | Codex |
| `.agents/AGENTS.md` | `~/.cursor/AGENTS.md` | Cursor |
| `.agents/AGENTS.md` | `~/.config/opencode/AGENTS.md` | OpenCode |
| `.agents/AGENTS.md` | `~/.factory/AGENTS.md` | Factory |
| `.agents/AGENTS.md` | `~/.config/amp/AGENTS.md` | Ampcode |
| `.agents/commands/` | `~/.claude/commands/` | Claude Code |
| `.agents/commands/` | `~/.gemini/commands/` | Gemini |
| `.agents/commands/` | `~/.codex/commands/` | Codex |
| `.agents/commands/` | `~/.cursor/commands/` | Cursor |
| `.agents/commands/` | `~/.config/opencode/commands/` | OpenCode |
| `.agents/commands/` | `~/.factory/commands/` | Factory |
| `.agents/commands/` | `~/.config/amp/commands/` | Ampcode |
| `.agents/hooks/` | `~/.claude/hooks/` | Claude Code |
| `.agents/hooks/` | `~/.factory/hooks/` | Factory |
| `.agents/skills/` | `~/.claude/skills/` | Claude Code |
| `.agents/skills/` | `~/.gemini/skills/` | Gemini |
| `.agents/skills/` | `~/.codex/skills/` | Codex |
| `.agents/skills/` | `~/.cursor/skills/` | Cursor |
| `.agents/skills/` | `~/.config/opencode/skills/` | OpenCode |
| `.agents/skills/` | `~/.config/amp/skills/` | Ampcode |

## Project Scope Mappings

Same structure, but rooted at the project directory instead of `~/`:

| Source | Target | Client |
|--------|--------|--------|
| `.agents/AGENTS.md` | `.claude/CLAUDE.md` | Claude Code |
| `.agents/commands/` | `.claude/commands/` | Claude Code |
| `.agents/skills/` | `.claude/skills/` | Claude Code |
| ... | ... | (same pattern for all clients) |

## Prompt File Precedence

For Claude and Gemini, client-specific files take priority:

1. **Claude**: `CLAUDE.md` (if exists) > `AGENTS.md` (fallback)
2. **Gemini**: `GEMINI.md` (if exists) > `AGENTS.md` (fallback)
3. **All others**: `AGENTS.md` directly

## Feature Support by Client

| Client | Commands | Hooks | Skills | Prompt |
|--------|----------|-------|--------|--------|
| Claude Code | ✓ | ✓ | ✓ | ✓ |
| Gemini | ✓ | | ✓ | ✓ |
| Codex | ✓ | | ✓ | ✓ |
| Cursor | ✓ | | ✓ | ✓ |
| OpenCode | ✓ | | ✓ | ✓ |
| Factory | ✓ | ✓ | | ✓ |
| Ampcode | ✓ | | ✓ | ✓ |
