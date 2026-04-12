---
name: audit
description: Scan the current Python project for dependency vulnerabilities via pip-audit (queries the OSV database for known CVEs). Use when the user asks to audit dependencies, check for vulnerabilities, scan for CVEs, or says "is this secure", "any known issues", "check security". Python-only in v1; webapps should use npm audit / yarn audit from the shell. Also runs automatically (non-blocking) after `uv add/remove/sync/lock` and `pip install` via the auto_audit.py PostToolUse hook.
argument-hint: ""
---

# /audit

Run a dependency vulnerability scan against the current Python project.
Uses `pip-audit` via `uvx` — queries the OSV database for known CVEs in
the resolved dependency set.

Python-only in v1. Webapps should use `npm audit` / `yarn audit` from the
shell.

## Task

Run exactly this, then summarize the output:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/audit.py
```

Report:
- the number of packages scanned
- how many (if any) have known vulnerabilities
- for each vulnerable package, a one-line summary: `<name> <version>: <CVE id> → fix in <version>`

If there are vulnerabilities, ask the user whether they want you to
upgrade the affected packages. Do NOT upgrade automatically.

If the script errors with "no pyproject.toml" or "uv not on PATH", report
the error verbatim and stop.

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
