#!/usr/bin/env bash
# tasks/github.sh — GitHub Issues source for /pulse, via the gh CLI.
#
# Sourced by pulse.sh. Requires `gh` on PATH and `gh auth login` (or GH_TOKEN).
# All functions are no-ops (return non-zero, print nothing) when gh is missing
# or the cwd is not a GitHub repo, so /pulse degrades gracefully.

set -uo pipefail

# True when gh is available AND we're inside a GitHub repo with a remote.
tasks_github_available() {
  command -v gh >/dev/null 2>&1 || return 1
  gh repo view --json nameWithOwner >/dev/null 2>&1
}

# Prints "owner/name" or nothing.
tasks_github_repo() {
  gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null
}

# Open issues as JSON array: [{number,title,state,labels,assignees,updatedAt,url}]
# Excludes PRs (gh issue list already does).
tasks_github_open_json() {
  gh issue list --state open --limit 200 \
    --json number,title,state,labels,assignees,updatedAt,url 2>/dev/null
}

# Count of open issues (0 on any failure). Excludes PRs.
tasks_github_open_count() {
  gh issue list --state open --limit 500 --json number -q 'length' 2>/dev/null || echo 0
}

# Path to the label taxonomy (config/task-taxonomy.json). Resolved from
# CLAUDE_PLUGIN_ROOT when set, else relative to this script (scripts/tasks/ ->
# ../../config/). Prints the path (may not exist).
tasks_github_taxonomy_path() {
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -f "$CLAUDE_PLUGIN_ROOT/config/task-taxonomy.json" ]]; then
    printf '%s\n' "$CLAUDE_PLUGIN_ROOT/config/task-taxonomy.json"
    return 0
  fi
  local here; here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  printf '%s\n' "$here/../../config/task-taxonomy.json"
}

# Read one field (color|description) for a taxonomy value.
# Args: <dimension type|structure> <value> <field color|description>
# Prints the field or nothing. Degrades gracefully if jq/python are missing.
tasks_github_taxonomy_field() {
  local dim="$1" val="$2" field="$3" path
  path=$(tasks_github_taxonomy_path)
  [[ -f "$path" ]] || return 1
  if command -v jq >/dev/null 2>&1; then
    jq -r --arg d "$dim" --arg v "$val" --arg f "$field" \
      '.[$d].values[$v][$f] // empty' "$path" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$path" "$dim" "$val" "$field" <<'PY' 2>/dev/null
import json, sys
path, dim, val, field = sys.argv[1:5]
try:
    d = json.load(open(path))
    print(d.get(dim, {}).get("values", {}).get(val, {}).get(field, "") or "")
except Exception:
    pass
PY
  else
    return 1
  fi
}

# Ensure a label exists (create-or-update via --force) from the taxonomy, then
# echo the label name so the caller can --add-label it. Args: <dimension> <value>
# No-op (returns non-zero) if the value isn't in the taxonomy.
tasks_github_ensure_label() {
  local dim="$1" val="$2" color desc
  [[ -n "$val" ]] || return 1
  color=$(tasks_github_taxonomy_field "$dim" "$val" color)
  desc=$(tasks_github_taxonomy_field "$dim" "$val" description)
  # Unknown value (not in taxonomy) -> skip rather than invent a label.
  [[ -n "$color" ]] || return 1
  gh label create "$val" --color "$color" --description "${desc:-}" --force >/dev/null 2>&1 || true
  printf '%s\n' "$val"
}

# Apply TYPE + STRUCTURE labels to an issue, creating them first from the
# taxonomy. Args: <issue-number> <type> <structure>. Either label may be empty.
tasks_github_apply_labels() {
  local num="$1" type="${2:-}" structure="${3:-}"
  local -a add=()
  local lbl
  if [[ -n "$type" ]]; then
    lbl=$(tasks_github_ensure_label type "$type") && [[ -n "$lbl" ]] && add+=(--add-label "$lbl")
  fi
  if [[ -n "$structure" ]]; then
    lbl=$(tasks_github_ensure_label structure "$structure") && [[ -n "$lbl" ]] && add+=(--add-label "$lbl")
  fi
  [[ ${#add[@]} -gt 0 ]] || return 0
  gh issue edit "$num" "${add[@]}" >/dev/null 2>&1
}

# Create an issue.  Args: [--type <t>] [--structure <s>] <title> [body...]
# Prints the new issue URL. Back-compat: with no --type/--structure it behaves
# exactly as before (no labels applied).
tasks_github_create() {
  local type="" structure=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --type|--structure)
        # Require a value — a trailing flag with no value would make `shift 2`
        # fail (only one arg left) and spin this loop forever.
        if [[ $# -lt 2 ]]; then
          echo "tasks_github_create: $1 requires a value" >&2; return 2
        fi
        case "$1" in
          --type) type="$2" ;;
          --structure) structure="$2" ;;
        esac
        shift 2 ;;
      --) shift; break ;;
      *) break ;;
    esac
  done
  local title="$1"; shift || true
  local body="${*:-}"
  local url; url=$(gh issue create --title "$title" --body "$body") || return 1
  printf '%s\n' "$url"
  if [[ -n "$type" || -n "$structure" ]]; then
    # Derive the issue number from the trailing path segment of the URL.
    # The issue is already created (URL printed above); a label-application
    # failure must NOT return non-zero — that would signal "add failed" and
    # invite a duplicate retry. Warn to stderr and succeed.
    local num="${url##*/}"
    if [[ "$num" =~ ^[0-9]+$ ]]; then
      tasks_github_apply_labels "$num" "$type" "$structure" \
        || echo "pulse: issue created but label apply failed (labels: type=$type structure=$structure)" >&2
    fi
  fi
}

# Resolve the acting agent's name, mirroring the agents-shared-log convention:
# $AGENT_NAME -> $DISPATCHER_SESSION_NAME -> basename "$PWD".
task_agent_prefix() {
  local name="${AGENT_NAME:-${DISPATCHER_SESSION_NAME:-$(basename "$PWD")}}"
  printf '[agent:%s] ' "$name"
}

# Prepend the [agent:<name>] prefix to a comment body unless empty or already
# prefixed. Prints the (possibly prefixed) body. Empty in -> empty out.
task_agent_prefix_comment() {
  local body="${1:-}"
  [[ -n "$body" ]] || { printf '%s' ""; return 0; }
  case "$body" in
    '[agent:'*) printf '%s' "$body" ;;
    *) printf '%s%s' "$(task_agent_prefix)" "$body" ;;
  esac
}

# Close an issue.  Args: <number> [comment...]
tasks_github_close() {
  local num="$1"; shift || true
  local comment="${*:-}"
  if [[ -n "$comment" ]]; then
    comment=$(task_agent_prefix_comment "$comment")
    gh issue close "$num" --comment "$comment"
  else
    gh issue close "$num"
  fi
}
