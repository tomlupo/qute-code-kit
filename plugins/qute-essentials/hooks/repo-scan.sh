#!/usr/bin/env bash
# SessionStart hook: detect new/unknown repos and flag for security scan.
#
# Tracks known repos in ~/.claude/permission-audit/known-repos.
# When a session starts in a repo not in the list, injects a warning
# telling Claude to run a security scan before doing any work.
set -euo pipefail

KNOWN_FILE="$HOME/.claude/permission-audit/known-repos"
mkdir -p "$(dirname "$KNOWN_FILE")"
touch "$KNOWN_FILE"

# Get current repo root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$REPO_ROOT" ]; then
  # Not a git repo — nothing to scan
  echo '{}'
  exit 0
fi

# Use python for hashing (md5sum not available on Windows/Git Bash)
REPO_ID=$(python -c "import hashlib; print(hashlib.md5('$REPO_ROOT'.encode()).hexdigest())" 2>/dev/null || python -c "import hashlib; print(hashlib.md5('$REPO_ROOT'.encode()).hexdigest())" 2>/dev/null)

# Check if we've seen this repo before
if grep -q "^$REPO_ID " "$KNOWN_FILE" 2>/dev/null; then
  # Known repo — no action needed
  echo '{}'
  exit 0
fi

# New repo detected — check for obvious red flags quickly
WARNINGS=""

# 1. Check for setup.py with obfuscation
if [ -f "$REPO_ROOT/setup.py" ]; then
  if grep -qE "exec\s*\(|__import__|base64|zlib|compile\(" "$REPO_ROOT/setup.py" 2>/dev/null; then
    WARNINGS="${WARNINGS}CRITICAL: setup.py contains obfuscated/suspicious code patterns. DO NOT run it.\n"
  fi
fi

# 2. Check for npm install scripts
if [ -f "$REPO_ROOT/package.json" ]; then
  SCRIPTS=$(python -c "
import json, sys
try:
    d = json.load(open('$REPO_ROOT/package.json'))
    for k in ('preinstall','postinstall','install'):
        v = d.get('scripts',{}).get(k,'')
        if v and any(s in v for s in ('curl','wget','node -e','eval','exec','bash','http','chmod','/dev/tcp')):
            print(f'CRITICAL: package.json has suspicious {k} script: {v[:100]}')
except: pass
" 2>/dev/null)
  [ -n "$SCRIPTS" ] && WARNINGS="${WARNINGS}${SCRIPTS}\n"
fi

# 3. Check for .env files tracked by git
TRACKED_ENV=$(git -C "$REPO_ROOT" ls-files '*.env' '.env.*' 2>/dev/null | grep -v '.example\|.sample\|.template' || true)
if [ -n "$TRACKED_ENV" ]; then
  WARNINGS="${WARNINGS}WARNING: .env files tracked by git: $TRACKED_ENV\n"
fi

# 4. Check for GitHub Actions with pull_request_target
if [ -d "$REPO_ROOT/.github/workflows" ]; then
  PRT=$(grep -rl "pull_request_target" "$REPO_ROOT/.github/workflows/" 2>/dev/null || true)
  [ -n "$PRT" ] && WARNINGS="${WARNINGS}WARNING: GitHub Actions with pull_request_target: $PRT\n"
fi

# Build the message
REPO_NAME=$(basename "$REPO_ROOT")
REMOTE=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || echo "no remote")

if [ -n "$WARNINGS" ]; then
  MSG="🔍 NEW REPO DETECTED: $REPO_NAME ($REMOTE)\n\n⚠️ SECURITY ISSUES FOUND:\n${WARNINGS}\nBefore doing any work, investigate these findings. Do NOT run npm install, pip install, or any build commands until the issues are resolved.\n\nAfter review, this repo will be marked as known."
else
  MSG="🔍 NEW REPO DETECTED: $REPO_NAME ($REMOTE)\n\nQuick scan found no obvious issues. Recommended: run /cso --code for a full audit before starting work.\n\nMarking repo as known."
  # Auto-mark clean repos
  echo "$REPO_ID $REPO_ROOT $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$KNOWN_FILE"
fi

# Escape for JSON
# Use printf instead of echo -e for cross-platform compat
ESCAPED=$(printf '%b' "$MSG" | python -c "import json,sys; print(json.dumps(sys.stdin.read()))")

echo "{\"additionalContext\":$ESCAPED}"
