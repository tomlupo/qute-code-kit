#!/usr/bin/env python3
"""
PostToolUse hook: trace tool executions to Langfuse for observability.

Logs tool name, input, output summary, and timing as Langfuse spans.
Groups traces by Claude Code session ID. Enables evaluation and
cost tracking in the Langfuse dashboard.

Toggle with `/guard <name> on/off` (persists to ~/.claude/qute-guards.json).
Requires: LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY env vars.
"""

import json
import os
import sys
from pathlib import Path


# Max output size to log (avoid bloating traces)
MAX_OUTPUT_LEN = 5000


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from guard_config import guard_enabled  # noqa: E402


def is_enabled() -> bool:
    """Whether Langfuse tracing is enabled (telemetry guard: fails closed).

    This hook fires on EVERY PostToolUse (no matcher — it must be able to
    trace any tool), and hooks.json is static so the process spawn itself
    can't be gated. So this check is the first thing main() does, before
    reading stdin or importing langfuse — the disabled path is a bare
    config read + print, the cheapest exit a per-call hook can manage.
    """
    return guard_enabled("langfuse")


def truncate(text: str, max_len: int = MAX_OUTPUT_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [truncated, {len(text)} total chars]"


def extract_output(tool_output) -> str:
    """Extract displayable output from tool result."""
    if isinstance(tool_output, str):
        return truncate(tool_output)
    if isinstance(tool_output, dict):
        content = tool_output.get("output", tool_output.get("content", ""))
        if isinstance(content, str):
            return truncate(content)
        return truncate(json.dumps(content))
    return str(tool_output)[:MAX_OUTPUT_LEN]


def main():
    if not is_enabled():
        print("{}")
        return

    # Check for required env vars
    if not os.environ.get("LANGFUSE_SECRET_KEY") or not os.environ.get(
        "LANGFUSE_PUBLIC_KEY"
    ):
        print("{}")
        return

    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print("{}")
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_output = input_data.get("tool_output", {})

    # Session identification
    session_id = input_data.get("session_id", input_data.get("conversation_id", ""))

    # Project identification from cwd / workspace_roots
    cwd = input_data.get("cwd", "")
    workspace_roots = input_data.get("workspace_roots", [])
    if not cwd and workspace_roots:
        cwd = workspace_roots[0] if isinstance(workspace_roots, list) else ""
    if not cwd:
        cwd = os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd())

    # Derive project name from cwd path
    project_name = Path(cwd).name if cwd else "unknown"

    # Detect source: dispatcher (tmux) vs interactive
    source = "interactive"
    tmux = os.environ.get("TMUX", "")
    if tmux:
        source = "dispatcher"

    # Hostname for multi-machine identification
    hostname = os.environ.get("HOSTNAME", "")
    if not hostname:
        import platform

        hostname = platform.node().split(".")[0]

    if not tool_name:
        print("{}")
        return

    try:
        from langfuse import get_client

        langfuse = get_client()

        # Build trace input (redact sensitive fields)
        trace_input = {}
        if tool_name == "Bash":
            trace_input["command"] = tool_input.get("command", "")[:500]
        elif tool_name in ("Read", "Edit", "Write"):
            trace_input["file_path"] = tool_input.get("file_path", "")
        elif tool_name in ("WebFetch", "WebSearch"):
            trace_input["url"] = tool_input.get("url", tool_input.get("query", ""))
        elif tool_name == "Grep":
            trace_input["pattern"] = tool_input.get("pattern", "")
            trace_input["path"] = tool_input.get("path", "")
        else:
            # MCP and other tools: log tool name + keys only
            trace_input["keys"] = list(tool_input.keys())[:10]

        output_text = extract_output(tool_output)

        # Determine success/failure
        exit_code = None
        if isinstance(tool_output, dict):
            exit_code = tool_output.get("exit_code")

        # Create trace as a span
        with langfuse.start_as_current_observation(
            name=f"tool:{tool_name}",
            as_type="span",
            input=trace_input,
            metadata={
                "tool_name": tool_name,
                "exit_code": exit_code,
                "output_length": len(output_text),
                "session_id": session_id or "",
                "project": project_name,
                "cwd": cwd,
                "source": source,
                "hostname": hostname,
            },
            tags=[
                f"project:{project_name}",
                f"source:{source}",
                f"tool:{tool_name}",
                f"host:{hostname}",
            ],
        ) as span:
            span.update(output=output_text)

            # Score: mark failures
            if exit_code is not None and exit_code != 0:
                langfuse.score_current_span(
                    name="tool_success",
                    value=0.0,
                    comment=f"Exit code: {exit_code}",
                )

        langfuse.flush()

    except ImportError:
        # langfuse not installed — skip silently
        pass
    except Exception:
        # Any error — don't break the hook chain
        pass

    print("{}")


if __name__ == "__main__":
    main()
