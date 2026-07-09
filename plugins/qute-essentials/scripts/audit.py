"""/audit — multi-scanner security audit for the current project.

Deterministic, repo-agnostic security scanning. Composes independent scanners,
each of which **graceful-degrades** when its binary is absent (reported, never
fatal):

  deps     — pip-audit via uvx (OSV database; Python dependency CVEs)   [default]
  secrets  — gitleaks (working-tree secret detection)          [--secrets/--deep]
  static   — semgrep (static analysis; --config auto)           [--static/--deep]
  hygiene  — pure-python sensitive-file + git-history secret sweep       [--deep]

Modes:
  (no flags)   deps only — identical to the original v1 behavior.
  --secrets    add the gitleaks secret scan.
  --static     add the semgrep static scan.
  --deep       heavier repo-agnostic pass: deps + secrets + static (deeper rule
               configs) + hygiene. Folds the /cso deep-dive into a portable verb.
  --no-deps    skip the dependency scan (e.g. secrets-only on a non-Python repo).

Structured return (Jimek verb contract, docs/playbooks/jimek-verb-contract.md):
  --json       print EXACTLY ONE JSON object as the final stdout line; all human
               and progress output goes to stderr. Carries findings-count by
               severity, per-scanner status, and the exit code.

Exit codes:
  0 — audit ran; no findings.
  1 — audit ran; one or more findings.
  2 — audit could not run at all (no scanner was able to execute).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------- #
# output helpers — respect --json (human text must not pollute stdout there)
# --------------------------------------------------------------------------- #

_JSON_MODE = False


def _out(msg: str = "") -> None:
    """Human/progress line. Goes to stderr under --json, else stdout."""
    print(msg, file=sys.stderr if _JSON_MODE else sys.stdout)


def info(msg: str) -> None:
    _out(f"audit: {msg}")


def warn(msg: str) -> None:
    print(f"audit: warning: {msg}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# severity taxonomy
# --------------------------------------------------------------------------- #

SEVERITIES = ("critical", "high", "medium", "low")


def _empty_counts() -> dict[str, int]:
    counts = {s: 0 for s in SEVERITIES}
    counts["total"] = 0
    return counts


def _scanner_result(
    *,
    available: bool,
    ran: bool,
    ok: bool | None,
    findings: int = 0,
    severity: dict[str, int] | None = None,
    reason: str = "",
    details: list | None = None,
) -> dict:
    return {
        "available": available,
        "ran": ran,
        "ok": ok,
        "findings": findings,
        "severity": severity or {s: 0 for s in SEVERITIES},
        "reason": reason,
        "details": details or [],
    }


def _degraded(reason: str) -> dict:
    """A scanner that could not run because its binary is missing."""
    return _scanner_result(available=False, ran=False, ok=None, reason=reason)


# --------------------------------------------------------------------------- #
# deps — pip-audit via uvx (OSV)
# --------------------------------------------------------------------------- #


def run_deps(root: Path) -> dict:
    if not (root / "pyproject.toml").exists():
        return _scanner_result(
            available=True,
            ran=False,
            ok=None,
            reason="no pyproject.toml (Python dependency scan skipped)",
        )
    if not shutil.which("uv"):
        return _degraded("uv not on PATH — install uv to run pip-audit via uvx")

    cmd = ["uvx", "pip-audit", "--format", "json", "--progress-spinner", "off"]
    info(f"deps: running `{' '.join(cmd)}`")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, cwd=root
        )
    except FileNotFoundError:
        return _degraded("uvx not available")
    except subprocess.TimeoutExpired:
        return _scanner_result(
            available=True, ran=False, ok=False, reason="pip-audit timed out (180s)"
        )

    if result.returncode not in (0, 1):
        if result.stderr and result.stderr.strip():
            warn(result.stderr.strip().splitlines()[-1])
        return _scanner_result(
            available=True,
            ran=False,
            ok=False,
            reason=f"pip-audit exit {result.returncode}",
        )

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return _scanner_result(
            available=True, ran=False, ok=False, reason="unparseable pip-audit output"
        )

    deps = data.get("dependencies", [])
    vulnerable = [d for d in deps if d.get("vulns")]
    severity = {s: 0 for s in SEVERITIES}
    details = []
    for dep in vulnerable:
        for v in dep.get("vulns", []):
            severity["high"] += 1  # dep CVE without CVSS → treat as high
            details.append(
                {
                    "package": dep.get("name", "?"),
                    "version": dep.get("version", "?"),
                    "id": v.get("id", "?"),
                    "aliases": v.get("aliases", []),
                    "fix_versions": v.get("fix_versions", []),
                    "severity": "high",
                }
            )
    count = len(details)
    info(f"deps: scanned {len(deps)} packages, {count} vulnerability(ies)")
    return _scanner_result(
        available=True,
        ran=True,
        ok=True,
        findings=count,
        severity=severity,
        details=details,
    )


# --------------------------------------------------------------------------- #
# secrets — gitleaks
# --------------------------------------------------------------------------- #


def run_secrets(root: Path, deep: bool = False) -> dict:
    if not shutil.which("gitleaks"):
        return _degraded("gitleaks not on PATH — install gitleaks to scan for secrets")

    with tempfile.NamedTemporaryFile(
        "r", suffix=".json", delete=False, prefix="gitleaks-"
    ) as tf:
        report = Path(tf.name)
    try:
        cmd = [
            "gitleaks",
            "detect",
            "--source",
            str(root),
            "--report-format",
            "json",
            "--report-path",
            str(report),
            "--no-banner",
            "--exit-code",
            "0",
        ]
        # Working-tree-only unless --deep, which also sweeps git history.
        if not deep:
            cmd.append("--no-git")
        scope = "history + working tree" if deep else "working tree"
        info(f"secrets: running gitleaks ({scope})")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, cwd=root
            )
        except subprocess.TimeoutExpired:
            return _scanner_result(
                available=True, ran=False, ok=False, reason="gitleaks timed out (300s)"
            )
        # We pass `--exit-code 0`, so gitleaks returns 0 whether or not it finds
        # leaks; any non-zero code is a genuine operational failure that must NOT
        # be reported as a clean scan.
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            reason = f"gitleaks exit {proc.returncode}"
            if tail:
                reason += f": {tail[-1]}"
            return _scanner_result(available=True, ran=False, ok=False, reason=reason)
        try:
            raw = report.read_text() or "[]"
            findings = json.loads(raw) if raw.strip() else []
        except (json.JSONDecodeError, OSError):
            return _scanner_result(
                available=True,
                ran=False,
                ok=False,
                reason="unparseable gitleaks report",
            )
    finally:
        report.unlink(missing_ok=True)

    severity = {s: 0 for s in SEVERITIES}
    details = []
    for f in findings:
        severity["critical"] += 1  # a live secret is always critical
        details.append(
            {
                "rule": f.get("RuleID") or f.get("Description", "secret"),
                "file": f.get("File", "?"),
                "line": f.get("StartLine"),
                "severity": "critical",
            }
        )
    count = len(details)
    info(f"secrets: {count} potential secret(s)")
    return _scanner_result(
        available=True,
        ran=True,
        ok=True,
        findings=count,
        severity=severity,
        details=details,
    )


# --------------------------------------------------------------------------- #
# static — semgrep
# --------------------------------------------------------------------------- #

_SEMGREP_SEVERITY = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}


def run_static(root: Path, deep: bool = False) -> dict:
    if not shutil.which("semgrep"):
        return _degraded("semgrep not on PATH — install semgrep to run static analysis")

    cmd = ["semgrep", "--quiet", "--json"]
    if deep:
        # Heavier, security-focused rule packs for the deep pass.
        for cfg in ("p/security-audit", "p/secrets", "p/owasp-top-ten"):
            cmd += ["--config", cfg]
    else:
        cmd += ["--config", "auto"]
    cmd.append(str(root))
    info(f"static: running semgrep ({'deep rulesets' if deep else 'auto'})")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, cwd=root
        )
    except subprocess.TimeoutExpired:
        return _scanner_result(
            available=True, ran=False, ok=False, reason="semgrep timed out (600s)"
        )

    # semgrep exits 0 (clean) or 1 (findings); >=2 is a fatal error whose partial
    # JSON must not be parsed as a clean scan.
    if result.returncode not in (0, 1):
        tail = (result.stderr or "").strip().splitlines()
        reason = f"semgrep exit {result.returncode}"
        if tail:
            reason += f": {tail[-1]}"
        return _scanner_result(available=True, ran=False, ok=False, reason=reason)

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return _scanner_result(
            available=True, ran=False, ok=False, reason="unparseable semgrep output"
        )

    severity = {s: 0 for s in SEVERITIES}
    details = []
    for r in data.get("results", []):
        raw_sev = (r.get("extra", {}) or {}).get("severity", "INFO")
        sev = _SEMGREP_SEVERITY.get(str(raw_sev).upper(), "low")
        severity[sev] += 1
        details.append(
            {
                "check_id": r.get("check_id", "?"),
                "file": r.get("path", "?"),
                "line": (r.get("start", {}) or {}).get("line"),
                "severity": sev,
            }
        )
    count = len(details)
    info(f"static: {count} finding(s)")
    return _scanner_result(
        available=True,
        ran=True,
        ok=True,
        findings=count,
        severity=severity,
        details=details,
    )


# --------------------------------------------------------------------------- #
# hygiene — pure-python sensitive-file sweep (always available; deep only)
# --------------------------------------------------------------------------- #

# Filename / suffix patterns that should never be committed.
_SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".netrc",
    "credentials",
    "secrets.yaml",
    "secrets.yml",
}
_SENSITIVE_SUFFIXES = (".pem", ".key", ".pfx", ".p12", ".keystore", ".jks")
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache"}


def run_hygiene(root: Path) -> dict:
    """Repo-agnostic sensitive-file detector. Pure python — never degrades."""
    info("hygiene: scanning for committed sensitive files")
    details = []
    severity = {s: 0 for s in SEVERITIES}

    tracked: set[str] | None = None
    if shutil.which("git") and (root / ".git").exists():
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=60,
            )
            if res.returncode == 0:
                tracked = set(res.stdout.splitlines())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tracked = None

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        name = path.name
        hit = name in _SENSITIVE_NAMES or path.suffix.lower() in _SENSITIVE_SUFFIXES
        if not hit:
            continue
        rel = str(path.relative_to(root))
        # A private key / .env in the tree is high; if git-tracked it is critical.
        is_tracked = tracked is not None and rel in tracked
        sev = "critical" if is_tracked else "high"
        severity[sev] += 1
        details.append({"file": rel, "tracked": is_tracked, "severity": sev})

    count = len(details)
    info(f"hygiene: {count} sensitive file(s)")
    return _scanner_result(
        available=True,
        ran=True,
        ok=True,
        findings=count,
        severity=severity,
        details=details,
    )


# --------------------------------------------------------------------------- #
# aggregation + reporting
# --------------------------------------------------------------------------- #


def aggregate(scanners: dict[str, dict]) -> dict:
    counts = _empty_counts()
    for res in scanners.values():
        for sev in SEVERITIES:
            counts[sev] += res["severity"].get(sev, 0)
    counts["total"] = sum(counts[s] for s in SEVERITIES)
    return counts


def compute_exit(scanners: dict[str, dict], findings_total: int) -> int:
    ran_any = any(r["ran"] for r in scanners.values())
    if not ran_any:
        return 2
    return 1 if findings_total > 0 else 0


def _public_scanner(res: dict) -> dict:
    """Trim the verbose `details` list out of the JSON status block."""
    return {
        "available": res["available"],
        "ran": res["ran"],
        "ok": res["ok"],
        "findings": res["findings"],
        "severity": res["severity"],
        "reason": res["reason"],
    }


def _detail_line(scanner: str, d: dict) -> str:
    if scanner == "deps":
        fix = ", ".join(d["fix_versions"]) or "no fix"
        return f"{d['package']} {d['version']}: {d['id']} → {fix}"
    if scanner == "secrets":
        return f"{d['file']}:{d['line']} [{d['rule']}]"
    if scanner == "static":
        return f"{d['file']}:{d['line']} [{d['check_id']}] ({d['severity']})"
    if scanner == "hygiene":
        tag = "tracked" if d["tracked"] else "untracked"
        return f"{d['file']} ({tag})"
    return str(d)


def report_human(scanners: dict[str, dict], counts: dict, exit_code: int) -> None:
    _out()
    _out("=== audit summary ===")
    for name, res in scanners.items():
        if not res["available"]:
            _out(f"  {name:8s} — SKIPPED ({res['reason']})")
        elif not res["ran"]:
            _out(f"  {name:8s} — DID NOT RUN ({res['reason']})")
        else:
            _out(f"  {name:8s} — {res['findings']} finding(s)")
        for d in res["details"]:
            _out(f"             · {_detail_line(name, d)}")
    _out()
    _out(
        "  findings: "
        + ", ".join(f"{s}={counts[s]}" for s in SEVERITIES)
        + f"  (total {counts['total']})"
    )
    verdict = {0: "clean", 1: "findings present", 2: "could not run"}[exit_code]
    _out(f"  verdict: {verdict} (exit {exit_code})")


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #


def run_audit(
    root: Path,
    *,
    deps: bool = True,
    secrets: bool = False,
    static: bool = False,
    deep: bool = False,
) -> tuple[dict, dict, int]:
    """Run the requested scanners. Returns (scanners, counts, exit_code)."""
    if deep:
        secrets = static = True

    scanners: dict[str, dict] = {}
    if deps:
        scanners["deps"] = run_deps(root)
    if secrets:
        scanners["secrets"] = run_secrets(root, deep=deep)
    if static:
        scanners["static"] = run_static(root, deep=deep)
    if deep:
        scanners["hygiene"] = run_hygiene(root)

    counts = aggregate(scanners)
    exit_code = compute_exit(scanners, counts["total"])
    return scanners, counts, exit_code


def build_json(
    scanners: dict[str, dict], counts: dict, exit_code: int, mode: str
) -> dict:
    return {
        "verb": "audit",
        "ok": exit_code != 2,
        "mode": mode,
        "findings": counts,
        "scanners": {name: _public_scanner(res) for name, res in scanners.items()},
        "exit_code": exit_code,
    }


def _mode_label(deep: bool, secrets: bool, static: bool) -> str:
    if deep:
        return "deep"
    active = [n for n, on in (("secrets", secrets), ("static", static)) if on]
    return "+".join(["deps", *active]) if active else "deps"


def main(argv: list[str] | None = None) -> int:
    global _JSON_MODE
    parser = argparse.ArgumentParser(
        prog="audit", description="Multi-scanner security audit."
    )
    parser.add_argument(
        "--secrets", action="store_true", help="run gitleaks secret scan"
    )
    parser.add_argument(
        "--static", action="store_true", help="run semgrep static analysis"
    )
    parser.add_argument(
        "--deep", action="store_true", help="deep pass: deps+secrets+static+hygiene"
    )
    parser.add_argument(
        "--no-deps", action="store_true", help="skip the dependency scan"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit one structured JSON line on stdout"
    )
    parser.add_argument("--path", default=None, help="repo root to scan (default: cwd)")
    args = parser.parse_args(argv)

    _JSON_MODE = args.json
    root = Path(args.path).resolve() if args.path else Path.cwd()

    deps = not args.no_deps
    scanners, counts, exit_code = run_audit(
        root, deps=deps, secrets=args.secrets, static=args.static, deep=args.deep
    )
    mode = _mode_label(args.deep, args.secrets, args.static)

    report_human(scanners, counts, exit_code)  # → stderr under --json
    if args.json:
        print(json.dumps(build_json(scanners, counts, exit_code, mode)))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
