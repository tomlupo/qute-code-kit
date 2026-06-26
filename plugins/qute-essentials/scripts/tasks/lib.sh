#!/usr/bin/env bash
# tasks/lib.sh — shared helpers for the tiered task engine (/board + /task).
#
# Source this from skill scripts:
#   source "$CLAUDE_PLUGIN_ROOT/scripts/tasks/lib.sh"
#
# Tiered model (generic, project-agnostic):
#   Tier 1 (default)  — TASKS.md in the repo root. Zero setup, plain markdown
#                       checklist. Used for small/new repos or any repo with no
#                       GitHub remote.
#   Tier 2 (graduate) — plain GitHub Issues via the `gh` CLI. A repo earns this
#                       once it has a GitHub remote AND the list outgrows a flat
#                       file (open-task count past a threshold, or a need for
#                       labels/assignees/sub-issues/cross-session durability).
#
# A repo has exactly ONE live store at a time. After migration TASKS.md becomes
# a tombstone pointing at the Issues tab; its presence-as-tombstone is how the
# engine knows the live store is now GitHub.
#
# After sourcing, the following are available:
#   tasks_repo_root               absolute path of current repo (git toplevel, or PWD)
#   tasks_tasksmd_path            absolute path of TASKS.md (whether or not it exists)
#   tasks_is_tombstone            true if TASKS.md exists and is a migration tombstone
#   tasks_is_keep_local           true if TASKS.md carries the "keep local" decline marker
#   tasks_open_count_md           number of open `- [ ]` items in TASKS.md (0 if absent)
#   tasks_active_store            prints "tasks-md" | "github"  (the live store)
#   tasks_should_propose          true if a Tier-1 -> Tier-2 migration should be offered
#   tasks_threshold               the open-task threshold (default 12, tunable)

set -uo pipefail

# Markers written into TASKS.md as HTML comments — invisible in rendered
# markdown, greppable by the engine.
TASKS_TOMBSTONE_MARKER='<!-- qute-tasks: migrated-to-github -->'
TASKS_KEEPLOCAL_MARKER='<!-- qute-tasks: keep-local -->'

# ---------------------------------------------------------------------------
# Repo discovery
# ---------------------------------------------------------------------------

tasks_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

tasks_tasksmd_path() {
  echo "$(tasks_repo_root)/TASKS.md"
}

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Open-task count at which a GitHub-backed repo is offered Issues migration.
# Override per-machine with QUTE_TASKS_THRESHOLD, or per-repo with a
# `## Task threshold: <N>` line in CLAUDE.md.
tasks_threshold() {
  local root claude_md decl
  if [[ -n "${QUTE_TASKS_THRESHOLD:-}" ]]; then
    echo "$QUTE_TASKS_THRESHOLD"; return 0
  fi
  root=$(tasks_repo_root)
  claude_md="$root/CLAUDE.md"
  if [[ -f "$claude_md" ]]; then
    decl=$(grep -E '^## Task threshold:' "$claude_md" 2>/dev/null | head -1 \
      | sed -E 's/^## Task threshold:[[:space:]]*//; s/[^0-9].*$//')
    [[ "$decl" =~ ^[0-9]+$ ]] && { echo "$decl"; return 0; }
  fi
  echo 12
}

# ---------------------------------------------------------------------------
# TASKS.md state
# ---------------------------------------------------------------------------

tasks_is_tombstone() {
  local f; f=$(tasks_tasksmd_path)
  [[ -f "$f" ]] && grep -qF "$TASKS_TOMBSTONE_MARKER" "$f" 2>/dev/null
}

tasks_is_keep_local() {
  local f; f=$(tasks_tasksmd_path)
  [[ -f "$f" ]] && grep -qF "$TASKS_KEEPLOCAL_MARKER" "$f" 2>/dev/null
}

# Count open `- [ ]` checklist items in TASKS.md (0 when absent/tombstoned).
tasks_open_count_md() {
  local f; f=$(tasks_tasksmd_path)
  [[ -f "$f" ]] || { echo 0; return 0; }
  grep -cE '^- \[ \]' "$f" 2>/dev/null || echo 0
}

# ---------------------------------------------------------------------------
# Active store resolution
# ---------------------------------------------------------------------------
#
# Precedence:
#   1. CLAUDE.md `## Task source: <github|tasks-md>`     -> explicit override
#   2. TASKS.md present AND tombstoned                   -> github
#   3. TASKS.md present (live)                           -> tasks-md
#   4. TASKS.md absent, gh remote reachable with >=1 open issue -> github
#   5. otherwise                                         -> tasks-md (Tier-1 default)
#
# Prints exactly one of: tasks-md | github
tasks_active_store() {
  local root claude_md decl
  root=$(tasks_repo_root)
  claude_md="$root/CLAUDE.md"
  if [[ -f "$claude_md" ]]; then
    decl=$(grep -E '^## Task source:' "$claude_md" 2>/dev/null | head -1 \
      | sed -E 's/^## Task source:[[:space:]]*//; s/[[:space:]].*$//' \
      | tr '[:upper:]' '[:lower:]')
    [[ "$decl" == tasks_md ]] && decl=tasks-md
    case "$decl" in github|tasks-md) echo "$decl"; return 0 ;; esac
  fi

  if [[ -f "$(tasks_tasksmd_path)" ]]; then
    if tasks_is_tombstone; then echo "github"; else echo "tasks-md"; fi
    return 0
  fi

  # No TASKS.md. If the repo already runs on Issues, stay there.
  if tasks_github_available 2>/dev/null; then
    local n; n=$(tasks_github_open_count 2>/dev/null || echo 0)
    [[ "$n" =~ ^[0-9]+$ ]] && (( n > 0 )) && { echo "github"; return 0; }
  fi
  echo "tasks-md"
}

# ---------------------------------------------------------------------------
# Migration proposal
# ---------------------------------------------------------------------------
#
# Propose a Tier-1 -> Tier-2 migration ONCE when ALL hold:
#   - live store is tasks-md
#   - a GitHub remote is reachable (gh can see the repo)
#   - the user hasn't declined (no keep-local marker)
#   - the list has earned it: open count >= threshold
#
# (A task needing labels/assignees/sub-issues is the other "earns it" trigger,
# but that's a judgement the skill makes from the task text, not the counter.)
tasks_should_propose() {
  [[ "$(tasks_active_store)" == tasks-md ]] || return 1
  tasks_github_available 2>/dev/null || return 1
  tasks_is_keep_local && return 1
  local n thr
  n=$(tasks_open_count_md)
  thr=$(tasks_threshold)
  (( n >= thr ))
}
