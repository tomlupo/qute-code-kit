#!/bin/bash
# PostToolUse hook: remind to update plan after file edits
# Silent when no .flow-state exists

FLOW_STATE=".flow-state"

[ ! -f "$FLOW_STATE" ] && exit 0

ACTIVE_PLAN=$(grep '^active_plan:' "$FLOW_STATE" 2>/dev/null | sed 's/^active_plan: *//')

[ -z "$ACTIVE_PLAN" ] && exit 0

echo "[flow] File modified. Update plan status if a phase was completed."

exit 0
