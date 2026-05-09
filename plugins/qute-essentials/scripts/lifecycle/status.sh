#!/usr/bin/env bash
# /status — pure-bash lifecycle dashboard. Target: <500ms wall time.
#
# Reads:
#   $CLAUDE_PROJECT_DIR/CLAUDE.md   (Subsystems table — alias + production paths)
#   git tag --list 'v*'             (latest release, single namespace)
#   git log --first-parent -- ...   (last change per subsystem path)
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
# Parse alias + production paths from CLAUDE.md::Subsystems table.
# Each entry: <alias>\t<comma-separated paths or empty>
# Column 3 is parsed for backticked path tokens containing '/'. Rows whose
# column 3 starts with '(' (e.g. "(research-only — ...)") are treated as
# having no production paths.
mapfile -t SUBSYSTEMS < <(
  awk '
    BEGIN { OFS="\t" }
    /^\| Alias / { in_tbl=1; next }
    in_tbl && /^\| `[a-z]/ {
      n = split($0, f, "|");
      alias = f[2]; gsub(/`/,"",alias); gsub(/^[ \t]+|[ \t]+$/,"",alias);
      col3 = f[4];
      trim = col3; gsub(/^[ \t]+|[ \t]+$/, "", trim);
      paths = "";
      if (trim !~ /^\(/) {
        while (match(col3, /`[^`]+\/[^`]*`/)) {
          token = substr(col3, RSTART+1, RLENGTH-2);
          paths = (paths == "" ? token : paths "," token);
          col3 = substr(col3, RSTART+RLENGTH);
        }
      }
      print alias, paths
    }
    in_tbl && /^[^|]/ { in_tbl=0 }
  ' CLAUDE.md 2>/dev/null
)

# Apply filter if given.
if [ -n "$filter" ]; then
  filtered=()
  for entry in "${SUBSYSTEMS[@]}"; do
    a="${entry%%$'\t'*}"
    [ "$a" = "$filter" ] && filtered+=("$entry")
  done
  SUBSYSTEMS=("${filtered[@]}")
fi

# ---- Header -------------------------------------------------------------
project=$(basename "$PWD")
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
last=$(git log -1 --format='%h %s' 2>/dev/null | cut -c -70)
dirty=""
[ -n "$(git status --porcelain 2>/dev/null)" ] && dirty=" (dirty)"

echo "$project @ $branch$dirty  ·  $last"

# Latest release + commits ahead on dev (single namespace, vX.Y.Z)
release=$(git tag --list 'v*' 2>/dev/null | sort -V | tail -1)
if [ -n "$release" ]; then
  release_date=$(git log -1 --format='%cs' "$release" 2>/dev/null)
  if git rev-parse --verify --quiet dev >/dev/null 2>&1; then
    ahead=$(git log --first-parent --oneline "${release}..dev" 2>/dev/null | wc -l | tr -d ' ')
    echo "Latest release: $release ($release_date)  ·  $ahead commits ahead on dev"
  else
    echo "Latest release: $release ($release_date)"
  fi
fi
echo

# ---- Subsystems ---------------------------------------------------------
if [ "${#SUBSYSTEMS[@]}" -gt 0 ]; then
  printf '%-12s %-50s %s\n' "Subsystem" "Last change" "Active branch"
  for entry in "${SUBSYSTEMS[@]}"; do
    alias="${entry%%$'\t'*}"
    paths="${entry#*$'\t'}"
    if [ -z "$paths" ]; then
      last_change="(research-only)"
    else
      # shellcheck disable=SC2206
      IFS=',' read -ra path_arr <<< "$paths"
      last_change=$(git log --first-parent -1 --format='%cs %h %s' -- "${path_arr[@]}" 2>/dev/null | cut -c -50)
      [ -z "$last_change" ] && last_change="(no commits on these paths)"
    fi
    active=$(git for-each-ref --format='%(refname:short)' \
                   "refs/heads/feat/${alias}-*" \
                   "refs/heads/research/${alias}-*" 2>/dev/null | head -1)
    printf '  %-10s %-50s %s\n' "$alias" "$last_change" "${active:-—}"
  done
  echo
fi

# ---- Worktrees ----------------------------------------------------------
wt_count=$(git worktree list 2>/dev/null | wc -l)
echo "Worktrees ($wt_count):"
git worktree list 2>/dev/null | awk '
  {
    path=$1; rest=$0;
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
    fname=$(basename "$f")
    # Disqualify orphan if: no task field; or task slug appears in TASKS.md;
    # or filename is cited from any TASKS.md → handoff: line.
    cited=0
    grep -qE "(### .*$task|task:[ ]*$task)" TASKS.md 2>/dev/null && cited=1
    grep -qF "$fname" TASKS.md 2>/dev/null && cited=1
    if [ -z "$task" ]; then
      orphans+=("$fname (no task: field)")
    elif [ "$cited" = "0" ]; then
      # Status: concluded/abandoned are expected to lack a TASKS.md row.
      status=$(awk '
        /^---$/{n++; next}
        n==1 && /^status:/{ sub(/^status:[ ]*/, ""); gsub(/[" ]/, ""); print; exit }
        n>=2 { exit }
      ' "$f")
      case "$status" in
        concluded|abandoned) ;;
        *) orphans+=("$fname (task: $task — no link in TASKS.md, status: ${status:-unset})") ;;
      esac
    fi
  done
  if [ "${#orphans[@]}" -gt 0 ]; then
    echo "Orphan handoffs (no TASKS.md link):"
    printf '  %s\n' "${orphans[@]}"
    echo
  fi
fi
