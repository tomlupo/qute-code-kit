"""repo_inventory — cross-host git-repo enumeration for the deep audit layer.

Enumerates the git repositories to scan across one or more *hosts* (core, forge,
prod, …) so `audit --deep` can iterate them. Repo-agnostic on purpose: it does
NOT hardcode `/home/tom/workspace/projects/*` (the old /cso scope gap). Roots and
hosts come from config, precedence high → low:

  1. --roots a,b,c           explicit CLI roots (local host only)
  2. QUTE_AUDIT_ROOTS env     colon- or comma-separated roots (local host only)
  3. config file              ~/.config/qute/audit-inventory.json  (or --config)
  4. default                  the current working directory

Config file schema (all keys optional):

    {
      "hosts": {
        "core":  {"roots": ["$HOME/workspace/projects"]},
        "forge": {"roots": ["/srv/repos"], "ssh": "forge"},
        "prod":  {"roots": ["/opt/apps"],  "ssh": "deploy@prod"}
      },
      "max_depth": 3
    }

A host with an `ssh` target is enumerated remotely via `ssh <target> find …`;
without it, the host is local. Remote/unreachable hosts **graceful-degrade** —
they are reported with an error and skipped, never crash the sweep.

CLI:
    repo_inventory.py [--roots a,b] [--host NAME] [--config PATH] [--json]

`--json` prints one JSON object: {"hosts": {...}, "repos": [...], "count": N}.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config" / "qute" / "audit-inventory.json"
DEFAULT_MAX_DEPTH = 3


def _expand(p: str) -> str:
    return os.path.expandvars(os.path.expanduser(p))


def _split_roots(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace(":", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def load_config(config_path: Path | None) -> dict:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"repo_inventory: warning: bad config {path}: {exc}", file=sys.stderr)
        return {}


def discover_local(roots: list[str], max_depth: int = DEFAULT_MAX_DEPTH) -> list[dict]:
    """Find git repos under the given roots on the local filesystem."""
    repos: list[dict] = []
    seen: set[str] = set()
    for raw_root in roots:
        root = Path(_expand(raw_root))
        if not root.exists():
            continue
        for dot_git in _find_git_dirs(root, max_depth):
            repo_dir = dot_git.parent
            key = str(repo_dir.resolve())
            if key in seen:
                continue
            seen.add(key)
            repos.append({"name": repo_dir.name, "path": str(repo_dir)})
    return sorted(repos, key=lambda r: r["path"])


def _find_git_dirs(root: Path, max_depth: int):
    """Yield `.git` entries under root up to max_depth, not descending into repos."""
    root_depth = len(root.parts)

    def _walk(dir_path: Path):
        depth = len(dir_path.parts) - root_depth
        if depth > max_depth:
            return
        try:
            entries = list(dir_path.iterdir())
        except (PermissionError, OSError):
            return
        git = dir_path / ".git"
        if git.exists():
            yield git
            return  # do not descend into a repo's subdirs
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                if entry.name in {".git", "node_modules", ".venv", "venv"}:
                    continue
                yield from _walk(entry)

    yield from _walk(root)


def discover_remote(
    ssh_target: str, roots: list[str], max_depth: int
) -> tuple[list[dict], str]:
    """Enumerate repos on a remote host via ssh. Returns (repos, error)."""
    # Guard: a rootless `find` would default to the remote's cwd and scan an
    # unbounded, unintended scope. Refuse instead.
    if not roots:
        return [], "no roots configured for remote host"
    expanded = " ".join(_shq(_expand(r)) for r in roots)
    # -prune stops find from descending into a repo once .git is seen.
    remote_cmd = (
        f"find {expanded} -maxdepth {max_depth} -name .git -prune -print 2>/dev/null"
    )
    try:
        res = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                ssh_target,
                remote_cmd,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return [], f"ssh failed: {exc}"
    if res.returncode != 0:
        err = (res.stderr or "").strip().splitlines()
        return [], f"ssh exit {res.returncode}: {err[-1] if err else 'unreachable'}"

    repos: list[dict] = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line.endswith("/.git") and line != ".git":
            continue
        repo_dir = line[: -len("/.git")] if line.endswith("/.git") else "."
        repos.append({"name": Path(repo_dir).name, "path": repo_dir})
    return sorted(repos, key=lambda r: r["path"]), ""


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def build_inventory(
    *,
    cli_roots: list[str] | None = None,
    only_host: str | None = None,
    config_path: Path | None = None,
) -> dict:
    """Resolve config + CLI/env into a host→repos inventory."""
    config = load_config(config_path)
    try:
        max_depth = int(config.get("max_depth", DEFAULT_MAX_DEPTH))
    except (TypeError, ValueError):
        print(
            f"repo_inventory: warning: bad max_depth in config, using {DEFAULT_MAX_DEPTH}",
            file=sys.stderr,
        )
        max_depth = DEFAULT_MAX_DEPTH
    hosts_cfg: dict = config.get("hosts", {})

    # Explicit CLI/env roots override the config entirely (local-only).
    env_roots = os.environ.get("QUTE_AUDIT_ROOTS", "")
    roots_override = cli_roots or (_split_roots(env_roots) if env_roots else None)

    if roots_override or not hosts_cfg:
        roots = roots_override or [str(Path.cwd())]
        repos = discover_local(roots, max_depth)
        return {
            "hosts": {
                "local": {"ssh": None, "roots": roots, "repos": repos, "error": ""}
            },
            "repos": repos,
            "count": len(repos),
        }

    hosts_out: dict[str, dict] = {}
    all_repos: list[dict] = []
    for host_name, hc in hosts_cfg.items():
        if only_host and host_name != only_host:
            continue
        roots = hc.get("roots", [])
        ssh_target = hc.get("ssh")
        if ssh_target:
            repos, error = discover_remote(ssh_target, roots, max_depth)
        else:
            repos, error = discover_local(roots, max_depth), ""
        for r in repos:
            r = {**r, "host": host_name}
            all_repos.append(r)
        hosts_out[host_name] = {
            "ssh": ssh_target,
            "roots": roots,
            "repos": repos,
            "error": error,
        }
    return {"hosts": hosts_out, "repos": all_repos, "count": len(all_repos)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_inventory", description="Enumerate git repos to scan across hosts."
    )
    parser.add_argument(
        "--roots", default=None, help="comma/colon-separated local roots"
    )
    parser.add_argument(
        "--host", default=None, help="limit to a single configured host"
    )
    parser.add_argument("--config", default=None, help="path to audit-inventory.json")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    cli_roots = _split_roots(args.roots) if args.roots else None
    config_path = Path(args.config) if args.config else None
    inv = build_inventory(
        cli_roots=cli_roots, only_host=args.host, config_path=config_path
    )

    if args.json:
        print(json.dumps(inv))
        return 0

    print(f"repo inventory: {inv['count']} repo(s)")
    for host_name, hc in inv["hosts"].items():
        tag = f" (ssh {hc['ssh']})" if hc.get("ssh") else " (local)"
        print(f"\n{host_name}{tag} — roots: {', '.join(hc['roots']) or '(none)'}")
        if hc.get("error"):
            print(f"  ! {hc['error']}")
        for r in hc["repos"]:
            print(f"  · {r['name']:30s} {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
