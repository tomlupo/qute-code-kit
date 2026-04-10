#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit that leaks secrets or touches credential files.

Two complementary checks:

1. **Content scan** — well-known secret patterns (AWS keys, GitHub tokens,
   private keys, Stripe live keys, Google API keys, OpenAI/Anthropic keys,
   JWTs, etc.). Patterns sourced from gitleaks rules.

2. **Filename block** — hard-blocks Write/Edit on files that should never be
   authored by Claude: `.env*` (except `.env.example`/`.env.template`),
   credential JSONs, private keys, `.netrc`, `.pgpass`, `database.ini`.

## Override mechanisms (in order of preference)

- **Session-wide**: `/guard secrets off` (flips `secrets.enabled` in
  `config/guards.json`).
- **Single write**: `touch ~/.claude/.secret-scan-override` — this file is
  consumed (deleted) on the next allowed write. Good for one-off overrides.
- **Environment**: `CLAUDE_SKIP_GUARDS=1` or `CLAUDE_GUARD_SECRETS=0`
  disables for the whole session (useful in CI or trusted contexts).

Toggle via config/guards.json {"secrets": {"enabled": true/false}}.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GUARDS_CONFIG = Path(__file__).parent.parent / "config" / "guards.json"
OVERRIDE_FILE = Path.home() / ".claude" / ".secret-scan-override"


def is_enabled() -> bool:
    if os.environ.get("CLAUDE_SKIP_GUARDS") == "1":
        return False
    if os.environ.get("CLAUDE_GUARD_SECRETS") == "0":
        return False
    try:
        with open(GUARDS_CONFIG) as f:
            config = json.load(f)
        return config.get("secrets", {}).get("enabled", True)
    except (FileNotFoundError, json.JSONDecodeError):
        return True


def consume_override() -> bool:
    """Return True and delete the override file if it exists (one-shot)."""
    if OVERRIDE_FILE.exists():
        try:
            OVERRIDE_FILE.unlink()
        except OSError:
            pass
        return True
    return False


# --- Filename patterns to hard-block -----------------------------------------
# fnmatch-style, checked against the basename.
BLOCKED_FILENAMES = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "id_ecdsa",
    "id_ecdsa.*",
    ".netrc",
    ".pgpass",
    "credentials.json",
    "credentials",
    "client_secret*.json",
    "service-account*.json",
    "service_account*.json",
    "database.ini",
]

# Allowlist: explicitly OK even if they'd match above (templates, examples)
ALLOWED_FILENAMES = [
    ".env.example",
    ".env.template",
    ".env.sample",
    ".env.dist",
]


def filename_blocked(file_path: str) -> tuple[bool, str]:
    name = Path(file_path).name
    if any(fnmatch.fnmatch(name, pat) for pat in ALLOWED_FILENAMES):
        return False, ""
    for pat in BLOCKED_FILENAMES:
        if fnmatch.fnmatch(name, pat):
            return True, f"filename `{name}` matches blocked pattern `{pat}`"
    return False, ""


# --- Content patterns --------------------------------------------------------
# (name, regex, description)
SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "aws-access-key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "AWS Access Key ID",
    ),
    (
        "aws-secret-key",
        re.compile(r"(?i)aws_?secret_?access_?key[\s:=\"']{1,5}[A-Za-z0-9/+=]{40}"),
        "AWS Secret Access Key",
    ),
    (
        "github-token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b"),
        "GitHub personal/app/oauth/refresh token",
    ),
    (
        "github-fine-grained",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
        "GitHub fine-grained personal access token",
    ),
    (
        "slack-token",
        re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]{10,}\b"),
        "Slack token",
    ),
    (
        "google-api-key",
        re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
        "Google API key",
    ),
    (
        "stripe-live-secret",
        re.compile(r"\bsk_live_[0-9a-zA-Z]{20,}\b"),
        "Stripe live secret key",
    ),
    (
        "stripe-live-restricted",
        re.compile(r"\brk_live_[0-9a-zA-Z]{20,}\b"),
        "Stripe live restricted key",
    ),
    (
        "anthropic-api-key",
        re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
        "Anthropic API key",
    ),
    (
        "openai-api-key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}\b"),
        "OpenAI API key",
    ),
    (
        "private-key-block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"
        ),
        "private key PEM block",
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_=-]{10,}\.eyJ[A-Za-z0-9_=-]{10,}\.[A-Za-z0-9_=-]{10,}\b"
        ),
        "JSON Web Token",
    ),
    (
        "azure-connection-string",
        re.compile(
            r"DefaultEndpointsProtocol=https;AccountName=[A-Za-z0-9]+;AccountKey=[A-Za-z0-9+/=]{40,}"
        ),
        "Azure Storage connection string",
    ),
    (
        "generic-high-entropy",
        re.compile(
            r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
            r"\s*[:=]\s*['\"][A-Za-z0-9+/=_\-]{24,}['\"]"
        ),
        "hardcoded credential in password/secret/api_key assignment",
    ),
]


def scan_content(content: str) -> list[tuple[str, str]]:
    """Return list of (pattern_name, description) matches."""
    hits: list[tuple[str, str]] = []
    for name, pattern, desc in SECRET_PATTERNS:
        if pattern.search(content):
            hits.append((name, desc))
    return hits


# --- Main --------------------------------------------------------------------


def extract_write_info(payload: dict) -> tuple[str, str]:
    """Extract (file_path, content) from a Write/Edit tool payload."""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    # Write tool: content field
    content = tool_input.get("content", "")
    # Edit tool: new_string (and optionally old_string)
    if not content:
        content = tool_input.get("new_string", "")
    return file_path, content


def main() -> int:
    if not is_enabled():
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # don't block on malformed input

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "NotebookEdit"):
        return 0

    file_path, content = extract_write_info(payload)

    # Check filename first (cheaper)
    blocked, reason = filename_blocked(file_path)
    filename_hit = blocked

    # Then content
    content_hits = scan_content(content) if content else []

    if not filename_hit and not content_hits:
        return 0

    # Check override (one-shot)
    if consume_override():
        print(
            "secrets-guard: override consumed — allowing this write (single shot)",
            file=sys.stderr,
        )
        return 0

    # Build block message
    print("secrets-guard: BLOCKED", file=sys.stderr)
    print(f"  file: {file_path}", file=sys.stderr)
    if filename_hit:
        print(f"  reason: {reason}", file=sys.stderr)
    for name, desc in content_hits:
        print(f"  secret detected: {name} — {desc}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Override options (use only with explicit user confirmation):", file=sys.stderr
    )
    print(
        "  1. One-shot: `touch ~/.claude/.secret-scan-override` then retry the write",
        file=sys.stderr,
    )
    print(
        "  2. Session:  `/guard secrets off` (re-enable with `/guard secrets on`)",
        file=sys.stderr,
    )
    print(
        "  3. CI:       set CLAUDE_SKIP_GUARDS=1 or CLAUDE_GUARD_SECRETS=0",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
