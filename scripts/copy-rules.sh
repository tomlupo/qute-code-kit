#!/usr/bin/env bash
# Copy rules, root files, and settings to a target project.
# Plugins handle skills and agents; this script handles everything else.
#
# Usage:
#   ./scripts/copy-rules.sh <target-dir> [--preset minimal|quant|webdev]
#
# Examples:
#   ./scripts/copy-rules.sh ~/projects/my-app                   # minimal rules
#   ./scripts/copy-rules.sh ~/projects/my-app --preset quant    # quant rules + python rules
#   ./scripts/copy-rules.sh ~/projects/my-app --preset webdev   # webdev rules

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RULES_DIR="$KIT_DIR/claude/rules"
ROOT_DIR="$KIT_DIR/claude/root-files"
SETTINGS_DIR="$KIT_DIR/claude/settings"

# --- Presets ---
MINIMAL_RULES=(
  code-quality.md
  general-rules.md
  work-organization.md
  context-management.md
  documentation.md
)

QUANT_RULES=(
  "${MINIMAL_RULES[@]}"
  python-rules.md
  python-patterns.md
  datasets.md
)

WEBDEV_RULES=(
  "${MINIMAL_RULES[@]}"
  coding-standards.md
)

# --- Parse args ---
TARGET=""
PRESET="minimal"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset)
      PRESET="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 <target-dir> [--preset minimal|quant|webdev]"
      echo ""
      echo "Copies rules and root files to a target project."
      echo "Use alongside qute-* plugins which provide skills and agents."
      echo ""
      echo "Presets:"
      echo "  minimal   5 base rules + CLAUDE.md + AGENTS.md"
      echo "  quant     minimal + python-rules, python-patterns, datasets"
      echo "  webdev    minimal + coding-standards"
      echo ""
      echo "Rules are copied to: <target>/.claude/rules/"
      echo "Root files copied to: <target>/CLAUDE.md, <target>/AGENTS.md"
      exit 0
      ;;
    *)
      TARGET="$1"
      shift
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Error: target directory required"
  echo "Usage: $0 <target-dir> [--preset minimal|quant|webdev]"
  exit 1
fi

# --- Select rules ---
case "$PRESET" in
  minimal) RULES=("${MINIMAL_RULES[@]}") ;;
  quant)   RULES=("${QUANT_RULES[@]}") ;;
  webdev)  RULES=("${WEBDEV_RULES[@]}") ;;
  *)
    echo "Error: unknown preset '$PRESET' (use minimal, quant, or webdev)"
    exit 1
    ;;
esac

# --- Create directories ---
mkdir -p "$TARGET/.claude/rules"

# --- Copy rules ---
echo "=== Copying $PRESET rules to $TARGET ==="
for rule in "${RULES[@]}"; do
  if [[ -f "$RULES_DIR/$rule" ]]; then
    cp "$RULES_DIR/$rule" "$TARGET/.claude/rules/$rule"
    echo "  [+] $rule"
  else
    echo "  [!] Missing: $rule"
  fi
done

# --- Copy root files ---
for root_file in CLAUDE.md AGENTS.md; do
  if [[ -f "$ROOT_DIR/$root_file" ]]; then
    cp "$ROOT_DIR/$root_file" "$TARGET/$root_file"
    echo "  [+] $root_file -> $TARGET/$root_file"
  fi
done

# --- Copy settings if available ---
SETTINGS_FILE=""
case "$PRESET" in
  quant)  SETTINGS_FILE="project-quant.json" ;;
  webdev) SETTINGS_FILE="project-webdev.json" ;;
esac

if [[ -n "$SETTINGS_FILE" && -f "$SETTINGS_DIR/$SETTINGS_FILE" ]]; then
  cp "$SETTINGS_DIR/$SETTINGS_FILE" "$TARGET/.claude/settings.json"
  echo "  [+] settings.json ($SETTINGS_FILE)"
fi

echo ""
echo "=== Done ==="
echo "  Rules: ${#RULES[@]} copied to $TARGET/.claude/rules/"
echo ""
echo "Next: install the matching plugin:"
echo "  claude plugin install qute-$PRESET@qute-marketplace"
