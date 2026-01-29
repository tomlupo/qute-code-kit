#!/usr/bin/env python3
"""
AI Reviewer - Orchestrate external AI model reviews via Codex and Gemini CLI.

Usage:
    python review.py --model codex --task review --context context.md --workdir /project
    python review.py --model both --task brainstorm --context context.md
    python review.py --model codex --task review --context context.md --effort high
    python review.py --model codex --task review --context context.md --suppress-thinking
    python review.py --resume --context "follow up question"
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Session file for resume capability
SESSION_FILE = Path.home() / ".claude" / "skills" / "ai-review" / ".last_session.json"


PROMPT_TEMPLATES = {
    "review": """You are a senior engineer performing a code review.

{context}

Review the code mentioned above for:
- Bugs and edge cases
- Security vulnerabilities
- Performance issues
- Code quality and maintainability

Read and analyze the relevant files, then respond with valid JSON:
{{"summary": "One-line assessment", "key_points": ["..."], "concerns": ["..."], "suggestions": ["..."]}}""",

    "brainstorm": """You are a creative technical collaborator generating alternatives.

{context}

Generate 3-5 distinct approaches to solve this problem, with pros/cons for each.

Respond with valid JSON:
{{"summary": "Solution space overview", "alternatives": [{{"name": "...", "description": "...", "pros": ["..."], "cons": ["..."]}}], "suggestions": ["Best fit given constraints"]}}""",

    "validate": """You are a critical reviewer validating completed work.

{context}

Validate this implementation by checking:
- Requirements coverage
- Edge cases
- Error handling
- Test sufficiency

Respond with valid JSON:
{{"summary": "Validation result", "key_points": ["Working well"], "concerns": ["Gaps found"], "suggestions": ["Before shipping"]}}""",

    "plan": """You are a software architect reviewing a technical approach.

{context}

Evaluate this plan for:
- Feasibility
- Gaps
- Scalability
- Alternative approaches

Respond as JSON:
{{"summary": "Plan assessment", "key_points": ["Core observations"], "concerns": ["Risks"], "suggestions": ["Refinements"], "alternatives": ["Other approaches"]}}"""
}


EXPECTED_SCHEMAS = {
    "review": {
        "summary": str,
        "key_points": [str],
        "concerns": [str],
        "suggestions": [str]
    },
    "plan": {
        "summary": str,
        "key_points": [str],
        "concerns": [str],
        "suggestions": [str],
        "alternatives": [str]
    },
    "brainstorm": {
        "summary": str,
        "alternatives": [{
            "name": str,
            "description": str,
            "pros": [str],
            "cons": [str]
        }],
        "suggestions": [str]
    },
    "validate": {
        "summary": str,
        "key_points": [str],
        "concerns": [str],
        "suggestions": [str]
    },
    "bug_hunting": {
        "summary": str,
        "concerns": [{
            "file": str,
            "line": int,
            "issue": str,
            "severity": str # Could be 'high', 'medium', 'low'
        }],
        "suggestions": [str]
    }
}


def save_session(model: str, task: str, effort: str, workdir: str):
    """Save session info for resume capability."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    session_data = {
        "model": model,
        "task": task,
        "effort": effort,
        "workdir": workdir,
        "timestamp": time.time()
    }
    SESSION_FILE.write_text(json.dumps(session_data, indent=2))


def load_session() -> dict | None:
    """Load last session info if available."""
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return None
    return None


def run_codex(prompt: str, workdir: str, timeout: int, effort: str = "medium",
              suppress_thinking: bool = False, resume: bool = False) -> dict:
    """Run Codex CLI in exec mode and return parsed response."""
    # On Windows, npm creates .cmd wrappers that need explicit extension
    codex_cmd = "codex.cmd" if sys.platform == "win32" else "codex"

    if resume:
        # Resume last session
        cmd = [
            codex_cmd, "exec",
            "--skip-git-repo-check",
            "resume", "--last"
        ]
        if prompt:
            # Pipe additional prompt for resume
            cmd = [codex_cmd, "exec", "--skip-git-repo-check", "resume", "--last", prompt]
    else:
        cmd = [
            codex_cmd, "exec",
            "--full-auto",
            "--json",
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "--config", f"model_reasoning_effort={effort}",
            "--cd", workdir,
            prompt
        ]

    start = time.time()
    try:
        # Handle stderr suppression (thinking tokens)
        if suppress_thinking:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                cwd=workdir
            )
            stderr_output = ""
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir
            )
            stderr_output = result.stderr
        duration = int((time.time() - start) * 1000)

        # Codex --json returns newline-delimited JSON events
        # Find the last assistant message or result
        response_text = ""
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                event = json.loads(line)
                # Look for message content or final response
                if event.get('type') == 'message' and event.get('role') == 'assistant':
                    response_text = event.get('content', '')
                elif 'message' in event:
                    response_text = event.get('message', '')
            except json.JSONDecodeError:
                # Plain text response
                response_text = line
        
        if not response_text and result.stdout:
            response_text = result.stdout.strip()

        return {
            "success": result.returncode == 0,
            "response": response_text,
            "stderr": stderr_output,
            "duration_ms": duration
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "response": "",
            "stderr": f"Timeout after {timeout}s",
            "duration_ms": timeout * 1000
        }
    except FileNotFoundError:
        return {
            "success": False,
            "response": "",
            "stderr": "codex CLI not found. Install with: npm i -g @openai/codex",
            "duration_ms": 0
        }


def run_gemini(prompt: str, workdir: str, timeout: int) -> dict:
    """Run Gemini CLI in headless mode and return parsed response."""
    # On Windows, npm creates .cmd wrappers that need explicit extension
    gemini_cmd = "gemini.cmd" if sys.platform == "win32" else "gemini"

    # Gemini CLI uses positional prompt for headless mode
    # and it automatically has access to the working directory
    cmd = [
        gemini_cmd,
        prompt, # Use positional prompt
        "--output-format", "json",
        "--approval-mode", "yolo" # Use approval-mode instead of --yolo
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir
        )
        duration = int((time.time() - start) * 1000)

        response_text = ""
        tokens_used = 0

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                # Try to get 'response' or 'text' key, otherwise use the whole JSON object as string
                response_text = data.get('response', data.get('text', json.dumps(data)))
                # Extract token stats if available
                stats = data.get('stats', {})
                models = stats.get('models', {})
                for model_stats in models.values():
                    tokens_used += model_stats.get('tokens', {}).get('total', 0)
            except json.JSONDecodeError:
                response_text = result.stdout.strip()

        return {
            "success": result.returncode == 0,
            "response": response_text,
            "stderr": result.stderr,
            "duration_ms": duration,
            "tokens_used": tokens_used
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "response": "",
            "stderr": f"Timeout after {timeout}s",
            "duration_ms": timeout * 1000
        }
    except FileNotFoundError:
        return {
            "success": False,
            "response": "",
            "stderr": "gemini CLI not found. Install from: https://github.com/google-gemini/gemini-cli",
            "duration_ms": 0
        }


def parse_ai_response(response_text: str) -> dict:
    """Parse AI response, handling JSON or plain text."""
    if not response_text:
        return {"raw_response": "Empty response"}
    
    # Try to extract JSON from response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first and last lines if they're code fences
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)
    
    # Try to find JSON object in text
    try:
        # Direct parse
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object boundaries
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    
    # Fallback: return as raw response
    return {"raw_response": response_text}


def validate_json_schema(data: dict, schema: dict) -> (bool, str):
    """
    Validates if the given data conforms to the expected schema.
    Returns (True, "") if valid, or (False, error_message) if invalid.
    """
    if not isinstance(data, dict):
        return False, f"Expected a dictionary, but got {type(data).__name__}"

    for key, expected_type in schema.items():
        if key not in data:
            return False, f"Missing key: '{key}'"

        actual_value = data[key]

        if isinstance(expected_type, list):
            # Expected a list of a specific type
            if not isinstance(actual_value, list):
                return False, f"Expected key '{key}' to be a list, but got {type(actual_value).__name__}"
            if len(expected_type) == 1: # List of a specific type (e.g., [str])
                item_expected_type = expected_type[0]
                if isinstance(item_expected_type, dict): # List of objects
                    for item in actual_value:
                        is_valid, msg = validate_json_schema(item, item_expected_type)
                        if not is_valid:
                            return False, f"Invalid item in list for key '{key}': {msg}"
                elif not all(isinstance(item, item_expected_type) for item in actual_value):
                    return False, f"Expected all items in list for key '{key}' to be {item_expected_type.__name__}"
        elif isinstance(expected_type, dict):
            # Expected a nested dictionary (object)
            is_valid, msg = validate_json_schema(actual_value, expected_type)
            if not is_valid:
                return False, f"Invalid nested object for key '{key}': {msg}"
        elif not isinstance(actual_value, expected_type):
            return False, f"Expected key '{key}' to be {expected_type.__name__}, but got {type(actual_value).__name__}"
    
    # Check for unexpected keys
    for key in data:
        if key not in schema:
            return False, f"Unexpected key: '{key}'"

    return True, ""


def main():
    parser = argparse.ArgumentParser(description='AI Reviewer - External model review orchestrator')
    parser.add_argument('--model', choices=['codex', 'gemini', 'both'],
                        help='Which AI model to use (required unless --resume)')
    parser.add_argument('--task', choices=['review', 'brainstorm', 'validate', 'plan', 'bug_hunting'],
                        help='Type of review task (required unless --resume)')
    parser.add_argument('--context', type=str,
                        help='Path to context file or inline context (required unless --resume)')
    parser.add_argument('--workdir', type=str, default='.',
                        help='Project working directory')
    parser.add_argument('--timeout', type=int, default=120,
                        help='Timeout in seconds (default: 120)')
    parser.add_argument('--effort', choices=['low', 'medium', 'high'], default='medium',
                        help='Reasoning effort level for Codex (default: medium)')
    parser.add_argument('--suppress-thinking', action='store_true',
                        help='Suppress thinking tokens (stderr) from Codex output')
    parser.add_argument('--resume', action='store_true',
                        help='Resume last Codex session (Codex only)')

    args = parser.parse_args()

    # Handle resume mode
    if args.resume:
        if args.model and args.model != 'codex':
            print(json.dumps({"error": "Resume is only supported for Codex"}), file=sys.stderr)
            sys.exit(1)
        last_session = load_session()
        if not last_session:
            print(json.dumps({"error": "No previous session found to resume"}), file=sys.stderr)
            sys.exit(1)
        # Use last session's settings, allow context override for follow-up
        args.model = 'codex'
        args.task = last_session.get('task', 'review')
        args.effort = last_session.get('effort', 'medium')
        args.workdir = last_session.get('workdir', '.')
    else:
        # Validate required args when not resuming
        if not args.model or not args.task or not args.context:
            parser.error("--model, --task, and --context are required unless using --resume")
    
    # Load context (may be None for resume without new prompt)
    context = ""
    if args.context:
        context_path = Path(args.context)
        if context_path.exists():
            context = context_path.read_text()
        else:
            context = args.context

    # Build prompt
    prompt_template = PROMPT_TEMPLATES.get(args.task, PROMPT_TEMPLATES['review'])
    prompt = prompt_template.format(context=context) if context else ""

    workdir = str(Path(args.workdir).resolve())
    results = []

    # Run selected model(s)
    if args.model in ['codex', 'both']:
        result = run_codex(
            prompt, workdir, args.timeout,
            effort=args.effort,
            suppress_thinking=args.suppress_thinking,
            resume=args.resume
        )
        # Save session for potential resume
        if result['success']:
            save_session(args.model, args.task, args.effort, workdir)
        parsed = parse_ai_response(result['response'])
        validation_error = None
        if result['success'] and args.task in EXPECTED_SCHEMAS and 'raw_response' not in parsed:
            is_valid, msg = validate_json_schema(parsed, EXPECTED_SCHEMAS[args.task])
            if not is_valid:
                validation_error = f"JSON schema validation failed: {msg}"
                result['success'] = False # Mark as failure due to schema validation

        results.append({
            "model": "codex",
            "task_type": args.task,
            "status": "success" if result['success'] else "error",
            "response": parsed if 'raw_response' not in parsed else None,
            "raw_response": parsed.get('raw_response'),
            "error": result['stderr'] if not result['success'] else validation_error,
            "metadata": {
                "duration_ms": result['duration_ms'],
                "effort": args.effort,
                "resumed": args.resume
            }
        })
    
    if args.model in ['gemini', 'both']:
        # Gemini works better with direct context instead of wrapped prompt
        # Use context directly for Gemini to avoid "ready to help" responses
        gemini_prompt = context if context else prompt
        result = run_gemini(gemini_prompt, workdir, args.timeout)
        parsed = parse_ai_response(result['response'])
        validation_error = None
        if result['success'] and args.task in EXPECTED_SCHEMAS and 'raw_response' not in parsed:
            is_valid, msg = validate_json_schema(parsed, EXPECTED_SCHEMAS[args.task])
            if not is_valid:
                validation_error = f"JSON schema validation failed: {msg}"
                result['success'] = False # Mark as failure due to schema validation

        results.append({
            "model": "gemini",
            "task_type": args.task,
            "status": "success" if result['success'] else "error",
            "response": parsed if 'raw_response' not in parsed else None,
            "raw_response": parsed.get('raw_response'),
            "error": result['stderr'] if not result['success'] else validation_error, # Prioritize validation error
            "metadata": {
                "duration_ms": result['duration_ms'],
                "tokens_used": result.get('tokens_used', 0)
            }
        })
    
    # Output
    if len(results) == 1:
        output = results[0]
    else:
        output = {"results": results}
    
    print(json.dumps(output, indent=2))
    
    # Exit with error if any model failed
    if any(r['status'] == 'error' for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()