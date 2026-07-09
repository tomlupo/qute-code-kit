"""Per-repo PR-workflow resolution for the qute-coder / qute-reviewer flow.

SINGLE SOURCE OF TRUTH — a committed, tool-agnostic CI config file at the repo
root: ``.github/qute-pr.yml``. BOTH surfaces read the SAME file:

  * the CI ``review-gate.yml`` workflow reads it (to know whether to enforce + who
    should have reviewed) → the visible server-side gate;
  * the client-side hooks + the ``/qute-coder`` skill read it (via this module).

Schema + defaults (``qutePrWorkflow`` policy, now homed in the YAML):

    | key                    | type | default   | meaning                                            |
    |------------------------|------|-----------|----------------------------------------------------|
    | ``assignTo``           | str  | "tomlupo" | who the PR is assigned to + review requested from  |
    | ``independentReview``  | bool | true      | run the auto independent review in the chain       |
    | ``allowAgentSelfMerge``| bool | false     | if false the agent must NOT merge (assign a human) |
    | ``enforce``            | bool | false     | whether the blocking PR-flow hooks + gate fire     |
    | ``baseBranch``         | str  | ""        | default PR base; "" => let ``gh`` pick the repo    |
    |                        |      |           | default (today's behavior). A caller ``--base``    |
    |                        |      |           | always wins over this.                             |

Example ``.github/qute-pr.yml``::

    # qute PR-flow policy — read by CI (review-gate.yml) AND the client hooks/skill.
    assignTo: tomlupo
    independentReview: true
    allowAgentSelfMerge: false
    enforce: false

Keys may also be nested under a top-level ``qutePrWorkflow:`` mapping — both flat
and nested forms are accepted.

Absent file → the documented defaults (review on, assign tomlupo, self-merge off,
enforce off), so a repo with no config behaves exactly as the defaults and nothing
new fails.

BACKWARD-COMPAT (transition): if a repo still has the ORIGINAL top-level marker
``"quteEnforcePrReview": true`` in ``.claude/settings.json`` (or
``settings.local.json``), it is honored as ``enforce: true``. ``.github/qute-pr.yml``
is the documented primary home; the settings.json marker is the legacy path.

Enforcement stays OPT-IN / DEFAULT OFF: a repo that merely has qute-essentials
installed but sets neither ``enforce: true`` nor the legacy marker gets exactly the
prior behaviour — no block, no warning, no failure.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# Backward-compat top-level enforcement marker in .claude/settings*.json.
MARKER = "quteEnforcePrReview"
# Optional top-level mapping key inside the YAML (flat keys also accepted).
WORKFLOW_KEY = "qutePrWorkflow"

# The committed, tool-agnostic single source of truth.
CONFIG_FILE = ".github/qute-pr.yml"
CONFIG_FILE_ALT = ".github/qute-pr.yaml"

# Resolved defaults when a key (or the whole file) is absent.
DEFAULTS: dict[str, object] = {
    "assignTo": "tomlupo",
    "independentReview": True,
    "allowAgentSelfMerge": False,
    "enforce": False,
    "baseBranch": "",
}
# Expected type per key — a value of the wrong type is ignored (default kept).
_TYPES: dict[str, type] = {
    "assignTo": str,
    "independentReview": bool,
    "allowAgentSelfMerge": bool,
    "enforce": bool,
    "baseBranch": str,
}

# Legacy per-repo settings files (only the enforce marker is read from these).
_SETTINGS_FILES = (".claude/settings.json", ".claude/settings.local.json")


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _parse_yaml(text: str) -> dict:
    """Parse the tiny flat/one-level YAML config.

    Uses PyYAML when importable; otherwise a minimal fallback that handles the
    documented flat ``key: value`` form (and a single ``qutePrWorkflow:`` nesting)
    with str/bool scalars — enough that the config never hard-depends on PyYAML.
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_yaml_fallback(text)
    except Exception:
        return {}


def _coerce_scalar(raw: str):
    v = raw.strip().strip('"').strip("'")
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    return v


def _parse_yaml_fallback(text: str) -> dict:
    out: dict = {}
    nest_key = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*(?:#.*)?$", line)
        if not m:
            continue
        indent, key, val = len(m.group(1)), m.group(2), m.group(3)
        if indent == 0:
            if val == "":
                nest_key = key
                out.setdefault(key, {})
            else:
                out[key] = _coerce_scalar(val)
                nest_key = None
        elif nest_key is not None and val != "":
            sub = out.get(nest_key)
            if isinstance(sub, dict):
                sub[key] = _coerce_scalar(val)
    return out


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


def _legacy_marker_truthy(cfg: dict) -> bool:
    """Accept the marker at top level or nested under a 'qute'/'quteEssentials' key."""
    if cfg.get(MARKER) is True:
        return True
    for ns in ("qute", "quteEssentials"):
        sub = cfg.get(ns)
        if isinstance(sub, dict) and sub.get(MARKER) is True:
            return True
        if isinstance(sub, dict) and sub.get("enforcePrReview") is True:
            return True
    return False


def _apply_block(resolved: dict, block: dict) -> None:
    """Merge a mapping of policy keys into ``resolved`` in place (typed, defensive)."""
    for key, expected in _TYPES.items():
        val = block.get(key, ...)
        if val is ...:
            continue
        # bool is a subclass of int; keep str/bool clean.
        if expected is bool and isinstance(val, bool):
            resolved[key] = val
        elif expected is str and isinstance(val, str):
            resolved[key] = val


def _load_yaml_config(root: Path) -> dict:
    for name in (CONFIG_FILE, CONFIG_FILE_ALT):
        p = root / name
        if p.is_file():
            try:
                return _parse_yaml(p.read_text(encoding="utf-8"))
            except OSError:
                return {}
    return {}


def resolve_workflow(cwd: str | os.PathLike | None = None) -> dict:
    """Resolve the effective PR-workflow policy for the repo containing ``cwd``.

    Precedence (low → high): defaults < ``.github/qute-pr.yml`` < legacy
    ``quteEnforcePrReview`` marker (enforce-on only) < ``QUTE_ENFORCE_PR_REVIEW`` env.
    Returns a full dict with every key present (defaults applied). Absent config →
    the documented defaults, so nothing new fails.
    """
    resolved = dict(DEFAULTS)
    root = find_repo_root(cwd)
    if root is not None:
        cfg = _load_yaml_config(root)
        if isinstance(cfg, dict):
            # accept flat keys and/or a nested `qutePrWorkflow:` mapping.
            _apply_block(resolved, cfg)
            nested = cfg.get(WORKFLOW_KEY)
            if isinstance(nested, dict):
                _apply_block(resolved, nested)
        # legacy transition: the old settings.json marker still flips enforce on.
        for name in _SETTINGS_FILES:
            if _legacy_marker_truthy(_read_json(root / name)):
                resolved["enforce"] = True
    override = os.environ.get("QUTE_ENFORCE_PR_REVIEW")
    if override == "1":
        resolved["enforce"] = True
    elif override == "0":
        resolved["enforce"] = False
    return resolved


def enforcement_enabled(cwd: str | os.PathLike | None = None) -> bool:
    """True iff the repo containing ``cwd`` has opted into PR-flow enforcement.

    Honors BOTH ``.github/qute-pr.yml`` ``enforce: true`` AND the legacy
    ``quteEnforcePrReview: true`` marker — either enables it. Env override:
    QUTE_ENFORCE_PR_REVIEW=1 forces on, =0 off.
    """
    return bool(resolve_workflow(cwd)["enforce"])


if __name__ == "__main__":  # tiny CLI for manual checks / tests / the flow script
    import sys

    args = sys.argv[1:]
    if args and args[0] == "--json":
        where = args[1] if len(args) > 1 else None
        print(json.dumps(resolve_workflow(where)))
    else:
        where = args[0] if args else None
        print("enabled" if enforcement_enabled(where) else "inert")
