# LLM Council Workflow

> Multi-model decision support: frame a question → run council → synthesize answer

## When to Use

When you need robust, bias-reduced answers to complex questions — investment decisions, architecture choices, strategy evaluation, creative ideation. The council runs multiple LLMs independently, then peer-reviews and synthesizes.

## Tools Used

| Tool | Role |
|------|------|
| LLM Council Reloaded | Multi-model orchestration (ask, debate, decide, minmax, brainstorm) |
| `/gist-report` | Share the council output as formatted HTML |

## Prerequisites

```bash
# Clone and set up
git clone https://github.com/tomlupo/llm-council-reloaded
cd llm-council-reloaded
# Configure at least 2 models in Settings (CLI-based models need no API keys)
```

## Modes

| Mode | Best for | How it works |
|------|----------|--------------|
| **Ask** | General questions | Independent responses → peer review → synthesis |
| **Debate** | Contested topics | Multi-round argumentation → final verdict |
| **Decide** | Option selection | Score options against criteria → aggregated recommendation |
| **Minmax** | Risk assessment | Worst-case scenario analysis → risk-averse recommendation |
| **Brainstorm** | Ideation | Collaborative rounds with cross-pollination |

## Workflow

### Phase 1: Frame the Question

Pick the right mode for your question type:

- "Should we use Postgres or DuckDB for analytics?" → **Decide** (clear options, scorable criteria)
- "What are the risks of this momentum strategy?" → **Minmax** (risk-focused)
- "How should we architect the data pipeline?" → **Ask** (open-ended, want diverse perspectives)
- "Is factor investing dead?" → **Debate** (contested, want argumentation)
- "Generate ideas for alternative data sources" → **Brainstorm** (creative, want volume)

### Phase 2: Configure and Run

Set parameters based on mode:

- **Decide/Minmax**: list your options and evaluation criteria
- **Debate**: set number of rounds (2-3 is usually enough)
- **Brainstorm**: set rounds and style (divergent vs convergent)
- **Ask**: just submit the question

### Phase 3: Review Synthesis

The chairman model produces a final synthesis. Key things to check:

- Does the synthesis capture minority opinions or just majority?
- Are the peer review scores consistent with the reasoning?
- Did any model surface a consideration others missed?

### Phase 4: Integrate Results

Bring council output into your Claude Code session:

```
Here's the council output on [topic]: [paste synthesis]
Use this as input for our analysis.
```

Or share via gist: `/gist-report`

## Tips

- Use **at least 3 models** for meaningful diversity (2 is minimum, 3+ is better)
- Mix model families (Claude + GPT + Gemini) to maximize perspective diversity
- For investment decisions, prefer **Decide** or **Minmax** over **Ask**
- Save council outputs alongside your research artifacts for audit trail
