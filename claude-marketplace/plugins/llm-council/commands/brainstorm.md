# /council:brainstorm

> **DETERMINISTIC EXECUTION**: Run the script below. Do NOT write custom code.
> All CLI/API logic is handled by the script automatically.

Collaborative brainstorming with multiple AI models for idea generation.

## Usage

```
/council:brainstorm "<topic>" [--style <wild|practical|balanced>]
```

## Execution

**Run with uv (handles dependencies automatically):**

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_brainstorm.py "<topic>" [--style <style>]
```

The script automatically:
- Tries CLI tools first (codex, gemini, claude) for speed
- Falls back to HTTP API if CLI unavailable
- Runs all models in parallel using asyncio
- Cross-pollinates ideas between models
- Synthesizes top ideas

## Example

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_brainstorm.py "Features for a new CLI tool" --style practical
```
