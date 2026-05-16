#!/usr/bin/env bash
# release-plugin.sh — atomic release of a plugin in this marketplace repo.
#
# Bumps `plugins/<plugin>/.claude-plugin/plugin.json::version`, regenerates
# `.claude-plugin/marketplace.json` (so its catalog version stays in
# lockstep), updates CHANGELOG.md from Conventional Commits since the
# last `vX.Y.Z` tag, creates a `chore(release): bump <plugin> to vX.Y.Z`
# commit, and tags `vX.Y.Z`.
#
# Does NOT push. Caller pushes when satisfied:  git push --follow-tags
#
# Usage:
#   scripts/release-plugin.sh <plugin> <patch|minor|major|X.Y.Z>
#
# Examples:
#   scripts/release-plugin.sh qute-essentials minor
#   scripts/release-plugin.sh qute-essentials 1.16.0
set -euo pipefail

usage() {
  cat >&2 <<EOF
Usage: $0 <plugin> <patch|minor|major|X.Y.Z>

Bumps plugins/<plugin>/.claude-plugin/plugin.json, regenerates
marketplace.json, writes a CHANGELOG entry from Conventional Commits
since the last tag, commits, and tags. Caller pushes.
EOF
  exit 2
}

[ $# -eq 2 ] || usage
plugin="$1"
spec="$2"

cd "$(git rev-parse --show-toplevel)"

plugin_json="plugins/${plugin}/.claude-plugin/plugin.json"
marketplace_json=".claude-plugin/marketplace.json"
changelog="CHANGELOG.md"
build_script="scripts/build-marketplace.py"

[ -f "$plugin_json" ]      || { echo "error: $plugin_json not found" >&2; exit 1; }
[ -f "$marketplace_json" ] || { echo "error: $marketplace_json not found" >&2; exit 1; }
[ -f "$build_script" ]     || { echo "error: $build_script not found" >&2; exit 1; }

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "error: working tree has uncommitted tracked changes. commit or stash first." >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

current="$(jq -r .version "$plugin_json")"
catalog="$(jq -r --arg n "$plugin" '.plugins[] | select(.name==$n) | .version' "$marketplace_json")"

if [ "$current" != "$catalog" ]; then
  echo "error: version drift detected before bump:" >&2
  echo "  $plugin_json:      $current" >&2
  echo "  $marketplace_json: $catalog" >&2
  echo "fix the drift first (manual edit or pick the higher), then re-run." >&2
  exit 1
fi

bump_semver() {
  local v="$1" kind="$2"
  IFS=. read -r maj min pat <<<"$v"
  case "$kind" in
    patch) echo "$maj.$min.$((pat+1))" ;;
    minor) echo "$maj.$((min+1)).0" ;;
    major) echo "$((maj+1)).0.0" ;;
    *)     echo "" ;;
  esac
}

case "$spec" in
  patch|minor|major) new="$(bump_semver "$current" "$spec")" ;;
  *) [[ "$spec" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "error: bad version '$spec'" >&2; exit 1; }
     new="$spec" ;;
esac

if [ "$new" = "$current" ] || [ -z "$new" ]; then
  echo "error: computed version '$new' is invalid given current '$current'" >&2
  exit 1
fi

last_tag="$(git tag --list 'v*' | sort -V | tail -1)"
range="${last_tag:+$last_tag..HEAD}"

# Group conventional commits since last tag into BREAKING / Feat / Fix /
# Refactor / Perf. Other types (chore, docs, style, test, ci, build) are
# excluded from the user-facing CHANGELOG by Keep-a-Changelog convention.
breaking="$(git log --pretty='%s' $range | grep -E '^[a-z]+(\(.+\))?!:|BREAKING CHANGE' || true)"
feats="$(git log --pretty='%s' $range | grep -E '^feat(\(.+\))?: ' || true)"
fixes="$(git log --pretty='%s' $range | grep -E '^fix(\(.+\))?: ' || true)"
refactors="$(git log --pretty='%s' $range | grep -E '^refactor(\(.+\))?: ' || true)"
perfs="$(git log --pretty='%s' $range | grep -E '^perf(\(.+\))?: ' || true)"

if [ -z "$breaking$feats$fixes$refactors$perfs" ] && [ -n "$last_tag" ]; then
  echo "warning: no feat/fix/refactor/perf/breaking commits since $last_tag — releasing anyway." >&2
fi

today="$(date +%Y-%m-%d)"
{
  echo "## v${new} (${today})"
  echo
  if [ -n "$breaking" ]; then
    echo "### BREAKING"; echo
    while IFS= read -r line; do echo "- ${line}"; done <<<"$breaking"
    echo
  fi
  if [ -n "$feats" ]; then
    echo "### Feat"; echo
    while IFS= read -r line; do echo "- ${line#feat*: }"; done <<<"$feats"
    echo
  fi
  if [ -n "$fixes" ]; then
    echo "### Fix"; echo
    while IFS= read -r line; do echo "- ${line#fix*: }"; done <<<"$fixes"
    echo
  fi
  if [ -n "$refactors" ]; then
    echo "### Refactor"; echo
    while IFS= read -r line; do echo "- ${line#refactor*: }"; done <<<"$refactors"
    echo
  fi
  if [ -n "$perfs" ]; then
    echo "### Perf"; echo
    while IFS= read -r line; do echo "- ${line#perf*: }"; done <<<"$perfs"
    echo
  fi
} > /tmp/release-plugin-entry.$$

# Prepend to CHANGELOG (handle missing file).
if [ -f "$changelog" ]; then
  cat /tmp/release-plugin-entry.$$ "$changelog" > /tmp/changelog.$$ && mv /tmp/changelog.$$ "$changelog"
else
  mv /tmp/release-plugin-entry.$$ "$changelog"
fi
rm -f /tmp/release-plugin-entry.$$

# Bump plugin.json (jq writes atomically via temp file).
tmp="$(mktemp)"
jq --arg v "$new" '.version=$v' "$plugin_json" > "$tmp" && mv "$tmp" "$plugin_json"

# Regenerate marketplace.json from plugin.json sources.
python3 "$build_script" >/dev/null

# Verify drift is now zero.
post_catalog="$(jq -r --arg n "$plugin" '.plugins[] | select(.name==$n) | .version' "$marketplace_json")"
if [ "$post_catalog" != "$new" ]; then
  echo "error: marketplace.json regen produced $post_catalog, expected $new" >&2
  exit 1
fi

# Sync pyproject.toml [tool.commitizen].version if present, so commitizen
# stays usable as a fallback release tool. Only updates the version line
# inside the [tool.commitizen] section — leaves [project] / [build-system]
# untouched.
files_to_stage=("$plugin_json" "$marketplace_json" "$changelog")
if [ -f "pyproject.toml" ] && grep -q '^\[tool\.commitizen\]' pyproject.toml; then
  awk -v new="$new" '
    /^\[tool\.commitizen\]/    { in_cz=1; print; next }
    in_cz && /^\[/             { in_cz=0; print; next }
    in_cz && /^version[ \t]*=/ { print "version = \"" new "\""; next }
                               { print }
  ' pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml
  files_to_stage+=("pyproject.toml")
fi

git add "${files_to_stage[@]}"
git commit -m "chore(release): bump ${plugin} to v${new}"
git tag -a "v${new}" -m "Release ${plugin} v${new}"

cat <<EOF

✓ Released ${plugin} v${new}
  commit: $(git rev-parse --short HEAD)
  tag:    v${new}
  push:   git push --follow-tags
EOF
