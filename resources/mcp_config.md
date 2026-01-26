# codex
• For Codex CLI there’s no magic auto-discovery beyond config files. By default, zero MCP servers load unless:

  - You set MCP_CONFIG_PATH, or
  - You have a .claude/settings.local.json (project-level or ~/.claude/settings.local.json) that tells the CLI to load
    project .mcp.json.


# gemini
.gemini/settings.json


# claude
.mcp.json


# cursor
• Cursor automatically loads MCP servers from `mcp.json` files:

  - **Global Configuration**: `~/.cursor/mcp.json` (Mac/Linux) or `C:\Users\YourUsername\.cursor\mcp.json` (Windows)
  - **Project-Specific**: `.cursor/mcp.json` in your project root

• Cursor automatically detects and loads MCP servers defined in these locations. No additional configuration needed - just restart Cursor after creating/editing the `mcp.json` file.

• The `mcp.json` format is the same as Claude's `.mcp.json` format (with `mcpServers` object).