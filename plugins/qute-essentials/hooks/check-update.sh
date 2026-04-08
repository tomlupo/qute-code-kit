#!/usr/bin/env bash
# check-update.sh — daily version check for qute-essentials plugin
# Called from SessionStart hook. Outputs JSON with update notice if available.
set -euo pipefail

STATE_DIR="$HOME/.gstack"
CACHE_FILE="$STATE_DIR/qute-essentials-update-check"
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/qute-marketplace"

mkdir -p "$STATE_DIR"

# Only check once per day
if [[ -f "$CACHE_FILE" ]]; then
  last_check=$(cat "$CACHE_FILE" 2>/dev/null || echo 0)
  now=$(date +%s)
  elapsed=$(( now - last_check ))
  if [[ $elapsed -lt 86400 ]]; then
    echo '{}'
    exit 0
  fi
fi

# Record check time
date +%s > "$CACHE_FILE"

# Get local version from plugin.json
local_version=""
for cache_dir in "$HOME/.claude/plugins/cache/qute-marketplace/qute-essentials"/*/; do
  if [[ -f "${cache_dir}plugin.json" ]]; then
    local_version=$(python3 -c "import json; print(json.load(open('${cache_dir}plugin.json'))['version'])" 2>/dev/null || echo "")
    break
  fi
done

if [[ -z "$local_version" ]]; then
  echo '{}'
  exit 0
fi

# Fetch latest from git (quick, just the marketplace.json)
remote_version=$(cd "$MARKETPLACE_DIR" 2>/dev/null && git fetch origin main --quiet 2>/dev/null && git show origin/main:.claude-plugin/marketplace.json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data.get('plugins', []):
    if p['name'] == 'qute-essentials':
        print(p['version'])
        break
" 2>/dev/null || echo "")

if [[ -z "$remote_version" ]]; then
  echo '{}'
  exit 0
fi

if [[ "$local_version" != "$remote_version" ]]; then
  msg="qute-essentials update available: $local_version → $remote_version. Run: claude plugin marketplace update && claude plugin update qute-essentials@qute-marketplace"
  # Escape for JSON
  echo "{\"additionalContext\":\"$msg\"}"
else
  echo '{}'
fi
