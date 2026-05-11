#!/usr/bin/env bash
# /status — pure-bash lifecycle dashboard. Target: <500ms wall time.
#
# Drift-on-branches model: handoffs and TASKS.md updates live on whichever
# branch the work was on. /status walks `git worktree list` to surface
# in-flight state from every active branch, plus subsystem changes since
# the last release.
#
# Reads:
#   $CLAUDE_PROJECT_DIR/CLAUDE.md   (Subsystems table — alias + production paths)
#   git tag --list 'v*'             (latest release; single namespace)
#   git log --first-parent -- ...   (last change per subsystem path)
#   git worktree list               (active worktrees of this repo)
#   each worktree's .claude/handoffs/*.md  (latest handoff per worktree, frontmatter parsed)
#   each worktree's TASKS.md::Now   (active queue per branch)
#   each worktree's docs/tasks/*.md (plan-file frontmatter, optional)
#
# Writes: stdout only. No LLM, no file mutations.
#
# Args:
#   $1 (optional)  — alias filter; if given, restrict subsystems to that one.
set -uo pipefail

cd "${CLAUDE_PROJECT_DIR:-$PWD}"
filter="${1:-}"

# ---- Subsystems registry ------------------------------------------------
# Parse alias + production paths from CLAUDE.md::Subsystems table.
# Column 3 is parsed for backticked path tokens containing '/'. Rows whose
# column 3 starts with '(' are treated as having no production paths.
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

# ---- Frontmatter parsing helpers ----------------------------------------
# Extract a top-level scalar from YAML frontmatter (first --- block).
# Usage: yaml_get <file> <key>
yaml_get() {
  awk -v key="$1" '
    /^---$/{n++; next}
    n==1 && $0 ~ "^"key":" {
      sub("^"key":[ ]*", "");
      gsub(/[" ]/, "");
      print; exit
    }
    n>=2 { exit }
  ' "$2" 2>/dev/null
}

# Extract first action: from a `next:` list block in frontmatter.
yaml_first_next_action() {
  awk '
    /^---$/{n++; next}
    n==1 && /^next:/{ in_next=1; next }
    n==1 && in_next && /^[a-zA-Z_]+:/ && !/^[ \t]/{ in_next=0 }
    n==1 && in_next && /action:/{
      sub(/.*action:[ ]*"?/, "");
      sub(/"$/, "");
      print; exit
    }
    n>=2 { exit }
  ' "$1" 2>/dev/null
}

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
# Per the canonical-checkout convention (dm-evo's git-workflow.md::Layout,
# generalizable to any project using the worktree-per-branch model), the
# main project dir stays on the integration branch ('dev'); 'main' is
# allowed silently during /ship ceremonies. Non-dev work belongs in a
# worktree under .worktrees/{project}-{slug}/. Warn when the canonical
# checkout drifts onto a worker branch — usually a skill created a branch
# in place and never switched back.
main_co=$(git worktree list --porcelain 2>/dev/null | awk '
  /^worktree / { wt=$2; in_main=(wt !~ /\/\.worktrees\//); next }
  /^branch / { if (in_main) { print wt"\t"$2; exit } }')
if [ -n "$main_co" ]; then
  main_path="${main_co%%$'\t'*}"
  main_br="${main_co#*$'\t'}"
  main_br="${main_br#refs/heads/}"
  if [ "$main_br" != "dev" ] && [ "$main_br" != "main" ]; then
    echo "⚠ main checkout ($main_path) is on '$main_br', expected 'dev'."
    echo "  Per git-workflow.md::Layout, the canonical checkout stays on dev;"
    echo "  non-dev work belongs in a worktree under .worktrees/{project}-{slug}/."
    echo
  fi
fi

# ---- Orphan-stash detector ----------------------------------------------
# Stashes referencing branches that no longer exist locally are dead WIP
# from sessions where `git stash` was followed by `git branch -d/--D` (or
# remote-branch-deleted-on-merge) without first applying or dropping the
# stash. Git doesn't warn about this; the stash survives but its branch
# context is gone. Without periodic surfacing, valuable WIP can sit
# unnoticed for weeks (or get lost entirely if the stash itself is dropped
# without review).
orphan_lines=()
while IFS= read -r line; do
  [ -z "$line" ] && continue
  # Line shape: "stash@{N}: On <branch>: <msg>"   OR
  #             "stash@{N}: WIP on <branch>: <msg>"
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
  echo "  Inspect with: git stash show '<ref>' --include-untracked"
  echo "  Apply with:   git stash apply '<ref>'   (then commit + drop)"
  echo "  Discard with: git stash drop '<ref>'    (after confirming content is stale)"
  echo
fi

# ---- Merged-worktree prune detector -------------------------------------
# Walks `git worktree list` and flags worktrees whose branch has a merged
# PR (per `gh pr list --state merged --head <branch>`). Catches the
# "PR merged, branch + worktree forgotten" pattern that accumulates local
# debt across sessions. Silently skipped if gh isn't available.
if command -v gh >/dev/null 2>&1; then
  merged_lines=()
  while IFS= read -r wt_line; do
    [ -z "$wt_line" ] && continue
    wt_path=$(echo "$wt_line" | awk '{print $1}')
    # Only consider .worktrees/ entries (skip the main checkout)
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
    echo "  Or use the /clean_gone skill (commit-commands plugin) to batch-prune."
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

# ---- Worktree dashboard --------------------------------------------------
# For each worktree: branch, latest handoff (with status + next), Now items
# from that worktree's TASKS.md.
mapfile -t WORKTREES < <(
  git worktree list --porcelain 2>/dev/null | awk '
    /^worktree /{wt=$2}
    /^branch /{print wt "\t" $2}
  '
)

if [ "${#WORKTREES[@]}" -gt 0 ]; then
  echo "Active worktrees:"
  for entry in "${WORKTREES[@]}"; do
    wt="${entry%%$'\t'*}"
    branch_full="${entry#*$'\t'}"
    branch_short="${branch_full#refs/heads/}"
    wt_name=$(basename "$wt")
    printf '  %-30s [%s]\n' "$wt_name" "$branch_short"

    # Latest handoff in this worktree (by mtime)
    if [ -d "$wt/.claude/handoffs" ]; then
      latest=$(ls -t "$wt"/.claude/handoffs/*.md 2>/dev/null | head -1)
      if [ -n "$latest" ] && [ -f "$latest" ]; then
        fname=$(basename "$latest")
        st=$(yaml_get status "$latest")
        nxt=$(yaml_first_next_action "$latest")
        line="    handoff: $fname"
        [ -n "$st" ] && line="$line · $st"
        [ -n "$nxt" ] && line="$line · next: $nxt"
        echo "$line"
      fi
    fi
  done
  echo
fi

# ---- TASKS.md::Now per worktree -----------------------------------------
# Each worktree may have its own Now (drift-on-branches). Show all.
if [ "${#WORKTREES[@]}" -gt 0 ]; then
  any_now=0
  buf=""
  for entry in "${WORKTREES[@]}"; do
    wt="${entry%%$'\t'*}"
    branch_full="${entry#*$'\t'}"
    branch_short="${branch_full#refs/heads/}"
    if [ -f "$wt/TASKS.md" ]; then
      now=$(awk '
        /^## Now/{flag=1; next}
        /^## /{flag=0}
        flag && /^### /{ sub(/^### /, ""); print "    " $0 }
      ' "$wt/TASKS.md")
      if [ -n "$now" ]; then
        buf+="  on $branch_short:"$'\n'"$now"$'\n'
        any_now=1
      fi
    fi
  done
  if [ "$any_now" = "1" ]; then
    echo "Now (per branch):"
    printf '%s' "$buf"
    echo
  fi
fi

# ---- Orphan handoffs ----------------------------------------------------
# Across all worktrees: handoff has task: that doesn't match any
# docs/tasks/{slug}.md and isn't __exploratory__.
mapfile -t ALL_PLANS < <(
  for entry in "${WORKTREES[@]}"; do
    wt="${entry%%$'\t'*}"
    [ -d "$wt/docs/tasks" ] || continue
    for f in "$wt"/docs/tasks/*.md; do
      [ -f "$f" ] || continue
      basename "$f" .md
    done
  done | sort -u
)

orphans=()
cutoff=$(date -d '30 days ago' +%s 2>/dev/null || echo 0)
for entry in "${WORKTREES[@]}"; do
  wt="${entry%%$'\t'*}"
  branch_full="${entry#*$'\t'}"
  branch_short="${branch_full#refs/heads/}"
  [ -d "$wt/.claude/handoffs" ] || continue
  for f in "$wt"/.claude/handoffs/*.md; do
    [ -f "$f" ] || continue
    mtime=$(stat -c %Y "$f" 2>/dev/null || echo 0)
    [ "$mtime" -lt "$cutoff" ] && continue
    task=$(yaml_get task "$f")
    [ "$task" = "__exploratory__" ] && continue
    [ -z "$task" ] && { orphans+=("$(basename "$f") on $branch_short (no task: field)"); continue; }
    # Match against any known plan slug
    matched=0
    for plan in "${ALL_PLANS[@]}"; do
      [ "$task" = "$plan" ] && { matched=1; break; }
    done
    if [ "$matched" = "0" ]; then
      st=$(yaml_get status "$f")
      case "$st" in
        concluded|abandoned) ;;
        *) orphans+=("$(basename "$f") on $branch_short (task: $task — no plan, status: ${st:-unset})") ;;
      esac
    fi
  done
done

if [ "${#orphans[@]}" -gt 0 ]; then
  # de-dupe (handoffs visible in multiple worktrees if same branch is checked out — shouldn't happen, but defend)
  echo "Orphan handoffs:"
  printf '  %s\n' "${orphans[@]}" | sort -u
  echo
fi

# ---- TASKS.md row-size lint (Now only) ----------------------------------
# Flag ### entries within ## Now that exceed 5 lines (header + 4 body).
# Per work-organization.md::Row-size discipline: pointer-shape Now rows are
# header + → plan: + → handoff: + Latest: = 4 lines. >5 total in Now =
# signal to promote to docs/tasks/{slug}.md. Next/Later are buffer queues
# where bullet-cluster entries are legitimate; those are not linted.
oversized=()
for entry in "${WORKTREES[@]}"; do
  wt="${entry%%$'\t'*}"
  branch_full="${entry#*$'\t'}"
  branch_short="${branch_full#refs/heads/}"
  [ -f "$wt/TASKS.md" ] || continue
  while read -r line; do
    [ -n "$line" ] && oversized+=("$line on $branch_short")
  done < <(awk '
    function flush() {
      if (current && lines >= 5) {
        title = current; sub(/^### /, "", title)
        print title " (" lines " lines)"
      }
    }
    /^## Now/ { in_section=1; current=""; lines=0; next }
    /^## / { flush(); current=""; in_section=0; next }
    in_section && /^### / { flush(); current=$0; lines=1; next }
    in_section && current && /^[ \t]*$/ { next }   # skip blanks
    in_section && current { lines++ }
    END { flush() }
  ' "$wt/TASKS.md")
done

if [ "${#oversized[@]}" -gt 0 ]; then
  echo "TASKS.md::Now row-size violations (≥5 lines — promote to docs/tasks/{slug}.md):"
  printf '  %s\n' "${oversized[@]}" | sort -u
  echo
fi
