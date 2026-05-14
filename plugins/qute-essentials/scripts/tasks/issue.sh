#!/usr/bin/env bash
# tasks/issue.sh — create a task in whichever backend this repo uses.
#
# Usage:
#   issue.sh "title" [description...]
#
# Backend = output of `tasks_detect_source` (paperclip | tasks-md | ambiguous | none).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  cat <<EOF
Usage: /issue <title> [description...]

Creates a task in this repo's backend (paperclip or tasks-md), auto-detected.
EOF
  exit 1
fi

title="$1"; shift
description="$*"

source_kind=$(tasks_detect_source)

case "$source_kind" in
  paperclip)
    company_id=$(tasks_paperclip_company)
    project_id=$(tasks_paperclip_project "$company_id")
    [[ -n "$project_id" ]] || { echo "issue: no Paperclip project matches $(tasks_repo_root)" >&2; exit 2; }
    body=$(jq -n -c \
      --arg t "$title" \
      --arg d "$description" \
      --arg p "$project_id" '
      {title: $t, projectId: $p, status: "todo", priority: "medium"}
      | (if $d != "" then .description = $d else . end)')
    result=$(tasks_curl POST "/companies/$company_id/issues" --data-raw "$body") || exit 1
    project_name=$(tasks_paperclip_project_name "$project_id")
    echo "$result" | jq -r --arg pn "$project_name" '"created \(.identifier) in \($pn) — \(.title)"'
    ;;
  tasks-md)
    root=$(tasks_repo_root)
    file="$root/TASKS.md"
    if [[ -n "$description" ]]; then
      echo "- [ ] $title — $description" >>"$file"
    else
      echo "- [ ] $title" >>"$file"
    fi
    echo "appended to $file"
    ;;
  ambiguous)
    cat >&2 <<EOF
issue: ambiguous task source for this repo (both TASKS.md and a matching
Paperclip project found). Add an explicit declaration to CLAUDE.md:

  ## Task source: paperclip
  (or)
  ## Task source: tasks-md

EOF
    exit 2
    ;;
  none)
    cat >&2 <<EOF
issue: no task source for this repo.

Quick setup:
  - For a small/experimental repo:  touch TASKS.md   (then re-run /issue)
  - For a tracked Paperclip repo:   create a Paperclip project whose
    codebase.localFolder = $(tasks_repo_root)
EOF
    exit 2
    ;;
esac
