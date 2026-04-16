#!/usr/bin/env python3
"""
SessionStart hook: detect new/unknown repos and flag for security scan.

Tracks known repos in ~/.claude/permission-audit/known-repos.
When a session starts in a repo not in the list, injects a warning
telling Claude to run a security scan before doing any work.

Cross-platform replacement for repo-scan.sh.
"""

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


def get_repo_root() -> str:
    """Get the git repo root, or empty string if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def get_repo_id(repo_root: str) -> str:
    """Generate a stable ID for a repo path."""
    return hashlib.md5(repo_root.encode()).hexdigest()


def check_setup_py(repo_root: str) -> str:
    """Check setup.py for obfuscation patterns."""
    setup_py = Path(repo_root) / "setup.py"
    if not setup_py.exists():
        return ""
    try:
        content = setup_py.read_text(errors="replace")
        if re.search(r"exec\s*\(|__import__|base64|zlib|compile\(", content):
            return "CRITICAL: setup.py contains obfuscated/suspicious code patterns. DO NOT run it.\n"
    except OSError:
        pass
    return ""


def check_package_json(repo_root: str) -> str:
    """Check package.json for suspicious install scripts."""
    pkg_json = Path(repo_root) / "package.json"
    if not pkg_json.exists():
        return ""
    try:
        data = json.loads(pkg_json.read_text())
        scripts = data.get("scripts", {})
        suspicious = (
            "curl",
            "wget",
            "node -e",
            "eval",
            "exec",
            "bash",
            "http",
            "chmod",
            "/dev/tcp",
            "powershell",
            "cmd /c",
        )
        warnings = []
        for key in ("preinstall", "postinstall", "install"):
            val = scripts.get(key, "")
            if val and any(s in val for s in suspicious):
                warnings.append(
                    f"CRITICAL: package.json has suspicious {key} script: {val[:100]}"
                )
        return "\n".join(warnings) + ("\n" if warnings else "")
    except (json.JSONDecodeError, OSError):
        return ""


def check_tracked_env(repo_root: str) -> str:
    """Check for .env files tracked by git."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "ls-files", "*.env", ".env.*"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""
        tracked = [
            f
            for f in result.stdout.strip().split("\n")
            if f and not any(s in f for s in (".example", ".sample", ".template"))
        ]
        if tracked:
            return f"WARNING: .env files tracked by git: {', '.join(tracked)}\n"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def check_pr_target(repo_root: str) -> str:
    """Check for GitHub Actions with pull_request_target."""
    workflows_dir = Path(repo_root) / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return ""
    flagged = []
    try:
        for wf in workflows_dir.iterdir():
            if wf.is_file() and wf.suffix in (".yml", ".yaml"):
                if "pull_request_target" in wf.read_text(errors="replace"):
                    flagged.append(str(wf))
    except OSError:
        pass
    if flagged:
        return (
            f"WARNING: GitHub Actions with pull_request_target: {', '.join(flagged)}\n"
        )
    return ""


def main():
    known_file = Path.home() / ".claude" / "permission-audit" / "known-repos"
    known_file.parent.mkdir(parents=True, exist_ok=True)
    if not known_file.exists():
        known_file.touch()

    repo_root = get_repo_root()
    if not repo_root:
        print("{}")
        return

    repo_id = get_repo_id(repo_root)

    # Check if we've seen this repo before
    known_content = known_file.read_text()
    if f"{repo_id} " in known_content:
        print("{}")
        return

    # New repo — check for red flags
    warnings = ""
    warnings += check_setup_py(repo_root)
    warnings += check_package_json(repo_root)
    warnings += check_tracked_env(repo_root)
    warnings += check_pr_target(repo_root)

    repo_name = Path(repo_root).name
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        remote = result.stdout.strip() if result.returncode == 0 else "no remote"
    except (subprocess.TimeoutExpired, OSError):
        remote = "no remote"

    if warnings:
        msg = (
            f"NEW REPO DETECTED: {repo_name} ({remote})\n\n"
            f"SECURITY ISSUES FOUND:\n{warnings}\n"
            f"Before doing any work, investigate these findings. "
            f"Do NOT run npm install, pip install, or any build commands until the issues are resolved.\n\n"
            f"After review, this repo will be marked as known."
        )
    else:
        msg = (
            f"NEW REPO DETECTED: {repo_name} ({remote})\n\n"
            f"Quick scan found no obvious issues. Recommended: run /cso --code for a full audit before starting work.\n\n"
            f"Marking repo as known."
        )
        # Auto-mark clean repos
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(known_file, "a") as f:
            f.write(f"{repo_id} {repo_root} {timestamp}\n")

    print(json.dumps({"additionalContext": msg}))


if __name__ == "__main__":
    main()
