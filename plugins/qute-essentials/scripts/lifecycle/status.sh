#!/usr/bin/env bash
# /status — pure-bash lifecycle dashboard. Target: <500ms wall time.
#
# Reads:
#   $CLAUDE_PROJECT_DIR/CLAUDE.md   (Subsystems table — alias list)
#   git tags                        (per-subsystem prod/dev versions)
#   git worktree list               (active worktrees)
#   TASKS.md                        (Now items)
#   .claude/handoffs/*.md           (orphan handoff check)
#
# Writes: stdout only. No LLM, no file mutations.
#
# Args:
#   $1 (optional)  — alias filter; if given, restrict to that subsystem only
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}"
filter="${1:-}"

# ---- Subsystems registry ------------------------------------------------
# Parse the alias column from CLAUDE.md::Subsystems table.
# Convention: header row contains "| Alias |"; data rows start with `| `<alias>` `.
mapfile -t ALIASES < <(
  awk '
    /^\| Alias \| / { in_tbl=1; next }
    in_tbl && /^\| `[a-z]/ {
      gsub(/`/,"");
      n = split($0, f, "|");
      gsub(/^[ \t]+|[ \t]+$/, "", f[2]);
      if (length(f[2])) print f[2]
    }
    in_tbl && /^[^|]/ { in_tbl=0 }
  ' CLAUDE.md 2>/dev/null
)

# Apply filter if given.
if [ -n "$filter" ]; then
  for a in "${ALIASES[@]}"; do
    if [ "$a" = "$filter" ]; then ALIASES=("$filter"); break; fi
  done
fi

# ---- Header -------------------------------------------------------------
project=$(basename "$PWD")
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
last=$(git log -1 --format='%h %s' 2>/dev/null | cut -c -70)
dirty=""
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then dirty=" (dirty)"; fi
echo "$project @ $branch$dirty  ·  $last"
echo

# ---- Subsystems ---------------------------------------------------------
if [ "${#ALIASES[@]}" -gt 0 ]; then
  printf '%-12s %-22s %-22s %s\n' "Subsystem" "Prod (main)" "Dev" "Active"
  for alias in "${ALIASES[@]}"; do
    prod=$(git tag --merged main --list "${alias}-v*" 2>/dev/null | sort -V | tail -1)
    devt=$(git tag --list "${alias}-v*" 2>/dev/null | sort -V | tail -1)
    active=$(git for-each-ref --format='%(refname:short)' \
                   "refs/heads/feat/${alias}-*" \
                   "refs/heads/research/${alias}-*" 2>/dev/null | head -1)
    [ "$devt" = "$prod" ] && devt="="
    printf '  %-10s %-22s %-22s %s\n' "$alias" "${prod:-—}" "${devt:-—}" "${active:-—}"
  done
  echo
fi

# ---- Worktrees ----------------------------------------------------------
wt_count=$(git worktree list 2>/dev/null | wc -l)
echo "Worktrees ($wt_count):"
git worktree list 2>/dev/null | awk '
  {
    path=$1; commit=$2; rest=$0;
    sub(/^[^ ]+ +[^ ]+ +/, "", rest);
    n=split(path, p, "/"); name=p[n];
    printf "  %-30s %s\n", name, rest
  }'
echo

# ---- TASKS.md::Now ------------------------------------------------------
if [ -f TASKS.md ]; then
  now=$(awk '
    /^## Now/{flag=1; next}
    /^## /{flag=0}
    flag && /^### /{ sub(/^### /, ""); print "  " $0 }
  ' TASKS.md)
  if [ -n "$now" ]; then
    echo "Now (TASKS.md):"
    echo "$now"
    echo
  fi
fi

# ---- Orphan handoffs ----------------------------------------------------
if [ -d .claude/handoffs ]; then
  cutoff=$(date -d '30 days ago' +%s 2>/dev/null || echo 0)
  orphans=()
  for f in .claude/handoffs/*.md; do
    [ -f "$f" ] || continue
    mtime=$(stat -c %Y "$f" 2>/dev/null || echo 0)
    [ "$mtime" -lt "$cutoff" ] && continue
    # Extract task: from first frontmatter block.
    task=$(awk '
      /^---$/{n++; next}
      n==1 && /^task:/{ sub(/^task:[ ]*/, ""); gsub(/[" ]/, ""); print; exit }
      n>=2 { exit }
    ' "$f")
    [ "$task" = "__exploratory__" ] && continue
    if [ -z "$task" ]; then
      orphans+=("$(basename "$f") (no task: field)")
    elif ! grep -qE "(### .*$task|task:[ ]*$task)" TASKS.md 2>/dev/null; then
      # Check status: concluded/abandoned — those are expected to lack a TASKS.md row.
      status=$(awk '
        /^---$/{n++; next}
        n==1 && /^status:/{ sub(/^status:[ ]*/, ""); gsub(/[" ]/, ""); print; exit }
        n>=2 { exit }
      ' "$f")
      case "$status" in
        concluded|abandoned) ;;
        *) orphans+=("$(basename "$f") (task: $task — not in TASKS.md, status: ${status:-unset})") ;;
      esac
    fi
  done
  if [ "${#orphans[@]}" -gt 0 ]; then
    echo "Orphan handoffs (no TASKS.md link):"
    printf '  %s\n' "${orphans[@]}"
    echo
  fi
fi
