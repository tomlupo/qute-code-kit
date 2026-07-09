#!/usr/bin/env bash
# tasks/pulse.sh — the tiered task engine behind /repo-status and /task.
#
# Part of qute-essentials. Generic and project-agnostic: TWO tiers only.
#   Tier 1 (default)  — TASKS.md in the repo root (managed directly here).
#   Tier 2 (graduate) — plain GitHub Issues via the `gh` CLI.
# A repo has ONE live store at a time (TASKS.md OR Issues), told apart by the
# migration tombstone in TASKS.md. See lib.sh for the detection rules.
#
# Usage:
#   pulse.sh                      read the ACTIVE store (default)
#   pulse.sh report               same as above           (<- /repo-status)
#   pulse.sh add "title" [body...]            create in the active store (<- /task)
#   pulse.sh add --to <github|tasks-md> ...   create in a named store
#   pulse.sh close <ref> [comment...]         complete in the active store (<- /task)
#   pulse.sh close --in <github|tasks-md> ... complete in a named store
#   pulse.sh migrate              move open TASKS.md items -> GitHub Issues + tombstone
#   pulse.sh decline              write the keep-local marker so migration stops nagging

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/github.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib.sh"

ROOT=$(tasks_repo_root)

# --- shared: emit the migration proposal block when warranted ---

_emit_proposal() {
  tasks_should_propose || return 0
  local n thr
  n=$(tasks_open_count_md)
  thr=$(tasks_threshold)
  echo
  echo "PROPOSE migrate to GitHub Issues:"
  echo "  TASKS.md has $n open item(s) (threshold $thr) and this repo is on GitHub."
  echo "  Graduate? \`/task migrate\` opens one issue per item and leaves TASKS.md as a"
  echo "  pointer to the Issues tab. One store, no double-tracking."
  echo "  Staying on TASKS.md is fine — \`/task decline\` silences this once and for all."
  # Record that we've proposed, so this fires truly ONCE (not "nag until declined").
  tasks_mark_proposed
}

# --- report (/repo-status) ---

cmd_report() {
  local store; store=$(tasks_active_store)
  echo "pulse · $(basename "$ROOT")  [store: $store]"

  case "$store" in
    github)
      # Distinguish "could not reach GitHub" from "genuinely 0 open issues":
      # if gh/auth/network is broken we must NOT render an empty board.
      if ! tasks_github_available 2>/dev/null; then
        echo "pulse: cannot reach GitHub (gh unavailable, not authenticated, or no remote)." >&2
        echo "       The active store is GitHub Issues but it could not be read — backlog state unknown." >&2
        return 1
      fi
      local json
      json=$(tasks_github_open_json 2>/dev/null)
      if [[ -z "$json" || "$json" == "null" ]]; then
        echo "pulse: failed to read GitHub issues (gh error) — backlog state unknown." >&2
        return 1
      fi
      if [[ "$json" == "[]" ]]; then
        echo "no open GitHub issues"
        return 0
      fi
      jq -r '.[] | "  open  #\(.number)  \(.title)"' <<<"$json" 2>/dev/null
      ;;
    tasks-md)
      local f; f=$(tasks_tasksmd_path)
      local n; n=$(tasks_open_count_md)
      if [[ ! -f "$f" ]]; then
        echo "no TASKS.md yet — \`/task \"<title>\"\` creates it"
        return 0
      fi
      if (( n == 0 )); then
        echo "TASKS.md has no open items"
      else
        grep -nE '^- \[ \]' "$f" 2>/dev/null | while IFS= read -r line; do
          local lineno text
          lineno=${line%%:*}
          text=${line#*:}
          text=$(sed -E 's/^- \[ \] *//; s/\*\*//g; s/[[:space:]]+$//' <<<"$text")
          printf '  open  L%-5s %s\n' "$lineno" "$text"
        done
      fi
      _emit_proposal
      ;;
  esac
}

# --- add / close (/task) ---

cmd_add() {
  local backend="" type="" structure=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --to|--type|--structure)
        # Value-taking flags: require a value so a trailing `--type` (no value)
        # can't spin the loop forever (shift 2 fails when only one arg remains).
        if [[ $# -lt 2 ]]; then
          echo "pulse: $1 requires a value" >&2; return 2
        fi
        case "$1" in
          --to) backend="$2" ;;
          --type) type="$2" ;;
          --structure) structure="$2" ;;
        esac
        shift 2 ;;
      --) shift; break ;;
      *) break ;;
    esac
  done
  local title="${1:-}"; shift || true
  local body="${*:-}"
  if [[ -z "$title" ]]; then
    echo 'usage: pulse.sh add [--to <github|tasks-md>] [--type <t>] [--structure <s>] "title" [body...]' >&2
    return 2
  fi
  [[ -n "$backend" ]] || backend=$(tasks_active_store)

  case "$backend" in
    github)
      tasks_github_available || { echo "pulse: gh unavailable or not a GitHub repo" >&2; return 1; }
      local -a create_opts=()
      [[ -n "$type" ]] && create_opts+=(--type "$type")
      [[ -n "$structure" ]] && create_opts+=(--structure "$structure")
      tasks_github_create ${create_opts[@]+"${create_opts[@]}"} "$title" "$body"
      ;;
    tasks-md)
      local file="$ROOT/TASKS.md"
      if [[ -f "$file" ]] && tasks_is_tombstone; then
        echo "pulse: TASKS.md is a tombstone (this repo graduated to GitHub Issues)." >&2
        echo "       Use \`--to github\`, or remove the tombstone to go back to local." >&2
        return 1
      fi
      # Create TASKS.md on first use so Tier 1 needs zero setup.
      [[ -f "$file" ]] || printf '# Tasks\n\n' >"$file"
      # Collapse embedded newlines so the line-based parser keeps working.
      title=${title//$'\n'/ }
      body=${body//$'\n'/ }
      if [[ -n "$body" ]]; then
        printf -- '- [ ] **%s** - %s\n' "$title" "$body" >>"$file"
      else
        printf -- '- [ ] **%s**\n' "$title" >>"$file"
      fi
      echo "appended to TASKS.md"
      _emit_proposal
      ;;
    *)
      echo "pulse: unknown backend '$backend' (expected github|tasks-md)" >&2; return 2 ;;
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
  if [[ -z "$id" ]]; then
    echo 'usage: pulse.sh close [--in <github|tasks-md>] <ref> [comment...]' >&2
    return 2
  fi
  [[ -n "$backend" ]] || backend=$(tasks_active_store)

  case "$backend" in
    github)
      tasks_github_available || { echo "pulse: gh unavailable or not a GitHub repo" >&2; return 1; }
      tasks_github_close "${id#\#}" "$comment"
      ;;
    tasks-md)
      echo "pulse: check the item off directly in TASKS.md (- [ ] -> - [x])" >&2
      return 2
      ;;
    *)
      echo "pulse: unknown backend '$backend' (expected github|tasks-md)" >&2; return 2 ;;
  esac
}

# --- migrate (TASKS.md -> GitHub Issues) ---

cmd_migrate() {
  local file="$ROOT/TASKS.md"
  tasks_github_available || { echo "pulse: gh unavailable or not a GitHub repo — cannot migrate" >&2; return 1; }
  [[ -f "$file" ]] || { echo "pulse: no TASKS.md to migrate" >&2; return 1; }
  if tasks_is_tombstone; then
    echo "pulse: TASKS.md is already a tombstone — nothing to migrate" >&2
    return 0
  fi

  local repo url created=0 total=0
  repo=$(tasks_github_repo)

  # Open each item as an issue. Track failures so we NEVER tombstone (and thus
  # erase) TASKS.md unless every open item migrated successfully.
  local urls=()
  local failed=()
  while IFS= read -r text; do
    [[ -n "$text" ]] || continue
    total=$((total + 1))
    url=$(tasks_github_create "$text" "Migrated from TASKS.md.") || {
      echo "pulse: failed to create issue for: $text" >&2
      failed+=("$text")
      continue
    }
    urls+=("$url")
    created=$((created + 1))
    echo "  + $url  $text"
  done < <(grep -nE '^- \[ \]' "$file" 2>/dev/null \
            | sed -E 's/^[0-9]+:- \[ \] *//; s/\*\*//g; s/[[:space:]]+$//')

  # Nothing to migrate — don't tombstone an (effectively) empty/no-open-items file.
  if (( total == 0 )); then
    echo "pulse: no open items in TASKS.md to migrate — leaving it intact" >&2
    return 1
  fi

  # Any failure -> leave TASKS.md fully intact so the failed items are preserved.
  if (( ${#failed[@]} > 0 )); then
    echo "pulse: $created/$total item(s) migrated; ${#failed[@]} failed — TASKS.md left intact (no tombstone)." >&2
    echo "pulse: failed item(s):" >&2
    local f
    for f in "${failed[@]}"; do echo "  - $f" >&2; done
    echo "pulse: re-run migrate after resolving the gh failure(s) above." >&2
    return 1
  fi

  # All open items migrated (created == total > 0): safe to tombstone.
  local issues_url="https://github.com/$repo/issues"
  {
    echo "# Tasks"
    echo ""
    echo "$TASKS_TOMBSTONE_MARKER"
    echo ""
    echo "This repo's task store graduated to **GitHub Issues** on $(date +%Y-%m-%d)."
    echo "Live backlog: $issues_url"
    echo ""
    echo "\`/task\` and \`/repo-status\` now route to Issues for this repo. Do not re-add"
    echo "tasks here — this file is a pointer, not a store."
  } >"$file"

  echo "migrated $created item(s) -> $issues_url ; TASKS.md is now a tombstone"
}

# --- decline (silence the migration proposal) ---

cmd_decline() {
  local file="$ROOT/TASKS.md"
  if [[ -f "$file" ]] && tasks_is_keep_local; then
    echo "already declined — TASKS.md carries the keep-local marker"
    return 0
  fi
  [[ -f "$file" ]] || printf '# Tasks\n\n' >"$file"
  # Insert the marker right after the first line (the heading) if present.
  if grep -qE '^# ' "$file" 2>/dev/null; then
    awk -v m="$TASKS_KEEPLOCAL_MARKER" 'NR==1{print; print ""; print m; next} {print}' \
      "$file" >"$file.tmp" && mv "$file.tmp" "$file"
  else
    printf '%s\n' "$TASKS_KEEPLOCAL_MARKER" >>"$file"
  fi
  echo "keep-local marker written — migration proposal silenced for this repo"
}

# --- dispatch ---

cmd="${1:-report}"
case "$cmd" in
  report)  shift || true; cmd_report "$@" ;;
  add)     shift;         cmd_add "$@" ;;
  close)   shift;         cmd_close "$@" ;;
  migrate) shift;         cmd_migrate "$@" ;;
  decline) shift;         cmd_decline "$@" ;;
  *)       cmd_report "$@" ;;
esac
