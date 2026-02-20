#!/bin/bash
# PreToolUse hook: re-read active plan header before Write/Edit/Bash decisions
# Silent when no .flow-state exists (zero noise)

FLOW_STATE=".flow-state"

[ ! -f "$FLOW_STATE" ] && exit 0

ACTIVE_PLAN=$(grep '^active_plan:' "$FLOW_STATE" 2>/dev/null | sed 's/^active_plan: *//')

[ -z "$ACTIVE_PLAN" ] && exit 0
[ ! -f "$ACTIVE_PLAN" ] && exit 0

# Show goal + current phase (first 30 lines covers this in standard plan format)
echo "[flow] Active plan: $ACTIVE_PLAN"
head -30 "$ACTIVE_PLAN" 2>/dev/null | grep -E '(^#|Goal|Current Phase|Status:)' || true

exit 0
