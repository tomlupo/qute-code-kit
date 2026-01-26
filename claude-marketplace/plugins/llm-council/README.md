# LLM Council Plugin

Multi-model council for questions, debates, decisions, and brainstorming with peer review.

Inspired by Andrej Karpathy's [llm-council](https://github.com/karpathy/llm-council) project.

## Core Concept

Instead of relying on a single AI model, the council queries multiple models simultaneously, has them peer-review each other's responses anonymously, and synthesizes a final answer through a "chairman" model.

### Three-Stage Process

1. **Stage 1 - Independent Responses**: All models answer without seeing others (prevents groupthink)
2. **Stage 2 - Peer Review**: Models evaluate each other's responses anonymously (reduces bias)
3. **Stage 3 - Chairman Synthesis**: Designated model creates authoritative final answer

## Commands

| Command | Purpose |
|---------|---------|
| `/council:ask` | General question with multi-model consensus |
| `/council:debate` | Structured debate with peer evaluation |
| `/council:decide` | Decision support with pros/cons matrix |
| `/council:brainstorm` | Collaborative idea generation |

## Quick Start

### 1. Configure API Keys

Set environment variables for the models you want to use:

```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Enable Models

Edit `config/models.json` to enable/disable specific models:

```json
{
  "models": [
    {"name": "gpt4", "enabled": true, ...},
    {"name": "gemini", "enabled": true, ...},
    {"name": "claude", "enabled": true, ...}
  ]
}
```

### 3. Use Commands

```bash
### Ask a question
/council:ask "What's the best way to handle authentication in a REST API?"

### Run a debate
/council:debate "Microservices vs Monolith"

### Get decision support
/council:decide "Which database?" --options "PostgreSQL,MongoDB,SQLite"

### Brainstorm ideas
/council:brainstorm "Features for a CLI tool"
```

## Configuration

### `config/models.json`

Define the AI models available to the council:

- `name`: Short identifier (gpt4, gemini, claude)
- `provider`: API provider (openai, google, anthropic)
- `model`: Specific model ID
- `endpoint`: API endpoint URL
- `api_key_env`: Environment variable for API key
- `enabled`: Whether to include in council

### `config/council.json`

Configure council behavior:

- `chairman_strategy`: How to select chairman (`rotating`, `fixed`)
- `peer_review.enabled`: Whether to run peer review stage
- `peer_review.anonymize`: Hide model identities during review
- `peer_review.scoring.criteria`: What to score (accuracy, completeness, etc.)

## Peer Review Scoring

Each model evaluates others on structured criteria (1-10 scale):

| Criterion | Description |
|-----------|-------------|
| **Accuracy** | Is the information factually correct? |
| **Completeness** | Does it cover all relevant aspects? |
| **Clarity** | Is it well-organized and understandable? |
| **Insight** | Does it offer valuable perspectives? |

## Requirements

- Python 3.9+
- `httpx` library for async HTTP requests
- API keys for enabled models

## File Structure

```
llm-council/
├── plugin.json           # Plugin manifest
├── README.md             # This file
├── config/
│   ├── models.json       # Model definitions
│   └── council.json      # Council settings
├── commands/
│   ├── ask.md            # /council:ask
│   ├── debate.md         # /council:debate
│   ├── decide.md         # /council:decide
│   └── brainstorm.md     # /council:brainstorm
├── scripts/
│   ├── council_engine.py # Core three-stage engine
│   ├── council_ask.py
│   ├── council_debate.py
│   ├── council_decide.py
│   └── council_brainstorm.py
└── skills/
    └── llm-council/
        └── SKILL.md      # Skill documentation
```

## Credits

- Concept: [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council)
- Implementation: Claude Code plugin marketplace
