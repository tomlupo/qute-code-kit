#!/usr/bin/env bash
# gist-report.sh — Wrap body HTML in a styled template, create gist, return preview URL
#
# Usage:
#   gist-report.sh <filename> [title]          # reads body HTML from stdin
#   gist-report.sh <filename> [title] < file   # reads body HTML from file
#
# The filename sets the gist filename (should end in .html).
# Body HTML is everything inside <body> — no doctype, head, or CSS needed.
#
# Examples:
#   echo '<h1>Hello</h1><p>World</p>' | gist-report.sh hello.html "My Report"
#   gist-report.sh report.html "Q4 Results" < /tmp/body.html

set -euo pipefail

FILENAME="${1:?Usage: gist-report.sh <filename.html> [title]}"
TITLE="${2:-Report}"

BODY=$(cat)

TMPFILE=$(mktemp /tmp/gist-XXXXXX.html)
trap 'rm -f "$TMPFILE"' EXIT

cat > "$TMPFILE" <<HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${TITLE}</title>
<style>
  :root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--heading:#f0f6fc;--accent:#58a6ff;--green:#3fb950;--yellow:#d29922;--red:#f85149;--muted:#8b949e}
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:2rem 1rem;max-width:820px;margin:0 auto}
  h1{color:var(--heading);font-size:1.8rem;margin-bottom:.5rem}
  h2{color:var(--accent);font-size:1.3rem;margin:1.8rem 0 .6rem;border-bottom:1px solid var(--border);padding-bottom:.3rem}
  h3{color:var(--heading);font-size:1.05rem;margin:1.2rem 0 .4rem}
  p{margin-bottom:.8rem}
  a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
  ul,ol{margin:.4rem 0 .8rem 1.4rem}li{margin-bottom:.3rem}
  .meta{color:var(--muted);font-size:.9rem;margin-bottom:1.2rem}
  .stats{display:flex;gap:1rem;margin:.5rem 0;flex-wrap:wrap}
  .stat{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.25rem .6rem;font-size:.85rem}
  .stat strong{color:var(--heading)}
  .card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1rem 1.2rem;margin:.6rem 0}
  .card-red{border-left:3px solid var(--red)}.card-green{border-left:3px solid var(--green)}.card-blue{border-left:3px solid var(--accent)}.card-yellow{border-left:3px solid var(--yellow)}
  .card-title{color:var(--heading);font-weight:600;margin-bottom:.3rem}
  .num{display:inline-block;background:var(--border);color:var(--heading);border-radius:50%;width:1.4rem;height:1.4rem;text-align:center;line-height:1.4rem;font-size:.8rem;margin-right:.3rem}
  pre{background:#0d1117;border:1px solid var(--border);border-radius:6px;padding:.8rem;overflow-x:auto;font-size:.85rem;margin:.5rem 0;color:#e6edf3;font-family:'SF Mono',Consolas,'Liberation Mono',Menlo,monospace}
  code{font-family:'SF Mono',Consolas,'Liberation Mono',Menlo,monospace;font-size:.85em;background:var(--card);padding:.1em .35em;border-radius:3px}
  pre code{background:none;padding:0}
  blockquote{border-left:3px solid var(--border);padding-left:1rem;color:var(--muted);margin:.6rem 0}
  table{border-collapse:collapse;width:100%;margin:.6rem 0}th,td{border:1px solid var(--border);padding:.4rem .6rem;text-align:left}th{background:var(--card);color:var(--heading)}
  .callout{background:linear-gradient(135deg,#161b22,#1c2431);border:1px solid var(--accent);border-radius:8px;padding:1rem;margin:1rem 0}
  .label{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:.2rem}
  hr{border:none;border-top:1px solid var(--border);margin:1.5rem 0}
  .footer{margin-top:2rem;padding-top:.8rem;border-top:1px solid var(--border);color:var(--muted);font-size:.8rem;text-align:center}
  img{max-width:100%;border-radius:6px}
</style>
</head>
<body>
${BODY}
</body>
</html>
HTMLEOF

# Rename tmp to desired filename for gist
GIST_FILE="/tmp/${FILENAME}"
cp "$TMPFILE" "$GIST_FILE"

# Create gist and extract URL
GIST_URL=$(gh gist create "$GIST_FILE" --public 2>&1 | grep -o 'https://gist.github.com/[^ ]*')

if [ -z "$GIST_URL" ]; then
    echo "Error: Failed to create gist" >&2
    rm -f "$GIST_FILE"
    exit 1
fi

# Extract components
USERNAME=$(echo "$GIST_URL" | cut -d/ -f4)
GIST_ID=$(echo "$GIST_URL" | cut -d/ -f5)

# Output preview URL
echo "https://htmlpreview.github.io/?https://gist.githubusercontent.com/${USERNAME}/${GIST_ID}/raw/${FILENAME}"

rm -f "$GIST_FILE"
