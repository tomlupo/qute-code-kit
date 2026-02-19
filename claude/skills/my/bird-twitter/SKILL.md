---
name: bird-twitter
description: Retrieve Twitter/X bookmarks and search tweets via Bird CLI (read-only). Use for "bookmarks", "tweets", "Twitter", "X search", "fintwit", or when scanning Twitter/X for research signals.
argument-hint: "[bookmarks|search] [query] [count]"
allowed-tools: Bash, Read
---

# Bird Twitter/X Skill

Read-only Twitter/X retrieval via the `@steipete/bird` CLI, proxied through the MCP Gateway.

## Architecture

```
Twitter/X API
      |
Bird CLI (@steipete/bird) — installed in Gateway container
      |
MCP Gateway (HTTP proxy, rate-limited, auth-gated)
  GET /bird/bookmarks   — fetch saved bookmarks
  GET /bird/search      — search tweets
      |
bird.sh (host wrapper, sources MCP_TOKEN from .env)
```

## Quick Commands

All commands use the wrapper script:
```bash
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh <command>
```

### Fetch Bookmarks
```bash
# Default 20 bookmarks
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh bookmarks

# Specific count (1-100)
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh bookmarks 5
```

### Search Tweets
```bash
# Basic search (default 10 results)
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh search "quantitative trading"

# With count (1-50)
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh search "#fintwit momentum" 20

# Research-oriented searches
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh search "mean reversion strategy" 15
bash ~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/scripts/bird.sh search "from:AQRCapital" 10
```

### Direct curl (alternative)
```bash
MCP_TOKEN=$(grep MCP_TOKEN /home/botops/openclaw/.env | cut -d= -f2)

# Bookmarks
curl -s -H "X-MCP-Token: $MCP_TOKEN" "http://127.0.0.1:8080/bird/bookmarks?count=10"

# Search
curl -s -H "X-MCP-Token: $MCP_TOKEN" -G --data-urlencode "q=quantitative trading" "http://127.0.0.1:8080/bird/search?count=10"
```

## Output Format

Both endpoints return JSON arrays. Each tweet object:

```json
{
  "id": "2024574875231215664",
  "text": "Full tweet text with links...",
  "createdAt": "Thu Feb 19 20:00:39 +0000 2026",
  "replyCount": 5,
  "retweetCount": 11,
  "likeCount": 125,
  "conversationId": "2024574875231215664",
  "author": {
    "username": "handle",
    "name": "Display Name"
  },
  "authorId": "123456789",
  "media": [
    {
      "type": "photo",
      "url": "https://pbs.twimg.com/media/...",
      "width": 870,
      "height": 490
    }
  ]
}
```

**Key fields**: `text`, `author.username`, `createdAt`, `likeCount`, `retweetCount`, `media`

## Query Selection

| User Request | Command |
|-------------|---------|
| "Show my bookmarks" | `bookmarks 20` |
| "Recent bookmarks" | `bookmarks 10` |
| "Search Twitter for X" | `search "X" 10` |
| "What's fintwit saying about momentum?" | `search "#fintwit momentum" 20` |
| "Find tweets from @AQRCapital" | `search "from:AQRCapital" 10` |
| "Quant research on Twitter" | `search "quantitative finance research" 15` |
| "Trending in systematic trading" | `search "systematic trading" 20` |

## Presentation Guidelines

When presenting results to the user:

1. **Summarize, don't dump** — extract key insights from tweets, don't paste raw JSON
2. **Attribution** — always credit `@username` and approximate time
3. **Engagement signal** — mention like/RT counts for high-engagement tweets (>100 likes)
4. **Links** — extract and present any paper/article links from tweet text
5. **Media** — note when tweets have images/charts but don't embed URLs unless asked

### Example presentation:

> **Recent bookmarks (3 highlights):**
>
> - **@iblanco_finance** (Feb 17) — New research on equity trend filters: 10-month MA delivers same ~10% CAGR as buy-and-hold but cuts max drawdown from -54% to -20%. Paper link: [url]. (125 likes)
> - **@SomeResearcher** (Feb 16) — Thread on mean reversion in crypto futures... (45 RTs)
> - **@QuantTwitter** (Feb 15) — Backtest results for momentum + quality factor combo...

## Rate Limits

- 10 requests/minute per endpoint (Gateway-enforced)
- Keep searches focused — prefer specific queries over broad ones

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `401 Unauthorized` | MCP_TOKEN mismatch — check `.env` |
| `502 Bird command failed` | Bird credentials expired — check `BIRD_AUTH_TOKEN` and `BIRD_CT0` in `.env` |
| `504 Timeout` | Twitter/X slow — retry after a moment |
| Empty results | Try broader search terms or check if bird_twitter shows `true` in `/health` |
| `Connection refused` | Gateway not running — `docker compose up -d mcp-gateway` |

## Files

```
~/.claude/plugins/marketplaces/qute-marketplace/claude/skills/my/bird-twitter/
  SKILL.md           # This file
  scripts/bird.sh    # Host-side wrapper script

Gateway implementation:
  /home/botops/openclaw/mcp-gateway/main.py  (lines 1186-1251)

Auth (in .env):
  MCP_TOKEN          # Gateway auth
  BIRD_AUTH_TOKEN    # Twitter/X auth token (Gateway container only)
  BIRD_CT0           # Twitter/X CSRF token (Gateway container only)
```
