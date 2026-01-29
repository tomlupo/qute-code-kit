#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# manage-clients.sh — Multi-Client AI Tool Manager
# Inspired by dotagents (github.com/iannuttall/dotagents)
#
# Manages a canonical .agents folder and creates symlinks to distribute
# commands, skills, hooks, and prompt files across multiple AI clients.
# Supports both global (~/) and project-level scopes.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
if [ -t 1 ]; then
    GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
    DIM='\033[2m'
else
    GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; NC=''; DIM=''
fi

# ---- Helpers ----------------------------------------------------------------

info()    { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}•${NC} $*"; }
conflict(){ echo -e "${RED}⚠${NC} $*"; }
error()   { echo -e "${RED}[!]${NC} $*" >&2; }
fatal()   { error "$@"; exit 1; }
header()  { echo -e "\n${BOLD}${CYAN}=== $* ===${NC}"; }

# ---- Supported clients and their path mappings ----------------------------

# Client config directories (global scope)
declare -A CLIENT_GLOBAL_ROOTS=(
    [claude]="$HOME/.claude"
    [gemini]="$HOME/.gemini"
    [codex]="$HOME/.codex"
    [cursor]="$HOME/.cursor"
    [opencode]="$HOME/.config/opencode"
    [factory]="$HOME/.factory"
    [ampcode]="$HOME/.config/amp"
)

# Which clients support which features
# Format: "commands hooks skills prompt"
declare -A CLIENT_FEATURES=(
    [claude]="commands hooks skills prompt"
    [gemini]="commands skills prompt"
    [codex]="commands skills prompt"
    [cursor]="commands skills prompt"
    [opencode]="commands skills prompt"
    [factory]="commands hooks prompt"
    [ampcode]="commands skills prompt"
)

# Client-specific prompt file names
declare -A CLIENT_PROMPT_FILES=(
    [claude]="CLAUDE.md"
    [gemini]="GEMINI.md"
    [codex]="AGENTS.md"
    [cursor]="AGENTS.md"
    [opencode]="AGENTS.md"
    [factory]="AGENTS.md"
    [ampcode]="AGENTS.md"
)

ALL_CLIENTS="claude gemini codex cursor opencode factory ampcode"

# ---- Path resolution -------------------------------------------------------

# Resolve the .agents canonical root
resolve_canonical_root() {
    local scope="$1"
    local project_root="${2:-$(pwd)}"

    if [ "$scope" = "global" ]; then
        echo "$HOME/.agents"
    else
        echo "$project_root/.agents"
    fi
}

# Resolve a client's root directory
resolve_client_root() {
    local client="$1"
    local scope="$2"
    local project_root="${3:-$(pwd)}"

    if [ "$scope" = "global" ]; then
        echo "${CLIENT_GLOBAL_ROOTS[$client]}"
    else
        echo "$project_root/.${client}"
    fi
}

# ---- Backup system ---------------------------------------------------------

create_backup_session() {
    local canonical_root="$1"
    local timestamp
    timestamp="$(date +%Y%m%d_%H%M%S)"
    local backup_dir="$canonical_root/backup/$timestamp"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

backup_path() {
    local source="$1"
    local backup_dir="$2"

    if [ ! -e "$source" ] && [ ! -L "$source" ]; then
        return 0
    fi

    local relative
    relative="$(echo "$source" | sed "s|^$HOME/||")"
    local dest="$backup_dir/$relative"
    mkdir -p "$(dirname "$dest")"

    if [ -L "$source" ]; then
        # Backup symlink target info
        local link_target
        link_target="$(readlink "$source")"
        echo "$link_target" > "${dest}.symlink"
        rm -f "$source"
        info "Backed up symlink: $source -> ${dest}.symlink"
    elif [ -d "$source" ]; then
        cp -r "$source" "$dest"
        info "Backed up directory: $source"
    else
        cp "$source" "$dest"
        info "Backed up file: $source"
    fi
}

write_backup_manifest() {
    local backup_dir="$1"
    local scope="$2"
    local operation="$3"
    shift 3
    local entries=("$@")

    local manifest="$backup_dir/manifest.json"
    local timestamp
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local json_entries=""
    for entry in "${entries[@]}"; do
        [ -n "$json_entries" ] && json_entries+=","
        json_entries+=$'\n    '"\"$entry\""
    done

    cat > "$manifest" <<EOF
{
  "version": 1,
  "createdAt": "$timestamp",
  "scope": "$scope",
  "operation": "$operation",
  "entries": [$json_entries
  ]
}
EOF
}

# ---- Undo system -----------------------------------------------------------

find_latest_backup() {
    local canonical_root="$1"
    local backup_root="$canonical_root/backup"

    if [ ! -d "$backup_root" ]; then
        echo ""
        return
    fi

    # Find most recent backup directory
    local latest=""
    for d in "$backup_root"/*/; do
        [ -d "$d" ] || continue
        [ -f "$d/manifest.json" ] || continue
        if [ -z "$latest" ] || [ "$d" \> "$latest" ]; then
            latest="$d"
        fi
    done

    echo "${latest%/}"
}

undo_last_change() {
    local canonical_root="$1"
    local latest
    latest="$(find_latest_backup "$canonical_root")"

    if [ -z "$latest" ]; then
        error "No backup found to undo"
        return 1
    fi

    header "Undoing last change"
    echo "  Backup: $latest"

    local restored=0
    local removed=0

    # Restore backed-up items
    while IFS= read -r -d '' backup_file; do
        local relative="${backup_file#$latest/}"

        if [[ "$backup_file" == *.symlink ]]; then
            # Restore symlink
            local orig_path="$HOME/${relative%.symlink}"
            local link_target
            link_target="$(cat "$backup_file")"
            mkdir -p "$(dirname "$orig_path")"
            if [ -e "$orig_path" ] || [ -L "$orig_path" ]; then
                rm -rf "$orig_path"
            fi
            ln -s "$link_target" "$orig_path"
            info "Restored symlink: $orig_path -> $link_target"
            ((restored++)) || true
        elif [ "$relative" != "manifest.json" ]; then
            local orig_path="$HOME/$relative"
            mkdir -p "$(dirname "$orig_path")"
            if [ -e "$orig_path" ] || [ -L "$orig_path" ]; then
                rm -rf "$orig_path"
            fi
            if [ -d "$backup_file" ]; then
                cp -r "$backup_file" "$orig_path"
            else
                cp "$backup_file" "$orig_path"
            fi
            info "Restored: $orig_path"
            ((restored++)) || true
        fi
    done < <(find "$latest" -not -path "$latest" -print0 2>/dev/null)

    echo ""
    echo "  Restored: $restored items"
    echo "  Backup preserved at: $latest"
}

# ---- Link operations -------------------------------------------------------

# Check if a symlink already points to the expected source
is_correctly_linked() {
    local target="$1"
    local expected_source="$2"

    if [ ! -L "$target" ]; then
        return 1
    fi

    local actual
    actual="$(readlink -f "$target" 2>/dev/null || echo "")"
    local expected
    expected="$(readlink -f "$expected_source" 2>/dev/null || echo "$expected_source")"

    [ "$actual" = "$expected" ]
}

# Create a symlink from source to target
create_link() {
    local source="$1"
    local target="$2"
    local backup_dir="${3:-}"

    # Ensure parent directory exists
    mkdir -p "$(dirname "$target")"

    # Handle existing target
    if [ -e "$target" ] || [ -L "$target" ]; then
        if is_correctly_linked "$target" "$source"; then
            return 0  # Already correct
        fi

        # Back up existing target if backup dir provided
        if [ -n "$backup_dir" ]; then
            backup_path "$target" "$backup_dir"
        else
            rm -rf "$target"
        fi
    fi

    ln -sf "$source" "$target"
}

# ---- Status checking -------------------------------------------------------

check_link_status() {
    local source="$1"
    local target="$2"

    if [ ! -e "$source" ] && [ ! -d "$source" ]; then
        echo "missing-source"
        return
    fi

    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
        echo "missing"
        return
    fi

    if [ -L "$target" ]; then
        if is_correctly_linked "$target" "$source"; then
            echo "linked"
        else
            echo "conflict"
        fi
        return
    fi

    # Target exists but isn't a symlink
    echo "conflict"
}

show_status() {
    local scope="$1"
    local project_root="${2:-$(pwd)}"
    local clients="${3:-$ALL_CLIENTS}"

    local canonical_root
    canonical_root="$(resolve_canonical_root "$scope" "$project_root")"

    header "Status ($scope scope)"
    echo -e "  Canonical root: ${DIM}$canonical_root${NC}"
    echo ""

    if [ ! -d "$canonical_root" ]; then
        warn "Canonical .agents directory not found at $canonical_root"
        echo "  Run with --apply to create it."
        return
    fi

    local total_linked=0
    local total_missing=0
    local total_conflicts=0

    for client in $clients; do
        local client_root
        client_root="$(resolve_client_root "$client" "$scope" "$project_root")"
        local features="${CLIENT_FEATURES[$client]}"

        echo -e "  ${BOLD}$client${NC} ($client_root)"

        # Check prompt file
        if [[ "$features" == *"prompt"* ]]; then
            local prompt_file="${CLIENT_PROMPT_FILES[$client]}"
            local source="$canonical_root/$prompt_file"
            local target="$client_root/$prompt_file"

            # Check for client-specific override first
            if [ -f "$canonical_root/$prompt_file" ]; then
                source="$canonical_root/$prompt_file"
            elif [ -f "$canonical_root/AGENTS.md" ]; then
                source="$canonical_root/AGENTS.md"
            fi

            local status
            status="$(check_link_status "$source" "$target")"
            case "$status" in
                linked)         echo -e "    ${GREEN}✓${NC} prompt ($prompt_file)"; ((total_linked++)) || true ;;
                missing)        echo -e "    ${YELLOW}•${NC} prompt ($prompt_file) — not linked"; ((total_missing++)) || true ;;
                missing-source) echo -e "    ${DIM}·${NC} prompt ($prompt_file) — no source file"; ((total_missing++)) || true ;;
                conflict)       echo -e "    ${RED}⚠${NC} prompt ($prompt_file) — conflict"; ((total_conflicts++)) || true ;;
            esac
        fi

        # Check directories (commands, hooks, skills)
        for dir_type in commands hooks skills; do
            if [[ "$features" != *"$dir_type"* ]]; then
                continue
            fi

            local source="$canonical_root/$dir_type"
            local target="$client_root/$dir_type"
            local status
            status="$(check_link_status "$source" "$target")"
            case "$status" in
                linked)         echo -e "    ${GREEN}✓${NC} $dir_type"; ((total_linked++)) || true ;;
                missing)        echo -e "    ${YELLOW}•${NC} $dir_type — not linked"; ((total_missing++)) || true ;;
                missing-source) echo -e "    ${DIM}·${NC} $dir_type — no source directory"; ((total_missing++)) || true ;;
                conflict)       echo -e "    ${RED}⚠${NC} $dir_type — conflict"; ((total_conflicts++)) || true ;;
            esac
        done

        echo ""
    done

    # Summary
    echo -e "  ${BOLD}Summary:${NC} ${GREEN}$total_linked linked${NC}, ${YELLOW}$total_missing missing${NC}, ${RED}$total_conflicts conflicts${NC}"
}

# ---- Apply/sync links ------------------------------------------------------

apply_links() {
    local scope="$1"
    local project_root="${2:-$(pwd)}"
    local clients="${3:-$ALL_CLIENTS}"
    local dry_run="${4:-0}"
    local force="${5:-0}"

    local canonical_root
    canonical_root="$(resolve_canonical_root "$scope" "$project_root")"

    header "Applying links ($scope scope)"

    # Ensure canonical root exists
    if [ ! -d "$canonical_root" ]; then
        if [ "$dry_run" = "1" ]; then
            echo -e "  ${GREEN}CREATE${NC} $canonical_root/"
        else
            mkdir -p "$canonical_root"
            info "Created canonical root: $canonical_root"
        fi
    fi

    # Create backup session
    local backup_dir=""
    local backed_up=()
    if [ "$dry_run" != "1" ]; then
        backup_dir="$(create_backup_session "$canonical_root")"
    fi

    local applied=0
    local skipped=0
    local conflicts=0

    for client in $clients; do
        local client_root
        client_root="$(resolve_client_root "$client" "$scope" "$project_root")"
        local features="${CLIENT_FEATURES[$client]}"

        echo -e "\n  ${BOLD}$client${NC}"

        # Link prompt file
        if [[ "$features" == *"prompt"* ]]; then
            local prompt_file="${CLIENT_PROMPT_FILES[$client]}"
            local source=""

            # Determine source: client-specific override or AGENTS.md fallback
            if [ -f "$canonical_root/$prompt_file" ]; then
                source="$canonical_root/$prompt_file"
            elif [ -f "$canonical_root/AGENTS.md" ]; then
                source="$canonical_root/AGENTS.md"
            fi

            if [ -n "$source" ]; then
                local target="$client_root/$prompt_file"
                local status
                status="$(check_link_status "$source" "$target")"

                if [ "$status" = "linked" ]; then
                    echo -e "    ${DIM}skip${NC}  $prompt_file (already linked)"
                    ((skipped++)) || true
                elif [ "$status" = "conflict" ] && [ "$force" != "1" ]; then
                    conflict "    $prompt_file — conflict (use --force to override)"
                    ((conflicts++)) || true
                else
                    if [ "$dry_run" = "1" ]; then
                        echo -e "    ${GREEN}LINK${NC}  $prompt_file -> $(basename "$source")"
                    else
                        create_link "$source" "$target" "$backup_dir"
                        backed_up+=("$target")
                        info "    Linked: $prompt_file -> $(basename "$source")"
                    fi
                    ((applied++)) || true
                fi
            fi
        fi

        # Link directories
        for dir_type in commands hooks skills; do
            if [[ "$features" != *"$dir_type"* ]]; then
                continue
            fi

            local source="$canonical_root/$dir_type"
            local target="$client_root/$dir_type"

            # Skip if source doesn't exist
            if [ ! -d "$source" ]; then
                continue
            fi

            local status
            status="$(check_link_status "$source" "$target")"

            if [ "$status" = "linked" ]; then
                echo -e "    ${DIM}skip${NC}  $dir_type/ (already linked)"
                ((skipped++)) || true
            elif [ "$status" = "conflict" ] && [ "$force" != "1" ]; then
                conflict "    $dir_type/ — conflict (use --force to override)"
                ((conflicts++)) || true
            else
                if [ "$dry_run" = "1" ]; then
                    echo -e "    ${GREEN}LINK${NC}  $dir_type/ -> $source"
                else
                    create_link "$source" "$target" "$backup_dir"
                    backed_up+=("$target")
                    info "    Linked: $dir_type/"
                fi
                ((applied++)) || true
            fi
        done
    done

    # Finalize backup
    if [ "$dry_run" != "1" ] && [ ${#backed_up[@]} -gt 0 ]; then
        write_backup_manifest "$backup_dir" "$scope" "apply" "${backed_up[@]}"
    elif [ "$dry_run" != "1" ] && [ -d "$backup_dir" ]; then
        # Remove empty backup dir
        rm -rf "$backup_dir"
    fi

    # Summary
    echo ""
    if [ "$dry_run" = "1" ]; then
        echo -e "  ${BOLD}Dry run:${NC} $applied would be applied, $skipped already linked, $conflicts conflicts"
    else
        echo -e "  ${BOLD}Done:${NC} $applied applied, $skipped already linked, $conflicts conflicts"
        if [ ${#backed_up[@]} -gt 0 ]; then
            echo -e "  Backup: $backup_dir"
        fi
    fi
}

# ---- Initialize .agents from existing client configs -----------------------

init_agents_dir() {
    local scope="$1"
    local project_root="${2:-$(pwd)}"
    local source_client="${3:-claude}"

    local canonical_root
    canonical_root="$(resolve_canonical_root "$scope" "$project_root")"

    header "Initializing .agents directory"

    if [ -d "$canonical_root" ] && [ "$(ls -A "$canonical_root" 2>/dev/null)" ]; then
        warn ".agents directory already exists and is not empty: $canonical_root"
        echo "  Use --force to overwrite."
        return 1
    fi

    local source_root
    source_root="$(resolve_client_root "$source_client" "$scope" "$project_root")"

    if [ ! -d "$source_root" ]; then
        info "Creating empty .agents structure at $canonical_root"
        mkdir -p "$canonical_root"/{commands,skills,hooks}
        # Create AGENTS.md template
        cat > "$canonical_root/AGENTS.md" <<'AGENTSEOF'
# AGENTS.md

Universal guidance for AI coding assistants (Claude, Gemini, Codex, Cursor, etc.).

## Project Overview

[Describe the project purpose and goals.]

## Key Paths

| Purpose | Location |
|---------|----------|
| Source code | `src/` |
| Tests | `tests/` |
| Documentation | `docs/` |

## Key Commands

| Task | Command |
|------|---------|
| Run tests | `...` |
| Build | `...` |
| Lint | `...` |

## Coding Conventions

- [List conventions here]

## Domain Knowledge

- [Domain-specific information here]
AGENTSEOF
        info "Created AGENTS.md template"
        return 0
    fi

    header "Migrating from $source_client to .agents"
    mkdir -p "$canonical_root"

    # Copy prompt files
    for prompt_file in CLAUDE.md AGENTS.md GEMINI.md; do
        if [ -f "$source_root/$prompt_file" ]; then
            cp "$source_root/$prompt_file" "$canonical_root/$prompt_file"
            info "Copied: $prompt_file"
        fi
    done

    # Copy directories
    for dir_type in commands hooks skills; do
        if [ -d "$source_root/$dir_type" ] && [ ! -L "$source_root/$dir_type" ]; then
            cp -r "$source_root/$dir_type" "$canonical_root/$dir_type"
            info "Copied: $dir_type/"
        fi
    done

    # Ensure AGENTS.md exists as fallback
    if [ ! -f "$canonical_root/AGENTS.md" ]; then
        if [ -f "$canonical_root/CLAUDE.md" ]; then
            cp "$canonical_root/CLAUDE.md" "$canonical_root/AGENTS.md"
            info "Created AGENTS.md from CLAUDE.md"
        fi
    fi

    echo ""
    info "Migration complete. Run with --apply to create symlinks."
}

# ---- Populate .agents from qute-code-kit ----------------------------------

populate_from_kit() {
    local canonical_root="$1"
    local kit_root="$SCRIPT_DIR/claude"
    local bundle="${2:-minimal}"
    local use_link="${3:-0}"

    header "Populating .agents from qute-code-kit ($bundle)"

    mkdir -p "$canonical_root"/{commands,skills,hooks}

    # Copy/link skills
    if [ -d "$kit_root/skills/my" ]; then
        for skill_dir in "$kit_root"/skills/my/*/; do
            [ -d "$skill_dir" ] || continue
            local name
            name="$(basename "$skill_dir")"
            local dest="$canonical_root/skills/$name"
            if [ ! -e "$dest" ]; then
                if [ "$use_link" = "1" ]; then
                    ln -sf "$skill_dir" "$dest"
                    info "Linked skill: $name"
                else
                    cp -r "$skill_dir" "$dest"
                    info "Copied skill: $name"
                fi
            fi
        done
    fi

    # Copy/link commands
    if [ -d "$kit_root/commands" ]; then
        for cmd_file in "$kit_root"/commands/*.md; do
            [ -f "$cmd_file" ] || continue
            local name
            name="$(basename "$cmd_file")"
            local dest="$canonical_root/commands/$name"
            if [ ! -e "$dest" ]; then
                if [ "$use_link" = "1" ]; then
                    ln -sf "$cmd_file" "$dest"
                    info "Linked command: $name"
                else
                    cp "$cmd_file" "$dest"
                    info "Copied command: $name"
                fi
            fi
        done
    fi

    echo ""
    info "Populated .agents with kit components"
}

# ---- Usage -----------------------------------------------------------------

usage() {
    cat <<'EOF'
Usage: manage-clients.sh [command] [options]

Multi-client AI tool manager. Maintains a canonical .agents folder and creates
symlinks to distribute configuration across AI clients.

Inspired by dotagents (github.com/iannuttall/dotagents).

Commands:
  status              Show current link status for all clients
  apply               Create symlinks from .agents to client directories
  init                Initialize .agents directory (optionally from existing client)
  populate            Populate .agents with components from qute-code-kit
  undo                Reverse the last apply operation
  list-clients        Show supported clients and their features

Options:
  --scope <scope>     global or project (default: global)
  --project <path>    Project directory (default: current dir)
  --clients <list>    Comma-separated client list (default: all)
  --force             Override existing files/conflicts
  --diff              Dry run (show what would change)
  --link              Use symlinks when populating (default: copy)
  --from <client>     Source client for init migration (default: claude)
  --bundle <name>     Bundle name for populate (default: minimal)
  -h, --help          Show this help

Examples:
  # Check what's linked globally
  manage-clients.sh status

  # Initialize .agents from existing Claude config
  manage-clients.sh init --from claude

  # Apply links to Claude and Gemini only
  manage-clients.sh apply --clients claude,gemini

  # Preview what would happen
  manage-clients.sh apply --diff

  # Project-level setup
  manage-clients.sh init --scope project --project ~/myapp
  manage-clients.sh apply --scope project --project ~/myapp

  # Populate from qute-code-kit
  manage-clients.sh populate --bundle minimal

  # Undo last change
  manage-clients.sh undo
EOF
    exit 0
}

# ---- Main ------------------------------------------------------------------

main() {
    local command=""
    local scope="global"
    local project_root=""
    local clients=""
    local force=0
    local dry_run=0
    local use_link=0
    local from_client="claude"
    local bundle="minimal"

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)         usage ;;
            status|apply|init|populate|undo|list-clients)
                command="$1"; shift ;;
            --scope)           scope="$2"; shift 2 ;;
            --project)         project_root="$2"; shift 2 ;;
            --clients)         clients="${2//,/ }"; shift 2 ;;
            --force)           force=1; shift ;;
            --diff)            dry_run=1; shift ;;
            --link)            use_link=1; shift ;;
            --from)            from_client="$2"; shift 2 ;;
            --bundle)          bundle="$2"; shift 2 ;;
            -*)                fatal "Unknown option: $1" ;;
            *)                 fatal "Unknown argument: $1" ;;
        esac
    done

    # Defaults
    [ -z "$project_root" ] && project_root="$(pwd)"
    [ -z "$clients" ] && clients="$ALL_CLIENTS"

    # Validate scope
    if [ "$scope" != "global" ] && [ "$scope" != "project" ]; then
        fatal "Invalid scope: $scope (must be 'global' or 'project')"
    fi

    case "$command" in
        status)
            show_status "$scope" "$project_root" "$clients"
            ;;
        apply)
            apply_links "$scope" "$project_root" "$clients" "$dry_run" "$force"
            ;;
        init)
            init_agents_dir "$scope" "$project_root" "$from_client"
            ;;
        populate)
            local canonical_root
            canonical_root="$(resolve_canonical_root "$scope" "$project_root")"
            populate_from_kit "$canonical_root" "$bundle" "$use_link"
            ;;
        undo)
            local canonical_root
            canonical_root="$(resolve_canonical_root "$scope" "$project_root")"
            undo_last_change "$canonical_root"
            ;;
        list-clients)
            header "Supported AI Clients"
            echo ""
            printf "  ${BOLD}%-12s %-50s %s${NC}\n" "Client" "Global Path" "Features"
            echo "  $(printf '%.0s-' {1..80})"
            for client in $ALL_CLIENTS; do
                printf "  %-12s %-50s %s\n" \
                    "$client" \
                    "${CLIENT_GLOBAL_ROOTS[$client]}" \
                    "${CLIENT_FEATURES[$client]}"
            done
            echo ""
            echo "  Prompt file precedence:"
            for client in $ALL_CLIENTS; do
                local pf="${CLIENT_PROMPT_FILES[$client]}"
                if [ "$pf" != "AGENTS.md" ]; then
                    echo "    $client: $pf (override) -> AGENTS.md (fallback)"
                else
                    echo "    $client: AGENTS.md"
                fi
            done
            ;;
        "")
            usage
            ;;
        *)
            fatal "Unknown command: $command"
            ;;
    esac
}

main "$@"
