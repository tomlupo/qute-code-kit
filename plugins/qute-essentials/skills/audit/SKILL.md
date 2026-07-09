---
name: audit
description: Multi-scanner security audit for the current repo — dependency CVEs (pip-audit/OSV), secrets (gitleaks), and static analysis (semgrep), plus a deep repo-agnostic pass. Use when the user asks to audit dependencies, scan for vulnerabilities/CVEs/secrets, run a security scan, or says "is this secure", "any known issues", "check security", "deep security audit". Dep scan is Python-only; secrets/static/deep work on any repo. Also runs automatically (non-blocking) after `uv add/remove/sync/lock` and `pip install` via the auto_audit.py PostToolUse hook.
argument-hint: "[--secrets] [--static] [--deep] [--json]"
---

# /audit

Multi-scanner security audit of the current repo. Composes independent
scanners, each of which **graceful-degrades** when its binary is absent
(reported, never fatal):

| Scanner | Tool | Enabled by | Scope |
|---|---|---|---|
| `deps` | `pip-audit` via `uvx` (OSV) | default | Python dependency CVEs |
| `secrets` | `gitleaks` | `--secrets`, `--deep` | working-tree (or git history on `--deep`) secrets |
| `static` | `semgrep` | `--static`, `--deep` | static analysis findings |
| `hygiene` | pure-python | `--deep` | committed sensitive files (`.env`, keys, …) |

The dependency scan is Python-only (needs `pyproject.toml`). The
secrets/static/hygiene scanners are repo-agnostic — use `--no-deps` to run
them on a non-Python repo.

## Task

Pick the invocation, then summarize the output:

```bash
# default — dependency CVE scan only (original behaviour)
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/audit.py

# add secret / static scans
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/audit.py --secrets --static

# deep pass — deps + secrets (incl. git history) + static (security rulesets) + hygiene
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/audit.py --deep

# structured JSON for a conductor (Jimek) — one JSON line on stdout, logs on stderr
${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/audit.py --deep --json
```

Report:
- per-scanner status (ran / skipped-because-binary-absent / findings count)
- for dep vulns, a one-line summary: `<name> <version>: <CVE id> → fix in <version>`
- for secrets/static/hygiene, the file and rule of each finding
- the overall findings-by-severity totals

If there are dependency vulnerabilities, ask the user whether they want you to
upgrade the affected packages. Do NOT upgrade automatically.

If a scanner binary is absent, report it as skipped (do not treat it as an
error). The audit only fails hard (exit 2) when **no** scanner could run.

## Deep pass (`--deep`)

`--deep` is the portable, repo-agnostic deep security layer (folds the old
`/cso` deep-dive into a verb, not a rotation-bound script): dependency audit +
gitleaks over **git history** + semgrep with the `p/security-audit`,
`p/secrets` and `p/owasp-top-ten` rulesets + a pure-python sensitive-file
sweep. Iterate it across many repos with the inventory helper:

```bash
# enumerate git repos across core + forge (+ prod) from config, no hardcoded paths
${CLAUDE_PLUGIN_ROOT}/scripts/repo_inventory.py --json
```

`repo_inventory.py` resolves roots from (high→low) `--roots`, `$QUTE_AUDIT_ROOTS`,
`~/.config/qute/audit-inventory.json` (per-host `roots` + optional `ssh`
target for remote hosts), else the cwd. Remote hosts graceful-degrade if
unreachable. Feed each repo path to `audit.py --deep --json --path <repo>`.

## Structured return (`--json`)

Per the Jimek verb contract (`docs/playbooks/jimek-verb-contract.md`), `--json`
prints exactly one JSON object as the final stdout line (all human/progress
output goes to stderr):

```json
{"verb":"audit","ok":true,"mode":"deep",
 "findings":{"critical":0,"high":2,"medium":1,"low":0,"total":3},
 "scanners":{
   "deps":{"available":true,"ran":true,"ok":true,"findings":2,"severity":{...},"reason":""},
   "secrets":{"available":true,"ran":true,"ok":true,"findings":0,"severity":{...},"reason":""},
   "static":{"available":false,"ran":false,"ok":null,"findings":0,"severity":{...},"reason":"semgrep not on PATH"},
   "hygiene":{"available":true,"ran":true,"ok":true,"findings":1,"severity":{...},"reason":""}},
 "exit_code":1}
```

Exit codes: `0` ran + no findings · `1` ran + findings present · `2` no scanner
could run. `ok:false` only at exit 2.

## Auto-run behaviour

This skill also runs automatically (non-blocking, informational) after
`uv add`, `uv remove`, `uv sync`, `uv lock`, and `pip install` via the
`auto_audit.py` PostToolUse hook. Toggle off with `/guard audit off`.

## Gotchas

- **Low-severity CVEs (CVSS < 4.0)** are often safe to ignore if the vulnerable code path is never exercised — don't upgrade reflexively; check the CVE description first
- **Lock file vs. venv drift**: `pip-audit` scans the resolved lock file; if `.venv` is out of sync with `pyproject.toml`, results may be stale — run `uv sync` before auditing
- **Transitive dependency upgrades**: fixing a CVE by upgrading package A may break package B's version constraint — always run tests after any upgrade
- **False positives**: some CVEs affect only specific build configurations or platforms — verify the CVE applies to your usage before acting
- **No pyproject.toml**: the script exits with an error rather than scanning global packages — the skill is project-scoped by design
