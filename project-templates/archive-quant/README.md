# Default Config

A comprehensive templates and configuration repository for standardizing development workflows, AI agent guidance, and project setup across all work.

## Overview

This repository contains reusable templates, configurations, and guidelines that can be copied or referenced when starting new projects. It provides:

- **AI Agent Guidance**: Standardized rules and guidelines for AI coding assistants (Claude, Cursor, etc.)
- **Project Templates**: Starter templates for common project structures
- **Configuration Files**: VS Code settings, MCP server configs, and tool configurations
- **Documentation Standards**: Templates and guidelines for consistent documentation
- **Workflow Definitions**: Standardized workflows and best practices

## Quick Start

1. **Copy relevant files** to your new project:
   - Copy `AGENTS.md` and `CLAUDE.md` to the project root
   - Copy `.ai/` directory if you want AI agent guidance
   - Copy `.claude/` directory if using Claude-specific features
   - Copy `.vscode/` settings if desired

2. **Customize**:
   - Update `CLAUDE.md` with project-specific rules
   - Adjust `.ai/` files to match your project's needs
   - Modify VS Code settings as needed

3. **Reference templates**:
   - Use templates from `templates/` directory
   - Reference `.ai/templates/` for documentation templates

## Structure

```
.default-config/
├── .ai/                    # AI agent guidance and rules
│   └── templates/          # Documentation templates
│
├── .claude/                # Claude-specific configurations
│   ├── agents/             # Agent definitions
│   │   ├── external/       # External agent templates
│   │   └── my/             # Custom agent definitions
│   ├── commands/           # Custom Claude commands
│   ├── hooks/              # Git hooks and automation
│   └── skills/             # Reusable skills
│
├── .mcp/                   # MCP server configurations
│
├── .vscode/                # VS Code settings and tasks
│
├── .codex/                 # Codex configuration
│
├── .gemini/                # Gemini configuration
│
├── claude-paralel/         # Parallel worktree management
│
├── claude-sessions/        # Session management commands
│
├── docs/                   # Documentation
│
├── templates/              # Project templates
│
├── AGENTS.md               # Main AI agent guidance entry point
├── CLAUDE.md               # Project-specific overrides
├── pyproject.toml          # Python project configuration
└── uv.lock                 # UV lock file
```

## Configuration

### AI Agent Guidance

The `AGENTS.md` file serves as the entry point for AI coding assistants. It references:

- **General Guidelines**: Workflow, organization, documentation standards
- **Language-Specific Rules**: Python best practices, code quality standards
- **Project-Specific Overrides**: Custom rules defined in `CLAUDE.md`

AI agents working in repositories with these files will automatically follow the defined guidelines.

### MCP Server Configuration

MCP (Model Context Protocol) server configurations are stored in `.mcp/`. Each subdirectory contains the configuration for a specific MCP server:

- **chrome-devtools**: Browser debugging tools
- **context7**: Library documentation access
- **firecrawl**: Web scraping and crawling
- **mcp-obsidian**: Obsidian integration
- **notionApi**: Notion API integration
- **supabase**: Supabase database and services
- **vercel**: Vercel deployment and management

## Key Components

### AI Agent Rules (`.ai/`)

Contains guidance files for AI coding assistants including:
- General rules and workflow guidelines
- Work organization and file structure patterns
- Documentation standards and templates
- Data handling principles
- Python-specific coding standards
- Code quality principles
- Context management strategies

### Claude Configuration (`.claude/`)

- **agents/**: Reusable agent definitions
  - **external/**: Pre-built agent templates for common tasks
  - **my/**: Custom agent definitions for specialized workflows
- **commands/**: Custom Claude commands
- **hooks/**: Git hooks for automation
- **skills/**: Reusable Claude skills for code review, context management, commit messages, and more

### Additional Tools

- **claude-paralel/**: Parallel worktree management for Claude
- **claude-sessions/**: Session management commands for Claude workflows
- **.codex/**: Codex AI configuration
- **.gemini/**: Google Gemini configuration

### Templates

Project templates and documentation templates for common use cases.

## Maintenance

This repository should be kept up-to-date with:

- Best practices and lessons learned from projects
- New tool configurations and integrations
- Updated documentation standards
- Improved workflow patterns

## Related Documentation

- **`AGENTS.md`**: AI agent guidance overview
- **`CLAUDE.md`**: Project-specific overrides and configuration
- **`.ai/documentation.md`**: Documentation standards and templates
- **`docs/mcp_config.md`**: MCP server configuration details
- **`docs/prompt-engineering.md`**: Best practices for writing effective prompts

## Development

This repository is not under active development. It is a template for new projects and a reference for existing projects.
