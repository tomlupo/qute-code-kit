#!/usr/bin/env bash
# tasks/lib.sh — shared helpers for /issue and /board.
#
# Source this from skill scripts:
#   source "$CLAUDE_PLUGIN_ROOT/scripts/tasks/lib.sh"
#
# After sourcing, the following are available:
#   tasks_repo_root           absolute path of current repo (git toplevel, or PWD)
#   tasks_detect_source       prints "paperclip" | "tasks-md" | "ambiguous" | "none"
#   tasks_paperclip_token     prints board token (from ~/.paperclip/auth.json)
#   tasks_paperclip_base      prints API base URL
#   tasks_paperclip_company   resolves declared company-id (or default tom-projects)
#   tasks_paperclip_project   resolves Paperclip project for current repo (UUID)
#   tasks_curl <method> <path> [curl-args...]   minimal authed JSON request

set -uo pipefail

# Cache lives in ~/.cache/qute-essentials/tasks for ephemeral lookups.
_TASKS_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/qute-essentials/tasks"
_TASKS_CACHE_TTL=300   # seconds

# ---------------------------------------------------------------------------
# Repo discovery
# ---------------------------------------------------------------------------

tasks_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Read `## Task source: <backend>` from CLAUDE.md (anywhere in the file).
# Prints "paperclip" or "tasks-md" or empty.
_tasks_read_declaration() {
  local root claude_md val
  root=$(tasks_repo_root)
  claude_md="$root/CLAUDE.md"
  [[ -f "$claude_md" ]] || return 0
  val=$(grep -E '^## Task source:' "$claude_md" 2>/dev/null \
    | head -1 \
    | sed -E 's/^## Task source:[[:space:]]*//; s/[[:space:]].*$//' \
    | tr '[:upper:]' '[:lower:]')
  case "$val" in
    paperclip|tasks-md|tasks_md) [[ "$val" == tasks_md ]] && val=tasks-md; echo "$val" ;;
    *) ;;
  esac
}

# ---------------------------------------------------------------------------
# Paperclip API basics — minimal subset, no orchestrator dependency
# ---------------------------------------------------------------------------

tasks_paperclip_base() {
  # Prefer the known core URL; fall back to first credential entry.
  local auth="$HOME/.paperclip/auth.json"
  [[ -f "$auth" ]] || return 1
  jq -r '
    .credentials["http://100.96.175.35:3100"].apiBase //
    (.credentials | to_entries[0].value.apiBase) // empty
  ' "$auth"
}

tasks_paperclip_token() {
  local auth="$HOME/.paperclip/auth.json"
  [[ -f "$auth" ]] || return 1
  jq -r '
    .credentials["http://100.96.175.35:3100"].token //
    (.credentials | to_entries[0].value.token) // empty
  ' "$auth"
}

# Authenticated curl. Path is /api/... or /...; normalized.
tasks_curl() {
  local method="$1" path="$2"; shift 2
  local base token
  base=$(tasks_paperclip_base) || { echo "tasks: no paperclip auth (~/.paperclip/auth.json)" >&2; return 1; }
  token=$(tasks_paperclip_token) || return 1
  [[ "$path" == /api/* ]] || path="/api/${path#/}"
  local body status tmp; tmp=$(mktemp)
  status=$(curl -sS -o "$tmp" -w '%{http_code}' \
    -X "$method" \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    "$@" \
    "${base%/}$path")
  body=$(cat "$tmp"); rm -f "$tmp"
  echo "$body"
  if [[ ! "$status" =~ ^2 ]]; then
    echo "tasks: $method $path → HTTP $status" >&2
    return 1
  fi
}

# Cached fetch (5min TTL) for company list + their projects.
_tasks_cached() {
  local key="$1" path="$2"
  local file="$_TASKS_CACHE_DIR/$key.json"
  if [[ -f "$file" ]]; then
    local mtime now
    mtime=$(stat -c %Y "$file" 2>/dev/null) || mtime=0
    now=$(date +%s)
    if (( now - mtime < _TASKS_CACHE_TTL )); then
      cat "$file"; return 0
    fi
  fi
  mkdir -p "$_TASKS_CACHE_DIR"
  tasks_curl GET "$path" >"$file" || { rm -f "$file"; return 1; }
  cat "$file"
}

# Resolve the company. Reads optional declaration "## Task source: paperclip
# (company: tom-projects)" or defaults to tom-projects. Prints the company UUID.
tasks_paperclip_company() {
  local root claude_md decl_company
  root=$(tasks_repo_root)
  claude_md="$root/CLAUDE.md"
  if [[ -f "$claude_md" ]]; then
    decl_company=$(grep -E '^## Task source:[[:space:]]*paperclip' "$claude_md" 2>/dev/null \
      | head -1 \
      | sed -nE 's/.*\(company:[[:space:]]*([^)]+)\).*/\1/p' \
      | tr -d ' ')
  fi
  local ref="${decl_company:-tom-projects}"
  local companies
  companies=$(_tasks_cached companies /companies) || return 1
  echo "$companies" | jq -e -r --arg r "$ref" '
    map(select(
      .id == $r or
      (.name|ascii_downcase) == ($r|ascii_downcase) or
      (.issuePrefix|ascii_downcase) == ($r|ascii_downcase)
    )) | if length == 0 then error("no company matching \($r)") else .[0].id end
  '
}

# Resolve the Paperclip project for the current repo. Match against each
# project's codebase.localFolder vs git toplevel. Prints UUID or empty.
tasks_paperclip_project() {
  local company_id="${1:-}"
  [[ -n "$company_id" ]] || company_id=$(tasks_paperclip_company) || return 1
  local root projects
  root=$(tasks_repo_root)
  projects=$(_tasks_cached "projects-$company_id" "/companies/$company_id/projects") || return 1
  echo "$projects" | jq -r --arg root "$root" '
    map(select(
      .codebase.localFolder == $root or
      .codebase.effectiveLocalFolder == $root
    )) | if length == 0 then "" else .[0].id end'
}

# Friendly project name for logs.
tasks_paperclip_project_name() {
  local pid="$1" company_id projects
  company_id=$(tasks_paperclip_company) || return 1
  projects=$(_tasks_cached "projects-$company_id" "/companies/$company_id/projects") || return 1
  echo "$projects" | jq -r --arg id "$pid" 'map(select(.id == $id)) | if length == 0 then $id else .[0].name end'
}

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

# Detection precedence:
#   1. CLAUDE.md `## Task source: <backend>` declaration → wins
#   2. Auto-detect:
#        Paperclip project matches CWD's git toplevel  → "paperclip"
#        TASKS.md exists in repo root                 → "tasks-md"
#   3. Both auto-detected → "ambiguous"
#   4. Neither             → "none"
#
# Prints exactly one of: paperclip | tasks-md | ambiguous | none
tasks_detect_source() {
  local declared
  declared=$(_tasks_read_declaration)
  if [[ -n "$declared" ]]; then
    echo "$declared"; return 0
  fi
  local has_paperclip="" has_tasks_md=""
  local root; root=$(tasks_repo_root)
  if [[ -f "$root/TASKS.md" ]]; then
    has_tasks_md=1
  fi
  # Paperclip auto-detect requires auth + a matching project.
  if [[ -f "$HOME/.paperclip/auth.json" ]]; then
    local pid
    pid=$(tasks_paperclip_project 2>/dev/null) || pid=""
    [[ -n "$pid" ]] && has_paperclip=1
  fi
  if [[ -n "$has_paperclip" && -n "$has_tasks_md" ]]; then
    echo "ambiguous"
  elif [[ -n "$has_paperclip" ]]; then
    echo "paperclip"
  elif [[ -n "$has_tasks_md" ]]; then
    echo "tasks-md"
  else
    echo "none"
  fi
}
