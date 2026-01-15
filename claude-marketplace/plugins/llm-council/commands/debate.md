# /council:debate

> **DETERMINISTIC EXECUTION**: Run the script below. Do NOT write custom code.
> All CLI/API logic is handled by the script automatically.

Have multiple AI models debate a topic with structured argumentation.

## Usage

```
/council:debate "<topic>" [--rounds <n>]
```

## Execution

**Run with uv (handles dependencies automatically):**

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_debate.py "<topic>" [--rounds <n>]
```

The script automatically:
- Tries CLI tools first (codex, gemini, claude) for speed
- Falls back to HTTP API if CLI unavailable
- Runs all models in parallel using asyncio
- Performs multi-round debate with rebuttals
- Chairman synthesizes verdict

## Example

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_debate.py "Microservices vs Monolith for a startup"
```
