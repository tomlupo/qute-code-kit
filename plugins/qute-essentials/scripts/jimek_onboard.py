"""jimek-onboard — make a target repo Jimek-managed in one command.

Runs INSIDE a target repo. Detects the repo's workflow conventions, then STAMPS
a schema-valid ``conductor.yml`` (the per-repo Jimek dispatch + workflow-policy
contract) plus the supporting ``review-gate`` CI, idempotently and without ever
clobbering an existing file (it backs up + diffs instead).

Division of labour (decided 2026-07-09):

  * qute-essentials owns the *verbs* and the repo-distribution mechanism — this
    skill is that mechanism.
  * Jimek owns *orchestration*; the contract SCHEMA is the single source of
    truth in ``dispatcher.jimek.JimekContract`` (the 8 Wave-1a policy fields +
    the core dispatch fields). This script only TEMPLATES a schema-valid
    ``conductor.yml`` from that schema's shape + the repo's detected conventions.

Validation is two-tier:

  1. A bundled structural check that always runs (no dispatcher needed) — it
     guards the invariants that bit the W1c fan-out, above all that a rigor
     tier's ``path`` is ``commit-to-default`` | ``pr`` ONLY (obsidian-vaults#114
     shipped ``"commit"`` — never repeat it).
  2. The AUTHORITATIVE loader: ``dispatcher.jimek.load_contract`` extracted from
     ``origin/master`` of a local dispatcher checkout. If reachable, the
     generated file MUST load clean or the run fails loudly; if the checkout is
     absent, tier 1 still runs and the run WARNS that the authoritative check
     was skipped.

Exit codes:
  0  success (stamped, or dry-run/print completed, nothing invalid)
  1  a generated artifact failed validation, or a hard I/O error
  2  bad invocation (unreadable repo root, etc.)

Usage:
  jimek_onboard.py [--repo DIR] [--dispatcher-repo DIR] [--dry-run] [--print]
                   [--force] [--no-review-gate]
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Fleet-standard constants ─────────────────────────────────────────────────
# board_states / concurrency / turns are identical across every merged per-repo
# contract (dm-evo, quantbox, …). They are fleet conventions, not per-repo
# detections, so we template them verbatim.
BOARD_ACTIVE = ["Todo", "In Progress", "Human Review", "Merging"]
BOARD_TERMINAL = ["Done", "Blocked"]
MAX_CONCURRENT = 3
MERGING_CAP = 1
TURNS_MAX = 20
STALL_TIMEOUT_MS = 600000

# Repos that use `dev` as the PR base (per the fleet convention Tom set).
DEV_BASE_REPOS = {"dm-evo", "quantbox", "quantbox-lab"}
# Live-capital repos — the dispatcher rigor engine already forces these to
# complex + a Tom gate; we only RECORD the fact (escalation.block_on).
LIVE_CAPITAL_REPOS = {"quantbox", "quantbox-live"}

# Allowed rigor `path` values — the ONLY legal values in the schema. The W1c bug
# was emitting "commit"; keep this list authoritative for the bundled check.
VALID_PATHS = {"commit-to-default", "pr"}

DEFAULT_DISPATCHER_REPO = Path.home() / "workspace" / "projects" / "jimek"


# ── Detection ────────────────────────────────────────────────────────────────
def _run_git(repo: Path, *args: str) -> str:
    """Return trimmed git stdout, or '' on any failure (detection is best-effort)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except OSError:
        return ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _policy_corpus(repo: Path) -> str:
    """Concatenated lowercase text of the repo's workflow-policy docs."""
    chunks: list[str] = []
    for rel in ("CLAUDE.md", "AGENTS.md"):
        chunks.append(_read_text(repo / rel))
    rules_dir = repo / ".claude" / "rules"
    if rules_dir.is_dir():
        for f in sorted(rules_dir.glob("*.md")):
            chunks.append(_read_text(f))
    return "\n".join(chunks).lower()


def _default_branch(repo: Path) -> str:
    """The repo's actual default branch, or 'main' if it can't be determined."""
    ref = _run_git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if ref:  # e.g. "refs/remotes/origin/master"
        return ref.rsplit("/", 1)[-1]
    head = _run_git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    return head or "main"


def _gh_login() -> str:
    """The authenticated GitHub login via `gh`, or '' if gh is unavailable."""
    try:
        out = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except OSError:
        return ""


def _tag_pattern(repo: Path) -> str:
    """Release tag glob from commitizen's tag_format, defaulting to 'v*'.

    Parsed with tomllib so inline comments / quoting can't corrupt the value.
    """
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        return "v*"
    try:
        import tomllib  # noqa: PLC0415 — 3.11+; degrade gracefully below

        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError, ModuleNotFoundError):
        return "v*"
    fmt = data.get("tool", {}).get("commitizen", {}).get("tag_format")
    if not isinstance(fmt, str) or not fmt:
        return "v*"
    # commitizen uses `$version`; translate to a glob. Reject anything that
    # would need YAML quoting gymnastics (newlines/quotes) → safe default.
    pattern = fmt.replace("$version", "*")
    if any(c in pattern for c in '"\n\r'):
        return "v*"
    return pattern or "v*"


def detect_conventions(repo: Path) -> dict:
    """Detect the repo's workflow conventions from git + its policy docs.

    Pure-ish: reads the filesystem/git of ``repo`` and returns a plain dict. All
    heuristics degrade to safe, schema-valid defaults.
    """
    name = repo.resolve().name
    corpus = _policy_corpus(repo)

    # ── base branch ──────────────────────────────────────────────────────────
    # Precedence: explicit doc marker → known dev-base repo → the repo's ACTUAL
    # default branch (origin/HEAD, so a `master` repo isn't forced to `main`).
    # We deliberately do NOT infer `dev` from loose "dev"/"main" substrings —
    # those match development/domain/maintain/… and misfire (review finding).
    default_branch = _default_branch(repo)
    has_origin_dev = bool(
        _run_git(repo, "show-ref", "--verify", "refs/remotes/origin/dev")
    )
    if "basebranch: dev" in corpus or "pr to dev" in corpus or "→ pr to dev" in corpus:
        base = "dev"
    elif name in DEV_BASE_REPOS:
        base = "dev"
    else:
        base = default_branch

    # ── direct-commit-to-default allowed? → trivial tier path ────────────────
    # If the docs forbid direct commits (everything goes through a PR), the
    # trivial tier still uses `pr` (it just skips the required review). Only when
    # direct commits are clearly permitted do we grant `commit-to-default`.
    # Markers are specific phrases (not generic substrings) to avoid false hits.
    forbids_direct = any(
        marker in corpus
        for marker in (
            "forbids direct commits",
            "no direct commits",
            "never commit to main directly",
            "never commit directly to",
            "all feature work goes through a pr",
        )
    )
    trivial_path = "pr" if forbids_direct else "commit-to-default"

    # ── live capital ─────────────────────────────────────────────────────────
    live_capital = (
        name in LIVE_CAPITAL_REPOS
        or "live-capital" in corpus
        or "live_capital" in corpus
    )

    # ── release / tag conventions ────────────────────────────────────────────
    tag_pattern = _tag_pattern(repo)
    # Tags are cut off the integration/release branch. dev-base repos tag off
    # main after dev→main; main-base repos tag off their default branch.
    release_branch = "main" if base == "dev" else default_branch

    # ── assignee (human gate) ────────────────────────────────────────────────
    # prFlow.assignTo/reviewRequestFrom need a GitHub *login*, not a git display
    # name. Prefer the authenticated gh login; fall back to the fleet human.
    assignee = (
        _run_git(repo, "config", "--get", "jimek.assignee") or _gh_login() or "tomlupo"
    )

    return {
        "name": name,
        "base": base,
        "trivial_path": trivial_path,
        "live_capital": live_capital,
        "tag_pattern": tag_pattern,
        "release_branch": release_branch,
        "assignee": assignee,
        "has_origin_dev": has_origin_dev,
        "forbids_direct": forbids_direct,
    }


# ── Templating ───────────────────────────────────────────────────────────────
def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def render_jimek_yml(conv: dict) -> str:
    """Render a schema-valid conductor.yml from detected conventions.

    Models the merged reference templates (dispatcher root PR #76 + the per-repo
    dm-evo/quantbox ones). Every value is one the origin/master JimekContract
    accepts; `path` is ALWAYS drawn from VALID_PATHS.
    """
    name = conv["name"]
    base = conv["base"]
    trivial_path = conv["trivial_path"]
    live_capital = conv["live_capital"]
    assignee = conv["assignee"]

    assert trivial_path in VALID_PATHS, f"BUG: illegal trivial path {trivial_path!r}"

    trivial_review = "review: []\n    reviewers_min: 0"
    trivial_note = (
        "tiny docs/config nudge — PR, but no required review"
        if trivial_path == "pr"
        else "tiny docs/config nudge — commit straight to the default branch"
    )

    block_on = "[live_capital, irreversible_op, design_fork]" if live_capital else "[]"
    escalation_note = (
        "live-capital repo — record the canonical triggers; the dispatcher rigor\n"
        "# engine already forces live-capital changes to complex + a Tom gate."
        if live_capital
        else "no auto-escalation today (empty). Opt in by naming ESCALATION_TRIGGERS."
    )

    lc_line = (
        "# This repo is LIVE-CAPITAL — the dispatcher rigor engine already forces\n"
        "# complex + a Tom gate on its changes; this file only records the policy.\n"
        if live_capital
        else ""
    )

    return f"""\
# conductor.yml — dispatch + workflow-policy contract for THIS repo ({name}).
#
# Per-repo instantiation of the JimekContract schema (Jimek Wave 1c), modeled on
# the APPROVED reference template (dispatcher repo-root conductor.yml, PR #76) and
# the merged per-repo contracts (dm-evo / quantbox). It codifies {name}'s
# CURRENT workflow policy — ADDITIVE, describing today's behavior.
#
# Schema + field reference: dispatcher docs/jimek-contract.md. Loaded and
# fail-closed validated by dispatcher.jimek.load_contract; every model is
# extra="forbid" + strict=True, so an unknown key / wrong type is a hard
# JimekError and the repo then has NO contract in effect (dispatch refuses
# rather than defaulting).
#
# Stamped by qute-essentials:jimek-onboard.
{lc_line}
version: 1

# ── Board state machine ──────────────────────────────────────────────────────
board_states:
  active:   {_yaml_list(BOARD_ACTIVE)}
  terminal: {_yaml_list(BOARD_TERMINAL)}

# ── Concurrency caps ─────────────────────────────────────────────────────────
concurrency:
  max_concurrent: {MAX_CONCURRENT}
  by_state:
    Merging: {MERGING_CAP}          # one merge in flight so the flow never races

# ── Rigor tiers ──────────────────────────────────────────────────────────────
# path is ALWAYS one of: commit-to-default | pr  (never "commit").
rigor:
  trivial:                  # {trivial_note}
    path: {trivial_path}
    {trivial_review}
  standard:                 # the DEFAULT flow: coder-pr → codex → independent reviewer
    path: pr
    review: [codex]
    reviewers_min: 1
  complex:                  # risky / architectural / live-capital — adds an independent session review
    path: pr
    review: [codex, independent-session]
    reviewers_min: 1

# ── Worktree mechanism (REFERENCE only) ──────────────────────────────────────
worktree:
  mechanism: qute-essentials
  skill: qute-essentials:worktrees

# ── Run limits ───────────────────────────────────────────────────────────────
turns:
  max: {TURNS_MAX}
  stall_timeout_ms: {STALL_TIMEOUT_MS}

# ── Auto-classification signals (consumed by the rigor classifier) ───────────
classify:
  trivial_globs: ["**/*.md", "docs/**", "**/CHANGELOG*"]
  complex_globs: []
  trivial_max_lines: 15

# ── Wave 1a workflow-policy fields (ADDITIVE; defaults = today's behavior) ────
baseBranch: {base}             # single PR base + worktree fork point

prIdentity:
  coderAppId: 4172326       # qute-coder[bot]  — opens PRs via ~/bin/coder-pr
  reviewAppId: 4172333      # qute-review[bot] — posts the independent verdict (must differ)
  ghAppsDir: "$GHAPPS"

prFlow:
  assignTo: "{assignee}"
  reviewRequestFrom: "{assignee}"
  allowAgentSelfMerge: false
  independentReview: true
  enforce: true

reviewEngine:
  engine: codex
  confidenceThreshold: 0.0
  multiRun: 1
  riskyPaths: []
  mode: auto
  dispatcherUrl: ""
  verdictPrefix: ""

# {escalation_note}
escalation:
  block_on: {block_on}

taskThreshold: 12

release:
  branch: {conv["release_branch"]}
  tagPattern: "{conv["tag_pattern"]}"
  forbiddenPaths: []

adrDir: docs/decisions
adrTemplate: ""
"""


def _review_gate_branches(conv: dict) -> list[str]:
    """The branch names the review-gate must trigger on for THIS repo.

    Rendered from the DETECTED conventions, not hard-coded — a `master`-base repo
    (or any non-`main` default) would otherwise get a `conductor.yml` telling it to
    open PRs to `<base>` while the stamped gate never fires on those PRs (review
    blocker 2026-07-09). We watch the PR base AND the release branch (dev-base
    repos merge dev→main, so the gate must also cover the eventual main PR),
    deduped with a stable order.
    """
    branches: list[str] = []
    for b in (conv["base"], conv["release_branch"]):
        if b and b not in branches:
            branches.append(b)
    return branches or ["main"]


# The single source of truth for review-gate.yml is the canonical template
# committed at ``templates/review-gate.yml`` (repo root, sibling of
# ``plugins/``). jimek-onboard used to stamp its OWN embedded, divergent copy
# here — a drift trap surfaced in #167 / PR #64: the canonical template gained
# a second job (audit-sensitive-paths: gitleaks/semgrep on security-sensitive
# PRs) and onboarded repos silently never inherited it, because this script
# rendered a different file entirely. Fixed in #65: render FROM the canonical
# template and apply only the branch-trigger substitution on top, so onboarded
# repos inherit the canonical gate (incl. future jobs) by construction.
_CANONICAL_REVIEW_GATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "review-gate.yml"
)

# The exact `on:` trigger block in the canonical template — matched verbatim so
# a drift in the canonical file (e.g. a changed event list) fails LOUD instead
# of silently skipping the branch-trigger substitution.
_CANONICAL_PR_TRIGGER = "  pull_request:\n    types: [opened, synchronize, reopened, ready_for_review, labeled, unlabeled]\n"


def render_review_gate_yml(conv: dict) -> str:
    """Render review-gate.yml FROM the canonical templates/review-gate.yml.

    Applies only the branch-trigger substitution on top (repos with a non-`main`
    base/release branch need the gate to actually fire on their PRs — regression
    2026-07-09). Everything else — including any future job added to the
    canonical template — passes through untouched, so onboarded repos can never
    drift from the canonical gate again.
    """
    text = _read_text(_CANONICAL_REVIEW_GATE_PATH)
    if _CANONICAL_PR_TRIGGER not in text:
        raise ValueError(
            "canonical templates/review-gate.yml's pull_request trigger block "
            "has drifted from the expected shape — jimek-onboard's branch "
            "substitution can no longer find its anchor. Update "
            "_CANONICAL_PR_TRIGGER in jimek_onboard.py to match."
        )
    branches = _yaml_list(_review_gate_branches(conv))
    replacement = _CANONICAL_PR_TRIGGER + f"    branches: {branches}\n"
    return text.replace(_CANONICAL_PR_TRIGGER, replacement, 1)


# ── Validation ───────────────────────────────────────────────────────────────
def builtin_validate(yaml_text: str) -> list[str] | None:
    """Bundled, dependency-light structural check.

    Returns a list of errors (empty = clean), or ``None`` when the check could
    not run because PyYAML is absent. ``None`` is a SKIP, not a failure: PyYAML
    is a genuinely optional dependency here (the plugin runs under ambient
    ``python3`` with no dependency-install step), so a missing parser must NOT
    block stamping — the authoritative dispatcher loader (when reachable) still
    gates, and the caller warns. Guards the invariants that bit the W1c fan-out —
    above all that every rigor tier's ``path`` is in VALID_PATHS.
    """
    errors: list[str] = []
    try:
        import yaml  # noqa: PLC0415 — optional dep, imported lazily
    except ImportError:
        return None

    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"]
    if not isinstance(doc, dict):
        return ["top level must be a mapping"]

    if doc.get("version") != 1:
        errors.append(f"version must be 1, got {doc.get('version')!r}")
    for key in ("board_states", "concurrency", "rigor", "worktree", "turns"):
        if key not in doc:
            errors.append(f"missing required key: {key}")

    rigor = doc.get("rigor")
    if not isinstance(rigor, dict) or not rigor:
        errors.append("rigor must be a non-empty mapping")
    else:
        for tier, spec in rigor.items():
            if not isinstance(spec, dict):
                errors.append(f"rigor.{tier} must be a mapping")
                continue
            path = spec.get("path")
            if path not in VALID_PATHS:
                errors.append(
                    f"rigor.{tier}.path={path!r} is invalid — must be one of "
                    f"{sorted(VALID_PATHS)} (the W1c 'commit' bug)"
                )
            review = spec.get("review", [])
            if path == "commit-to-default" and review:
                errors.append(
                    f"rigor.{tier}: commit-to-default cannot require review {review}"
                )
    return errors


def authoritative_validate(yaml_path: Path, dispatcher_repo: Path) -> tuple[bool, str]:
    """Validate via the REAL loader extracted from origin/master of dispatcher.

    Extracts ``src/dispatcher/jimek.py`` from ``origin/master`` (NOT the working
    tree, which can be stale) into a temp module and runs ``load_contract`` on
    the directory holding ``yaml_path``.

    Returns (ok, message). ``ok`` is True on a clean load; a False with a
    "skipped:" message means the loader was unreachable (soft) — the caller
    decides how loud to be. A False without that prefix is a real validation
    failure (hard).
    """
    if not (dispatcher_repo / ".git").exists():
        return False, f"skipped: no dispatcher checkout at {dispatcher_repo}"

    src = subprocess.run(
        [
            "git",
            "-C",
            str(dispatcher_repo),
            "show",
            "origin/master:src/dispatcher/jimek.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if src.returncode != 0:
        return (
            False,
            f"skipped: cannot read origin/master jimek.py ({src.stderr.strip()})",
        )

    try:
        import yaml  # noqa: F401,PLC0415
        import pydantic  # noqa: F401,PLC0415
    except ImportError as e:
        return False, f"skipped: {e.name} not importable for the authoritative loader"

    import importlib.util  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as td:
        mod_path = Path(td) / "jimek_master.py"
        mod_path.write_text(src.stdout, encoding="utf-8")
        # Load as a real module registered in sys.modules so pydantic can resolve
        # the `from __future__ import annotations` forward refs (Literal, …).
        spec = importlib.util.spec_from_file_location("jimek_master", mod_path)
        if spec is None or spec.loader is None:
            return (
                False,
                "skipped: could not build a module spec for origin/master schema",
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules["jimek_master"] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:  # noqa: BLE001
            sys.modules.pop("jimek_master", None)
            return False, f"skipped: could not import origin/master schema module ({e})"

        try:
            contract = module.load_contract(yaml_path.parent)
        except module.JimekError as e:
            return False, str(e)
        finally:
            sys.modules.pop("jimek_master", None)
        return (
            True,
            f"loaded clean: rigor={sorted(contract.rigor)} baseBranch={contract.baseBranch!r}",
        )


# ── Stamping (idempotent, back up + diff, never blind-clobber) ───────────────
def _stamp(
    target: Path, content: str, *, force: bool, dry_run: bool, log: list[str]
) -> None:
    """Write ``content`` to ``target`` idempotently.

    absent            → write (or, in dry-run, report would-create).
    present+identical → skip (idempotent no-op).
    present+differs   → print a unified diff; back up to <name>.bak and write
                        ONLY when ``force``; otherwise leave the file untouched
                        and write <name>.jimek-proposed for review.
    """
    rel = target.name
    if not target.exists():
        log.append(f"  + create {target}")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return

    existing = _read_text(target)
    if existing == content:
        log.append(f"  = unchanged {target}")
        return

    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"{rel} (existing)",
            tofile=f"{rel} (proposed)",
        )
    )
    log.append(f"  ~ differs   {target}")
    log.append("".join(f"      {line}" for line in diff.splitlines(keepends=True)))

    if dry_run:
        return
    if force:
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)
        target.write_text(content, encoding="utf-8")
        log.append(f"    backed up existing → {backup}, wrote new (--force)")
    else:
        proposed = target.with_name(target.name + ".jimek-proposed")
        proposed.write_text(content, encoding="utf-8")
        log.append(
            f"    NOT clobbered; proposal written → {proposed} (re-run with --force to apply)"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="jimek-onboard", description="Make a repo Jimek-managed."
    )
    ap.add_argument("--repo", default=".", help="target repo root (default: cwd)")
    ap.add_argument(
        "--dispatcher-repo",
        default=os.environ.get("DISPATCHER_REPO", str(DEFAULT_DISPATCHER_REPO)),
        help="dispatcher checkout for the authoritative loader",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="detect + render, write nothing"
    )
    ap.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="print the conductor.yml and exit",
    )
    ap.add_argument(
        "--force", action="store_true", help="back up + overwrite existing files"
    )
    ap.add_argument(
        "--no-review-gate", action="store_true", help="do not stamp review-gate.yml"
    )
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not repo.is_dir() or not (repo / ".git").exists():
        print(f"error: {repo} is not a git repo", file=sys.stderr)
        return 2

    conv = detect_conventions(repo)
    jimek_yml = render_jimek_yml(conv)

    # Always run the bundled check before writing anything. A None result means
    # PyYAML is absent → the check is SKIPPED (not failed): warn and continue so
    # the tool still stamps under a plain-python3 runner; the authoritative
    # loader below still gates when a dispatcher checkout is reachable.
    builtin_errors = builtin_validate(jimek_yml)
    if builtin_errors is None:
        print(
            "warning: PyYAML not available — bundled structural check skipped "
            "(the authoritative dispatcher loader still gates if reachable).",
            file=sys.stderr,
        )
    elif builtin_errors:
        print(
            "error: generated conductor.yml failed the bundled structural check:",
            file=sys.stderr,
        )
        for e in builtin_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if args.print_only:
        sys.stdout.write(jimek_yml)
        return 0

    # Authoritative validation against origin/master, if reachable. Validate a
    # throwaway copy so we never leave a file behind when just checking.
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "conductor.yml").write_text(jimek_yml, encoding="utf-8")
        ok, msg = authoritative_validate(
            Path(td) / "conductor.yml", Path(args.dispatcher_repo)
        )
    if ok:
        auth_line = f"authoritative loader (origin/master): OK — {msg}"
    elif msg.startswith("skipped:"):
        auth_line = f"authoritative loader: {msg} (bundled check passed)"
    else:
        print(
            "error: generated conductor.yml is REJECTED by the authoritative loader:",
            file=sys.stderr,
        )
        print(f"  {msg}", file=sys.stderr)
        return 1

    # ── Stamp ────────────────────────────────────────────────────────────────
    log: list[str] = []
    _stamp(
        repo / "conductor.yml",
        jimek_yml,
        force=args.force,
        dry_run=args.dry_run,
        log=log,
    )
    if not args.no_review_gate:
        _stamp(
            repo / ".github" / "workflows" / "review-gate.yml",
            render_review_gate_yml(conv),
            force=args.force,
            dry_run=args.dry_run,
            log=log,
        )

    # ── Summary ──────────────────────────────────────────────────────────────
    print("jimek-onboard — detected conventions:")
    print(f"  repo            {conv['name']}")
    print(f"  baseBranch      {conv['base']}")
    print(f"  trivial path    {conv['trivial_path']}")
    print(f"  live-capital    {conv['live_capital']}")
    print(f"  assignee        {conv['assignee']}")
    print(f"  release tag     {conv['tag_pattern']} on {conv['release_branch']}")
    print(f"  {auth_line}")
    print()
    print("stamped:" if not args.dry_run else "would stamp (dry-run):")
    for line in log:
        print(line)
    # ── Fleet rules advisory (item 4 — non-clobbering) ───────────────────────
    # We deliberately do NOT write into .claude here: the rules are stamped by
    # /setup-qute-repo (ADR-0005 §5); blindly copying them into a target repo
    # risks clobbering repo-specific config. Instead we report what's missing so
    # the operator wires it deliberately.
    advisories: list[str] = []
    if not (repo / ".claude" / "rules").is_dir():
        advisories.append(
            "no .claude/rules — run /setup-qute-repo to stamp the behavioral core"
        )
    if (repo / ".github" / "qute-pr.yml").is_file():
        advisories.append(
            "STALE .github/qute-pr.yml present — delete it (ADR-0005: the rigor tier "
            "in conductor.yml is the sole merge authority; the gate no longer reads it)"
        )

    print()
    print("next steps:")
    print("  1. review conductor.yml (and any *.jimek-proposed)")
    print(
        f"  2. commit on a branch, then open a PR to `{conv['base']}` via /qute-coder"
    )
    if advisories:
        print("  3. (optional) wire the fleet rules/guards — none clobbered:")
        for a in advisories:
            print(f"       - {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
