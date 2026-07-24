"""Validate research/<line>/ Model C pins AND the ADR-0007 reproducibility contract.

Two deterministic layers, no LLM and no network:

1. **Structural (ADR-0002 / Model C).** Every ``research/<line>/pyproject.toml`` pins
   each configured ``pin_target`` to a full 40-char git SHA; the required per-line
   files exist; forbidden production dirs carry no tracked files.

2. **Provenance-on-conclude (ADR-0007).** For any line whose README frontmatter is
   ``status: concluded``, assert reproducibility keyed on ``reproducibility_class``:

     - ``pinned``          -> data_inputs.yaml exists with a non-null 64-hex sha256 on
                             every input, AND the provenance fields are filled (no TBD).
     - ``snapshot-frozen`` -> declared snapshot inputs present on disk under the line
                             AND a sha256 for each.
     - ``live-data`` / ``historical`` -> EXEMPT from hashes; require the class be set and
                             a non-empty ``repro_note`` explaining why it can't be pinned.

   Active / paused / abandoned / superseded lines are exempt — the contract binds at
   conclusion, so live iteration against the sibling checkout stays allowed.

Reads ``.research-config.yaml`` at the repo root. Exit 0 if all lines pass; exit 1
with a precise per-violation report otherwise.

USAGE:  python scripts/check_research_pins.py

Canonical source: qute-code-kit ``templates/research/check_research_pins.py``, stamped
into consumer repos by ``/setup-qute-repo``. Edit it there, not per-repo.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

VALID_CLASSES = {"pinned", "snapshot-frozen", "live-data", "historical"}
HASH_CLASSES = {"pinned", "snapshot-frozen"}
NOTE_CLASSES = {"live-data", "historical"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def _parse_frontmatter(md_path: Path) -> dict:
    """Return the YAML frontmatter of a markdown file as a dict ({} if none/invalid)."""
    if not md_path.exists():
        return {}
    text = md_path.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_tbd(value: object) -> bool:
    """True if a provenance value is unfilled (None / empty / a ``TBD`` placeholder)."""
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.upper() == "TBD"


def _check_provenance_on_conclude(line_dir: Path, fm: dict) -> list[str]:
    """ADR-0007 checks for a concluded line, keyed on ``reproducibility_class``."""
    name = line_dir.name
    errors: list[str] = []

    cls = fm.get("reproducibility_class")
    if cls is None:
        return [
            f"{name}: status=concluded but reproducibility_class is not set "
            f"(one of {sorted(VALID_CLASSES)})"
        ]
    if cls not in VALID_CLASSES:
        return [
            f"{name}: invalid reproducibility_class {cls!r} (one of {sorted(VALID_CLASSES)})"
        ]

    if cls in NOTE_CLASSES:
        if _is_tbd(fm.get("repro_note")):
            errors.append(
                f"{name}: reproducibility_class={cls} requires a non-empty repro_note "
                f"explaining why the line cannot be pinned (do not fabricate hashes)"
            )
        return errors

    # HASH_CLASSES: pinned + snapshot-frozen both need data_inputs.yaml + hashes.
    di_path = line_dir / "data_inputs.yaml"
    if not di_path.exists():
        return [
            f"{name}: reproducibility_class={cls} requires data_inputs.yaml (missing)"
        ]
    try:
        di = yaml.safe_load(di_path.read_text()) or {}
    except yaml.YAMLError as exc:
        return [f"{name}: data_inputs.yaml is not valid YAML ({exc})"]

    inputs = di.get("inputs") or []
    if not inputs:
        errors.append(f"{name}: data_inputs.yaml declares no inputs")
    for i, item in enumerate(inputs):
        if not isinstance(item, dict):
            errors.append(f"{name}: data_inputs.yaml inputs[{i}] is not a mapping")
            continue
        path = item.get("path", f"<input {i}>")
        sha = item.get("sha256")
        if _is_tbd(sha) or not SHA256_RE.match(str(sha).strip()):
            errors.append(
                f"{name}: data_inputs.yaml input {path!r} has no valid sha256 (got {sha!r})"
            )
        if cls == "snapshot-frozen":
            snap = line_dir / str(item.get("path", ""))
            if not snap.exists():
                errors.append(
                    f"{name}: snapshot-frozen input {path!r} not present under the line "
                    f"(expected force-added snapshot at {line_dir.name}/{item.get('path', '')})"
                )

    if cls == "pinned":
        prov = fm.get("provenance")
        if not isinstance(prov, dict) or not prov:
            errors.append(
                f"{name}: reproducibility_class=pinned requires a filled provenance block "
                f"(engine_commit, ran_at)"
            )
        else:
            if _is_tbd(prov.get("engine_commit")) or not SHA40_RE.match(
                str(prov.get("engine_commit", "")).strip()
            ):
                errors.append(
                    f"{name}: provenance.engine_commit must be a 40-char engine SHA "
                    f"on a concluded pinned line (got {prov.get('engine_commit')!r})"
                )
            if _is_tbd(prov.get("ran_at")):
                errors.append(
                    f"{name}: provenance.ran_at is unfilled (TBD) on a concluded pinned line"
                )

    return errors


def check(root: Path) -> tuple[int, list[str]]:
    """Run all checks against ``root``. Return (exit_code, violations)."""
    config_path = root / ".research-config.yaml"
    if not config_path.exists():
        return 1, [f"{config_path} not found"]

    cfg = yaml.safe_load(config_path.read_text()) or {}
    research_root = root / cfg.get("research_root", "research")
    pin_targets = {pt["name"] for pt in cfg.get("pin_targets", [])}
    rules = cfg.get("structural_rules", {})
    forbidden_dirs = rules.get("forbidden_dirs", [])
    required_files = rules.get("required_per_research", [])
    require_sha = rules.get("require_sha_pins", True)

    errors: list[str] = []

    # Rule 1: forbidden dirs at repo root — only count git-TRACKED files, so local
    # untracked WIP does not fail CI.
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=root, text=True
        ).splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tracked = []
    for d in forbidden_dirs:
        if any(t.startswith(f"{d}/") for t in tracked):
            errors.append(
                f"forbidden directory has tracked files: {d}/ (Model C violation — "
                f"production code belongs in the engine repo, not the lab)"
            )

    if not research_root.is_dir():
        return (1 if errors else 0), errors

    for line_dir in sorted(research_root.iterdir()):
        if not line_dir.is_dir() or line_dir.name.startswith("_"):
            continue

        # Rule 2: structural pin + required-file checks (only frozen projects).
        pyp = line_dir / "pyproject.toml"
        if pyp.exists():
            text = pyp.read_text()
            for req in required_files:
                if not (line_dir / req).exists():
                    errors.append(f"{line_dir.name}: missing required file {req}")
            if require_sha:
                for pkg in pin_targets:
                    pattern = re.compile(
                        rf"{re.escape(pkg)}(?:\[[^\]]+\])?\s*@\s*git\+[^@]+@(\S+?)\""
                    )
                    m = pattern.search(text)
                    if not m:
                        errors.append(
                            f"{line_dir.name}: pin for {pkg} not found in pyproject.toml"
                        )
                        continue
                    sha = m.group(1)
                    if not SHA40_RE.match(sha):
                        errors.append(
                            f"{line_dir.name}: {pkg} pinned to {sha!r} — must be a 40-char git SHA"
                        )

        # Rule 3 (ADR-0007): provenance-on-conclude, keyed on reproducibility_class.
        fm = _parse_frontmatter(line_dir / "README.md")
        if fm.get("status") == "concluded":
            errors.extend(_check_provenance_on_conclude(line_dir, fm))

    return (1 if errors else 0), errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    code, errors = check(root)
    if errors:
        print(f"\n{len(errors)} research-contract violations:\n")
        for e in errors:
            print(f"  - {e}")
        print()
    else:
        print("All research lines pass Model C + ADR-0007 reproducibility checks.")
    return code


if __name__ == "__main__":
    sys.exit(main())
