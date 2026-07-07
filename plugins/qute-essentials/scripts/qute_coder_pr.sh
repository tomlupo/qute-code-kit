#!/usr/bin/env bash
# qute_coder_pr.sh — `gh pr create` authored by the qute-coder GitHub App (app id 4172326),
# so `require-independent-reviewer` passes BY CONSTRUCTION (author != reviewer).
#
# Drop-in for `gh pr create`: all args pass straight through.
#   qute_coder_pr.sh --repo o/r --base main --title "…" --body "…"
#
# FAIL-LOUD (deliberately unlike ~/bin/coder-pr, which fails SOFT to the default
# gh user): if the qute-coder App creds are absent on this host, this errors and
# exits non-zero instead of silently opening a PR authored as the default gh user
# (e.g. tomlupo). A forge/CI host without creds MUST error, never mis-attribute.
#
# Creds (reused from the shared gh-apps helpers, resolved under $HOME):
#   $HOME/.config/gh-apps/coding.env   (CODING_APP_ID=…)
#   $HOME/.config/gh-apps/coding.pem
#   $HOME/.config/gh-apps/gh-app-token (JWT/installation-token minter)
set -euo pipefail

GHAPPS="${QUTE_GH_APPS_DIR:-$HOME/.config/gh-apps}"
ENV="$GHAPPS/coding.env"
PEM="$GHAPPS/coding.pem"
MINTER="$GHAPPS/gh-app-token"

die() { echo "qute-coder: $*" >&2; exit 1; }

[ -r "$ENV" ]    || die "qute-coder App creds MISSING on this host: $ENV not readable.
  This host cannot author a PR as qute-coder[bot]. Refusing to fall back to the
  default gh user (that would mis-attribute the PR). Provision the gh-apps creds
  (coding.env/coding.pem/gh-app-token) or run /qute-coder on a host that has them."
[ -r "$PEM" ]    || die "qute-coder App key MISSING: $PEM not readable. See above."
[ -x "$MINTER" ] || die "gh-app-token minter MISSING/not executable: $MINTER. See above."

APP_ID="$(sed -n 's/^CODING_APP_ID=//p' "$ENV" | head -n1)"
[ -n "$APP_ID" ] || die "CODING_APP_ID not set in $ENV."

TOKEN="$("$MINTER" "$APP_ID" "$PEM")" \
  || die "failed to mint a qute-coder installation token (App id $APP_ID).
  Check the App is installed on the target repo and the .pem is valid."
[ -n "$TOKEN" ] || die "minted an empty token — App likely not installed on the repo."

echo "qute-coder: authoring PR as qute-coder[bot] (App id $APP_ID)" >&2
GH_TOKEN="$TOKEN" gh pr create "$@"
