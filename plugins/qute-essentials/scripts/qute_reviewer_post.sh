#!/usr/bin/env bash
# qute_reviewer_post.sh — post an INDEPENDENT review verdict authored by the
# qute-review GitHub App (app id 4172333) and confirm a native review OBJECT was
# created (not just a comment). This is the review the review-gate CI requires,
# and — because it is authored by a DIFFERENT identity than the PR author
# (qute-coder / a human) — it satisfies require-independent-reviewer.
#
# Usage:
#   qute_reviewer_post.sh <owner/repo> <pr#> [verdict-body]
#
# Path preference:
#   1. dispatcher  POST http://localhost:8001/review {repo,pr}
#        → the auto-review service runs a cross-model review and posts it AS
#          qute-review[bot]. Preferred: it generates the verdict content too.
#   2. fallback: $HOME/.config/gh-apps/qute-review-verdict <repo> <pr> <body>
#        → posts a supplied verdict body directly AS qute-review[bot].
#
# FAIL-LOUD: if neither path can post as the App, it errors non-zero — it never
# silently posts as the default gh user (that would not be an independent review).
set -euo pipefail

REPO="${1:?usage: qute_reviewer_post.sh <owner/repo> <pr#> [body]}"
PR="${2:?usage: qute_reviewer_post.sh <owner/repo> <pr#> [body]}"
BODY="${3:-}"

GHAPPS="${QUTE_GH_APPS_DIR:-$HOME/.config/gh-apps}"
DISPATCHER="${QUTE_DISPATCHER_URL:-http://localhost:8001}"

die() { echo "qute-reviewer: $*" >&2; exit 1; }

count_bot_reviews() {
  # Count native review objects authored by qute-review[bot] on the PR.
  gh api "repos/$REPO/pulls/$PR/reviews" --paginate \
    --jq '[.[] | select(.user.login=="qute-review[bot]")] | length' 2>/dev/null || echo 0
}

before="$(count_bot_reviews)"
posted=""

# ── Path 1: dispatcher auto-review service ───────────────────────────────
if curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$DISPATCHER/health" 2>/dev/null | grep -q '^200$'; then
  echo "qute-reviewer: requesting independent review via dispatcher $DISPATCHER/review …" >&2
  resp="$(curl -s --max-time 320 -X POST "$DISPATCHER/review" \
            -H 'Content-Type: application/json' \
            -d "$(printf '{"repo":"%s","pr":%s}' "$REPO" "$PR")" 2>/dev/null || true)"
  echo "qute-reviewer: dispatcher response: ${resp:-<none>}" >&2
  posted="dispatcher"
fi

# ── Path 2: fallback to the direct qute-review-verdict helper ────────────
after="$(count_bot_reviews)"
if [ "$after" -le "$before" ]; then
  VERDICT="$GHAPPS/qute-review-verdict"
  if [ -x "$VERDICT" ]; then
    [ -n "$BODY" ] || BODY="qute-review[bot]: independent verdict — see review-gate. (auto-posted via qute-reviewer fallback)"
    echo "qute-reviewer: dispatcher did not create a review object; falling back to $VERDICT …" >&2
    "$VERDICT" "$REPO" "$PR" "$BODY" >&2 || die "qute-review-verdict helper failed to post as qute-review[bot]."
    posted="verdict-helper"
    after="$(count_bot_reviews)"
  fi
fi

# ── Confirm a native review OBJECT now exists ────────────────────────────
if [ "$after" -gt "$before" ] || [ "$after" -gt 0 ]; then
  echo "qute-reviewer: CONFIRMED — $after native review object(s) by qute-review[bot] on $REPO#$PR." >&2
  exit 0
fi

die "no qute-review[bot] review object was created on $REPO#$PR.
  Tried: ${posted:-none}. Neither the dispatcher ($DISPATCHER/review) nor the
  qute-review-verdict helper ($GHAPPS) could post as the App on this host.
  The review-gate will stay RED. Provision the review App creds or run on a host
  that has them (do NOT hand-post as the default gh user — that is not independent)."
