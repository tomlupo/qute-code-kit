#!/usr/bin/env bash
# pickup-ctx.sh — list files /pickup should load into LLM context.
#
# Reads: TASKS.md (current ## Now block) and finds cited handoff/plan paths.
# Writes: tab-separated lines to stdout: <kind>\t<value>
#   Kinds: now-row, handoff, plan
#
# Args:
#   $1 (optional)  — alias or substring filter; matches first ### row in Now
#                    whose title contains the substring (case-insensitive)
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}"
focus="${1:-}"

[ -f TASKS.md ] || { echo "(no TASKS.md)" >&2; exit 0; }

# Find focus row title.
row_title=$(awk -v focus="$focus" '
  /^## Now/{flag=1; next}
  /^## /{flag=0}
  flag && /^### /{
    title=$0; sub(/^### /, "", title);
    if (focus == "" || tolower(title) ~ tolower(focus)) { print title; exit }
  }
' TASKS.md)

[ -z "$row_title" ] && { echo "(no Now row found${focus:+ for filter '$focus'})" >&2; exit 0; }
printf 'now-row\t%s\n' "$row_title"

# Extract cited handoff/plan paths from the row body (lines after ### until next ### or ##).
body=$(awk -v t="$row_title" '
  $0 == "### " t { flag=1; next }
  /^### / && flag { exit }
  /^## / && flag { exit }
  flag { print }
' TASKS.md)

# Handoff path.
handoff=$(echo "$body" | grep -oE '\.claude/handoffs/[^ )`]+\.md' | head -1)
[ -n "$handoff" ] && [ -f "$handoff" ] && printf 'handoff\t%s\n' "$handoff"

# Plan path.
plan=$(echo "$body" | grep -oE 'docs/tasks/[^ )`]+\.md' | head -1)
[ -n "$plan" ] && [ -f "$plan" ] && printf 'plan\t%s\n' "$plan"
