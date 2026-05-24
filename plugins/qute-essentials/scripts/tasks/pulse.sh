#!/usr/bin/env bash
# tasks/pulse.sh — the unified task engine behind /board and /task.
#
# Part of qute-essentials. Reuses lib.sh (Paperclip helpers) and github.sh (gh).
# MERGES every task source present in the repo (TASKS.md, GitHub Issues, Paperclip)
# into one picture, flags likely duplicates, and can create/close in any one of them.
#
# Usage:
#   pulse.sh                      unified read of all present sources (default)
#   pulse.sh report               same as above   (<- /board calls this)
#   pulse.sh add [--to <backend>] "title" [body...]   create   (<- /task)
#   pulse.sh close --in <backend> <id> [comment...]   complete (<- /task)
#
# backend in { github | paperclip | tasks-md }

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/github.sh"

ROOT=$(tasks_repo_root)

# --- collectors: TSV  source<TAB>ref<TAB>status<TAB>title ; silent when absent ---

_collect_tasks_md() {
  local file="$ROOT/TASKS.md"
  [[ -f "$file" ]] || return 0
  grep -nE '^- \[ \]' "$file" 2>/dev/null | while IFS= read -r line; do
    local lineno text
    lineno=${line%%:*}
    text=${line#*:}
    text=$(sed -E 's/^- \[ \] *//; s/\*\*//g; s/[[:space:]]+$//' <<<"$text")
    printf 'tasks-md\tL%s\topen\t%s\n' "$lineno" "$text"
  done
}

_collect_github() {
  tasks_github_available || return 0
  local json
  json=$(tasks_github_open_json) || return 0
  [[ -n "$json" && "$json" != "null" ]] || return 0
  jq -r '.[] | "github\t#\(.number)\t\(.state|ascii_downcase)\t\(.title)"' <<<"$json" 2>/dev/null
}

_collect_paperclip() {
  [[ -f "$HOME/.paperclip/auth.json" ]] || return 0
  local company_id project_id issues
  company_id=$(tasks_paperclip_company 2>/dev/null) || return 0
  project_id=$(tasks_paperclip_project "$company_id" 2>/dev/null) || return 0
  [[ -n "$project_id" ]] || return 0
  issues=$(tasks_curl GET \
    "/companies/$company_id/issues?projectId=$project_id&status=todo,in_progress,in_review,blocked" \
    2>/dev/null) || return 0
  jq -r '.[] | "paperclip\t\(.identifier)\t\(.status)\t\(.title)"' <<<"$issues" 2>/dev/null
}

# --- report (/board) ---

cmd_report() {
  local all
  all=$(_collect_tasks_md; _collect_github; _collect_paperclip)

  if [[ -z "$all" ]]; then
    echo "pulse · $(basename "$ROOT")"
    echo "no open tasks found (checked TASKS.md, GitHub Issues, Paperclip project)"
    return 0
  fi

  local n_t n_g n_p
  n_t=$(awk -F'\t' '$1=="tasks-md"{c++} END{print c+0}' <<<"$all")
  n_g=$(awk -F'\t' '$1=="github"{c++}   END{print c+0}' <<<"$all")
  n_p=$(awk -F'\t' '$1=="paperclip"{c++}END{print c+0}' <<<"$all")

  echo "pulse · $(basename "$ROOT")"
  printf 'sources: TASKS.md %s · GitHub %s · Paperclip %s\n' "$n_t" "$n_g" "$n_p"

  local src rows
  for src in paperclip github tasks-md; do
    rows=$(awk -F'\t' -v s="$src" '$1==s' <<<"$all")
    [[ -n "$rows" ]] || continue
    echo
    echo "[$src]"
    while IFS=$'\t' read -r _s ref status title; do
      printf '  %-11s %-12s %s\n' "$status" "$ref" "$title"
    done <<<"$rows"
  done

  local dups
  dups=$(awk -F'\t' '
    function norm(s){ s=tolower(s); gsub(/[^a-z0-9]+/," ",s); gsub(/^ +| +$/,"",s); return s }
    { k=norm($4); refs[k]=refs[k] sprintf("    [%s %s] %s\n",$1,$2,$4); seen[k","$1]=1 }
    END{
      for(k in refs){
        n=0; for(c in seen){ split(c,a,","); if(a[1]==k) n++ }
        if(n>1){ printf "%s", refs[k] }
      }
    }' <<<"$all")

  if [[ -n "$dups" ]]; then
    echo
    echo "WARN possible duplicates (same title across sources - link or drop one):"
    printf '%s' "$dups"
  fi
}

# --- add / close (/task) ---

_resolve_add_target() {
  local root claude_md decl
  root=$(tasks_repo_root)
  claude_md="$root/CLAUDE.md"
  if [[ -f "$claude_md" ]]; then
    decl=$(grep -E '^## Task source:' "$claude_md" 2>/dev/null | head -1 \
      | sed -E 's/^## Task source:[[:space:]]*//; s/[[:space:]].*$//' \
      | tr '[:upper:]' '[:lower:]')
    [[ "$decl" == tasks_md ]] && decl=tasks-md
    case "$decl" in github|paperclip|tasks-md) echo "$decl"; return 0 ;; esac
  fi
  local present=()
  [[ -f "$root/TASKS.md" ]] && present+=(tasks-md)
  if [[ -f "$HOME/.paperclip/auth.json" ]]; then
    local pid; pid=$(tasks_paperclip_project 2>/dev/null) || pid=""
    [[ -n "$pid" ]] && present+=(paperclip)
  fi
  tasks_github_available 2>/dev/null && present+=(github)
  [[ ${#present[@]} -eq 1 ]] && echo "${present[0]}"
}

cmd_add() {
  local backend=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --to) backend="${2:-}"; shift 2 ;;
      --) shift; break ;;
      *) break ;;
    esac
  done
  local title="${1:-}"; shift || true
  local body="${*:-}"
  [[ -n "$backend" ]] || backend=$(_resolve_add_target)
  if [[ -z "$title" ]]; then
    echo 'usage: pulse.sh add [--to <github|paperclip|tasks-md>] "title" [body...]' >&2
    return 2
  fi
  if [[ -z "$backend" ]]; then
    echo 'pulse: multiple/no task sources - pass --to <github|paperclip|tasks-md> or declare "## Task source:" in CLAUDE.md' >&2
    return 2
  fi

  case "$backend" in
    github)
      tasks_github_available || { echo "pulse: gh unavailable or not a GitHub repo" >&2; return 1; }
      tasks_github_create "$title" "$body"
      ;;
    tasks-md)
      local file="$ROOT/TASKS.md"
      [[ -f "$file" ]] || { echo "pulse: no TASKS.md in $ROOT" >&2; return 1; }
      # Collapse embedded newlines so the line-based parser in _collect_tasks_md
      # keeps working when someone pastes a multi-line title or body.
      title=${title//$'\n'/ }
      body=${body//$'\n'/ }
      if [[ -n "$body" ]]; then
        printf -- '- [ ] **%s** - %s\n' "$title" "$body" >>"$file"
      else
        printf -- '- [ ] **%s**\n' "$title" >>"$file"
      fi
      echo "appended to TASKS.md"
      ;;
    paperclip)
      local company_id project_id payload response
      company_id=$(tasks_paperclip_company) || return 1
      project_id=$(tasks_paperclip_project "$company_id") || return 1
      [[ -n "$project_id" ]] || { echo "pulse: no Paperclip project for $ROOT" >&2; return 1; }
      payload=$(jq -n --arg t "$title" --arg b "$body" --arg p "$project_id" \
        '{title:$t, description:(if $b=="" then null else $b end), projectId:$p, status:"todo", priority:"medium"}')
      response=$(tasks_curl POST "/companies/$company_id/issues" --data "$payload") || return 1
      jq -re '"\(.identifier // .id) \(.title)"' <<<"$response" \
        || { echo "pulse: paperclip create succeeded but response missing identifier/id" >&2; echo "$response" >&2; return 1; }
      ;;
    *)
      echo "pulse: unknown backend '$backend'" >&2; return 2 ;;
  esac
}

cmd_close() {
  local backend=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --in) backend="${2:-}"; shift 2 ;;
      --) shift; break ;;
      *) break ;;
    esac
  done
  local id="${1:-}"; shift || true
  local comment="${*:-}"
  if [[ -z "$backend" || -z "$id" ]]; then
    echo 'usage: pulse.sh close --in <github|paperclip> <id> [comment...]' >&2
    return 2
  fi

  case "$backend" in
    github)
      tasks_github_available || { echo "pulse: gh unavailable or not a GitHub repo" >&2; return 1; }
      tasks_github_close "$id" "$comment"
      ;;
    paperclip)
      local response
      response=$(tasks_curl PATCH "/issues/$id" --data "$(jq -n '{status:"done"}')") || return 1
      jq -re '.identifier // .id' <<<"$response" \
        || { echo "pulse: paperclip close response missing identifier/id" >&2; echo "$response" >&2; return 1; }
      ;;
    tasks-md)
      echo "pulse: check off the item directly in TASKS.md (- [ ] -> - [x])" >&2
      return 2
      ;;
    *)
      echo "pulse: unknown backend '$backend'" >&2; return 2 ;;
  esac
}

# --- dispatch ---

cmd="${1:-report}"
case "$cmd" in
  report) shift || true; cmd_report "$@" ;;
  add)    shift;        cmd_add "$@" ;;
  close)  shift;        cmd_close "$@" ;;
  *)      cmd_report "$@" ;;
esac
