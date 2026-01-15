---
name: llm-council
description: |
  Multi-model council for getting diverse AI perspectives on questions,
  decisions, debates, and brainstorming. Uses a three-stage council pattern:
  independent responses, peer review, and chairman synthesis.

  Use when:
  - You want multiple perspectives on a question → /council:ask
  - You need to evaluate tradeoffs → /council:debate
  - You're making a decision with multiple options → /council:decide
  - You want creative ideas → /council:brainstorm
---

# LLM Council

Get multiple AI perspectives with peer review and synthesis.

## When to Use This Skill

Use the LLM Council when you need:

1. **Multiple perspectives** on a technical question
2. **Objective comparison** between options or approaches
3. **Structured debate** to explore tradeoffs
4. **Creative brainstorming** with diverse ideas

## How the Council Works

### Three-Stage Process

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Independent Responses                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │  GPT-4  │  │ Gemini  │  │ Claude  │  ← No cross-talk    │
│  └────┬────┘  └────┬────┘  └────┬────┘                     │
│       │            │            │                           │
│       ▼            ▼            ▼                           │
├─────────────────────────────────────────────────────────────┤
│  Stage 2: Peer Review (Anonymized)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Response A ← scored by B, C                         │   │
│  │  Response B ← scored by A, C                         │   │
│  │  Response C ← scored by A, B                         │   │
│  └─────────────────────────────────────────────────────┘   │
│       │            │            │                           │
│       ▼            ▼            ▼                           │
├─────────────────────────────────────────────────────────────┤
│  Stage 3: Chairman Synthesis                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • Consensus points                                  │   │
│  │  • Disagreements resolved                            │   │
│  │  • Unique insights highlighted                       │   │
│  │  • Final recommendation                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Available Commands

### `/council:ask "<question>"`

Best for: Technical questions with nuance, "best practices" queries, questions with no single right answer.

```
/council:ask "What's the best approach for caching in Python?"
/council:ask "Should I use SQLAlchemy or raw SQL?" --quick
```

Options:
- `--quick` - Skip peer review for faster response
- `--chairman <model>` - Force specific model as chairman

### `/council:debate "<topic>"`

Best for: Architectural decisions, technology comparisons, policy discussions.

```
/council:debate "Microservices vs Monolith"
/council:debate "REST vs GraphQL" --rounds 3
```

Options:
- `--rounds <n>` - Number of debate rounds (default: 2)
- `--positions <a,b,c>` - Assign specific positions to models

### `/council:decide "<decision>" --options "a,b,c"`

Best for: Choosing between options, evaluating tradeoffs, making justified recommendations.

```
/council:decide "Which database?" --options "PostgreSQL,MongoDB,SQLite"
/council:decide "Frontend framework" --options "React,Vue,Svelte" --criteria "learning-curve,ecosystem,performance"
```

Options:
- `--options` - Comma-separated options (required)
- `--criteria` - Custom evaluation criteria

### `/council:brainstorm "<topic>"`

Best for: Feature ideation, problem-solving, creative exploration.

```
/council:brainstorm "Features for a new CLI tool"
/council:brainstorm "Ways to improve CI/CD" --style practical
```

Options:
- `--rounds <n>` - Iteration rounds (default: 2)
- `--style` - `wild` (creative), `practical` (feasible), `balanced` (default)

## Configuration

### Required API Keys

Set these environment variables for the models you want to use:

```bash
OPENAI_API_KEY=sk-...      # For GPT-4
GOOGLE_API_KEY=AIza...     # For Gemini
ANTHROPIC_API_KEY=sk-ant-... # For Claude
```

### Model Selection

Edit `config/models.json` to enable/disable models:

```json
{"name": "gpt4", "enabled": true}
{"name": "gemini", "enabled": true}
{"name": "claude", "enabled": false}
```

### Peer Review Settings

Edit `config/council.json`:

```json
{
  "peer_review": {
    "enabled": true,
    "anonymize": true,
    "scoring": {
      "criteria": ["accuracy", "completeness", "clarity", "insight"]
    }
  }
}
```

## Best Practices

1. **Use for important decisions**: Council overhead is worth it for significant choices
2. **Enable at least 2 models**: More models = more diverse perspectives
3. **Use `--quick` for exploration**: Skip peer review when brainstorming
4. **Review individual responses**: Don't just read the synthesis
5. **Configure criteria**: Custom criteria improve relevance for specific domains
