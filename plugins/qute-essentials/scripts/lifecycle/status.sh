#!/usr/bin/env bash
# /status — pure-bash git/worktree dashboard. Target: <500ms wall time.
#
# Reads:
#   $CLAUDE_PROJECT_DIR/CLAUDE.md   (Subsystems table — alias + production paths, optional)
#   git tag --list 'v*'             (latest release; single namespace)
#   git log --first-parent -- ...   (last change per subsystem path)
#   git worktree list               (active worktrees of this repo)
#
# Writes: stdout only. No LLM, no file mutations.
#
# Args:
#   $1 (optional)  — alias filter; if given, restrict subsystems to that one.
#
# Scope: git state + a read-only open-tasks glance (Open tasks section below,
# via the shared tasks/pulse.sh engine — TASKS.md or GitHub Issues, auto-
# detected; folded in from the retired /board skill, issue #51). Session state
# lives in ~/.claude/handoffs/ (use /pickup to load latest).
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}"
filter="${1:-}"

# ---- Subsystems registry (optional) -------------------------------------
# Parse alias + production paths from CLAUDE.md::Subsystems table if present.
# Repos without a Subsystems table just skip this section.
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

# Latest release + commits ahead on dev
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

# ---- Main-checkout discipline lint --------------------------------------
# Per the worktree-per-branch convention: the main project dir stays on the
# integration branch ('dev'); 'main' is allowed during release ceremonies.
# Non-dev work belongs in a worktree. Warn when the canonical checkout drifts
# onto a worker branch — usually a skill created a branch in place and never
# switched back.
main_co=$(git worktree list --porcelain 2>/dev/null | awk '
  /^worktree / { wt=$2; in_main=(wt !~ /\/\.worktrees\//); next }
  /^branch / { if (in_main) { print wt"\t"$2; exit } }')
if [ -n "$main_co" ]; then
  main_path="${main_co%%$'\t'*}"
  main_br="${main_co#*$'\t'}"
  main_br="${main_br#refs/heads/}"
  if [ "$main_br" != "dev" ] && [ "$main_br" != "main" ]; then
    echo "⚠ main checkout ($main_path) is on '$main_br', expected 'dev'."
    echo "  Non-dev work belongs in a worktree under .worktrees/{project}-{slug}/."
    echo
  fi
fi

# ---- Orphan-stash detector ----------------------------------------------
# Stashes referencing branches that no longer exist locally are dead WIP from
# sessions where `git stash` was followed by branch deletion (or remote-merge
# branch cleanup) without first applying or dropping the stash. Surface them
# so they don't sit unnoticed for weeks.
orphan_lines=()
while IFS= read -r line; do
  [ -z "$line" ] && continue
  ref=$(echo "$line" | sed -n 's/^\(stash@{[0-9][0-9]*}\):.*/\1/p')
  br=$(echo "$line" | sed -nE 's/^stash@\{[0-9]+\}: (On |WIP on )([^:]+):.*/\2/p')
  if [ -n "$ref" ] && [ -n "$br" ]; then
    if ! git rev-parse --verify --quiet "refs/heads/$br" >/dev/null 2>&1; then
      orphan_lines+=("  $ref → branch '$br' is deleted")
    fi
  fi
done < <(git stash list 2>/dev/null)
if [ "${#orphan_lines[@]}" -gt 0 ]; then
  echo "⚠ Orphan stashes (their source branch no longer exists):"
  printf '%s\n' "${orphan_lines[@]}"
  echo "  Inspect: git stash show '<ref>' --include-untracked"
  echo "  Apply:   git stash apply '<ref>'   (then commit + drop)"
  echo "  Discard: git stash drop '<ref>'    (after confirming content is stale)"
  echo
fi

# ---- Merged-worktree prune detector -------------------------------------
# Walks `git worktree list` and flags worktrees whose branch has a merged PR.
# Catches the "PR merged, branch + worktree forgotten" pattern. Skipped if gh
# isn't available.
if command -v gh >/dev/null 2>&1; then
  merged_lines=()
  while IFS= read -r wt_line; do
    [ -z "$wt_line" ] && continue
    wt_path=$(echo "$wt_line" | awk '{print $1}')
    case "$wt_path" in
      */.worktrees/*) ;;
      *) continue ;;
    esac
    wt_br=$(echo "$wt_line" | sed -nE 's/.*\[([^]]+)\].*/\1/p')
    [ -z "$wt_br" ] && continue
    pr_num=$(gh pr list --state merged --head "$wt_br" --json number --jq '.[0].number // empty' 2>/dev/null)
    if [ -n "$pr_num" ]; then
      merged_lines+=("  ${wt_path##*/}  [$wt_br]  PR #$pr_num merged")
    fi
  done < <(git worktree list 2>/dev/null)
  if [ "${#merged_lines[@]}" -gt 0 ]; then
    echo "⚠ Worktrees with merged PRs (safe to prune):"
    printf '%s\n' "${merged_lines[@]}"
    echo "  Cleanup: git worktree remove <path> && git branch -D <branch>"
    echo
  fi
fi

# ---- Subsystems ---------------------------------------------------------
if [ "${#SUBSYSTEMS[@]}" -gt 0 ]; then
  printf '%-12s %-50s %s\n' "Subsystem" "Last change" "Active branch"
  for entry in "${SUBSYSTEMS[@]}"; do
    alias="${entry%%$'\t'*}"
    paths="${entry#*$'\t'}"
    if [ -z "$paths" ]; then
      last_change="(research-only)"
    else
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

# ---- Active worktrees ---------------------------------------------------
mapfile -t WORKTREES < <(
  git worktree list --porcelain 2>/dev/null | awk '
    /^worktree /{wt=$2}
    /^branch /{print wt "\t" $2}
  '
)

if [ "${#WORKTREES[@]}" -gt 1 ]; then
  echo "Active worktrees:"
  for entry in "${WORKTREES[@]}"; do
    wt="${entry%%$'\t'*}"
    branch_full="${entry#*$'\t'}"
    branch_short="${branch_full#refs/heads/}"
    wt_name=$(basename "$wt")
    printf '  %-30s [%s]\n' "$wt_name" "$branch_short"
  done
  echo
fi

# ---- Open tasks ---------------------------------------------------------
# Folded in from the former /board skill (issue #51): a read-only glance at the
# repo's open task list from its single ACTIVE store — TASKS.md (Tier 1) or
# GitHub Issues (Tier 2), auto-detected. Reuses the shared task engine
# (pulse.sh) rather than reimplementing store detection. Non-fatal on error.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PULSE="$SCRIPT_DIR/../tasks/pulse.sh"
if [ -x "$PULSE" ] || [ -f "$PULSE" ]; then
  tasks_out=$(bash "$PULSE" report 2>/dev/null)
  if [ -n "$tasks_out" ]; then
    echo "Open tasks:"
    printf '%s\n' "$tasks_out" | sed 's/^/  /'
    echo
  fi
fi
