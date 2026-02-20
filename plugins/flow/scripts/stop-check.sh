#!/bin/bash
# Stop hook: check plan completion status before session ends
# Silent when no .flow-state exists

FLOW_STATE=".flow-state"

[ ! -f "$FLOW_STATE" ] && exit 0

ACTIVE_PLAN=$(grep '^active_plan:' "$FLOW_STATE" 2>/dev/null | sed 's/^active_plan: *//')

[ -z "$ACTIVE_PLAN" ] && exit 0

if [ ! -f "$ACTIVE_PLAN" ]; then
    echo "[flow] Warning: active plan '$ACTIVE_PLAN' not found. Run /flow:deactivate to clear."
    exit 0
fi

# Count phases and completion
TOTAL=$(grep -c '### ' "$ACTIVE_PLAN" 2>/dev/null || echo 0)
COMPLETE=$(grep -ciE '(status.*complete|\[x\])' "$ACTIVE_PLAN" 2>/dev/null || echo 0)

if [ "$TOTAL" -gt 0 ] && [ "$COMPLETE" -ge "$TOTAL" ]; then
    echo "[flow] All phases complete ($COMPLETE/$TOTAL). Run /flow:complete to archive."
else
    echo "[flow] Plan in progress ($COMPLETE/$TOTAL phases complete): $ACTIVE_PLAN"
fi

exit 0
