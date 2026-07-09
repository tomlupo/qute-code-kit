#!/usr/bin/env bash
# qute_reviewer_post.sh — post an INDEPENDENT review verdict authored by the
# qute-review GitHub App (app id 4172333) as a native review OBJECT, PORTABLY.
#
# Two modes, auto-selected (override with QUTE_REVIEW_MODE=dispatcher|local|auto,
# default auto):
#
#   dispatcher  — POST $QUTE_DISPATCHER_URL/review {repo,pr}. The dispatcher runs
#                 codex and posts the review AS qute-review[bot]. Only reachable on
#                 core (127.0.0.1:8001). Preferred there — it generates the verdict.
#
#   local       — dispatcher NOT reachable (forge / any box with gh-apps creds).
#                 Generate the verdict in a SEPARATE HEADLESS PROCESS with its own
#                 CLEAN CONTEXT (codex exec — cross-model gpt-5.x — primary; a fresh
#                 `claude -p` headless invocation as fallback), fed ONLY the PR diff,
#                 then post it as a native review OBJECT via the DIRECT review-App
#                 token (mint from $GHAPPS/review.pem -> gh api .../pulls/N/reviews).
#                 Needs ONLY gh-apps creds, NOT the dispatcher.
#
#   auto        — probe dispatcher reachability; dispatcher if up, else local.
#
# INDEPENDENCE GUARANTEE (Tom's explicit requirement): local-mode verdict
# generation runs in a SEPARATE OS PROCESS with a fresh context (codex exec, or
# `claude -p`) — NEVER an in-process Agent-tool subagent (a subagent inherits the
# caller's context and can rationalize the same way, defeating independence).
#
# FAIL-LOUD: if no path can post as the App, it errors non-zero — it never posts
# as the default gh user (that would not be an independent review).
#
# ── VERB CONTRACT (for Jimek / any conductor) ────────────────────────────
#   --json   emit ONE machine-readable JSON object as the final stdout line
#            (human logs stay on stderr) so a conductor can branch on the verdict.
#   --force  post a fresh review even if one already exists at the PR's head SHA.
#
# IDEMPOTENT (default): if a qute-review[bot] review OBJECT already exists for the
# PR's CURRENT head SHA, this NO-OPS (does not post a duplicate) and reports the
# existing verdict — re-running is safe. A new commit (new head SHA) re-reviews.
#
# EXIT CODES: 0 review present (posted OR idempotent-existing); non-zero if no
# review could be posted (gate stays red).
#
# Usage: qute_reviewer_post.sh [--json] [--force] <owner/repo> <pr#> [verdict body]
set -euo pipefail

OPT_JSON=0
OPT_FORCE=0
POS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --json)  OPT_JSON=1; shift ;;
    --force) OPT_FORCE=1; shift ;;
    --)      shift; while [ $# -gt 0 ]; do POS+=("$1"); shift; done ;;
    *)       POS+=("$1"); shift ;;
  esac
done
set -- "${POS[@]}"
REPO="${1:?usage: qute_reviewer_post.sh [--json] [--force] <owner/repo> <pr#> [body]}"
PR="${2:?usage: qute_reviewer_post.sh [--json] [--force] <owner/repo> <pr#> [body]}"
BODY_OVERRIDE="${3:-}"

GHAPPS="${QUTE_GH_APPS_DIR:-$HOME/.config/gh-apps}"
DISPATCHER="${QUTE_DISPATCHER_URL:-http://localhost:8001}"
MODE="${QUTE_REVIEW_MODE:-auto}"

log() { echo "qute-reviewer: $*" >&2; }

# ── structured JSON (contract) ───────────────────────────────────────────
# emit_json <ok> <mode> <verdict> <posted> <idempotent_skip> <count>
emit_json() {
  [ "$OPT_JSON" = "1" ] || return 0
  OK="$1" MODE="$2" VERDICT="$3" POSTED="$4" SKIP="$5" COUNT="$6" \
  J_REPO="$REPO" J_PR="$PR" python3 - <<'PY'
import json, os
def b(x): return str(x).lower() in ("1", "true", "yes")
print(json.dumps({
    "verb": "qute-reviewer",
    "ok": b(os.environ["OK"]),
    "repo": os.environ["J_REPO"],
    "pr": int(os.environ["J_PR"]) if os.environ["J_PR"].isdigit() else os.environ["J_PR"],
    "mode": os.environ["MODE"] or None,
    "verdict": os.environ["VERDICT"] or None,
    "posted": b(os.environ["POSTED"]),
    "idempotent_skip": b(os.environ["SKIP"]),
    "review_count": int(os.environ["COUNT"] or 0),
}))
PY
}
# die: on --json, emit an ok=false object first so a conductor still gets a result.
die() { echo "qute-reviewer: $*" >&2; emit_json false "${chosen:-}" "" false false "0"; exit 1; }

count_bot_reviews() {
  gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
    --jq '[.[] | select(.user.login=="qute-review[bot]")] | length' 2>/dev/null \
    | awk '{s=$0} END{print (s==""?0:s)}'
}

pr_head_sha() {
  gh api "repos/$REPO/pulls/$PR" --jq '.head.sha' 2>/dev/null || true
}

# Count qute-review[bot] review objects whose commit_id == the PR head SHA.
count_bot_reviews_at_head() {
  local sha="$1"
  [ -n "$sha" ] || { echo 0; return; }
  { gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      --jq "[.[] | select(.user.login==\"qute-review[bot]\") | select(.commit_id==\"$sha\")] | length" 2>/dev/null \
    || true; } | awk '{s=$0} END{print (s==""?0:s)}'
}

# Verdict text (SHIP / SHIP-WITH-NITS / BLOCKER) from the most recent
# qute-review[bot] review object. Never fails (empty if none) — safe under set -e.
latest_bot_verdict() {
  { gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
      --jq '[.[] | select(.user.login=="qute-review[bot]")] | last | .body' 2>/dev/null \
    | grep -oiE 'VERDICT:[[:space:]]*(SHIP-WITH-NITS|SHIP|BLOCKER)' \
    | head -n1 \
    | sed -E 's/^[Vv][Ee][Rr][Dd][Ii][Cc][Tt]:[[:space:]]*//'; } || true
}

dispatcher_reachable() {
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$DISPATCHER/health" 2>/dev/null)" = "200" ]
}

select_mode() {
  case "$MODE" in
    dispatcher|local) echo "$MODE" ;;
    auto) if dispatcher_reachable; then echo dispatcher; else echo local; fi ;;
    *) die "invalid QUTE_REVIEW_MODE='$MODE' (want dispatcher|local|auto)" ;;
  esac
}

# ── dispatcher mode ──────────────────────────────────────────────────────
run_dispatcher() {
  dispatcher_reachable || die "QUTE_REVIEW_MODE=dispatcher but $DISPATCHER/review is unreachable.
  Use QUTE_REVIEW_MODE=local (or auto) on a box without the dispatcher."
  log "requesting independent review via dispatcher $DISPATCHER/review …"
  local resp
  resp="$(curl -s --max-time 320 -X POST "$DISPATCHER/review" \
            -H 'Content-Type: application/json' \
            -d "$(printf '{"repo":"%s","pr":%s}' "$REPO" "$PR")" 2>/dev/null || true)"
  log "dispatcher response: ${resp:-<none>}"
}

# ── local mode: separate-headless-process verdict generation ─────────────
REVIEW_PROMPT='You are an INDEPENDENT code reviewer with NO prior context on this change — a cold
skeptic who assumes the diff is wrong until proven otherwise. Review ONLY the unified diff below.
Hunt these failure classes and report REAL findings only, each with file:line + a one-line fix:
correctness/edge-cases; path/IO safety (traversal, unguarded overwrite/delete, symlinks);
authz/authn (fail-open, allowlist bypass); injection (shell/SQL/template/prompt); secrets/data
egress; silent failure/data loss (swallowed errors, partial writes); concurrency/resources.
Output a first line exactly "VERDICT: SHIP" or "VERDICT: SHIP-WITH-NITS" or "VERDICT: BLOCKER",
then concise bullets. Diff follows:'

generate_verdict_local() {
  local diff_file="$1" out=""
  # PRIMARY: codex exec — separate process, cross-model, clean context.
  if [ -z "${QUTE_REVIEW_NO_CODEX:-}" ] && command -v codex >/dev/null 2>&1; then
    log "generating verdict in a separate headless process: codex exec (cross-model, clean context)…"
    if out="$(printf '%s\n\n%s\n' "$REVIEW_PROMPT" "$(cat "$diff_file")" \
              | codex exec --skip-git-repo-check - 2>/dev/null)" && [ -n "$out" ]; then
      printf 'codex (local headless): %s' "$out"
      return 0
    fi
    log "codex unavailable/empty — falling back to a fresh headless claude -p."
  fi
  # FALLBACK: a FRESH `claude -p` headless invocation — its OWN clean context,
  # given ONLY the diff. Explicitly NOT the Agent tool / not an in-process subagent.
  command -v claude >/dev/null 2>&1 \
    || die "no separate-process reviewer available (codex and claude both absent).
  Cannot generate an independent verdict on this host."
  log "generating verdict in a separate headless process: fresh 'claude -p' (own clean context)…"
  out="$(printf '%s\n\n%s\n' "$REVIEW_PROMPT" "$(cat "$diff_file")" \
          | claude -p --dangerously-skip-permissions 2>/dev/null)" \
    || die "fresh claude -p reviewer invocation failed."
  [ -n "$out" ] || die "fresh claude -p reviewer returned empty."
  printf 'claude -p (local headless): %s' "$out"
}

mint_review_token() {
  local env="$GHAPPS/review.env" pem="$GHAPPS/review.pem" minter="$GHAPPS/gh-app-token"
  [ -r "$env" ] && [ -r "$pem" ] && [ -x "$minter" ] \
    || die "qute-review App creds MISSING on this host (need $GHAPPS/{review.env,review.pem,gh-app-token}).
  Cannot post an independent review object as qute-review[bot]. Provision the creds or run on a host that has them."
  # shellcheck disable=SC1090
  source "$env"
  local app_id="${REVIEW_APP_ID:-}"
  [ -n "$app_id" ] || die "REVIEW_APP_ID not set in $env."
  "$minter" "$app_id" "$pem" || die "failed to mint a qute-review installation token (App id $app_id)."
}

post_review_object() {
  local body="$1" token
  token="$(mint_review_token)"
  [ -n "$token" ] || die "minted an empty review token — App likely not installed on the repo."
  log "posting native review object as qute-review[bot] via gh api repos/$REPO/pulls/$PR/reviews …"
  GH_TOKEN="$token" gh api "repos/$REPO/pulls/$PR/reviews" \
    -X POST -f event=COMMENT -f body="$body" >/dev/null \
    || die "gh api failed to create the review object as qute-review[bot]."
}

run_local() {
  local diff_file body
  diff_file="$(mktemp)"; trap 'rm -f "$diff_file"' RETURN
  gh pr diff "$PR" --repo "$REPO" >"$diff_file" 2>/dev/null \
    || die "could not fetch the PR diff (gh pr diff $PR --repo $REPO)."
  [ -s "$diff_file" ] || die "PR diff was empty — nothing to review."
  if [ -n "$BODY_OVERRIDE" ]; then
    body="$BODY_OVERRIDE"
  else
    body="$(generate_verdict_local "$diff_file")"
  fi
  post_review_object "$body"
}

# ── main ─────────────────────────────────────────────────────────────────
chosen="$(select_mode)"
log "mode=$chosen (QUTE_REVIEW_MODE=$MODE)"

# ── idempotency: skip if a bot review already exists at the PR head SHA ───
HEAD_SHA="$(pr_head_sha)"
if [ "$OPT_FORCE" != "1" ]; then
  at_head="$(count_bot_reviews_at_head "$HEAD_SHA")"
  if [ "${at_head:-0}" -gt 0 ]; then
    verdict="$(latest_bot_verdict)"
    log "idempotent: $at_head qute-review[bot] review object(s) already exist at head ${HEAD_SHA:0:7} — not posting a duplicate (use --force to override)."
    emit_json true "$chosen" "$verdict" false true "$at_head"
    exit 0
  fi
fi

before="$(count_bot_reviews)"

case "$chosen" in
  dispatcher) run_dispatcher ;;
  local)      run_local ;;
esac

# CONFIRM by the CURRENT head SHA (what the gate actually needs) — a stale review
# on an older SHA must NOT count as success. When the head SHA is unknown (older
# gh / API hiccup) fall back to "a new review object appeared THIS run" (after >
# before), which is still strictly better than the old any-review-exists check.
after_head="$(count_bot_reviews_at_head "$HEAD_SHA")"
after_total="$(count_bot_reviews)"
if { [ -n "$HEAD_SHA" ] && [ "${after_head:-0}" -gt 0 ]; } || [ "$after_total" -gt "$before" ]; then
  verdict="$(latest_bot_verdict)"
  count="$after_total"; [ -n "$HEAD_SHA" ] && count="$after_head"
  log "CONFIRMED — $count qute-review[bot] review object(s) at head ${HEAD_SHA:0:7} on $REPO#$PR (mode=$chosen). verdict=${verdict:-<unparsed>}"
  emit_json true "$chosen" "$verdict" true false "$count"
  exit 0
fi
die "no qute-review[bot] review object was created at the current head SHA on $REPO#$PR (mode=$chosen). Gate stays RED."
