# /council:ask

> **DETERMINISTIC EXECUTION**: Run the script below. Do NOT write custom code.
> All CLI/API logic is handled by the script automatically.

Get answers from multiple AI models (GPT, Gemini, Claude, DeepSeek) with peer review and synthesis.

## Usage

```
/council:ask "<question>" [--quick]
```

## Execution

**Run with uv (handles dependencies automatically):**

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_ask.py "<question>" [--quick]
```

The script automatically:
- Tries CLI tools first (codex, gemini, claude) for speed
- Falls back to HTTP API if CLI unavailable
- Runs all models in parallel using asyncio
- Performs peer review (skip with --quick)
- Synthesizes final answer

## Example

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_ask.py "What's the best approach for caching in Python?" --quick
```
