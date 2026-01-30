#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# setup-project.sh — Claude Toolkit Setup
# Bootstraps Claude Code projects with skills, agents, rules, and configs
# from the qute-code-kit repository.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$SCRIPT_DIR/claude"

# Colors (disable if not a terminal)
if [ -t 1 ]; then
    GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; NC=''
fi

# ---- Helpers ----------------------------------------------------------------

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[!]${NC} $*" >&2; }
fatal() { error "$@"; exit 1; }
header(){ echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

usage() {
    cat <<'EOF'
Usage: setup-project.sh <target> [options]

Bootstrap or update a Claude Code project with skills, agents, rules, and settings.

Arguments:
  <target>               Path to the project directory

Options:
  --bundle <name>        Apply bundle (minimal, quant, webdev)
  --add <component>      Add single component (e.g., my:ai-review, mcp:playwright)
  --add @<sub-bundle>    Add skill sub-bundle (e.g., @skills/visualization)
  --link                 Symlink instead of copy
  --diff                 Dry run — show what would be installed
  --update               Re-sync from source (overwrite existing)
  --list                 List all available components
  --list-bundles         List bundles with contents
  --init                 Create standard project directories
  --no-pyproject         Skip pyproject.toml
  --no-root-files        Skip CLAUDE.md, AGENTS.md

Examples:
  setup-project.sh ~/projects/new-fund --bundle quant --init
  setup-project.sh ~/projects/existing-app --bundle webdev
  setup-project.sh ~/projects/app --add my:ai-review
  setup-project.sh ~/projects/app --add mcp:playwright
  setup-project.sh ~/projects/app --add @skills/visualization
  setup-project.sh ~/projects/app --bundle quant --diff
  setup-project.sh ~/projects/app --update
EOF
    exit 0
}

# ---- Source path resolution -------------------------------------------------

# Map a component reference to its source path on disk.
# Returns empty string if source doesn't exist.
resolve_source() {
    local ref="$1"
    local src=""

    case "$ref" in
        rules/*)
            local ref_name="${ref#rules/}"
            src="$CLAUDE_DIR/rules/$ref_name"
            ;;
        root/CLAUDE.md)
            src="$CLAUDE_DIR/root-files/CLAUDE.md"
            ;;
        root/AGENTS.md)
            src="$CLAUDE_DIR/root-files/AGENTS.md"
            ;;
        settings/*)
            src="$CLAUDE_DIR/$ref"
            ;;
        pyproject/*)
            local name="${ref#pyproject/}"
            src="$SCRIPT_DIR/templates/pyproject/$name"
            ;;
        commands/*)
            src="$CLAUDE_DIR/$ref"
            ;;
        hooks/*)
            src="$CLAUDE_DIR/$ref"
            ;;
        my:*)
            local name="${ref#my:}"
            # Skills are directories, agents can be .md files or directories
            if [ -d "$CLAUDE_DIR/skills/my/$name" ]; then
                src="$CLAUDE_DIR/skills/my/$name"
            elif [ -f "$CLAUDE_DIR/agents/my/$name" ]; then
                src="$CLAUDE_DIR/agents/my/$name"
            elif [ -d "$CLAUDE_DIR/agents/my/$name" ]; then
                src="$CLAUDE_DIR/agents/my/$name"
            fi
            ;;
        external:scientific/*)
            local name="${ref#external:scientific/}"
            if [ -d "$CLAUDE_DIR/skills/external/scientific-skills/$name" ]; then
                src="$CLAUDE_DIR/skills/external/scientific-skills/$name"
            fi
            ;;
        external:*)
            local name="${ref#external:}"
            if [ -d "$CLAUDE_DIR/skills/external/$name" ]; then
                src="$CLAUDE_DIR/skills/external/$name"
            elif [ -f "$CLAUDE_DIR/agents/external/$name" ]; then
                src="$CLAUDE_DIR/agents/external/$name"
            elif [ -d "$CLAUDE_DIR/agents/external/$name" ]; then
                src="$CLAUDE_DIR/agents/external/$name"
            fi
            ;;
        mcp:*)
            local name="${ref#mcp:}"
            if [ -f "$CLAUDE_DIR/mcp/$name.json" ]; then
                src="$CLAUDE_DIR/mcp/$name.json"
            fi
            ;;
    esac

    echo "$src"
}

# Map a component reference to its target path in the project.
resolve_target() {
    local ref="$1"
    local target_dir="$2"

    case "$ref" in
        rules/*)
            local name="${ref#rules/}"
            echo "$target_dir/.claude/rules/$name"
            ;;
        root/CLAUDE.md)
            echo "$target_dir/CLAUDE.md"
            ;;
        root/AGENTS.md)
            echo "$target_dir/AGENTS.md"
            ;;
        settings/*)
            echo "$target_dir/.claude/settings.json"
            ;;
        pyproject/*)
            echo "$target_dir/pyproject.toml"
            ;;
        commands/*)
            local name="${ref#commands/}"
            echo "$target_dir/.claude/commands/$name"
            ;;
        hooks/*)
            local name="${ref#hooks/}"
            echo "$target_dir/.claude/hooks/$name"
            ;;
        my:*|external:scientific/*|external:*)
            local name
            case "$ref" in
                my:*)
                    name="${ref#my:}"
                    ;;
                external:scientific/*)
                    name="${ref#external:scientific/}"
                    ;;
                external:*)
                    name="${ref#external:}"
                    ;;
            esac
            # Determine type from source
            local src
            src="$(resolve_source "$ref")"
            if [ -z "$src" ]; then
                echo ""
                return
            fi
            # Check if it's a skill or agent based on source path
            if [[ "$src" == *"/skills/"* ]]; then
                echo "$target_dir/.claude/skills/$name/"
            elif [[ "$src" == *"/agents/"* ]]; then
                echo "$target_dir/.claude/agents/$name"
            fi
            ;;
        mcp:*)
            local name="${ref#mcp:}"
            echo "$target_dir/.mcp/$name/.mcp.json"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Detect component type for manifest
detect_type() {
    local ref="$1"
    case "$ref" in
        rules/*)              echo "rule" ;;
        root/*)               echo "root" ;;
        settings/*)           echo "settings" ;;
        pyproject/*)          echo "pyproject" ;;
        commands/*)           echo "command" ;;
        hooks/*)              echo "hook" ;;
        my:*|external:*)
            local src
            src="$(resolve_source "$ref")"
            if [[ "$src" == *"/skills/"* ]]; then
                echo "skill"
            elif [[ "$src" == *"/agents/"* ]]; then
                echo "agent"
            else
                echo "unknown"
            fi
            ;;
        mcp:*) echo "mcp" ;;
        *) echo "unknown" ;;
    esac
}

# ---- Bundle resolution ------------------------------------------------------

# Parse a bundle file and append component references to a temp file.
# Expands @inherits recursively. Uses a visited-file to prevent cycles.

resolve_bundle() {
    local bundle_file="$1"
    local output_file="$2"
    local visited_file="$3"

    if [ ! -f "$bundle_file" ]; then
        error "Bundle not found: $bundle_file"
        return 1
    fi

    # Prevent infinite recursion
    local abs_path
    abs_path="$(realpath "$bundle_file")"
    if grep -qxF "$abs_path" "$visited_file" 2>/dev/null; then
        return 0
    fi
    echo "$abs_path" >> "$visited_file"

    while IFS= read -r line || [ -n "$line" ]; do
        # Strip comments and whitespace
        line="${line%%#*}"
        line="$(echo "$line" | xargs)"
        [ -z "$line" ] && continue

        if [[ "$line" == @* ]]; then
            # Bundle reference — resolve recursively
            local ref="${line#@}"
            local ref_file="$CLAUDE_DIR/bundles/$ref.txt"
            if [ -f "$ref_file" ]; then
                resolve_bundle "$ref_file" "$output_file" "$visited_file"
            else
                warn "Bundle not found: $ref (from $bundle_file)"
            fi
        else
            echo "$line" >> "$output_file"
        fi
    done < "$bundle_file"
}

# ---- Install ----------------------------------------------------------------

install_component() {
    local ref="$1"
    local target_dir="$2"
    local use_link="$3"
    local force="$4"
    local dry_run="$5"

    local src dst
    src="$(resolve_source "$ref")"
    dst="$(resolve_target "$ref" "$target_dir")"

    if [ -z "$src" ]; then
        warn "Source not found: $ref"
        return 1
    fi

    if [ -z "$dst" ]; then
        warn "Cannot determine target for: $ref"
        return 1
    fi

    # Check if already exists
    if [ -e "$dst" ] && [ "$force" != "1" ]; then
        if [ "$dry_run" = "1" ]; then
            echo -e "  ${YELLOW}SKIP${NC}  $ref  ->  $dst  (exists)"
        fi
        return 0
    fi

    if [ "$dry_run" = "1" ]; then
        if [ -e "$dst" ] && [ "$force" = "1" ]; then
            echo -e "  ${CYAN}UPDATE${NC}  $ref  ->  $dst"
        else
            echo -e "  ${GREEN}ADD${NC}     $ref  ->  $dst"
        fi
        return 0
    fi

    # Create parent directory
    mkdir -p "$(dirname "$dst")"

    # Install
    if [ "$use_link" = "1" ]; then
        # Symlink — strip trailing slash for directory targets
        local link_dst="${dst%/}"
        if [ -e "$link_dst" ] || [ -L "$link_dst" ]; then
            rm -rf "$link_dst"
        fi
        ln -sf "$src" "$link_dst"
        info "Linked: $ref -> $link_dst"
    else
        # Copy
        if [ -d "$src" ]; then
            # Copy directory
            if [ -e "$dst" ]; then
                rm -rf "$dst"
            fi
            cp -r "$src" "$dst"
            info "Copied: $ref -> $dst"
        else
            cp "$src" "$dst"
            info "Copied: $ref -> $dst"
        fi
    fi
    return 0
}

# ---- Manifest tracking ------------------------------------------------------

write_manifest() {
    local target_dir="$1"
    local bundle_name="$2"
    local mode="$3"
    shift 3
    local components=("$@")

    local manifest="$target_dir/.claude/.toolkit-manifest.json"
    mkdir -p "$(dirname "$manifest")"

    local timestamp
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # Build components JSON array
    local json_components=""
    for ref in "${components[@]}"; do
        local comp_type comp_name
        comp_type="$(detect_type "$ref")"
        case "$ref" in
            rules/*)              comp_name="${ref#rules/}" ;;
            root/*)               comp_name="${ref#root/}" ;;
            settings/*)           comp_name="${ref#settings/}" ;;
            pyproject/*)          comp_name="${ref#pyproject/}" ;;
            commands/*)           comp_name="${ref#commands/}" ;;
            hooks/*)              comp_name="${ref#hooks/}" ;;
            mcp:*)                comp_name="${ref#mcp:}" ;;
            my:*)                 comp_name="${ref#my:}" ;;
            external:scientific/*) comp_name="${ref#external:scientific/}" ;;
            external:*)           comp_name="${ref#external:}" ;;
            *)                    comp_name="$ref" ;;
        esac

        if [ -n "$json_components" ]; then
            json_components+=","
        fi
        json_components+=$'\n    '"{\"type\": \"$comp_type\", \"name\": \"$comp_name\", \"src\": \"$ref\"}"
    done

    cat > "$manifest" <<EOF
{
  "source": "$SCRIPT_DIR",
  "bundle": "$bundle_name",
  "installed": "$timestamp",
  "mode": "$mode",
  "components": [$json_components
  ]
}
EOF
    info "Manifest written: $manifest"
}

# ---- Listing ----------------------------------------------------------------

list_components() {
    header "Skills (my)"
    for d in "$CLAUDE_DIR"/skills/my/*/; do
        [ -d "$d" ] && echo "  my:$(basename "$d")"
    done

    header "Skills (external)"
    for d in "$CLAUDE_DIR"/skills/external/*/; do
        [ -d "$d" ] || continue
        local base
        base="$(basename "$d")"
        if [ "$base" = "scientific-skills" ]; then
            for sd in "$d"*/; do
                [ -d "$sd" ] && echo "  external:scientific/$(basename "$sd")"
            done
        else
            echo "  external:$base"
        fi
    done

    header "Agents (my)"
    for f in "$CLAUDE_DIR"/agents/my/*; do
        [ -e "$f" ] || continue
        local name
        name="$(basename "$f")"
        [[ "$name" == *.Identifier ]] && continue
        echo "  my:$name"
    done

    header "Agents (external)"
    for f in "$CLAUDE_DIR"/agents/external/*; do
        [ -e "$f" ] || continue
        local name
        name="$(basename "$f")"
        [[ "$name" == *.Identifier ]] && continue
        echo "  external:$name"
    done

    header "Commands"
    for f in "$CLAUDE_DIR"/commands/*.md; do
        [ -f "$f" ] && echo "  commands/$(basename "$f")"
    done

    header "Hooks"
    for f in "$CLAUDE_DIR"/hooks/*; do
        [ -f "$f" ] && echo "  hooks/$(basename "$f")"
    done

    header "Settings"
    for f in "$CLAUDE_DIR"/settings/*.json; do
        [ -f "$f" ] && echo "  settings/$(basename "$f")"
    done

    header "Rules"
    for f in "$CLAUDE_DIR"/rules/*.md; do
        [ -f "$f" ] && echo "  rules/$(basename "$f")"
    done

    header "MCP Servers"
    for f in "$CLAUDE_DIR"/mcp/*.json; do
        [ -f "$f" ] && echo "  mcp:$(basename "$f" .json)"
    done

    header "pyproject Templates"
    for f in "$SCRIPT_DIR"/templates/pyproject/*.toml; do
        [ -f "$f" ] && echo "  pyproject/$(basename "$f")"
    done
}

list_bundles() {
    header "Available Bundles"
    for f in "$CLAUDE_DIR"/bundles/*.txt; do
        [ -f "$f" ] || continue
        local name
        name="$(basename "$f" .txt)"
        echo -e "\n${BOLD}$name${NC}:"
        # Show contents with indent
        while IFS= read -r line || [ -n "$line" ]; do
            line_trimmed="${line%%#*}"
            line_trimmed="$(echo "$line_trimmed" | xargs)"
            [ -z "$line_trimmed" ] && continue
            echo "  $line_trimmed"
        done < "$f"
    done

    header "Skill Sub-Bundles"
    for f in "$CLAUDE_DIR"/bundles/skills/*.txt; do
        [ -f "$f" ] || continue
        local name
        name="$(basename "$f" .txt)"
        echo -e "\n${BOLD}@skills/$name${NC}:"
        while IFS= read -r line || [ -n "$line" ]; do
            line_trimmed="${line%%#*}"
            line_trimmed="$(echo "$line_trimmed" | xargs)"
            [ -z "$line_trimmed" ] && continue
            echo "  $line_trimmed"
        done < "$f"
    done
}

# ---- Init project directories -----------------------------------------------

init_dirs() {
    local target_dir="$1"
    local dirs=(
        src scripts data/raw data/processed docs config output
        reports scratch notebooks tests
    )
    for d in "${dirs[@]}"; do
        if [ ! -d "$target_dir/$d" ]; then
            mkdir -p "$target_dir/$d"
            info "Created: $d/"
        fi
    done

    # Append .gitignore entries if template exists
    local gi_template="$SCRIPT_DIR/templates/.gitignore.claude"
    local gi_target="$target_dir/.gitignore"
    if [ -f "$gi_template" ]; then
        if [ -f "$gi_target" ]; then
            # Only append if marker not already present
            if ! grep -q "# Claude Code" "$gi_target" 2>/dev/null; then
                echo "" >> "$gi_target"
                cat "$gi_template" >> "$gi_target"
                info "Appended .gitignore.claude entries to .gitignore"
            fi
        else
            cp "$gi_template" "$gi_target"
            info "Created .gitignore from template"
        fi
    fi
}

# ---- .env.example for MCP env vars ------------------------------------------

update_env_example() {
    local target_dir="$1"
    shift
    local components=("$@")

    # Collect env vars from MCP configs
    local env_vars=()
    for ref in "${components[@]}"; do
        if [[ "$ref" != mcp:* ]]; then
            continue
        fi
        local name="${ref#mcp:}"
        local src="$CLAUDE_DIR/mcp/$name.json"
        [ -f "$src" ] || continue
        # Extract ${VAR_NAME} patterns from the file
        while IFS= read -r var; do
            env_vars+=("$var")
        done < <(grep -oP '\$\{\K[^}]+' "$src" 2>/dev/null || true)
    done

    [ ${#env_vars[@]} -eq 0 ] && return 0

    # Deduplicate
    local unique_vars=()
    for var in "${env_vars[@]}"; do
        local found=0
        for u in "${unique_vars[@]+"${unique_vars[@]}"}"; do
            [ "$u" = "$var" ] && found=1 && break
        done
        [ "$found" = "0" ] && unique_vars+=("$var")
    done

    local env_file="$target_dir/.env.example"
    local needs_header=1
    if [ -f "$env_file" ] && grep -q "# MCP Server" "$env_file" 2>/dev/null; then
        needs_header=0
    fi

    local added=0
    for var in "${unique_vars[@]}"; do
        if [ -f "$env_file" ] && grep -q "^${var}=" "$env_file" 2>/dev/null; then
            continue
        fi
        if [ "$needs_header" = "1" ]; then
            [ -f "$env_file" ] && echo "" >> "$env_file"
            echo "# MCP Server API keys" >> "$env_file"
            needs_header=0
        fi
        echo "${var}=" >> "$env_file"
        ((added++)) || true
    done

    if [ "$added" -gt 0 ]; then
        info "Updated .env.example with $added MCP env var(s)"
    fi
}

# ---- Main -------------------------------------------------------------------

main() {
    local target=""
    local bundle=""
    local add_refs=()
    local use_link=0
    local dry_run=0
    local force=0
    local do_init=0
    local no_pyproject=0
    local no_root_files=0

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --help|-h)    usage ;;
            --bundle)     bundle="$2"; shift 2 ;;
            --add)        add_refs+=("$2"); shift 2 ;;
            --link)       use_link=1; shift ;;
            --diff)       dry_run=1; shift ;;
            --update)     force=1; shift ;;
            --list)       list_components; exit 0 ;;
            --list-bundles) list_bundles; exit 0 ;;
            --init)       do_init=1; shift ;;
            --no-pyproject)   no_pyproject=1; shift ;;
            --no-root-files)  no_root_files=1; shift ;;
            -*)           fatal "Unknown option: $1" ;;
            *)
                if [ -z "$target" ]; then
                    target="$1"; shift
                else
                    fatal "Unexpected argument: $1"
                fi
                ;;
        esac
    done

    # Validate
    if [ -z "$target" ] && [ -z "$bundle" ] && [ ${#add_refs[@]} -eq 0 ]; then
        usage
    fi

    if [ -z "$target" ]; then
        fatal "Target directory is required"
    fi

    # Resolve target to absolute path
    target="$(realpath -m "$target")"

    # Collect all components to install
    local all_components=()

    # Temp files for bundle resolution
    local tmp_output tmp_visited
    tmp_output="$(mktemp)"
    tmp_visited="$(mktemp)"
    trap "rm -f '$tmp_output' '$tmp_visited'" EXIT

    # From bundle
    if [ -n "$bundle" ]; then
        local bundle_file="$CLAUDE_DIR/bundles/$bundle.txt"
        if [ ! -f "$bundle_file" ]; then
            fatal "Bundle not found: $bundle (looked in $bundle_file)"
        fi

        : > "$tmp_output"
        : > "$tmp_visited"
        resolve_bundle "$bundle_file" "$tmp_output" "$tmp_visited"

        while IFS= read -r comp; do
            [ -z "$comp" ] && continue
            all_components+=("$comp")
        done < "$tmp_output"
    fi

    # From --add flags
    for ref in "${add_refs[@]}"; do
        if [[ "$ref" == @* ]]; then
            # Sub-bundle reference
            local sub_name="${ref#@}"
            local sub_file="$CLAUDE_DIR/bundles/$sub_name.txt"
            if [ ! -f "$sub_file" ]; then
                warn "Sub-bundle not found: $sub_name"
                continue
            fi
            : > "$tmp_output"
            : > "$tmp_visited"
            resolve_bundle "$sub_file" "$tmp_output" "$tmp_visited"
            while IFS= read -r comp; do
                [ -z "$comp" ] && continue
                all_components+=("$comp")
            done < "$tmp_output"
        else
            all_components+=("$ref")
        fi
    done

    if [ ${#all_components[@]} -eq 0 ] && [ "$do_init" != "1" ]; then
        fatal "No components to install. Use --bundle or --add."
    fi

    # Filter out excluded components
    local filtered=()
    for ref in "${all_components[@]}"; do
        if [ "$no_pyproject" = "1" ] && [[ "$ref" == pyproject/* ]]; then
            continue
        fi
        if [ "$no_root_files" = "1" ] && [[ "$ref" == root/* ]]; then
            continue
        fi
        filtered+=("$ref")
    done

    # Deduplicate while preserving order
    local seen=()
    local unique=()
    for ref in "${filtered[@]}"; do
        local found=0
        for s in "${seen[@]+"${seen[@]}"}"; do
            if [ "$s" = "$ref" ]; then
                found=1
                break
            fi
        done
        if [ "$found" = "0" ]; then
            seen+=("$ref")
            unique+=("$ref")
        fi
    done

    # Report
    local mode_label="copy"
    [ "$use_link" = "1" ] && mode_label="symlink"

    if [ "$dry_run" = "1" ]; then
        header "Dry Run — ${#unique[@]} components ($mode_label mode)"
        echo "  Target: $target"
        [ -n "$bundle" ] && echo "  Bundle: $bundle"
        echo ""
    else
        header "Installing ${#unique[@]} components to $target ($mode_label mode)"
    fi

    # Init dirs first
    if [ "$do_init" = "1" ]; then
        if [ "$dry_run" = "1" ]; then
            echo -e "\n${BOLD}Project directories:${NC}"
            echo "  src/ scripts/ data/raw/ data/processed/ docs/ config/ output/"
            echo "  reports/ scratch/ notebooks/ tests/"
            echo ""
        else
            init_dirs "$target"
        fi
    fi

    # Ensure .claude dir exists
    if [ "$dry_run" != "1" ]; then
        mkdir -p "$target/.claude"
    fi

    # Install each component
    local installed=()
    local skipped=0
    local failed=0

    for ref in "${unique[@]}"; do
        if install_component "$ref" "$target" "$use_link" "$force" "$dry_run"; then
            installed+=("$ref")
        else
            ((failed++)) || true
        fi
    done

    # Write manifest (skip in dry run)
    if [ "$dry_run" != "1" ] && [ ${#installed[@]} -gt 0 ]; then
        write_manifest "$target" "${bundle:-custom}" "$mode_label" "${installed[@]}"
        update_env_example "$target" "${installed[@]}"
    fi

    # Summary
    if [ "$dry_run" = "1" ]; then
        echo ""
        echo -e "${BOLD}Summary:${NC} ${#unique[@]} components would be installed"
    else
        header "Done"
        echo "  Installed: ${#installed[@]} components"
        [ "$failed" -gt 0 ] && echo -e "  ${YELLOW}Failed: $failed${NC}"
        echo "  Manifest: $target/.claude/.toolkit-manifest.json"
    fi
}

main "$@"
