# qute-essentials

Essential hooks, guards, and skills for Claude Code. Provides prompt injection screening, destructive command blocking, observability tracing, notifications, and utility skills.

## Guard System

Five security guards — toggleable via `/guard`. Two run PreToolUse (block before execution), three run PostToolUse (scan after):

```
                     ┌──────────────────────────────┐
                     │   Tool call (any tool)        │
                     └──────────────┬───────────────┘
                                    │
          ┌─────────── PreToolUse ──┴──────┐
          │                                │
 ┌────────▼──────────┐         ┌───────────▼──────┐
 │ Destructive Guard │         │  Secrets Guard   │
 │ blocks rm -rf,    │         │  blocks writes   │
 │ git reset --hard  │         │  with API keys   │
 └───────────────────┘         └──────────────────┘
                                    │
                                 executes
                                    │
          ┌─────────── PostToolUse ─┼──────────────┐
          │                         │              │
 ┌────────▼──────────┐  ┌───────────▼──────┐  ┌───▼──────────────┐
 │   Lakera Guard    │  │ Langfuse Tracing  │  │   Audit Guard    │
 │  prompt injection │  │  observability   │  │  pip-audit after │
 │  screening (API)  │  │  tracing (API)   │  │  pkg installs    │
 └───────────────────┘  └──────────────────┘  └──────────────────┘
                                    │
                               ┌────▼────┐
                               │  ntfy   │  alerts to phone
                               │  push   │
                               └─────────┘
```

### Secrets Guard (PreToolUse)

Blocks `Write`/`Edit`/`NotebookEdit` on files that leak secrets or target credential files.

**Content scan** — well-known patterns from gitleaks rules:
- AWS access keys (`AKIA…`) and secret keys
- GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `github_pat_…`)
- Slack, Google, Stripe live, Anthropic, OpenAI API keys
- Private key PEM blocks (`-----BEGIN … PRIVATE KEY-----`)
- JWTs, Azure connection strings
- Generic `password = "…"` / `api_key = "…"` assignments with high-entropy values

**Filename block** — hard-blocks by basename:
- `.env`, `.env.*` (except `.env.example` / `.env.template` / `.env.sample`)
- `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*`
- `.netrc`, `.pgpass`
- `credentials.json`, `client_secret*.json`, `service-account*.json`
- `database.ini`

**Override mechanisms** (require explicit user confirmation):
1. One-shot: `touch ~/.claude/.secret-scan-override` then retry the write (file is consumed on use)
2. Session: `/guard secrets off` (re-enable with `/guard secrets on`)
3. CI / trusted: `CLAUDE_SKIP_GUARDS=1` or `CLAUDE_GUARD_SECRETS=0`

### Destructive Guard (PreToolUse)

Blocks dangerous commands before they execute. Context-aware: won't block `grep "rm -rf"` or dry-run flags.

| Category | Examples |
|----------|----------|
| Git | `reset --hard`, `push --force`, `clean -f`, `stash clear`, `branch -D` |
| Filesystem | `rm -rf /`, `rm -rf ~/`, `find -delete`, `mkfs`, `dd of=/dev/` |
| Database | `DROP TABLE`, `TRUNCATE`, `DELETE FROM x;` (no WHERE), `dropdb` |
| Docker | `system prune -a`, mass container removal |
| System | `sudo rm -rf`, `chmod -R 777`, `crontab -r`, `pkill -9 -u` |
| Custom | Obsidian vault paths, production quantlab, trading crons |

Logs to `~/.claude/permission-audit/destructive-blocks.jsonl`. Sends ntfy alert on every block.

### Lakera Guard (PostToolUse)

Screens tool outputs for prompt injection via the Lakera Guard API. The hook matcher is scoped to the untrusted-content ingestion surface only:

- WebFetch, WebSearch (always screened)
- MCP tool responses (always screened)

Bash and Read are **not** screened — the matcher was narrowed to web/MCP ingestion (the real injection surface), removing the per-Bash/Read API round-trip. If you pull untrusted web content via `curl`/`summarize` (which run through Bash), prefer `WebFetch` so it gets screened.

When injection is detected, a warning is injected into the conversation context and an urgent ntfy alert is sent. Requires `LAKERA_GUARD_API_KEY` env var. Free tier: 10k requests/month.

Logs to `~/.claude/permission-audit/guard-detections.jsonl`.

### Langfuse Tracing (PostToolUse)

Traces every tool execution to Langfuse for observability and evaluation. Async hook, no latency impact.

Each trace includes:
- Tool name, input (redacted), output (truncated)
- `session_id` (groups tool calls per conversation)
- `project` (derived from cwd)
- `source` (`dispatcher` or `interactive`, detected via `$TMUX`)
- `hostname` (for multi-machine setups)
- Tags: `project:<name>`, `source:<type>`, `tool:<name>`, `host:<name>`

Failed commands (non-zero exit code) are auto-scored `tool_success: 0`.

Requires `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` env vars. Free tier: 50k traces/month.

## Toggle Guards

```
/guard                      # show status of all guards
/guard lakera off           # disable Lakera screening
/guard langfuse off         # disable Langfuse tracing
/guard secrets off          # disable secrets guard (session override)
/guard destructive off      # disable destructive command blocking
/guard audit off            # disable auto pip-audit
/guard gh-verbs off         # stop warning on raw gh issue/label create
/guard all on               # re-enable everything
```

Config resolution: user overrides at `~/.claude/qute-guards.json` (which survive
plugin updates, user-wins per guard) merged over the shipped defaults in
`config/guards.json`. `/guard` writes toggles to the user file. Changes take
effect immediately.

## Other Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `format_python.py` | PostToolUse (Edit/Write) | Auto-format Python with `ruff format` (cosmetic only — `ruff check --fix` deliberately omitted so per-edit F401 doesn't strip imports mid-task) |
| `log_use.py` | PostToolUse (Skill/Agent), SubagentStart | Skill/agent activity logging |
| `auto_audit.py` | PostToolUse (Bash) | Runs `/audit` after `uv add` / `pip install` |
| `pr-flow-guard.py` | PreToolUse (Bash) | **Opt-in, default OFF** (`.github/qute-pr.yml` `enforce:true`; legacy `quteEnforcePrReview` marker still honored). Blocks `gh pr create` → `/qute-coder`; gates `gh pr merge` on `allowAgentSelfMerge`. Inert unless the repo opts in — see "PR-flow enforcement" below |
| `gh-verb-guard.py` | PreToolUse (Bash) | `gh-verbs` guard (toggleable, default ON, fails OPEN). **Warns, never blocks** on raw `gh issue create` / `gh label create` — steers repo issue ops to the `task` verb (applies the TYPE+STRUCTURE label taxonomy + `[agent:]` comment prefix) and board ops to `gh-track` (#177). Suppressed when the command comes from `pulse.sh`/`gh-track` |

## Notifications

Push notifications via [ntfy.sh](https://ntfy.sh). Config in `config/ntfy.json` (`server` + `topic`).

The guards resolve the endpoint from `ntfy.json`; leave `topic` empty to auto-derive `{hostname}-{username}-claude` (e.g., `core-tom-claude`), or set it explicitly to override. Subscribe in the ntfy app to receive alerts for:
- Destructive command blocks
- Prompt injection detections

## Skills

| Skill | Description |
|-------|-------------|
| `/guard` | Toggle any of the 5 security guards on/off, check status |
| `generating-commit-messages` | Conventional Commits guidance (auto-applied before any `git commit`) |
| `/decision` | Record architecture decisions as ADRs with auto-numbering |
| `/handoff` | Prepare session handoff document (captures context, ADRs, TASKS) |
| `/pickup` | Resume work from a previous handoff |
| `/ship` | Cut a release — auto-detects Plugin mode (`marketplace.json`) or Python mode (`pyproject.toml`). Auto-runs first-time setup (commitizen + CHANGELOG + workflow) on Python projects |
| `/task` | Add or close a task — tiered: manages `TASKS.md` by default, graduates to GitHub Issues once the list earns it; proposes migration once |
| `/repo-status` | Git/worktree dashboard **plus** a read-only Open tasks glance at the repo's active store — `TASKS.md` (Tier 1) or GitHub Issues via `gh` (Tier 2), auto-detected (folds in the retired `/board`) |
| `/audit` | Dependency vulnerability scan (Python, via pip-audit/uvx) |
| `/test` | Run test suite, interpret failures, propose fixes |
| `/worktrees` | Manage git worktrees for parallel development |
| `/readme` | Generate or update README files |
| `/gbu` | Good/bad/ugly structured code or design review |
| `/wtf` | Activated on frustration/pushback — captures failure, applies three guardrail tiers (feedback memory + CLAUDE.md rule + hook), proposes smallest fix |
| `/qute-review` | Independent adversarial multi-agent code review; posts gate verdict (approve / request-changes) as a structured report |
| `/qute-coder` | Open a PR authored by the **qute-coder** GitHub App (qute-coder[bot]) — same args as `gh pr create`; makes the independent-reviewer gate pass by construction. Fail-loud if App creds are absent (never mis-attributes to your gh user) |
| `/qute-reviewer` | Post an INDEPENDENT verdict authored by the **qute-review** GitHub App (qute-review[bot]) via the dispatcher `/review` service (fallback: `qute-review-verdict` helper), and confirm a native review **object** was created — the review the gate requires |

## PR-flow enforcement (opt-in, default OFF)

The two skills above are always available and purely additive. On top of them, an **opt-in** PreToolUse
hook (`pr-flow-guard.py`) enforces the flow **per repo** — it is **inert by default**. A repo that merely
has qute-essentials installed behaves exactly as before (no block, no warning, no failure) until it opts in.

**Policy lives in a committed, tool-agnostic single source of truth: `.github/qute-pr.yml`** (read by BOTH
the client hooks / `/qute-coder` skill AND the CI review-gate). Copy `templates/qute-pr.yml` and edit:

```yaml
assignTo: tomlupo          # PR assignee + requested reviewer (default tomlupo)
independentReview: true    # auto-run the qute-review[bot] review in the /qute-coder chain
allowAgentSelfMerge: false # false → agent must NOT merge (assign to the human)
enforce: true              # turn on the blocking hooks + CI gate (default false = inert)
```

Keys may be flat (as above) or nested under a top-level `qutePrWorkflow:` mapping. Absent file/keys →
documented defaults (review on, assign tomlupo, self-merge off, enforce off) — nothing new fails.

When `enforce: true`, in that repo only, the hook:
- blocks `gh pr create` → directs you to `/qute-coder` (so the PR is authored by qute-coder[bot]);
- gates `gh pr merge` on `allowAgentSelfMerge`: `false` (default) blocks agent merge entirely
  (assign-to-human); `true` allows it only once a native **qute-review[bot]** review object exists
  (fail-open on ambiguity: if the PR can't be resolved it warns rather than blocking).

**Backward-compat (transition):** a repo that still has the legacy `{ "quteEnforcePrReview": true }` marker
in `.claude/settings.json` is honored as `enforce: true`. `.github/qute-pr.yml` is the primary home going
forward. Env overrides: `QUTE_ENFORCE_PR_REVIEW=1|0`.

### Optional CI gate

`templates/review-gate.yml` is a workflow template (NOT auto-added to any repo) that turns a missing
independent review into a red check. Install it into an opting-in repo on request:

```bash
mkdir -p .github/workflows && cp "$(claude plugin path qute-essentials)/templates/review-gate.yml" .github/workflows/review-gate.yml
```

(or copy the file from the plugin's `templates/` directory).

## Setup

```bash
# Install via Claude Code plugin system
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace

# Add API keys to ~/.claude/settings.json env block
# LAKERA_GUARD_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
```
