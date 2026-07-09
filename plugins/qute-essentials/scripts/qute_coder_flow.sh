#!/usr/bin/env bash
# qute_coder_flow.sh — the full /qute-coder CHAIN in one command:
#
#   1. OPEN   the PR authored by qute-coder[bot]         (qute_coder_pr.sh; existing behavior)
#   2. REVIEW it independently as qute-review[bot]        (qute_reviewer_post.sh) — unless disabled
#   3. ASSIGN the PR to the human + request their review  (gh pr edit / gh api)
#   4. REPORT the PR URL + the review verdict + that it's assigned
#
# ── VERB CONTRACT (for Jimek / any conductor) ────────────────────────────
# This verb is composable. Baked-in policy is now PARAMETERIZED via flags that
# DEFAULT to today's human-invocation behavior:
#
#   --base <b>          PR base branch (native gh flag; also settable as policy
#                       baseBranch in .github/qute-pr.yml). Default: gh picks the
#                       repo default branch — unchanged from today.
#   --no-review         skip the independent-review step (default: policy
#                       independentReview, normally ON).
#   --no-assign         skip assigning + requesting review from the human
#                       (default: assign ON).
#   --assign-to <login> override policy assignTo for this run.
#   --review-mode M     force the reviewer mode (dispatcher|local|auto).
#   --json              emit ONE machine-readable JSON object as the final stdout
#                       line (human logs stay on stderr) so a conductor can branch.
#
# Everything ELSE passes straight through to `gh pr create` (--title, --body,
# --head, --repo, --draft, …) exactly as before.
#
# IDEMPOTENT: re-invoking for the same head branch does NOT open a second PR — an
# existing OPEN PR for the branch is reused (created=false), then review/assign
# (both idempotent) run against it.
#
# EXIT CODES: 0 ok (PR open/reused, review ok or skipped); 2 PR could not be
# opened; 3 PR is open but the independent review FAILED (gate stays red).
#
# Policy comes from the repo's committed `.github/qute-pr.yml` (single source of
# truth, read by BOTH this client flow and the CI review-gate). Resolved via
# scripts/pr_flow_config.py --json. Keys (defaults): assignTo=tomlupo,
# independentReview=true, allowAgentSelfMerge=false, enforce=false, baseBranch="".
#
# Usage:
#   qute_coder_flow.sh [--base b] [--no-review] [--no-assign] [--assign-to u] \
#                      [--review-mode M] [--json] -- <gh pr create args…>
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODER="$HERE/qute_coder_pr.sh"
REVIEWER="$HERE/qute_reviewer_post.sh"
CFG_PY="$HERE/pr_flow_config.py"

log() { echo "qute-coder-flow: $*" >&2; }

# ── flag parsing: split chain-control flags from gh-pr-create passthrough ──
PASS=()
OPT_JSON=0
OVR_NO_REVIEW=0
OVR_NO_ASSIGN=0
OVR_ASSIGN_TO=""
OVR_REVIEW_MODE=""
BASE_ARG=""
HEAD_ARG=""
REPO_ARG=""
# requires a value operand for a two-token flag; guards against `shift 2` on a
# dangling flag (which under `set -u` w/o `set -e` would spin forever).
need2() { [ "$1" -ge 2 ] || { echo "qute-coder-flow: flag '$2' requires a value" >&2; exit 2; }; }
# Parse chain-control flags out of the `gh pr create` arg stream. To avoid
# MIS-CLAIMING a passthrough VALUE that happens to look like a chain flag (e.g.
# `--body "--no-review"`), every VALUE-TAKING `gh pr create` flag consumes its
# next token OPAQUELY (flag + value straight into PASS, never re-interpreted).
# Only a bare chain flag that is NOT the operand of a preceding value-flag is
# treated as a chain flag. Use `--` to force everything after it to passthrough.
while [ $# -gt 0 ]; do
  case "$1" in
    # ── value-taking gh pr create flags: consume the value opaquely ──────
    --base|-B)   need2 "$#" "$1"; BASE_ARG="$2"; PASS+=("$1" "$2"); shift 2 ;;
    --head|-H)   need2 "$#" "$1"; HEAD_ARG="$2"; PASS+=("$1" "$2"); shift 2 ;;
    --repo|-R)   need2 "$#" "$1"; REPO_ARG="$2"; PASS+=("$1" "$2"); shift 2 ;;
    --base=*)    BASE_ARG="${1#*=}"; PASS+=("$1"); shift ;;
    --head=*)    HEAD_ARG="${1#*=}"; PASS+=("$1"); shift ;;
    --repo=*)    REPO_ARG="${1#*=}"; PASS+=("$1"); shift ;;
    --title|-t|--body|-b|--body-file|-F|--assignee|-a|--reviewer|-r|--label|-l|--milestone|-m|--project|-p|--template|-T|--recover|--head-repo)
                 need2 "$#" "$1"; PASS+=("$1" "$2"); shift 2 ;;
    # ── chain-control flags (default to today's behavior) ────────────────
    --no-review)     OVR_NO_REVIEW=1; shift ;;
    --no-assign)     OVR_NO_ASSIGN=1; shift ;;
    --assign-to)     need2 "$#" "$1"; OVR_ASSIGN_TO="$2"; shift 2 ;;
    --assign-to=*)   OVR_ASSIGN_TO="${1#*=}"; shift ;;
    --review-mode)   need2 "$#" "$1"; OVR_REVIEW_MODE="$2"; shift 2 ;;
    --review-mode=*) OVR_REVIEW_MODE="${1#*=}"; shift ;;
    --json)          OPT_JSON=1; shift ;;
    --)              shift; while [ $# -gt 0 ]; do PASS+=("$1"); shift; done ;;
    *)               PASS+=("$1"); shift ;;
  esac
done

# ── emit structured JSON (or nothing) then exit with $EMIT_CODE ───────────
# Reads the ctx vars set along the way; missing ones default sanely.
emit() {
  local code="${EMIT_CODE:-0}"
  if [ "$OPT_JSON" = "1" ]; then
    OK="${OK:-false}" PR_URL="${PR_URL:-}" PR_NUM="${PR_NUM:-}" REPO="${REPO:-}" \
    BASE="${BASE_ARG:-}" HEAD="${HEAD:-}" CREATED="${CREATED:-false}" \
    RVRAN="${REVIEW_RAN:-false}" RVOK="${REVIEW_OK:-false}" VERDICT="${VERDICT:-}" \
    ASRAN="${ASSIGN_RAN:-false}" ASSIGNED_B="${ASSIGNED_BOOL:-false}" \
    RVREQ="${REVIEW_REQ_BOOL:-false}" ASSIGN_TO="${ASSIGN_TO:-}" \
    python3 - <<'PY'
import json, os
def b(x): return str(x).lower() in ("1", "true", "yes")
def i(x):
    try: return int(x)
    except Exception: return None
print(json.dumps({
    "verb": "qute-coder",
    "ok": b(os.environ["OK"]),
    "pr_url": os.environ["PR_URL"] or None,
    "pr_number": i(os.environ["PR_NUM"]),
    "repo": os.environ["REPO"] or None,
    "base": os.environ["BASE"] or None,
    "head": os.environ["HEAD"] or None,
    "created": b(os.environ["CREATED"]),
    "review": {"ran": b(os.environ["RVRAN"]), "ok": b(os.environ["RVOK"]),
               "verdict": os.environ["VERDICT"] or None},
    "assign": {"ran": b(os.environ["ASRAN"]), "ok": b(os.environ["ASSIGNED_B"]),
               "to": os.environ["ASSIGN_TO"] or None},
    "review_requested": b(os.environ["RVREQ"]),
}))
PY
  fi
  exit "$code"
}
die() { log "$*"; EMIT_CODE="${FAIL_CODE:-2}" emit; }

# ── resolve policy from .github/qute-pr.yml (defaults if absent) ──────────
CFG_JSON="$(python3 "$CFG_PY" --json "$PWD" 2>/dev/null || echo '{}')"
jqget() { printf '%s' "$CFG_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }
ASSIGN_TO="$(jqget assignTo)";            [ -n "$ASSIGN_TO" ] || ASSIGN_TO="tomlupo"
INDEP_REVIEW="$(jqget independentReview)"; [ -n "$INDEP_REVIEW" ] || INDEP_REVIEW="True"
POLICY_BASE="$(jqget baseBranch)"

# flag overrides win over policy (flags default to today's behavior).
[ -n "$OVR_ASSIGN_TO" ] && ASSIGN_TO="$OVR_ASSIGN_TO"
[ "$OVR_NO_REVIEW" = "1" ] && INDEP_REVIEW="False"
[ "$OVR_NO_ASSIGN" = "1" ] && ASSIGN_TO=""   # empty => skip the assign step

# base branch: caller --base wins; else policy baseBranch; else gh's default.
if [ -z "$BASE_ARG" ] && [ -n "$POLICY_BASE" ]; then
  BASE_ARG="$POLICY_BASE"
  PASS+=(--base "$POLICY_BASE")
  log "policy baseBranch=$POLICY_BASE applied (no --base given)."
fi
log "policy: assignTo=${ASSIGN_TO:-<skip>} independentReview=$INDEP_REVIEW base=${BASE_ARG:-<gh default>}"

# ── resolve repo + head for the idempotency probe (best-effort) ──────────
REPO="$REPO_ARG"
[ -n "$REPO" ] || REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
HEAD="$HEAD_ARG"
[ -n "$HEAD" ] || HEAD="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"

# ── step 1: OPEN (or reuse an existing OPEN PR for this branch) ───────────
CREATED=false
PR_URL=""
if [ -n "$REPO" ] && [ -n "$HEAD" ]; then
  EXIST="$(gh pr list --repo "$REPO" --head "$HEAD" --state open --json url --jq '.[0].url' 2>/dev/null || true)"
  if [ -n "$EXIST" ]; then
    PR_URL="$EXIST"
    log "idempotent: an OPEN PR for '$HEAD' already exists — reusing $PR_URL (no second PR opened)."
  fi
fi

if [ -z "$PR_URL" ]; then
  log "step 1/3 — opening PR as qute-coder[bot] …"
  if ! CODER_OUT="$(bash "$CODER" "${PASS[@]}")"; then
    printf '%s\n' "$CODER_OUT" >&2
    FAIL_CODE=2 die "PR creation failed (qute_coder_pr.sh). Aborting chain."
  fi
  # keep stdout a single JSON line under --json; otherwise echo the URL as before.
  if [ "$OPT_JSON" = "1" ]; then printf '%s\n' "$CODER_OUT" >&2; else echo "$CODER_OUT"; fi
  PR_URL="$(printf '%s\n' "$CODER_OUT" | grep -oE 'https://github\.com/[^ ]+/pull/[0-9]+' | tail -n1)"
  [ -n "$PR_URL" ] || FAIL_CODE=2 die "could not parse the created PR URL. Chain stops."
  CREATED=true
fi

REPO="$(printf '%s' "$PR_URL" | sed -E 's#https://github\.com/([^/]+/[^/]+)/pull/[0-9]+#\1#')"
PR_NUM="$(printf '%s' "$PR_URL" | grep -oE '[0-9]+$')"
log "PR $REPO#$PR_NUM — $PR_URL (created=$CREATED)"

# ── step 2: independent review as qute-review[bot] (unless disabled) ──────
REVIEW_RAN=false
REVIEW_OK=false
VERDICT="skipped (independentReview=false)"
case "$INDEP_REVIEW" in
  True|true|1|yes)
    REVIEW_RAN=true
    log "step 2/3 — posting independent review (qute-review[bot]) …"
    REV_ENV=()
    [ -n "$OVR_REVIEW_MODE" ] && REV_ENV=(env "QUTE_REVIEW_MODE=$OVR_REVIEW_MODE")
    REV_ERR="$(mktemp)"
    # ask the reviewer for its OWN JSON (verb composition) so we lift the verdict.
    if REV_JSON="$("${REV_ENV[@]}" bash "$REVIEWER" --json "$REPO" "$PR_NUM" 2>"$REV_ERR")"; then
      cat "$REV_ERR" >&2
      REVIEW_OK=true
      VERDICT="$(printf '%s' "$REV_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("verdict") or "posted")' 2>/dev/null || echo posted)"
    else
      cat "$REV_ERR" >&2
      VERDICT="ATTEMPTED but FAILED — gate stays red; review manually with /qute-reviewer"
      log "WARNING: independent review failed; continuing to assignment so the PR still lands in the human's queue."
    fi
    rm -f "$REV_ERR"
    ;;
  *) log "step 2/3 — independent review DISABLED (independentReview=false / --no-review); skipping." ;;
esac

# ── step 3: assign the PR to the human + request their review ─────────────
ASSIGN_RAN=false
ASSIGNED="skipped"
REVIEW_REQ="no"
if [ -n "$ASSIGN_TO" ]; then
  ASSIGN_RAN=true
  log "step 3/3 — assigning $REPO#$PR_NUM to @$ASSIGN_TO and requesting their review …"
  ASSIGNED="no"
  if gh pr edit "$PR_NUM" --repo "$REPO" --add-assignee "$ASSIGN_TO" >/dev/null 2>&1; then
    ASSIGNED="yes"
  elif gh api "repos/$REPO/issues/$PR_NUM/assignees" -X POST -f "assignees[]=$ASSIGN_TO" >/dev/null 2>&1; then
    ASSIGNED="yes"
  fi
  [ "$ASSIGNED" = "yes" ] && log "assigned to @$ASSIGN_TO." || log "WARNING: could not assign @$ASSIGN_TO (check the login is a collaborator)."
  if gh pr edit "$PR_NUM" --repo "$REPO" --add-reviewer "$ASSIGN_TO" >/dev/null 2>&1; then
    REVIEW_REQ="yes"
  elif gh api "repos/$REPO/pulls/$PR_NUM/requested_reviewers" -X POST -f "reviewers[]=$ASSIGN_TO" >/dev/null 2>&1; then
    REVIEW_REQ="yes"
  fi
  [ "$REVIEW_REQ" = "yes" ] && log "review requested from @$ASSIGN_TO." || log "note: review request not applied."
else
  log "step 3/3 — assignment DISABLED (--no-assign); skipping."
fi

# ── step 4: report ───────────────────────────────────────────────────────
cat >&2 <<EOF

qute-coder chain complete:
  PR:                 $PR_URL (created=$CREATED)
  independent review: $VERDICT
  assigned to:        ${ASSIGN_TO:-<skipped>} ($( [ "$ASSIGNED" = yes ] && echo assigned || echo "$ASSIGNED" ))
  review requested:   $( [ "$REVIEW_REQ" = yes ] && echo "yes, from @$ASSIGN_TO" || echo "not applied" )
  merge:              left to the human — this chain never merges.
EOF

# overall status: ok unless the review was supposed to run and failed.
OK=true
EMIT_CODE=0
if [ "$REVIEW_RAN" = "true" ] && [ "$REVIEW_OK" != "true" ]; then OK=false; EMIT_CODE=3; fi
ASSIGNED_BOOL=$([ "$ASSIGNED" = yes ] && echo true || echo false)
REVIEW_REQ_BOOL=$([ "$REVIEW_REQ" = yes ] && echo true || echo false)
emit
