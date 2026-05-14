#!/usr/bin/env bash
# tasks/board.sh — list open tasks in this repo's backend.
#
# Usage:
#   board.sh           # full output
#   board.sh --open    # tasks-md mode: only unchecked items

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"

open_only=0
[[ "${1:-}" == "--open" ]] && open_only=1

source_kind=$(tasks_detect_source)

case "$source_kind" in
  paperclip)
    company_id=$(tasks_paperclip_company)
    project_id=$(tasks_paperclip_project "$company_id")
    [[ -n "$project_id" ]] || { echo "board: no Paperclip project matches $(tasks_repo_root)" >&2; exit 2; }
    project_name=$(tasks_paperclip_project_name "$project_id")
    issues=$(tasks_curl GET "/companies/$company_id/issues?projectId=$project_id&status=todo,in_progress,in_review,blocked") || exit 1
    total=$(echo "$issues" | jq 'length')
    echo "$project_name  ($total open)"
    for s in in_progress todo blocked in_review; do
      count=$(echo "$issues" | jq --arg s "$s" 'map(select(.status == $s)) | length')
      (( count > 0 )) || continue
      echo
      echo "  $s ($count)"
      echo "$issues" | jq -r --arg s "$s" '
        def pri_rank: {critical:1, high:2, medium:3, low:4}[. // ""] // 5;
        map(select(.status == $s))
        | sort_by([(.priority | pri_rank), .identifier])[]
        | "    \(.identifier)  \(.priority // "—")  \(.title)"'
    done
    ;;
  tasks-md)
    root=$(tasks_repo_root)
    file="$root/TASKS.md"
    if (( open_only )); then
      grep -E '^- \[ \]' "$file" 2>/dev/null || echo "(no open items)"
    else
      cat "$file"
    fi
    ;;
  ambiguous)
    cat >&2 <<EOF
board: ambiguous task source for this repo (TASKS.md + matching Paperclip project).
Add to CLAUDE.md:  ## Task source: paperclip   (or tasks-md)
EOF
    exit 2
    ;;
  none)
    echo "(no task source for this repo — touch TASKS.md or create a Paperclip project to set one up)"
    ;;
esac
