# qute-essentials

Essential hooks, guards, and skills for Claude Code. Provides prompt injection screening, destructive command blocking, observability tracing, notifications, and utility skills.

## Guard System

Six security guards — toggleable via `/guard`. Three run PreToolUse (before execution), three run PostToolUse (scan after):

```
                     ┌──────────────────────────────┐
                     │   Tool call (any tool)        │
                     └──────────────┬───────────────┘
                                    │
     ┌──────────────── PreToolUse ──┴───────────────┐
     │                    │                         │
┌────▼──────────┐ ┌───────▼──────────┐  ┌───────────▼──────┐
│ Destructive   │ │  Secrets Guard   │  │ Provenance Guard │
│ Guard         │ │  blocks writes   │  │ tags shared-rec  │
│ blocks rm -rf │ │  with API keys   │  │ writes [agent:/  │
│ git reset -H  │ │                  │  │ session:]        │
└───────────────┘ └──────────────────┘  └──────────────────┘
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

### Provenance Guard (PreToolUse)

Stamps an identity tag on every automated write to a shared record, so `author != reviewer` is visible without any App (ADR-0006 §6/§7). Closes the one lane server-side stamping can't reach — direct MCP writes. Fires on:

- **Linear MCP** write verbs — `save_issue`, `save_comment`, `save_document`, `save_status_update` (both linear MCP server-name variants)
- **Bash** — `gh pr review|comment|create`

One resolution rule: `QUTE_AGENT_NAME` set → `[agent: <name>]`; otherwise `[session: <name-or-cwd-basename>]`. Behavior is **idempotent auto-inject** — a valid leading tag no-ops; otherwise the tag is prepended (via `hookSpecificOutput.updatedInput`, plus a non-blocking reminder for harnesses that don't apply it). Fail-safe: on unresolved identity it injects `[session: <cwd-basename>]` rather than block — this guard **never denies a write**. On by default.

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
/guard provenance off       # disable identity-tag auto-injection
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
| `auto_audit.py` | PostToolUse (Bash) | Runs `/audit` after `uv add` / `pip install` |
| `worktree_create.py` | WorktreeCreate | Creates native worktrees with the worktrees skill's `.claude/worktree.json` setup (shared_dirs, copy_files, venv, post-worktree.sh); setup failures fail creation loudly |
| `worktree_remove.py` | WorktreeRemove | Reaps the per-worktree venv (`$HOME/.venvs/<name>`) on worktree removal; refuses anything that isn't provably an unused venv strictly inside `~/.venvs` (logged to `~/.claude/qute-worktree-reap.log`) |

## `pre-push` branch guard (a git hook, not a Claude hook)

`templates/hooks/pre-push-branch-guard` refuses a push whose destination is a
guarded branch. `/setup-qute-repo` stamps it into opted-in repos via
`scripts/install_pre_push_guard.py`.

It sits at the git layer on purpose. An agent-side `PreToolUse` guard reads a
shell command string, so it never sees a human at a terminal or a script, and
inferring a push destination from a command line has an unbounded tail of shapes
(`git push origin HEAD`, `--repo=origin`, git aliases, `env VAR=x git push …` —
all real bypasses found in review). Git runs `pre-push` after alias expansion,
after `env`, after option parsing, and hands it the refs it is about to send.
Nothing to parse, nothing to infer, and it fires for humans, scripts and agents
alike.

- **Opt-in and config are shared with the agent-side guard** —
  `.claude/git-guard.json` in the repo root, same fields, same defaults, so the
  two layers can never disagree about which branches are guarded. No file = both
  are a no-op for that repo.
- **Install:** `python3 scripts/install_pre_push_guard.py --repo . [--opt-in]
  [--adopt-existing]`. It resolves the path git will actually use
  (`git rev-parse --git-path hooks/pre-push`, which honours `core.hooksPath`),
  installs there, never clobbers an existing `pre-push` — with
  `--adopt-existing` it chains it from `pre-push.d/` instead — and then drives
  the installed hook through that same path with synthetic ref lines to prove it
  is reachable. `--check` verifies without installing.
- **It always takes the native hook path, never the pre-commit framework's
  `pre-push` stage.** The framework drops ref lines whose local sha is all zeros
  before running any hook (so branch *deletions* never reach the guard) and
  exposes only the first pushable ref of a multi-ref push. That is a fine
  tradeoff for a convenience hook and not for the layer whose whole job is that
  it holds, so `auto` never selects it. A repo that already uses pre-commit
  keeps working: its generated shim is relocated to `pre-push.d/50-pre-commit`
  and runs behind the guard with the ref lines replayed to it.
  `--mechanism pre-commit` remains for a repo that genuinely cannot take the
  native slot — and there verification **fails** on the coverage it cannot
  provide rather than warning, so nobody is told they are protected when they
  are not.
- **A later `pre-commit install --hook-type pre-push` reclaims the slot** and
  moves the dispatcher to `<slot>.legacy` — which pre-commit's shim runs first
  with the raw stdin, ORing its exit code into its own, so full coverage
  survives (measured, not assumed; see the test suite).
- **Residual risk you should know about: `pre-commit install -f --hook-type
  pre-push` DELETES `<slot>.legacy`, which silently uninstalls this guard.**
  Nothing here can prevent that — pre-commit owns the `-f` semantics and it runs
  long after onboarding. What the installer can do is detect it, so **re-run
  `--check` after any forced pre-commit install**, and treat a `NOT OK` there as
  "the safety net is gone", not as a cosmetic warning. This is exactly the kind
  of thing that quietly stops protecting a repo months later.
- **A hook path that resolves outside the repository is refused by default** —
  judged on the resolved path, never on which config scope named it. A
  repo-local `core.hooksPath = /home/me/.githooks` or `../shared-hooks` is
  exactly as shared as a global one: every repo pointed at that directory gets
  the same file, and the second repo "installed" silently inherits the first
  one's hook. `--allow-shared-hooks-path` accepts that deliberately; the refusal
  names the resolved path, the repo it is not inside, the config file that set
  it, and anything already sitting in that directory.
- **`git push --no-verify` bypasses it.** That is the contract of a client-side
  hook and it is what makes it safe to install: it catches the accidental push
  and yields to the deliberate one. It is **not** a substitute for server-side
  branch protection — it exists because protection is unavailable on these
  repos' plan.
- **Fails open, loudly.** An internal error prints a `QUTE_PRE_PUSH_GUARD:
  internal error …` warning and allows the push — a guard bug must not wedge
  every push in a repo, but it must never be silent about stepping aside.

## Notifications

Push notifications via [ntfy.sh](https://ntfy.sh). Config in `config/ntfy.json` (`server` + `topic`).

The guards resolve the endpoint from `ntfy.json`; leave `topic` empty to auto-derive `{hostname}-{username}-claude` (e.g., `core-tom-claude`), or set it explicitly to override. Subscribe in the ntfy app to receive alerts for:
- Destructive command blocks
- Prompt injection detections

## Skills

| Skill | Description |
|-------|-------------|
| `/guard` | Toggle any of the 6 security guards on/off, check status |
| `generating-commit-messages` | Conventional Commits guidance (auto-applied before any `git commit`) |
| `/decision` | Record architecture decisions as ADRs with auto-numbering |
| `/handoff` | Prepare session handoff document (captures context, ADRs, TASKS) |
| `/pickup` | Resume work from a previous handoff |
| `/ship` | Cut a release — auto-detects Plugin mode (`marketplace.json`) or Python mode (`pyproject.toml`). Auto-runs first-time setup (commitizen + CHANGELOG + workflow) on Python projects |
| `/task` | Add or close a task — tiered: manages `TASKS.md` by default, graduates to GitHub Issues once the list earns it; proposes migration once |
| `/repo-status` | Git/worktree dashboard **plus** a read-only Open tasks glance at the repo's active store — `TASKS.md` (Tier 1) or GitHub Issues via `gh` (Tier 2), auto-detected |
| `/board` | Linear board write-identity conventions (ADR-0003/0006): interactive sessions write via the Linear MCP tagged `[session:]`; agents/crons via `linear-post` → dispatcher `:8002/post` tagged `[agent:]` |
| `/audit` | Dependency vulnerability scan (Python, via pip-audit/uvx) |
| `/test` | Run test suite, interpret failures, propose fixes |
| `/worktrees` | Manage git worktrees for parallel development |
| `/readme` | Generate or update README files |
| `/gbu` | Good/bad/ugly structured code or design review |
| `/wtf` | Activated on frustration/pushback — captures failure, applies three guardrail tiers (feedback memory + CLAUDE.md rule + hook), proposes smallest fix |
| `/qute-review` | The shared review core (ADR-0005): Matt-review-base + quant layer, adversarial failure-class framing (`review-core.md`), cross-model via codex; posts the native GitHub review verdict the gate requires. Same core drives jimek's autonomous reviewer |

## PR governance (ADR-0005: tier or rules, no policy file)

There is **no per-repo PR policy file and no blocking client hook** — `.github/qute-pr.yml` and
`pr-flow-guard.py` were deleted (qute-code-kit ADR-0005). Merge/PR governance is:

- **Jimek-managed repos** — the rigor **tier** in `conductor.yml` is the sole merge authority
  (trivial = auto-merge, standard = self-merge on SHIP, complex = human merges). The conductor
  stamps `jimek-tier:*` labels on managed PRs; the review-gate CI reads them.
- **Standalone repos** — `.claude/rules` (stamped by `/setup-qute-repo`) states the expectations;
  the review-gate CI enforces "get an independent review"; a human merges.

### Optional CI gate (tier-aware)

`templates/review-gate.yml` is a workflow template (NOT auto-added to any repo) that turns a missing
independent review into a red check — **installing the file is the opt-in** (no policy file). It is
tier-aware: `jimek-tier:trivial` passes with no review; `standard`/`complex`/no-label require an
independent review object. Install it into an opting-in repo on request:

```bash
mkdir -p .github/workflows && cp "$(claude plugin path qute-essentials)/templates/review-gate.yml" .github/workflows/review-gate.yml
```

(or copy the file from the plugin's `templates/` directory).

The same workflow carries a second job, **`audit-sensitive-paths`** — on a PR that
touches security-sensitive files (`pyproject.toml`, `uv.lock`, `requirements*.txt`,
`.github/workflows/**`, `**/hooks/**`, `Dockerfile*`, `.env*`, `**/*.py`) it runs the
deterministic `audit` verb: **gitleaks (`--secrets`) hard-fails** the check (a leaked
secret must block merge) while **semgrep (`--static`) is annotate-only** (advisory, to
avoid false-positive merge blocks). Installing the workflow opts the repo into this job too.

### Optional release/lock guards

Two more opt-in workflow templates, stamped the same way (`/setup-qute-repo` Step 9, or copy from
`templates/` by hand). Both stay **silent in repos they don't apply to** — `release-tag-guard`
only fires on a pushed `v*` tag, `lockfile-check` passes with no `uv.lock` — so installing them
costs nothing. Where they *do* apply they are fail-closed, not best-effort:

- **`templates/release-tag-guard.yml`** — fires on a pushed `v*` tag, two jobs:
  - `tag-on-release-branch` asserts the tagged commit is an **ancestor of the release branch**
    (`git merge-base --is-ancestor`). This is the check a version-string guard cannot make: a tag
    cut on an integration branch whose PR is then **squash-merged** points at a commit the release
    branch never contains, so anything pinning the tag installs code that was never released.
    Requires `fetch-depth: 0` (the template sets it) and refuses to pass on a shallow clone, a
    missing branch ref, or a `merge-base` error — a vacuous pass is worse than no check.
    The release branch comes from the `RELEASE_BRANCH` job env; **leave it empty** and the repo's
    GitHub default branch is used. Set it only when `conductor.yml`'s `release.branch` differs.
  - `version-matches-tag` asserts the declared version strings equal the tag, reading commitizen's
    own `[tool.commitizen] version_files` + `tag_format` instead of hardcoded paths. **A declared
    version is always asserted.** The job passes without checking anything only when the repo
    declares no version at all: no `pyproject.toml`, or a `pyproject.toml` with no readable
    version string anywhere. A missing `[tool.commitizen]` block is *not* that case — it only
    means no `version_files` are declared, and `[project].version` is still checked against the
    tag (a hand-cut tag on a repo whose static `[project].version` was never bumped is exactly
    what this job is for). And a `version_files` entry that IS declared but cannot be read —
    missing path, unreadable file, uncompilable pattern, no parseable version literal — **fails**
    the job by name: skipping one and reporting success is the same vacuous pass the ancestry job
    refuses.
- **`templates/lockfile-check.yml`** — runs `uv lock --check` on PRs and pushes, failing when
  `uv.lock` is out of step with `pyproject.toml`. A project's own version is recorded in its
  lockfile, so every `/ship` bump staleness the lock and nothing else notices. No `uv.lock` → the
  job reports the absence and passes. (`--check` = staleness; `--check-exists` = presence only.)

### Event-driven security audit (3 layers)

The `audit` verb is wired to run by *change*, not by calendar (obsidian-vaults#167):

1. **On-change** — `auto_audit.py` runs the fast deps-only scan after `uv add/remove/sync/lock` + `pip install/uninstall`.
2. **On-PR** — the `audit-sensitive-paths` CI job above (`--secrets` hard-fail, `--static` advisory).
3. **Weekly deep sweep** — `scripts/deep_sweep.py` runs `audit --deep` over the **local-host**
   repos from `templates/audit-inventory.json` (install to `~/.config/qute/audit-inventory.json`),
   **live-capital first** (`priority` key), and writes a one-table report. LLM-free; a
   single cron replaces the old daily round-robin. (Remote ssh hosts are reported unscanned —
   run the sweep on each host; the verb is portable.)

```bash
# weekly sweep, priority repos first, report to a dir
python3 "$(claude plugin path qute-essentials)/scripts/deep_sweep.py" \
  --config ~/.config/qute/audit-inventory.json --report ~/audit-reports
```

## Setup

```bash
# Install via Claude Code plugin system
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace

# Add API keys to ~/.claude/settings.json env block
# LAKERA_GUARD_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL
```
