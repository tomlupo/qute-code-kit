#!/usr/bin/env bash
# qute_coder_flow.sh — the full /qute-coder CHAIN in one command:
#
#   1. OPEN   the PR authored by qute-coder[bot]         (qute_coder_pr.sh; existing behavior)
#   2. REVIEW it independently as qute-review[bot]        (qute_reviewer_post.sh) — unless disabled
#   3. ASSIGN the PR to the human + request their review  (gh pr edit / gh api)
#   4. REPORT the PR URL + the review verdict + that it's assigned
#
# Policy comes from the repo's committed `.github/qute-pr.yml` (single source of
# truth, read by BOTH this client flow and the CI review-gate). Resolved via
# scripts/pr_flow_config.py --json. Keys (defaults): assignTo=tomlupo,
# independentReview=true, allowAgentSelfMerge=false, enforce=false.
#
# All positional/flag args are the SAME as `gh pr create` and pass straight
# through to step 1. Usage:
#   qute_coder_flow.sh --repo o/r --base main --title "…" --body "…"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODER="$HERE/qute_coder_pr.sh"
REVIEWER="$HERE/qute_reviewer_post.sh"
CFG_PY="$HERE/pr_flow_config.py"

log() { echo "qute-coder-flow: $*" >&2; }
die() { echo "qute-coder-flow: $*" >&2; exit 1; }

# ── resolve policy from .github/qute-pr.yml (defaults if absent) ──────────
CFG_JSON="$(python3 "$CFG_PY" --json "$PWD" 2>/dev/null || echo '{}')"
jqget() { printf '%s' "$CFG_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }
ASSIGN_TO="$(jqget assignTo)";            [ -n "$ASSIGN_TO" ] || ASSIGN_TO="tomlupo"
INDEP_REVIEW="$(jqget independentReview)"; [ -n "$INDEP_REVIEW" ] || INDEP_REVIEW="True"
log "policy: assignTo=$ASSIGN_TO independentReview=$INDEP_REVIEW (from .github/qute-pr.yml or defaults)"

# ── step 1: open the PR as qute-coder[bot] ───────────────────────────────
log "step 1/3 — opening PR as qute-coder[bot] …"
CODER_OUT="$(bash "$CODER" "$@")" || die "PR creation failed (qute_coder_pr.sh). Aborting chain."
echo "$CODER_OUT"
# gh pr create prints the PR URL on its own line.
PR_URL="$(printf '%s\n' "$CODER_OUT" | grep -oE 'https://github\.com/[^ ]+/pull/[0-9]+' | tail -n1)"
[ -n "$PR_URL" ] || die "could not parse the created PR URL from qute_coder_pr.sh output. Chain stops."
REPO="$(printf '%s' "$PR_URL" | sed -E 's#https://github\.com/([^/]+/[^/]+)/pull/[0-9]+#\1#')"
PR_NUM="$(printf '%s' "$PR_URL" | grep -oE '[0-9]+$')"
log "opened $REPO#$PR_NUM — $PR_URL"

# ── step 2: independent review as qute-review[bot] (unless disabled) ──────
VERDICT="skipped (independentReview=false)"
case "$INDEP_REVIEW" in
  True|true|1|yes)
    log "step 2/3 — posting independent review (qute-review[bot]) …"
    if REV_OUT="$(bash "$REVIEWER" "$REPO" "$PR_NUM" 2>&1)"; then
      echo "$REV_OUT" >&2
      VERDICT="posted (qute-review[bot] review object confirmed)"
    else
      echo "$REV_OUT" >&2
      VERDICT="ATTEMPTED but FAILED — see log above; gate stays red, review manually with /qute-reviewer"
      log "WARNING: independent review step failed; continuing to assignment so the PR still lands in the human's queue."
    fi
    ;;
  *) log "step 2/3 — independent review DISABLED by policy (independentReview=false); skipping." ;;
esac

# ── step 3: assign the PR to the human + request their review ────────────
log "step 3/3 — assigning $REPO#$PR_NUM to @$ASSIGN_TO and requesting their review …"
ASSIGNED="no"
if gh pr edit "$PR_NUM" --repo "$REPO" --add-assignee "$ASSIGN_TO" >/dev/null 2>&1; then
  ASSIGNED="yes"
else
  # fallback: issues assignee API
  if gh api "repos/$REPO/issues/$PR_NUM/assignees" -X POST -f "assignees[]=$ASSIGN_TO" >/dev/null 2>&1; then
    ASSIGNED="yes"
  fi
fi
[ "$ASSIGNED" = "yes" ] && log "assigned to @$ASSIGN_TO." || log "WARNING: could not assign @$ASSIGN_TO (check the login is a collaborator)."

# request review (best-effort; the human is not the PR author so this is valid)
REVIEW_REQ="no"
if gh pr edit "$PR_NUM" --repo "$REPO" --add-reviewer "$ASSIGN_TO" >/dev/null 2>&1; then
  REVIEW_REQ="yes"
elif gh api "repos/$REPO/pulls/$PR_NUM/requested_reviewers" -X POST -f "reviewers[]=$ASSIGN_TO" >/dev/null 2>&1; then
  REVIEW_REQ="yes"
fi
[ "$REVIEW_REQ" = "yes" ] && log "review requested from @$ASSIGN_TO." || log "note: review request not applied (often because @$ASSIGN_TO can't be requested on this repo)."

# ── step 4: report ───────────────────────────────────────────────────────
cat <<EOF

qute-coder chain complete:
  PR:              $PR_URL
  independent review: $VERDICT
  assigned to:     @$ASSIGN_TO ($( [ "$ASSIGNED" = yes ] && echo assigned || echo 'ASSIGN FAILED — do it manually' ))
  review requested: $( [ "$REVIEW_REQ" = yes ] && echo "yes, from @$ASSIGN_TO" || echo "not applied" )
  merge:           left to the human ($ASSIGN_TO) — this chain never merges.
EOF
