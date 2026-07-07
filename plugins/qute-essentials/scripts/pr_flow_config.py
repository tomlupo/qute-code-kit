"""Per-repo opt-in resolution for the PR-flow enforcement hook.

The enforcement hook (pr-flow-guard.py) is OPT-IN and DEFAULT OFF. A repo that
merely has qute-essentials installed behaves exactly as before — no block, no
warning, no failure — UNLESS it explicitly opts in.

Opt-in marker: ``"quteEnforcePrReview": true`` at the top level of the repo's
``.claude/settings.json`` (or ``.claude/settings.local.json``). Absent, false,
or unreadable → enforcement is INERT.

This is deliberately a PER-REPO file marker (not the global ~/.claude guard
toggle), so adding/updating the plugin can never start failing an existing repo:
the marker lives in the target repo and only that repo's owner sets it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MARKER = "quteEnforcePrReview"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def find_repo_root(start: str | os.PathLike | None) -> Path | None:
    """Walk up from ``start`` to the nearest dir containing .git or .claude."""
    try:
        cur = Path(start).resolve() if start else Path.cwd()
    except (OSError, ValueError):
        return None
    if cur.is_file():
        cur = cur.parent
    for d in (cur, *cur.parents):
        if (d / ".git").exists() or (d / ".claude").is_dir():
            return d
    return None


def _truthy(cfg: dict) -> bool:
    """Accept the marker at top level or nested under a 'qute'/'quteEssentials' key."""
    if cfg.get(MARKER) is True:
        return True
    for ns in ("qute", "quteEssentials"):
        sub = cfg.get(ns)
        if isinstance(sub, dict) and sub.get(MARKER) is True:
            return True
        # also accept short key under the namespace, e.g. {"qute": {"enforcePrReview": true}}
        if isinstance(sub, dict) and sub.get("enforcePrReview") is True:
            return True
    return False


def enforcement_enabled(cwd: str | os.PathLike | None = None) -> bool:
    """True iff the repo containing ``cwd`` has opted into PR-flow enforcement.

    Env override for tests/emergencies: QUTE_ENFORCE_PR_REVIEW=1 forces on, =0 off.
    """
    override = os.environ.get("QUTE_ENFORCE_PR_REVIEW")
    if override == "1":
        return True
    if override == "0":
        return False
    root = find_repo_root(cwd)
    if root is None:
        return False
    for name in (".claude/settings.json", ".claude/settings.local.json"):
        if _truthy(_read_json(root / name)):
            return True
    return False


if __name__ == "__main__":  # tiny CLI for manual checks / tests
    import sys

    where = sys.argv[1] if len(sys.argv) > 1 else None
    print("enabled" if enforcement_enabled(where) else "inert")
