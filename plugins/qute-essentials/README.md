# qute-essentials

Essential hooks, guards, and skills for Claude Code. Provides prompt injection screening, destructive command blocking, observability tracing, notifications, and utility skills.

## Guard System

Seven security guards — toggleable via `/guard`. Four run PreToolUse (before execution), three run PostToolUse (scan after):

```
                     ┌──────────────────────────────┐
                     │   Tool call (any tool)        │
                     └──────────────┬───────────────┘
                                    │
   ┌───────────────── PreToolUse ───┴──────────────────────┐
   │                │                  │                   │
┌──▼────────────┐ ┌─▼────────────┐ ┌───▼──────────────┐ ┌──▼───────────────┐
│ Destructive   │ │ Git Workflow │ │  Secrets Guard   │ │ Provenance Guard │
│ Guard         │ │ blocks direct│ │  blocks writes   │ │ tags shared-rec  │
│ blocks rm -rf │ │ commit/push  │ │  with API keys   │ │ writes [agent:/  │
│ git reset -H  │ │ on main/dev  │ │                  │ │ session:]        │
└───────────────┘ └──────────────┘ └──────────────────┘ └──────────────────┘
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

### Git Workflow Guard (PreToolUse)

> **An agent-side speed bump, not enforcement.** It has to be right about two things — the *command* (what git verb, what destination) and the *environment* (which repo and branch git will actually act on) — and it targets *ordinary invocation forms*, within which a miss on either is a defect. But it reads a shell string and sees Claude tool calls only, so it cannot resist deliberately constructed evasion. **`pre-push` (TOM-348) is the enforcement layer.** Read [What this covers](#what-this-covers--and-the-line-that-decides-it) below before relying on it for anything.

A nudge for repos where GitHub branch protection isn't available (private repos on the Free plan). Aims at one class of mistake: a direct `git commit` / `git push` onto a branch that work is supposed to reach through a PR.

Two branches are guarded, and denial applies to both:

| | Default | Notes |
|---|---|---|
| `protected_branch` | `main` | the release branch |
| `integration_branch` | `dev` | **only if `origin/dev` exists** in that repo |

The integration branch is guarded for the same reason as the protected one: that's where the review gate lives. Work arrives via a PR; a direct commit opens no PR, so it runs neither review nor CI.

**Opt in per repo** by committing `.claude/git-guard.json`. The *presence* of that file is the opt-in — with no file the guard is a total no-op for that repo, which is what keeps it out of scratch repos and third-party clones. Every field is optional, so a repo that wants house defaults can commit `{}`:

```json
{
  "protected_branch": "main",
  "integration_branch": "dev",
  "release_tool": "commitizen (/ship)"
}
```

An explicit `"integration_branch": null` means *this repo genuinely has none* (feature → PR → `main`) and is never overridden by the `dev` default. `release_tool` only feeds the guidance text.

**Dry runs are never blocked.** `git commit --dry-run` and `git push --dry-run`/`-n` write nothing. Note `git commit -n` is `--no-verify` — a *real* commit — and stays blocked; option values are skipped, so `git commit -m --dry-run` is a real commit too.

**Tag pushes are never branch pushes.** `--tags` with no refspec sends tags and nothing else, so the current-branch fallback doesn't fire; `git push origin tag <name>` is `refs/tags/<name>` even when the tag is called `main`. `--follow-tags` is the opposite — a normal branch push plus reachable tags — and keeps the fallback.

**A push with no refspec is resolved from config, not assumed to be the current branch.** Git consults `remote.<name>.push` first, then `push.default` — and `upstream`/`tracking` send the push to `branch.<cur>.merge`, which is `main` for any branch created with `git checkout -b feat/x origin/main`. `matching` is unresolvable (it pushes every branch that exists on both sides) and therefore **denied**; `nothing` pushes nothing; `simple`/`current` mean the same-name branch.

**Push destinations are resolved, not string-matched.** `git push origin HEAD` (and `@`) resolves to the branch you are standing on, a `+` force sigil and a `refs/heads/` prefix are stripped, and in `src:dst` only `dst` counts — so `HEAD`, `@`, `+main`, `refs/heads/main`, `HEAD:refs/heads/main` and `:main` are all recognised as the protected branch. A destination the guard *cannot* resolve — an unexpanded `$BRANCH`, a glob refspec (`refs/heads/*:refs/heads/*`), ref navigation (`@{-1}`, `HEAD~1`, `main^`), an empty dst (`main:`), or `HEAD` on a detached HEAD — is **denied**, not allowed: a check that cannot verify must not report success.

Each git command in a chain is scoped to the repo it actually targets — `cd <other> && git commit`, `(cd <other> && git commit)`, `git -C <other> commit` and `git --git-dir=<other>/.git commit` all resolve to that repo's branch and config, not the session's. `-C` and `--git-dir` **compose** in git's documented order — `-C` moves the cwd first (whatever order they appear in), then `--git-dir` names the repo, with a relative git dir resolved against the `-C` directory. Equally, the repo does *not* move where git and the shell don't move it either:

- a `cd` to a directory that **doesn't exist** — it fails, so the shell stays put and the guard stays with it. A `cd` whose operand the guard *can't expand* (`cd "$MAIN_REPO"`, `cd $(…)`, `cd repo-*`, `cd -` with no prior `cd`) is a third case: the location becomes **unknown**, and a `git commit`/`git push` that still depends on the cwd is then **denied** rather than guessed at. `~` and a bare `cd` are expanded, not guessed;
- **`--work-tree` without `--git-dir`** — git identifies a repo by its git dir and still discovers `.git` from the current directory, so `git --work-tree ../scratch commit` commits *here*;
- a `cd` **inside `( … )`** — it dies with the subshell, so a command after the `)` is back in the original repo. Brace groups (`{ …; }`) run in the current shell and their `cd` does persist.
- a `cd` in a **pipeline element** or before a **`&`** — bash runs those in their own process, so the `cd` dies with it. `;`, `&&` and `||` keep the shell in one process and do propagate.
- a `cd` behind an assignment or a `command`/`builtin` wrapper **does** move the shell and is followed; `env cd` and `exec cd` look up a nonexistent external `cd`, fail, and are not.
- a `cd` bash **skips**. A `cd` is the one command whose exit status the guard can compute, so `&&`/`||` short-circuiting is modelled: `cd /missing && cd other` never applies the second `cd`, and `cd other || git commit` never reaches the commit. An unknown status (any non-`cd` command) leaves both branches live.

A path operand the guard **can't expand** — `cd "$D"`, `git -C "$D"`, `git --git-dir="$D/.git"`, a glob, a command substitution — makes the target **unknown**, not "a literal directory of that name". Guarded verbs then fail closed; read-only ones are untouched, and any later *absolute literal* operand re-anchors the target and clears it. Command substitutions are treated as opaque parts of a word, never as command boundaries.

Here-doc bodies (`cat <<EOF … EOF`) are skipped as data, not parsed as commands — the terminator must match exactly, with `<<-` allowing leading tabs; `<<<` is a here-string and is left alone. `command -v`/`-V` is a lookup, not an invocation. Redirections are stripped wherever they appear — before the command word (`>/tmp/out git commit`) or after it (`git push origin >main`, where `main` is a *filename*) — and `2>&1` / `>|file` are read as redirection syntax rather than as a background `&` or a pipe. The segment scan is quote-aware, so a `)` or a `;` inside `git commit -m "done)"` is text, not syntax. Shell reserved words that stand in front of a command are peeled before parsing it, so `if …; then git commit; fi`, `while …; do git push origin main; done`, `! git …` and `time git …` are read as the git commands they contain.

**Never prompts.** The decision is always allow or deny, never `ask`, and the guard never reads `permission_mode`. A hook that asks renders an interactive confirmation, and in a *backgrounded* agent session that stalls the worker at `waiting/blocked` until a human attaches — and the payload can't distinguish that from a headless run that would block cleanly (both report `permission_mode: "auto"`). The escape hatch is therefore the visible, deliberate toggle: `/guard git-workflow off`.

The remote is read from `--repo <r>` / `--repo=<r>` when given, so every positional is treated as a refspec rather than one being swallowed as the remote. Git actually *ignores* `--repo` once a positional repository is also given, and the two readings can't be told apart without knowing the repo's remotes — so with a single positional both are honoured: every positional is checked as a refspec, the current-branch fallback stays alive, and the no-refspec config lookup runs against **both** candidate remotes.

**Git is matched on the normalised name of the executable, and wrappers are peeled first.** The name is the basename, lowercased, with a Windows `.exe` suffix stripped — so `/usr/bin/git`, `git.exe` and `/mingw64/bin/git.exe` all count. `command git push`, `exec git commit`, and `env GIT_AUTHOR_NAME=x git commit` (including `/usr/bin/env`, `-i`, `-u NAME`, and `-C dir`, which scopes the target repo exactly like git's own `-C`) all resolve to the git command underneath. A wrapper whose command can't be pinned down — `env -S`/`--split-string`, or any wrapper option the parser doesn't know, since a new option could swallow the token we'd read as `git` — is **denied**, not allowed. Lookalikes (`gitk`, `git-secret`) are correctly excluded.

**An unrecognised subcommand is resolved one level as an alias** — from `-c alias.<name>=<expansion>` on the command line first (git prefers it over config, and so does the guard), then `git config --get alias.<name>` in the *target* repo — so `git ci` and `git publish` are read as the `commit`/`push` they expand to. The lookup is gated on the subcommand being unrecognised *and* the repo being opted in, so ordinary commands cost nothing. Resolution is deliberately **non-recursive**: an alias that expands to another alias, or to a `!shell` command, is **denied** rather than chased — chasing either re-opens exactly the unbounded-parser problem below. That over-denies a `!git status` alias in an opted-in repo; `/guard git-workflow off` is the escape hatch.

**Option arity is modelled, because a value in the next token shifts every positional after it.** For `git push` that's `-o`, `--push-option`, `--receive-pack`, `--exec` and `--recurse-submodules`; for git's global options `-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace`, `--super-prefix`, `--attr-source`, `--config-env`. A global whose arity *isn't* modelled is only acted on when it leaves the subcommand unidentifiable (neither a builtin nor an alias) — then it's **denied**, so `git --literal-pathspecs status` and `git -p log` still cost nothing.

**`--all` / `--mirror` push every local branch** and override `push.default`, so their destinations are the local branch list — denied when a guarded branch is in it, allowed when it isn't, and denied if the list can't be read. (This used to be a "deliberate gap", caught only from a guarded branch. It isn't one: it's an ordinary invocation that writes the protected branch from anywhere.)

Fail-open by design: no config, malformed config, a non-git directory, or any internal error all allow. One deliberate gap remains: a switch-then-act chain (`git checkout main && git commit`) reads the *current* branch and isn't caught. `/ship` needs no exemption — its git calls run inside a Python subprocess no PreToolUse hook observes, and its tag push carries a tag refspec, not a branch.

#### What this covers — and the line that decides it

The guard answers one question: **will this command write to a guarded branch?** It can be wrong about that on two independent axes, and a defect on **either** is in scope, because both end the same way — it evaluates a context that isn't the one git is about to act in, and says yes.

- **The command (parsing)** — *what* is being run, and against which destination. `/usr/bin/git commit`, `env VAR=x git commit`, `command git push`, a `git ci` alias, `git push origin HEAD`, an option whose arity shifts the positionals.
- **The environment (context)** — *which* repo and branch git will actually act on. Nothing to do with how the command is written; it's about whether the guard's model of the world matches the shell's and git's. A `cd` that **fails** leaves the shell where it was; `--work-tree` without `--git-dir` leaves the **repo** where it was; a `cd` inside `( … )` moves the shell only until the `)`. All three looked like ordinary commands and all three let a direct commit on a guarded branch through, because the guard went looking somewhere else.

An environment-axis defect is in scope however ordinary the command looks. The "ordinary invocation forms" line below bounds the **first** axis only, and is about the kind of command, not the kind of bug.

On the parsing axis the target is **ordinary invocation forms**: what a person or an agent actually types or scripts. Within that target the guard is meant to be correct, and a miss is a **defect**.

It is **not**, and cannot be, resistant to **deliberately constructed evasion**. It reads a shell string, and git's command-line surface is unbounded; no amount of parsing closes that. That distinction is the line, and a new finding can be placed on one side of it without asking anyone:

- **In scope** — a shape someone would plausibly write without trying to evade anything (all the parsing examples above). These are defects; fix them.
- **Out of scope** — a shape that only occurs when someone is routing around the guard on purpose. Anyone doing that also has `--no-verify`, git behind a shell variable or a here-doc, a wrapper script, or simply their own terminal. Hardening the parser against them buys nothing, and `pre-push` is the layer that answers them.

There is no equivalent escape clause on the environment axis: "the command was weird" never excuses evaluating the wrong repo.

So: a **speed bump, not enforcement** — but with a criterion, not a shrug.

Two limits are structural rather than defects, and neither has a fix in this hook:

- **It observes Claude tool calls only.** A human typing in their own terminal, a Makefile target, a CI job, or any script an agent launches that shells out to git internally are all invisible to it — no PreToolUse hook ever sees them.
- **Its opt-in gate needs a repo it can name.** When a `cd` leaves the location unknown, the fail-closed deny is gated on the *last known* directory being opted in — so `cd "$MAIN_REPO" && git commit` started from a scratch repo that never opted in stays a no-op even if `$MAIN_REPO` expands into a guarded one. Closing that would mean denying on every unexpandable `cd` in every repo on the machine, ending the opt-in contract that keeps this hook out of scratch repos and third-party clones. `pre-push` is installed *in* the guarded repo, so it has no such gap.
- **Its knowledge of git's option arity is a table, and git's surface grows.** A *future* value-taking `git push` option would shift the positionals the way `--recurse-submodules` did. The global-option case has a backstop; the push-option case has none, because the only available one — re-arming the current-branch fallback whenever an unknown option appears — would false-block ordinary pushes of an unguarded refspec from a guarded branch.

Defects review has found, **all now handled** — kept as evidence the tail is real, not as a checklist that's complete. 1–9, 14, 15, 19–21, 23, 24 and 27–32 are parsing; 10–13, 16–18, 22, 25 and 26 are the environment axis, and are why that axis is written down at all. Most let something *through*; 24, 27 and 29–32 **blocked** something they shouldn't have, which is a defect on the same footing — a guard that cries wolf gets turned off:

| # | Axis | Defect | What went wrong |
|---|---|---|---|
| 1 | parsing | bare `HEAD` | compared as the literal `"HEAD"`, never equal to `main` |
| 2 | parsing | unresolvable refspecs | were allowed rather than denied |
| 3 | parsing | `--repo <remote>` | supplies the remote, so every positional is a refspec — `git push --repo=origin main` parsed as "no refspec at all" |
| 4 | parsing | the `env` wrapper | `env GIT_AUTHOR_NAME=x git commit`, bare `env git push origin main` |
| 5 | parsing | git aliases | `git ci`, `git publish` — neither the literal `commit` nor the literal `push` |
| 6 | parsing | push-option arity | `git push --recurse-submodules on-demand origin` read `on-demand` as the remote and `origin` as a harmless explicit refspec |
| 7 | parsing | global-option arity | `git --namespace foo commit -m x` read `foo` as the subcommand |
| 8 | parsing | the executable form | `/usr/bin/git commit`, `command git commit` — only `tokens[0] == "git"` had ever matched |
| 9 | parsing | `-c alias.ci=commit` | an alias defined on the command line, invisible to a repo-config lookup |
| 10 | environment | a failing `cd` | `cd /gone ; git commit` and `cd /gone \|\| git commit` run the commit in the original repo, but the guard followed the dead path into a non-repo |
| 11 | environment | `--work-tree` without `--git-dir` | git still uses the current repo's `.git`, but the guard treated the work tree as the repo |
| 12 | environment | subshell grouping | `(cd ../other && git commit)` was evaluated against the original repo — the segment splitter dropped `(` and `)` instead of scoping the working directory to them |
| 13 | environment | `-C` + `--git-dir` | `-C` was treated as overriding `--git-dir`, but git applies `-C` to the cwd and still lets `--git-dir` pick the repo, so `git -C ../feature --git-dir=/repo-on-main/.git commit` was evaluated against `../feature` |
| 14 | parsing | shell control flow | reserved words sit in front of the command they introduce, so `if …; then git commit; fi` tokenized as `["then", "git", …]` and never registered as a git command |
| 15 | parsing | the Windows spelling | `git.exe commit`, `/mingw64/bin/git.exe push origin main` and any case variant matched neither the executable check nor the `"git" in command` fast path |
| 16 | environment | an unexpanded `cd` operand | `cd "$MAIN_REPO" && git commit` was read as a *failed* `cd`, so the guard kept evaluating the current repo while bash expanded the variable and committed elsewhere |
| 17 | environment | where a refspec-less push goes | `git push` was read as "the current branch", but `push.default=upstream` and a configured `remote.<name>.push` send it to `main` from a feature branch tracking `origin/main` |
| 18 | environment | pipelines and `&` | bash runs each pipeline element, and any command ended by `&`, in its own process — so `cd other \| git commit` commits in the original repo, but `\|` was treated like `;` and the `cd` leaked |
| 19 | parsing | `--repo <r>` as two tokens | the value was skipped rather than captured, so the no-refspec fallback read the default remote's `push` refspec instead of `<r>`'s |
| 20 | parsing | `--all` / `--mirror` | they push every *local* branch and override `push.default`, so `git push --all origin` from a feature branch writes the protected branch with nothing on the command line naming it |
| 21 | parsing | the `--repo` ambiguity, half-handled | the positionals were read under both meanings, but the *config* lookup still used the `--repo` value — so `git push --repo=origin upstream` consulted `remote.origin.push` while git pushed to `upstream` |
| 22 | environment | an unexpanded `-C` / `--git-dir` operand | defect 16 one operand over — `git -C "$MAIN_REPO" commit` was read as a literal directory of that name, found not to be a repo, and allowed |
| 23 | parsing | command substitutions as boundaries | `$( … )` is part of a word, but both the segment scanner and `shlex` broke it apart, so `git -C $(cat path) commit` stopped being recognised as a git command |
| 24 | parsing | tag pushes read as branch pushes | `git push --tags origin` sends tags and *no* branch, and `git push origin tag <name>` is `refs/tags/<name>` — both were read as branch destinations and blocked from a guarded branch, falsifying the claim below and breaking `/ship` |
| 25 | environment | `&&` / `\|\|` short-circuit | a `cd` bash *skips* was applied anyway, so `cd /missing && cd ../feature ; git commit` evaluated `../feature` while the commit really happened in the original, guarded repo |
| 26 | environment | a wrapped `cd` | `FOO=1 cd /guarded`, `command cd /guarded` and `builtin cd /guarded` all move the shell, but only a bare `cd` was recognised |
| 27 | parsing | dry runs treated as writes | `git commit --dry-run` and `git push --dry-run`/`-n` write nothing, yet were blocked |
| 28 | parsing | redirections | bash allows them anywhere: `>/tmp/out git commit` left the redirection as token 0 so the segment stopped looking like git, and `git push origin >main` counted the *filename* as a refspec, suppressing the current-branch fallback |
| 29 | parsing | `builtin git` | `builtin` runs only shell builtins, so git never runs — it was in the run-wrapper list anyway and got denied |
| 30 | parsing | here-doc bodies | `cat <<EOF … EOF` feeds its body to stdin, but newline splitting turned every line into a command, so a `git commit` line inside one could be blocked |
| 31 | parsing | the here-doc terminator | bash needs an exact match (`<<-` strips only leading tabs); comparing a stripped line closed the body early on an indented ` EOF` and handed the rest of the data back as commands |
| 32 | parsing | `command -v` | it looks a name up and prints it, running nothing, but the flag was skipped and `command -v git commit` read as a commit |

**`pre-push` is the actual enforcement layer** (TOM-348, being built in parallel). Git invokes `pre-push` with the real local/remote refs it's about to send — after alias expansion, after `env`, after every shell trick, and regardless of who or what ran the command. It needs no command-line parser, it is handed the repo it is running in rather than inferring it, so neither axis exists at that layer, and it covers a human's own pushes too.

The two are **complementary, not redundant**: this hook gives an agent immediate feedback and a message naming the right route before the command runs; `pre-push` is what holds. Anyone tempted to harden this parser against the out-of-scope side of the line should land TOM-348 instead.

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
/guard git-workflow off     # allow direct commit/push on protected + integration branches
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

## Notifications

Push notifications via [ntfy.sh](https://ntfy.sh). Config in `config/ntfy.json` (`server` + `topic`).

The guards resolve the endpoint from `ntfy.json`; leave `topic` empty to auto-derive `{hostname}-{username}-claude` (e.g., `core-tom-claude`), or set it explicitly to override. Subscribe in the ntfy app to receive alerts for:
- Destructive command blocks
- Prompt injection detections

## Skills

| Skill | Description |
|-------|-------------|
| `/guard` | Toggle any of the 7 security guards on/off, check status |
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
