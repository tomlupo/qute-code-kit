"""/audit — dependency vulnerability scan for the current project (Python v1).

Runs `pip-audit` via `uvx` against the current project and reports known CVEs
in installed dependencies. Reads from the resolved environment (works with
uv-managed projects, plain venvs, and system Python).

Exit codes:
  0 — no vulnerabilities found
  1 — vulnerabilities found (details on stdout)
  2 — audit could not run (missing tool, no lockfile, etc.)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def info(msg: str) -> None:
    print(f"audit: {msg}")


def warn(msg: str) -> None:
    print(f"audit: warning: {msg}", file=sys.stderr)


def fail(msg: str) -> int:
    print(f"audit: error: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    root = Path.cwd()

    if not (root / "pyproject.toml").exists():
        return fail("no pyproject.toml in current directory (Python only in v1)")

    if not shutil.which("uv"):
        return fail("uv not on PATH — install uv to run pip-audit via uvx")

    # Prefer uvx pip-audit (no persistent install needed)
    cmd = ["uvx", "pip-audit", "--format", "json", "--progress-spinner", "off"]
    info(f"running `{' '.join(cmd)}`")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return fail("uvx not available")
    except subprocess.TimeoutExpired:
        return fail("pip-audit timed out after 120s")

    if result.returncode not in (0, 1):
        # pip-audit exits 0 on clean, 1 when vulns found, other on error
        warn(f"pip-audit exit code {result.returncode}")
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return fail("pip-audit failed to run")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        warn("could not parse pip-audit output")
        print(result.stdout)
        return 2

    dependencies = data.get("dependencies", [])
    total = len(dependencies)
    vulnerable = [d for d in dependencies if d.get("vulns")]

    info(f"scanned {total} packages")

    if not vulnerable:
        info("no known vulnerabilities")
        return 0

    print()
    print(f"Found vulnerabilities in {len(vulnerable)} package(s):")
    print()
    for dep in vulnerable:
        name = dep.get("name", "?")
        version = dep.get("version", "?")
        vulns = dep.get("vulns", [])
        print(f"  {name} {version}")
        for v in vulns:
            vid = v.get("id", "?")
            aliases = ", ".join(v.get("aliases", [])) or "—"
            fix_versions = ", ".join(v.get("fix_versions", [])) or "no fix available"
            description = (v.get("description") or "").strip().split("\n")[0][:120]
            print(f"    - {vid} (aliases: {aliases})")
            print(f"      fix: {fix_versions}")
            if description:
                print(f"      {description}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
