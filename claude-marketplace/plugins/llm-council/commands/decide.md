# /council:decide

> **DETERMINISTIC EXECUTION**: Run the script below. Do NOT write custom code.
> All CLI/API logic is handled by the script automatically.

Get decision support with pros/cons analysis from multiple AI models.

## Usage

```
/council:decide "<decision>" --options "<opt1,opt2,...>"
```

## Execution

**Run with uv (handles dependencies automatically):**

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_decide.py "<decision>" --options "<opt1,opt2,...>"
```

The script automatically:
- Tries CLI tools first (codex, gemini, claude) for speed
- Falls back to HTTP API if CLI unavailable
- Runs all models in parallel using asyncio
- Each model analyzes options with pros/cons
- Aggregates into decision matrix

## Example

```bash
cd /home/twilc/projects/qute-ai-tools/claude-marketplace/plugins/llm-council && uv run python scripts/council_decide.py "Which database?" --options "PostgreSQL,MongoDB,SQLite"
```
