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

# Create an issue.  Args: <title> [body...]   Prints the new issue URL.
tasks_github_create() {
  local title="$1"; shift || true
  local body="${*:-}"
  gh issue create --title "$title" --body "$body"
}

# Close an issue.  Args: <number> [comment...]
tasks_github_close() {
  local num="$1"; shift || true
  local comment="${*:-}"
  if [[ -n "$comment" ]]; then
    gh issue close "$num" --comment "$comment"
  else
    gh issue close "$num"
  fi
}
