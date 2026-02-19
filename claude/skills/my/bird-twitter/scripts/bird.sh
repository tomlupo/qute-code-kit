#!/usr/bin/env bash
# bird.sh — CLI wrapper for Bird (Twitter/X) via MCP Gateway
# Usage: bird.sh <command> [options]
#   bird.sh bookmarks [count]
#   bird.sh search <query> [count]
#
# Reads MCP_TOKEN from environment or from openclaw .env file.

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8080}"
ENV_FILE="/home/botops/openclaw/.env"

# Resolve MCP_TOKEN
if [ -z "${MCP_TOKEN:-}" ] && [ -f "$ENV_FILE" ]; then
    MCP_TOKEN=$(grep -m1 '^MCP_TOKEN=' "$ENV_FILE" | cut -d= -f2)
fi

if [ -z "${MCP_TOKEN:-}" ]; then
    echo "Error: MCP_TOKEN not set and not found in $ENV_FILE" >&2
    exit 1
fi

usage() {
    cat <<'EOF'
Usage: bird.sh <command> [options]

Commands:
  bookmarks [count]        Fetch Twitter/X bookmarks (default: 20, max: 100)
  search <query> [count]   Search Twitter/X (default: 10, max: 50)

Examples:
  bird.sh bookmarks 5
  bird.sh search "quantitative trading" 20
  bird.sh search "#fintwit momentum" 10
EOF
    exit 1
}

[ $# -lt 1 ] && usage

CMD="$1"
shift

case "$CMD" in
    bookmarks)
        COUNT="${1:-20}"
        curl -sf -H "X-MCP-Token: $MCP_TOKEN" \
            "${GATEWAY_URL}/bird/bookmarks?count=${COUNT}"
        ;;
    search)
        [ $# -lt 1 ] && { echo "Error: search requires a query" >&2; usage; }
        QUERY="$1"
        COUNT="${2:-10}"
        curl -sf -H "X-MCP-Token: $MCP_TOKEN" \
            --data-urlencode "q=${QUERY}" \
            -G "${GATEWAY_URL}/bird/search?count=${COUNT}"
        ;;
    *)
        echo "Unknown command: $CMD" >&2
        usage
        ;;
esac
