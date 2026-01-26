# qute-ai-tools

A collection of AI tools and utilities for autonomous coding, skill creation, and Claude Code integration.

## What's in this repo
- Ralph (`repos/ralph/README.md`): file-based agent loop for autonomous coding
- SkillForge (`repos/SkillForge/README.md`): 4-phase methodology for skill creation
- Claude Marketplace (`claude-marketplace/README.md`): personal Claude Code plugin marketplace
- Claude Skills (`claude/skills/README.md`): custom and external skills for Claude Code
- Claude Agents (`claude/agents/`): custom and external agent definitions
- Clawdbot (`clawdbot/`): auxiliary tools and skills for booking analysis
- Project Templates (`project-templates/`): starter templates and guidance
- Prompts (`prompts/`): prompt references and templates
- Resources (`resources/README.md`): external references and experiments
- Root Instructions (`CLAUDE.md`): repo-specific guidance for Claude Code

## Quick Start

### Ralph
```bash
npm i -g @iannuttall/ralph
ralph prd
ralph build 1
```

### SkillForge
```bash
cp -r repos/SkillForge ~/.claude/skills/
# Then use: SkillForge: {goal}
```

### Claude Marketplace
```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
# Or from GitHub:
claude plugin install github:twilc/claude-marketplace
```

### Claude Skills
Reference in your project's `CLAUDE.md`:
```markdown
## Skills
- Use skills in `claude/skills/my/` for development workflows
- Use `claude/skills/external/scientific-skills/` for quantitative analysis
- ALWAYS use generating-commit-messages skill before any commit
```

## Directory Map
```
qute-ai-tools/
├── CLAUDE.md                # Repo-wide Claude guidance
├── claude/                  # Claude Code skills + agents
├── claude-marketplace/       # Claude Code plugin marketplace
├── clawdbot/                 # Clawdbot tools and skills
├── project-templates/        # Starter templates
├── repos/                    # Subprojects (Ralph, SkillForge)
├── resources/                # External links and experiments
└── prompts/                  # Prompt references
```
