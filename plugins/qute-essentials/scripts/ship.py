"""/ship — universal release command.

One entry point, two modes (detected automatically):

Either mode refuses to release if any tracked file lives under a forbidden
path — that gate runs before dispatch, so it is a property of /ship rather
than of one mode.

* **Plugin mode** — `.claude-plugin/marketplace.json` at repo root.
  Delegates to `scripts/release-plugin.sh <plugin> <bump>`.
* **Python mode** — `pyproject.toml` at repo root (and no marketplace).
  Additionally refuses if the tracked working tree is dirty, runs
  first-time-setup idempotently, then bumps.

Python mode drives commitizen in **files-only** mode
(`cz bump --yes --changelog --version-files-only`): cz rewrites the version
files and `CHANGELOG.md` but creates neither commit nor tag. This script then
creates the bump commit and an **annotated** tag itself. One tagging path,
owned here — a lightweight tag is silently skipped by `git push
--follow-tags`, so a release can otherwise look cut while never leaving the
machine.

**Bump and tag are separate acts, and the branch selects which one happens**
(ADR-0008). On the integration branch `/ship` bumps and commits, no tag; on
the release branch of a two-stage repo `/ship --tag` completes the release;
in a single-stage repo the release branch still bumps and tags in one go. Any
other branch is refused — a feature branch has no legitimate release.

Webapps (`package.json`) use `gstack ship` instead.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import string
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# Universal forbidden paths — skill-generated artifacts that must not reach main.
# Project-specific additions live in .claude/forbidden-paths.txt (one per line).
UNIVERSAL_FORBIDDEN = (
    "docs/superpowers",
    "docs/specs",
    ".claude/handoffs",
    ".claude/skill-use-log.jsonl",
)

BUMP_KINDS = {"patch", "minor", "major"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# House rule (ADR-0008 §5): releases are cut from `main`, integration happens on
# `dev`, and the topology is derived from whether `origin/dev` exists. A repo's
# `conductor.yml` may declare `release.branch`, and that declaration wins — the
# release tool and the dispatch policy must not silently disagree.
DEFAULT_RELEASE_BRANCH = "main"
DEFAULT_INTEGRATION_BRANCH = "dev"
CONDUCTOR_FILES = ("conductor.yml", "conductor.yaml")

# Tried in order when no contract declares a release branch, and ONLY as an
# existence test — the first of these the repo actually has is its release
# branch. `main` is the house rule; `master` is here because refusing every
# branch of a pre-`main` repo would be a release tool that cannot release. Three
# repos in this fleet (atlas, qute-platform, forgejo-review-kit) are `master`
# with no `main` and no contract, and a gate that locks them out is a worse
# defect than the one it prevents. This is deliberately NOT `origin/HEAD`, which
# ADR-0008 rejected as unreliable: it is unset in a good share of real clones,
# and a release branch resolved from an unset ref is a wrong answer rather than
# a missing one.
RELEASE_BRANCH_CANDIDATES = ("main", "master")

# The three things /ship can do. The branch picks one; the flags override.
MODE_BUMP_ONLY = "bump-only"
MODE_BUMP_AND_TAG = "bump-and-tag"
MODE_TAG = "tag"

# commitizen's own defaults — mirrored so the history a repo already has stays
# continuous when ship.py takes over commit/tag creation from cz.
DEFAULT_TAG_FORMAT = "v$version"
BUMP_MESSAGE = "bump: version $current_version → $new_version"
DEFAULT_CHANGELOG_FILE = "CHANGELOG.md"


def info(msg: str) -> None:
    print(f"ship: {msg}")


def fail(msg: str) -> int:
    print(f"ship: error: {msg}", file=sys.stderr)
    return 1


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


USAGE = """\
Usage:
  /ship [--dry-run]                                  # Python: auto-bump from commits
  /ship [patch|minor|major|X.Y.Z] [--dry-run]        # Python: forced bump
  /ship --tag [X.Y.Z] [--dry-run]                    # Python: tag an already-bumped release
  /ship [<plugin>] <patch|minor|major|X.Y.Z>         # Plugin: delegate to release-plugin.sh

Detects mode by repo root:
  .claude-plugin/marketplace.json → plugin mode
  pyproject.toml                  → python mode

The BRANCH selects bump-vs-tag (ADR-0008); no flag is required:
  integration branch (`dev`)      → bump + changelog + lockfile + commit, NO tag
  release branch, two-stage repo  → `--tag` completes the release (creates + pushes it)
  release branch, single-stage    → bump and tag together
  any other branch                → refused; a feature branch has no release

Explicit overrides: --bump-only, --bump-and-tag, --tag.
"""


def main() -> int:
    args = sys.argv[1:]
    if any(a in {"-h", "--help"} for a in args):
        print(USAGE)
        return 0

    root = Path.cwd()

    marketplace_json = root / ".claude-plugin" / "marketplace.json"
    pyproject = root / "pyproject.toml"

    # Forbidden-paths gate, enforced HERE — at the single point where the modes
    # diverge — rather than inside one of them. It used to live in
    # `ship_python()` only, so plugin mode dispatched straight to
    # release-plugin.sh and cut releases with skill artifacts tracked, while
    # SKILL.md advertised the refusal as a property of /ship. (qute-code-kit is
    # itself a plugin-mode repo, so it had no protection at all.) A gate that
    # applies to "a release" belongs above the branch that picks how to make
    # one; putting it here also means a future third mode cannot silently skip
    # it. It is a pure `git ls-files` read, so it is safe ahead of either
    # mode's own preconditions — neither writes before validating its args.
    #
    # Deliberately after project-type detection: a repo /ship cannot ship at
    # all should hear that, not a lecture about forbidden paths.
    if marketplace_json.exists() or pyproject.exists():
        if rc := check_forbidden_paths(root):
            return rc

    if marketplace_json.exists():
        return ship_plugin(root, marketplace_json, args)

    if pyproject.exists():
        return ship_python(root, pyproject, args)

    if (root / "package.json").exists():
        return fail(
            "package.json detected — webapps are handled by `gstack ship`, not `/ship`."
        )

    if (root / "Cargo.toml").exists():
        return fail("Cargo.toml detected — Rust is not yet supported.")

    return fail(
        "no supported project type detected. "
        "/ship requires `.claude-plugin/marketplace.json` (plugin mode) "
        "or `pyproject.toml` (Python mode) at the repo root."
    )


# ---------------------------------------------------------------------------
# Branch topology — which branch releases, which one integrates
# ---------------------------------------------------------------------------


class Topology(NamedTuple):
    """Where a release comes from in this repo, and where we are standing.

    `integration is None` means a **single-stage** repo: one branch, releases
    cut on it, bump and tag in one act. `current is None` inside a git repo
    means a detached HEAD, which is not a branch and therefore not a release.
    """

    release: str
    integration: str | None
    current: str | None
    in_git: bool
    # False when the resolved release branch does not exist in this repo at
    # all. The refusal then has to say something different — "you are on the
    # wrong branch" is unhelpful when the right one does not exist.
    release_exists: bool = True

    @property
    def two_stage(self) -> bool:
        return self.integration is not None


def _git_out(root: Path, *args: str) -> str | None:
    """`git -C root <args>` stdout, stripped. None if git failed or is absent."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip()


def current_branch(root: Path) -> tuple[bool, str | None]:
    """`(inside a git repo, branch name)`. Branch is None on a detached HEAD."""
    if _git_out(root, "rev-parse", "--git-dir") is None:
        return (False, None)
    return (True, _git_out(root, "symbolic-ref", "--quiet", "--short", "HEAD") or None)


def conductor_release_branch(root: Path) -> str | None:
    """`release.branch` from the repo's `conductor.yml`, if it declares one.

    `conductor.yml` is jimek's dispatch contract, not /ship's (ADR-0008 §10):
    this READS one key and interoperates. Where a repo has declared which
    branch it releases from, the release tool must use the same answer as the
    dispatch policy — two sources of truth for one fact is the drift class this
    whole ADR is about.
    """
    for name in CONDUCTOR_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if branch := _release_branch_from_yaml(text):
            return branch
    return None


def _release_branch_from_yaml(text: str) -> str | None:
    """`release.branch` out of a YAML document, with or without PyYAML.

    ship.py runs under whatever interpreter `run-hook` finds, with no
    guaranteed dependencies, so it cannot require PyYAML. It uses it when it is
    importable — the real parser, right about anchors, quoting and flow style —
    and otherwise falls back to a scan for a top-level `release:` block. The
    fallback is deliberately narrow: it reads one key out of a file whose shape
    is fixed by the contract schema, and returns None on anything it does not
    recognise (which lands on the house default, not on a wrong branch).
    """
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        # Not installed, or installed and broken. Either way the scan below is
        # the answer — `except ModuleNotFoundError` would let a half-installed
        # PyYAML take /ship down over one optional config key.
        pass
    else:
        try:
            data = yaml.safe_load(text)
        except Exception:  # malformed YAML — fall through to the scan
            data = None
        else:
            release = data.get("release") if isinstance(data, dict) else None
            branch = release.get("branch") if isinstance(release, dict) else None
            return (
                branch.strip() if isinstance(branch, str) and branch.strip() else None
            )

    in_release = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[:1].isspace():  # a top-level key ends any block we were in
            in_release = re.match(r"^release\s*:\s*(#.*)?$", line) is not None
            continue
        if not in_release:
            continue
        m = re.match(r"^\s+branch\s*:\s*(.+?)\s*(?:#.*)?$", line)
        if m:
            value = m.group(1).strip().strip("\"'")
            return value or None
    return None


def resolve_topology(root: Path) -> Topology:
    """The repo's release topology and the branch we are standing on.

    Two-stage is derived from `origin/dev` existing, per ADR-0008 §5 — a purely
    local ref read, no network. `origin/HEAD` was considered and rejected for
    this job: it is unset in a good share of real clones, so depending on it
    would silently mis-answer rather than fail.
    """
    in_git, current = current_branch(root)

    declared = conductor_release_branch(root)
    if declared:
        # A declaration is authoritative even for a branch that does not exist
        # locally yet — the repo said which branch releases, and /ship is not
        # entitled to second-guess the dispatch contract.
        release, release_exists = declared, True
    elif not in_git:
        release, release_exists = DEFAULT_RELEASE_BRANCH, True
    else:
        found = next(
            (b for b in RELEASE_BRANCH_CANDIDATES if _branch_exists(root, b)), None
        )
        release, release_exists = (found or DEFAULT_RELEASE_BRANCH), found is not None

    integration: str | None = None
    if in_git and DEFAULT_INTEGRATION_BRANCH != release:
        ref = f"refs/remotes/origin/{DEFAULT_INTEGRATION_BRANCH}"
        if _git_out(root, "rev-parse", "--verify", "--quiet", ref):
            integration = DEFAULT_INTEGRATION_BRANCH

    return Topology(release, integration, current, in_git, release_exists)


def _branch_exists(root: Path, name: str) -> bool:
    """True if `name` exists locally or on `origin`.

    Either is enough: a fresh clone that has never checked out the release
    branch still has `origin/<branch>`, and a local-only repo has only
    `refs/heads/<branch>`.
    """
    return any(
        _git_out(root, "rev-parse", "--verify", "--quiet", ref)
        for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}")
    )


def _wrong_branch_message(topo: Topology, *, verb: str = "release") -> str:
    """Why this branch cannot {verb}, and where to go instead."""
    if not topo.release_exists:
        return (
            "cannot tell which branch this repo releases from. It has no "
            f"{' and no '.join('`' + b + '`' for b in RELEASE_BRANCH_CANDIDATES)}, "
            "and no `conductor.yml` declaring `release.branch`.\n"
            f"  Refusing to {verb}; nothing was written. Declare it once, in "
            "`conductor.yml`:\n"
            "    release:\n"
            "      branch: <the branch this repo releases from>\n"
            "  That is the same key jimek's dispatch policy reads, so the two "
            "cannot disagree."
        )
    where = (
        f"`{topo.integration}` (bump) then `{topo.release}` (`/ship --tag`)"
        if topo.two_stage
        else f"`{topo.release}`"
    )
    return (
        f"`{topo.current}` is neither the release branch (`{topo.release}`) nor "
        f"the integration branch "
        f"({'`' + topo.integration + '`' if topo.two_stage else 'none — single-stage repo'}). "
        f"Refusing to {verb}; nothing was written.\n"
        f"  A feature branch has no legitimate release. Bumping here computes the\n"
        f"  changelog from a branch that is usually behind integration — release\n"
        f"  metadata describing code that is not the release — and leaves the new\n"
        f"  version untagged, which blocks the next real release.\n"
        f"  Release from {where}."
    )


def resolve_mode(
    topo: Topology, requested: str | None
) -> tuple[str | None, str | None]:
    """`(mode, refusal)` — exactly one is None.

    The branch selects the mode. The prior failure this replaces was a
    correctly-documented convention that someone did not apply in the moment,
    and a flag reproduces that failure shape exactly; you cannot not be on a
    branch. `requested` is the explicit override, and it can pick the ACT but
    never unlock a branch that has no release.
    """
    if not topo.in_git:
        # No branch to select on (and no git to tag with). Today's behaviour,
        # unchanged: the commit/tag steps fail loudly on their own if it
        # matters. Refusing here would break `/ship` inside a plain directory
        # for a reason that is not about releases.
        return (requested or MODE_BUMP_AND_TAG, None)

    if topo.current is None:
        return (
            None,
            "HEAD is detached, so there is no branch to release from. "
            f"Check out `{topo.release}` (or `{topo.integration or topo.release}`) "
            "and re-run; nothing was written.",
        )

    on_release = topo.current == topo.release
    on_integration = topo.two_stage and topo.current == topo.integration

    if not (on_release or on_integration):
        return (None, _wrong_branch_message(topo))

    # Every override that CREATES A TAG is confined to the release branch.
    #
    # `--bump-and-tag` used to be allowed anywhere a release was allowed, which
    # left the incident's exact shape reachable behind one flag: a tag cut on
    # `dev`, naming a commit a squash-merge never makes an ancestor of `main`.
    # An override that reintroduces the failure the ADR removes is the failure,
    # explicitness notwithstanding — and there is no case it serves. Its reason
    # for existing is a hotfix bumped and tagged straight ON the release branch
    # of a two-stage repo, which this still permits. `--bump-only` writes no tag
    # and stays available on either branch.
    if requested in (MODE_TAG, MODE_BUMP_AND_TAG) and not on_release:
        flag = "--tag" if requested == MODE_TAG else "--bump-and-tag"
        return (
            None,
            f"`{flag}` creates the release tag, which belongs on `{topo.release}`; "
            f"you are on `{topo.current}`.\n"
            f"  A tag cut here names a commit that a squash-merge never makes an "
            f"ancestor of\n"
            f"  `{topo.release}` — the tag would name code the release branch does "
            f"not contain.\n"
            f"  Bump here (`/ship` or `/ship --bump-only`), merge the release PR, "
            f"then run\n"
            f"  `/ship --tag` on `{topo.release}`. Nothing was written.",
        )

    if requested in (MODE_TAG, MODE_BUMP_ONLY, MODE_BUMP_AND_TAG):
        return (requested, None)

    if on_integration:
        return (MODE_BUMP_ONLY, None)

    if topo.two_stage:
        return (
            None,
            f"`{topo.release}` is the release branch of a two-stage repo "
            f"(`{topo.integration}` -> `{topo.release}`), so a bump does not belong here.\n"
            f"  Bump on `{topo.integration}`, merge the release PR, then complete the\n"
            f"  release here with:\n"
            f"    /ship --tag\n"
            f"  If you really mean to bump AND tag on `{topo.release}` (a hotfix cut\n"
            f"  directly on the release branch), say so explicitly:\n"
            f"    /ship --bump-and-tag",
        )

    return (MODE_BUMP_AND_TAG, None)


# ---------------------------------------------------------------------------
# Plugin mode
# ---------------------------------------------------------------------------


def ship_plugin(root: Path, marketplace_json: Path, args: list[str]) -> int:
    with open(marketplace_json) as f:
        marketplace = json.load(f)

    plugins = [p["name"] for p in marketplace.get("plugins", [])]
    if not plugins:
        return fail(f"{marketplace_json.relative_to(root)} has no plugins")

    if len(args) == 2:
        plugin_name, bump_spec = args
    elif len(args) == 1:
        if len(plugins) > 1:
            return fail(
                f"marketplace has multiple plugins ({', '.join(plugins)}); "
                "specify name: /ship <plugin> <patch|minor|major|X.Y.Z>"
            )
        plugin_name = plugins[0]
        bump_spec = args[0]
    else:
        return fail("usage: /ship [<plugin>] <patch|minor|major|X.Y.Z>")

    if plugin_name not in plugins:
        return fail(
            f"plugin '{plugin_name}' not in marketplace; available: {', '.join(plugins)}"
        )

    if bump_spec not in BUMP_KINDS and not SEMVER_RE.match(bump_spec):
        return fail(
            f"bump spec '{bump_spec}' must be patch|minor|major or explicit X.Y.Z"
        )

    # Branch gate. Plugin mode has no bump/tag split to select between —
    # `release-plugin.sh` owns the whole release and does both in one step — so
    # the only question the branch answers here is whether a release is
    # legitimate at all. Requiring the release branch is the half of ADR-0008 §2
    # that applies: a feature branch has no release in either mode. The other
    # half (bump-only on the integration branch) is deliberately NOT invented
    # for a script this file does not own; a two-stage plugin repo is refused
    # with a message saying so rather than silently bumping-and-tagging on the
    # wrong branch, which is the defect this ADR exists to remove.
    topo = resolve_topology(root)
    if topo.in_git and topo.current != topo.release:
        where = topo.current or "a detached HEAD"
        return fail(
            f"plugin releases are cut on `{topo.release}`; you are on `{where}`. "
            "Nothing was written.\n"
            "  Plugin mode delegates to scripts/release-plugin.sh, which bumps and "
            "tags in ONE step,\n"
            "  so there is no bump/tag split to run from an integration branch. "
            f"Check out `{topo.release}` and re-run."
        )

    release_script = root / "scripts" / "release-plugin.sh"
    if not release_script.exists():
        return fail(f"{release_script.relative_to(root)} not found")

    try:
        run(["bash", str(release_script), plugin_name, bump_spec])
    except subprocess.CalledProcessError as exc:
        return fail(f"release-plugin.sh failed with exit code {exc.returncode}")
    return 0


# ---------------------------------------------------------------------------
# Python mode
# ---------------------------------------------------------------------------


def parse_python_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="/ship", add_help=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--increment", choices=sorted(BUMP_KINDS))
    # The three overrides are mutually exclusive: each names a different act,
    # and a combination has no meaning to resolve. They exist for the cases the
    # branch cannot express (a hotfix bumped and tagged straight on the release
    # branch; a deliberate bump-only in a single-stage repo) — never as the
    # default path, which must need nothing remembered.
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--tag", dest="mode", action="store_const", const=MODE_TAG, default=None
    )
    mode_group.add_argument(
        "--bump-only", dest="mode", action="store_const", const=MODE_BUMP_ONLY
    )
    mode_group.add_argument(
        "--bump-and-tag", dest="mode", action="store_const", const=MODE_BUMP_AND_TAG
    )
    parsed, leftover = parser.parse_known_args(args)
    parsed.version = None
    for a in leftover:
        if SEMVER_RE.match(a):
            parsed.version = a
        elif a in BUMP_KINDS:
            parsed.increment = a
        else:
            parser.error(f"unknown argument: {a}")
    if parsed.mode == MODE_TAG and parsed.increment:
        parser.error(
            "--tag names an existing bump; it cannot also compute one. "
            "Drop the increment, or bump first and tag afterwards."
        )
    return parsed


def ship_python(root: Path, pyproject: Path, args: list[str]) -> int:
    parsed = parse_python_args(args)

    # 1. Forbidden-paths check — now enforced in `main()`, before mode
    #    dispatch, so plugin mode gets it too. Not repeated here.

    # 1b. Branch gate, FIRST of everything that could write. `setup_python`
    #     below legitimately edits pyproject.toml and creates CHANGELOG.md, so a
    #     refusal decided after it would already have written to a branch that
    #     has no release. "Refuses, writing nothing" is only true if the gate
    #     runs here.
    topo = resolve_topology(root)
    mode, refusal = resolve_mode(topo, parsed.mode)
    if refusal:
        return fail(refusal)

    if mode == MODE_TAG:
        return ship_tag(root, pyproject, topo, parsed)

    # 2. Clean-tree gate. Deliberately BEFORE setup: setup legitimately writes
    #    to pyproject.toml / CHANGELOG.md, so checking afterwards would trip on
    #    its own edits. Everything from here on is either a write or a commit.
    #    Under --dry-run this reports the dirty paths instead of refusing —
    #    nothing it produces can be contaminated, since it creates nothing.
    if rc := check_clean_worktree(root, dry_run=parsed.dry_run):
        return rc

    # 2b. In-flight guard, deliberately BEFORE setup — setup WRITES, and a
    #     refusal that has already edited `pyproject.toml` sends the next run
    #     into the clean-tree gate for an unrelated reason. (Observed: refuse,
    #     then refuse again with a different message on a tree the user never
    #     touched.) Read-only cz resolution for the same reason: this needs only
    #     the tag NAME for a version already declared, and `uv run cz` would
    #     materialize `.venv` on the way to refusing.
    #
    #     Pre-setup is also the RIGHT version to test. Setup's own reconciliation
    #     legitimately moves the declared version past the last tag (seeding cz
    #     from the highest of {project version, latest tag, literals}), and must
    #     not be blocked by the very run that performs it.
    guard_cz = resolve_cz(root, dry_run=True) or ["cz"]
    if rc := check_bump_in_flight(
        root,
        guard_cz,
        _read_cz_config(pyproject),
        declared_version(root, pyproject, guard_cz),
    ):
        return rc

    # 3. First-time setup — idempotent; safe to call every time. Under
    #    --dry-run it stays read-only: it still reads, queries git and computes
    #    the reconciled seed version, but reports every write instead of making
    #    it, so a dry run leaves the working tree exactly as it found it.
    from ship_setup import setup_python

    if rc := setup_python(root, pyproject, dry_run=parsed.dry_run):
        return rc

    # 3b. A dry run against an unconfigured repo stops here. Setup only
    #     *reported* the `[tool.commitizen]` block it would create, so there is
    #     no config for cz to bump against — and reaching for cz via `uv run`
    #     would materialize `.venv`/`uv.lock`, i.e. write to the very tree the
    #     dry run promised to leave alone.
    if parsed.dry_run and "[tool.commitizen]" not in pyproject.read_text(
        encoding="utf-8"
    ):
        info(
            "dry run complete; setup has not been applied yet, so the bump "
            "itself was not simulated. No files written, no commit or tag "
            "created."
        )
        return 0

    # 4. Build the cz command.
    #
    # `--version-files-only` makes cz a pure file rewriter: it bumps every
    # `version_files` entry AND the `[tool.commitizen] version` field, writes
    # the changelog, and then stops — no commit, no tag, changes left in the
    # working tree. Commit and tag creation happen below, in this script, so
    # there is exactly ONE tagging path and it always produces an annotated tag.
    cz = resolve_cz(root, dry_run=parsed.dry_run)
    if cz is None:
        if parsed.dry_run:
            return fail(
                "cannot simulate the bump without writing to the working tree.\n"
                "  A dry run promises to leave the tree exactly as it found it, and the\n"
                "  only commitizen reachable here is `uv run cz` — which materializes\n"
                "  `.venv` (and can write `uv.lock`) before cz ever executes.\n"
                "  Give the dry run a cz that already exists, then re-run:\n"
                "    uv sync                 # populates .venv/bin/cz\n"
                "    uv tool install commitizen   # or put cz on PATH\n"
                "  A real release (without --dry-run) may use `uv run cz` and will."
            )
        return fail("neither `uv` nor `cz` found on PATH. Install commitizen or uv.")

    cmd = [*cz, "bump", "--yes", "--changelog", "--version-files-only"]

    if parsed.dry_run:
        cmd.append("--dry-run")
    if parsed.increment:
        cmd += ["--increment", parsed.increment.upper()]
    if parsed.version:
        cmd.append(parsed.version)

    cz_config = _read_cz_config(pyproject)
    old_version = _current_version(root, pyproject, cz)

    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        return fail(f"commitizen bump failed with exit code {exc.returncode}")

    if parsed.dry_run:
        info("dry run complete; no files written, no commit or tag created.")
        return 0

    # 5. Create the bump commit — cz's own default message, so `git log` reads
    #    continuously across the handover.
    new_version = _current_version(root, pyproject, cz)
    if not new_version:
        return fail(
            "could not read the bumped version from pyproject.toml after cz bump; "
            "the version files were rewritten but no commit or tag was created."
        )
    if old_version == new_version:
        return fail(
            f"cz bump left the version unchanged at {new_version}; "
            "no commit or tag created."
        )

    # 5b. Refresh the lockfile INTO the bump commit. The version the project
    #     declares is pinned in its own lockfile, so a bump that leaves the lock
    #     stale ships a release whose lock disagrees with it — and the next
    #     `uv sync --frozen` (or a lockfile-check CI job) fails on a tree nobody
    #     touched. Best-effort by contract: a refresh failure warns, it does not
    #     block an otherwise correct release.
    refresh_lockfile(root)

    message = (
        string.Template(BUMP_MESSAGE)
        .safe_substitute(current_version=old_version or "?", new_version=new_version)
        .strip()
    )
    if rc := git_commit_bump(root, pyproject, cz_config, message):
        return rc

    # 5c. Two-stage repo, integration branch: STOP here. The tag belongs on the
    #     release branch, after this bump has merged into it — see ADR-0008 §1.
    #     A tag cut here names a commit that a squash-merge will never make an
    #     ancestor of the release branch, which is exactly the quantbox v0.4.0
    #     incident.
    if mode == MODE_BUMP_ONLY:
        wipe_tasks_completed(root, pyproject)
        report_bump_only(topo, old_version, new_version)
        return 0

    # 6. Create the tag — ALWAYS annotated. `git push --follow-tags` silently
    #    ignores lightweight tags, so a release cut with one never leaves the
    #    machine; making it annotated here removes the dependency on a config
    #    key (`annotated_tag`) being set correctly in every consuming repo.
    tag = resolve_tag(root, cz, cz_config, new_version)
    tag_message = build_tag_message(root, cz_config, tag, new_version)
    try:
        # `--cleanup=whitespace` because the default (`strip`) treats lines
        # beginning with `#` as comments and deletes them — which silently eats
        # the `### Feat` / `### Fix` headings out of a markdown changelog body.
        run(
            [
                "git",
                "-C",
                str(root),
                "tag",
                "-a",
                "--cleanup=whitespace",
                tag,
                "-m",
                tag_message,
            ]
        )
    except subprocess.CalledProcessError as exc:
        return fail(f"`git tag -a {tag}` failed with exit code {exc.returncode}")
    info(f"created annotated tag {tag}")

    # 7. Wipe TASKS.md::Completed sections — canonical now in CHANGELOG.md.
    #    Deliberately AFTER the tag: its follow-up commit must land on top of
    #    the bump commit and must not be captured by the release tag.
    wipe_tasks_completed(root, pyproject)

    info(
        "done. Review the bump commit and tag, then `git push --follow-tags` when ready."
    )
    return 0


# ---------------------------------------------------------------------------
# `--tag` — completing a two-stage release
# ---------------------------------------------------------------------------


def ship_tag(
    root: Path, pyproject: Path, topo: Topology, parsed: argparse.Namespace
) -> int:
    """Create and push the release tag for a bump that has already merged.

    Five preconditions, all asserted before anything is created:

      1. the tree is clean, so the release this tag names is the committed one;
      2. the remote is reachable and has been fetched;
      3. the local release branch matches its remote — the tag must name the
         commit everyone else can see, not a local one;
      4. the version declared at the TIP is the one this tag names, and matches
         any explicit `X.Y.Z` given;
      5. the tag does not already exist.

    Then it tags and **pushes**. Not pushing fails silently and late: the tag
    sits local, everything looks green, and it surfaces when a consumer cannot
    resolve the ref. Pushing fails loudly and immediately, because the
    release-tag-guard workflow asserts on push that the tagged commit is an
    ancestor of the release branch.

    Deliberately does NOT run first-time setup: it writes, and there is nothing
    here to set up.

    **The clean-tree gate does run**, contrary to the first version of this
    function, which skipped it on the reasoning that "a tag names a commit, so a
    dirty file cannot ride into it". That reasoning covered the version and
    nothing else, and review found the hole: a tag is *rendered* from
    `tag_format`, which lives in `pyproject.toml`, which cz reads from the
    WORKING TREE. Reproduced before fixing — an uncommitted
    `tag_format = "release-$version"` over a committed `v$version` made
    `/ship --tag` create and PUSH `release-0.2.0`, a tag name the released
    commit never defined. `changelog_file` and the changelog body carried into
    the tag message have the same shape.

    Requiring the whole tree clean rather than enumerating "release metadata"
    files is deliberate: any such list is a partial rule that drifts out of step
    with what cz actually reads, which is how this bug existed in the first
    place. Being too strict costs a `git stash`; being too lax publishes a
    mis-named release tag that consumers pin.
    """
    # ── 1. Clean tree ───────────────────────────────────────────────────────
    if rc := check_clean_worktree(root, dry_run=parsed.dry_run, why=TAG_DIRTY_REASON):
        return rc

    cz_config = _read_cz_config(pyproject)
    # Read-only cz resolution even though this is not a dry run: `uv run cz`
    # materializes `.venv` before cz executes, and tagging an existing commit
    # has no business writing to the tree. Absent cz, `resolve_tag` falls back
    # to local rendering and says so.
    cz = resolve_cz(root, dry_run=True) or ["cz"]

    remote = _remote_name(root)
    if remote is None and (configured := _remotes(root)):
        return fail(
            "cannot tell which remote to publish this release to: "
            f"{', '.join('`' + r + '`' for r in configured)}, and none is named "
            "`origin`.\n"
            "  `--tag` verifies against a remote and pushes to it, so guessing is "
            "not an option\n"
            "  and proceeding without one would silently skip both. Name the "
            "publishing remote\n"
            "  `origin`, or run the tag step from a clone that has one. Nothing "
            "was created."
        )

    # ── 2. Fetch ────────────────────────────────────────────────────────────
    if remote:
        if _git_out(root, "fetch", "--quiet", "--tags", remote) is None:
            return fail(
                f"could not fetch from `{remote}`.\n"
                "  `--tag` pushes the tag it creates, and it must first confirm this\n"
                "  branch matches the remote — neither is possible offline. Unlike the\n"
                "  in-flight guard's best-effort fetch, this one is required: creating a\n"
                "  release tag against an unverified remote is how a tag ends up naming\n"
                "  code the release branch does not contain.\n"
                "  Reconnect and re-run."
            )
    else:
        info(
            "no git remote is configured; skipping the remote-sync check and the "
            "push. The tag will exist only in this repo."
        )

    # ── 3. Local branch matches its remote ──────────────────────────────────
    if remote:
        local = _git_out(root, "rev-parse", "HEAD")
        upstream = _git_out(
            root,
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/{remote}/{topo.current}",
        )
        if not upstream:
            return fail(
                f"`{topo.current}` has no counterpart on `{remote}` "
                f"(no `{remote}/{topo.current}`). A release tag must name a commit "
                "the remote already has; push the branch first."
            )
        if local != upstream:
            ahead_behind = (
                _git_out(
                    root,
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"HEAD...{remote}/{topo.current}",
                )
                or "?\t?"
            ).split()
            ahead, behind = (ahead_behind + ["?", "?"])[:2]
            return fail(
                f"`{topo.current}` does not match `{remote}/{topo.current}` "
                f"({ahead} commit(s) ahead, {behind} behind).\n"
                "  The tag would name a commit the remote does not have, or miss one it\n"
                "  does. Bring them into sync (`git pull --ff-only` / `git push`) and\n"
                "  re-run; nothing was created."
            )

    # ── 4. The version at the tip is the version being tagged ───────────────
    tip_version = _version_at_tip(root, pyproject)
    if not tip_version:
        return fail(
            "could not read the declared version from the commit at the tip of "
            f"`{topo.current}`. Nothing was created."
        )

    # The version still comes from the TIP rather than the tree, because that
    # is what the tag means. A tree-vs-tip comparison used to sit here as the
    # defence against a dirty version; the clean-tree gate above now makes the
    # two provably equal, so that comparison could no longer be made to fire
    # through the CLI. It is gone rather than kept: an assertion no test can
    # trigger is a claim of safety, not safety — the same reason the `ls-remote`
    # check below was removed.
    tag = resolve_tag(root, cz, cz_config, tip_version)

    if parsed.version and parsed.version != tip_version:
        return fail(
            f"asked to tag {parsed.version}, but the tip of `{topo.current}` declares "
            f"{tip_version} (tag `{tag}`).\n"
            "  Either the bump has not merged yet, or the version you named is not the\n"
            "  one this branch is at. Nothing was created."
        )

    # ── 5. The tag does not already exist ───────────────────────────────────
    #
    # The LOCAL ref list is authoritative here only because step 2 fetched
    # `--tags` and refused to continue if it could not: a tag pushed from
    # another machine is local by the time this runs. A second `ls-remote`
    # check was written and removed — after a required fetch there is no state
    # it can see that this one cannot, and an assertion that no test can make
    # fire is a claim of safety rather than safety.
    if _git_out(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"):
        return fail(
            f"tag `{tag}` already exists"
            + (f" (locally or on `{remote}`)" if remote else " locally")
            + ". The release it names has already been cut; bump again before "
            "tagging again. Nothing was created."
        )

    tag_message = build_tag_message(root, cz_config, tag, tip_version)

    if parsed.dry_run:
        info(
            f"dry run: all preconditions pass; would create annotated tag `{tag}` "
            f"at {(_git_out(root, 'rev-parse', '--short', 'HEAD') or 'HEAD')}"
            + (f" and push it to `{remote}`." if remote else ".")
        )
        info("dry run complete; nothing was created or pushed.")
        return 0

    try:
        # `--cleanup=whitespace` for the same reason the bump path uses it: the
        # default strips `#`-leading lines, eating markdown headings out of the
        # changelog body carried in the message.
        run(
            [
                "git",
                "-C",
                str(root),
                "tag",
                "-a",
                "--cleanup=whitespace",
                tag,
                "-m",
                tag_message,
            ]
        )
    except subprocess.CalledProcessError as exc:
        return fail(f"`git tag -a {tag}` failed with exit code {exc.returncode}")
    info(f"created annotated tag {tag}")

    if not remote:
        info("no remote to push to; the tag is local only.")
        return 0

    try:
        run(["git", "-C", str(root), "push", remote, tag])
    except subprocess.CalledProcessError as exc:
        return fail(
            f"`git push {remote} {tag}` failed with exit code {exc.returncode}.\n"
            f"  The tag EXISTS locally. Push it (`git push {remote} {tag}`) or delete it\n"
            f"  (`git tag -d {tag}`) — an unpushed release tag looks green here and "
            "fails\n  for everyone else."
        )
    info(f"pushed {tag} to {remote}. Release complete.")
    return 0


def _remotes(root: Path) -> list[str]:
    """Every configured remote, in git's order."""
    listed = _git_out(root, "remote")
    return [r for r in (listed or "").splitlines() if r.strip()]


def _remote_name(root: Path) -> str | None:
    """`origin` if configured, else the sole remote, else None.

    **None is ambiguous on purpose-free reading and must not be treated as "no
    remote".** It means either a local-only repo or several remotes with no
    `origin` among them, and those want opposite handling: the first is a
    legitimate local-only tag, the second is a repo where publishing to the
    wrong place is a real possibility. Callers that care ask `_remotes()` too —
    `ship_tag` fails closed on the ambiguous case rather than announcing "no
    remote is configured" and quietly skipping the sync check and the push,
    which is precisely the silent-late failure this whole change exists to end.
    Best-effort callers (the in-flight tag fetch) can take None as "skip".
    """
    remotes = _remotes(root)
    if "origin" in remotes:
        return "origin"
    return remotes[0] if len(remotes) == 1 else None


def _version_at_tip(root: Path, pyproject: Path) -> str | None:
    """The version declared by the COMMIT at HEAD, not by the working tree.

    Read out of `git show HEAD:<pyproject>` on purpose. "The version declared
    at the tip" is a statement about what merged, and reading the working tree
    would answer a different question — one an uncommitted edit can change.
    """
    rel = _repo_relative(pyproject, root) or "pyproject.toml"
    content = _git_out(root, "show", f"HEAD:{rel}")
    if content is None:
        return None
    return _declared_version_in_toml(content)


def _declared_version_in_toml(content: str) -> str | None:
    """`[tool.commitizen] version`, falling back to `[project] version`.

    The fallback covers `version_provider = "pep621"` / `"uv"`, where cz keeps
    no version of its own and the project table is the single source.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        data = None
    else:
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            data = None

    if isinstance(data, dict):
        tool = data.get("tool")
        cz = tool.get("commitizen") if isinstance(tool, dict) else None
        version = cz.get("version") if isinstance(cz, dict) else None
        if isinstance(version, str) and version.strip():
            return version.strip()
        project = data.get("project")
        version = project.get("version") if isinstance(project, dict) else None
        return version.strip() if isinstance(version, str) and version.strip() else None

    # tomllib unavailable or the document did not parse: same targeted scan the
    # rest of this module falls back to.
    for table in (r"\[tool\.commitizen\]", r"\[project\]"):
        block = re.search(rf"^{table}\n(.*?)(?=^\[|\Z)", content, re.S | re.M)
        if not block:
            continue
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', block.group(1))
        if m:
            return m.group(1)
    return None


def report_bump_only(topo: Topology, old_version: str | None, new_version: str) -> None:
    """Say plainly what happened, and what the release still needs.

    A bump commit where you expected a release is surprising the first time,
    and a surprise that is not explained gets "fixed" by someone hand-cutting
    the tag — which is the failure this split removes. So the second command is
    reported by the first, in full, rather than left to documentation.
    """
    info(f"bumped {old_version or '?'} -> {new_version} on `{topo.current}`.")
    info("NO tag was created. This repo releases in two stages:")
    info(f"  1. bump on `{topo.integration}`            <- done, just now")
    info(f"  2. open + merge the release PR into `{topo.release}`")
    info(f"  3. on `{topo.release}`, complete the release:  /ship --tag")
    info(
        f"The tag must be cut on `{topo.release}` so it names a commit that branch "
        "actually contains — a tag cut here does not survive a squash-merge."
    )
    info("Push this bump commit and open the release PR when ready.")


def refresh_lockfile(root: Path) -> None:
    """Best-effort `uv lock`, so the lock lands in the bump commit.

    Only when `uv.lock` is TRACKED: an untracked lock is scratch (the
    clean-tree gate deliberately lets it through) and would not be staged
    anyway, so refreshing it would be a write with no release meaning.

    Best-effort by contract (ADR-0008): a project whose dependencies do not
    currently resolve still has a correct version bump to make, and blocking it
    on an unrelated resolver failure trades a small staleness for a stuck
    release. It warns instead — and the staleness is visible, because the
    lockfile-check CI job fails on exactly this.
    """
    tracked = _tracked_files(root)
    if tracked is None or "uv.lock" not in tracked:
        return
    if not shutil.which("uv"):
        info("uv.lock is tracked but `uv` is not on PATH; lockfile NOT refreshed.")
        return
    cmd = ["uv", "lock"]
    print(f"$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=root, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        info(
            f"lockfile refresh failed ({exc}); continuing. uv.lock may still name "
            "the previous version — refresh it in a follow-up commit."
        )


def declared_version(root: Path, pyproject: Path, cz: list[str]) -> str | None:
    """The version this project declares, however it declares it.

    Three sources, in order: `[tool.commitizen] version`, `[project] version`,
    then cz's own provider.

    The middle one is load-bearing and was missing on the first pass (caught in
    review). Under `version_provider = "pep621"` commitizen keeps NO version of
    its own — the entire declaration lives in `[project] version` — so reading
    only the commitizen table returns None there. A guard handed None does not
    fire, which would have left pep621 repos as precisely the ones with no
    protection against the double-bump this exists to prevent.

    File reads first, cz last: this runs before first-time setup on a path that
    may end in a refusal, and `cz version --project` is a subprocess we would
    rather not spawn to answer a question `pyproject.toml` already answers.
    """
    try:
        version = _declared_version_in_toml(pyproject.read_text(encoding="utf-8"))
    except OSError:
        version = None
    return version or _current_version(root, pyproject, cz)


def _release_tag_matcher(tag: str, version: str):
    """Predicate for "this tag belongs to the same release series as `tag`".

    Derived from the RESOLVED tag rather than re-parsed out of `tag_format`:
    whatever cz renders for a version, the literal text around the version is
    this repo's series, and the version slot is a version.

    An earlier version of this globbed `tag.replace(version, "*")`, which the
    review on #88 broke correctly: `tag_format = "$version"` is a supported
    config that renders bare semver tags, and there the glob collapses to `*` —
    every tag in the repo, so a `nightly-2026-07-28` lying around made a FIRST
    release look like an abandoned bump. Requiring the version slot to actually
    look like a version is what keeps the prefix-free format honest.

    If the version does not appear in the tag at all (a `tag_format` this can
    make no sense of), every tag counts. That direction only over-refuses, and
    the refusal names its exits.
    """
    prefix, found, suffix = tag.partition(version)
    if not found:
        return lambda _t: True
    pattern = re.compile(
        re.escape(prefix) + r"\d+\.\d+\.\d+\S*" + re.escape(suffix) + r"\Z"
    )
    return lambda t: pattern.match(t) is not None


def check_bump_in_flight(
    root: Path, cz: list[str], cz_config: dict[str, object], version: str | None
) -> int:
    """Refuse a second bump while the declared version is still untagged.

    Between the bump and the tag the declared version has no tag. commitizen
    computes the next increment from the LAST TAG, so a second `/ship` in that
    window reads a baseline one release behind and bumps off it — silently
    producing a version that skips or repeats.

    Two exceptions, both deliberate:

    * **No release tags at all** — a first release, where "declared but
      untagged" is simply the initial state.
    * **The tag fetch is best-effort** — a tag pushed from elsewhere may not be
      local yet, so this tries to fetch first; being offline degrades to the
      local view rather than blocking a release.

    Accepted consequence: an abandoned bump is sticky until it is finished or
    reverted. A stuck release is loud; a double-bump is silent. The refusal
    therefore names BOTH exits — it is not a dead end.
    """
    if not version:
        return 0  # nothing to compare; later steps fail loudly on their own

    if remote := _remote_name(root):
        # Best-effort: refuse to let a network hiccup block a correct release.
        _git_out(root, "fetch", "--quiet", "--tags", remote)

    tag = resolve_tag(root, cz, cz_config, version)

    listed = _git_out(root, "tag", "--list")
    if listed is None:
        return 0  # not a git repo / git unavailable — nothing to assert against

    matches_series = _release_tag_matcher(tag, version)
    existing = [t for t in listed.splitlines() if t.strip() and matches_series(t)]
    if not existing:
        return 0  # first release
    if tag in existing:
        return 0  # the declared version is tagged; the last release is complete

    bump_commit = _git_out(root, "log", "-1", "--format=%h %s", "--grep=^bump: ") or ""

    print(
        f"ship: error: version {version} is declared but `{tag}` does not exist — "
        "a bump is already in flight.",
        file=sys.stderr,
    )
    print(
        "\nA previous /ship bumped the version and the release was never tagged.\n"
        "commitizen computes the next increment from the LAST TAG, so bumping again\n"
        "would compute from a stale baseline and double-bump.\n"
        "\nTwo ways out — take one, then re-run:\n"
        f"  FINISH it   merge the bump into `{DEFAULT_RELEASE_BRANCH}` (or your release\n"
        f"              branch) and run `/ship --tag` there. That creates `{tag}`.\n"
        "  ABANDON it  revert the bump commit, so the declared version matches the\n"
        "              last tag again:\n"
        f"                git revert {bump_commit.split(' ', 1)[0] or '<bump commit>'}\n"
        "              (or `git reset --hard HEAD~1` if it has not been pushed)\n"
        + (f"\nThe bump commit looks like: {bump_commit}\n" if bump_commit else ""),
        file=sys.stderr,
    )
    return 1


def git_commit_bump(
    root: Path, pyproject: Path, cz_config: dict[str, object], message: str
) -> int:
    """Stage the files cz rewrote and create the bump commit."""
    files = bumped_files(root, pyproject, cz_config)
    if not files:
        return fail("cz bump rewrote no files; nothing to commit.")

    try:
        run(["git", "-C", str(root), "add", "--", *files])
        run(["git", "-C", str(root), "commit", "-m", message])
    except subprocess.CalledProcessError as exc:
        return fail(f"bump commit failed with exit code {exc.returncode}")
    return 0


def resolve_cz(root: Path, *, dry_run: bool) -> list[str] | None:
    """How to invoke commitizen. Read-only under `--dry-run`. None = give up.

    A real bump prefers `uv run cz`: uv resolves the project's OWN pinned
    commitizen, syncing `.venv` if it must. Writing is fine there — the bump
    rewrites files by design.

    A dry run must not, and `uv run` cannot be made safe. It materializes the
    environment BEFORE cz ever executes, so the write happens whatever cz would
    have reported. Measured against uv 0.11.3 in a project with no `.venv`:

        uv run cz                     -> Creating virtual environment at: .venv
        uv run --no-sync cz           -> Creating virtual environment at: .venv
        uv run --no-sync --frozen cz  -> Creating virtual environment at: .venv

    `--no-sync` suppresses dependency syncing, not venv creation. So there is no
    uv mode that both runs the project's cz and provably writes nothing, and a
    dry run instead only ever executes a cz that ALREADY exists:

      1. `.venv/bin/cz` — the exact commitizen the real bump would use, so the
         simulation predicts the release rather than approximating it.
      2. `cz` on PATH — an activated venv, a `uv tool install`, or a global one.

    Anything else returns None and the caller stops with a read-only message.
    Falling back to `uv run` here would write the very files the dry run
    promised to leave alone, which is the failure silently degrading would
    cause: a user runs `/ship --dry-run` to look, and it changes the tree.
    """
    if dry_run:
        venv_cz = root / ".venv" / "bin" / "cz"
        if venv_cz.is_file() and os.access(venv_cz, os.X_OK):
            return [str(venv_cz)]
        if on_path := shutil.which("cz"):
            return [on_path]
        return None

    if shutil.which("uv"):
        return ["uv", "run", "cz"]
    if shutil.which("cz"):
        return ["cz"]
    return None


def bumped_files(
    root: Path, pyproject: Path, cz_config: dict[str, object]
) -> list[str]:
    """Paths cz may have rewritten: version_files + config file + changelog.

    `pyproject.toml` is always included because cz writes the new version into
    `[tool.commitizen] version` there regardless of `version_files`.

    Three mechanisms feed the result and ALL THREE agree on one rule: a file
    enters the bump commit only if git already tracks it, and the changelog is
    the single exception. The glob half mirrors commitizen's own expansion
    (below); the dirty-tracked-file sweep is the backstop for anything the glob
    cannot see; the tracked filter at the end is what makes "untracked means
    excluded" true of the whole function rather than of one branch of it.

    That rule is not cosmetic. `check_clean_worktree` deliberately lets
    untracked files through (`--untracked-files=no`) so a lockfile or scratch
    output can never block a release — which means an untracked file CAN be
    sitting in the tree when this runs, and `git add` would put it inside the
    release commit and the annotated tag consumers pin. Scratch is not a
    release artifact. `CHANGELOG.md` is exempt because cz legitimately creates
    it from nothing on a first release, and a release without its changelog is
    not a release.
    """
    candidates: list[Path] = [pyproject]

    version_files = cz_config.get("version_files")
    if isinstance(version_files, list):
        for entry in version_files:
            if not isinstance(entry, str):
                continue
            # `path:pattern` — cz splits on the first colon; the path half may
            # itself be a glob.
            raw = entry.split(":", 1)[0].strip()
            if not raw:
                continue
            # Deliberately NOT `recursive=True`. commitizen resolves
            # `version_files` with a bare `iglob(pattern)`
            # (`commitizen.bump._resolve_files_and_regexes`), so `**` matches a
            # SINGLE path component there — exactly as it does here. Verified
            # against cz 4.16.5: with `version_files = ["src/**/*.py:__version__"]`
            # cz rewrote `src/pkg/__init__.py` and left `src/pkg/sub/deep.py`
            # untouched. Globbing recursively would make /ship stage paths cz
            # never rewrote, including UNTRACKED ones at any depth — and the
            # clean-tree gate deliberately lets untracked files through
            # (`--untracked-files=no`), so `git add` would sweep scratch into
            # the release commit. Mirror cz; never out-glob it.
            matches = glob.glob(str(root / raw))
            if matches:
                candidates.extend(Path(m) for m in matches)
            else:
                candidates.append(root / raw)

    # Normalize the changelog ONCE, then use the normalized form as both the
    # candidate and the exemption key. Raw config text used to be compared
    # against candidates that had been through `resolve().relative_to(root)`,
    # so the exemption only matched when a repo spelled `changelog_file`
    # canonically. `./CHANGELOG.md` and `docs/../CHANGELOG.md` are ordinary
    # valid spellings, and under them a FIRST release — whose changelog is
    # untracked precisely because cz had just created it — committed without
    # the changelog cz wrote. Exactly the partial release this function exists
    # to prevent.
    #
    # The candidate must be normalized too, not just the key: `docs/../X` does
    # not `stat()` when `docs/` does not exist (the kernel walks components
    # literally), so the raw spelling would be dropped as non-existent even
    # with the exemption keyed correctly.
    #
    # `None` means the configured path escapes the repo: no candidate, no
    # exemption. `changelog_section()` refuses to read such a path; this
    # refuses to stage it.
    changelog = cz_config.get("changelog_file")
    changelog_rel = _repo_relative(
        root / (changelog if isinstance(changelog, str) else DEFAULT_CHANGELOG_FILE),
        root,
    )
    if changelog_rel is not None:
        candidates.append(root / changelog_rel)

    # Backstop: anything git reports as a modified TRACKED file was written by
    # cz, because `check_clean_worktree` already refused to get here unless the
    # tracked tree was clean before the bump. So the bump commit can be complete
    # without this function having to out-guess cz's pattern expansion — if cz
    # ever changes how it resolves `version_files` (or resolves a pattern this
    # function mis-parses), the rewritten file still lands in the commit instead
    # of being left behind for a partial release. This source is tracked-only by
    # construction (`git diff` never reports untracked paths), which is the same
    # rule the filter below applies to the glob source.
    candidates.extend(root / rel for rel in _modified_tracked_files(root))

    tracked = _tracked_files(root)

    seen: dict[str, None] = {}
    for path in candidates:
        if not path.exists():
            continue
        rel = _repo_relative(path, root)
        if rel is None:  # outside the repo — cz would not have touched it
            continue
        # The one filter, applied to every source. `tracked is None` means git
        # could not be asked at all; there is nothing to filter against, and the
        # commit step below fails loudly on its own in that state.
        if tracked is not None and rel not in tracked and rel != changelog_rel:
            continue
        seen.setdefault(rel, None)
    return list(seen)


def _repo_relative(path: Path, root: Path) -> str | None:
    """`path` as a repo-relative posix string, or None if it escapes `root`.

    The single normalizer for this module: every path that gets compared,
    filtered or staged goes through it, so `./CHANGELOG.md`, `CHANGELOG.md` and
    `docs/../CHANGELOG.md` cannot disagree about whether they are the same
    file. Comparing a normalized path against raw config text is precisely the
    bug this exists to make unrepresentable.
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _tracked_files(root: Path) -> set[str] | None:
    """Repo-relative paths git tracks, or None if git cannot be asked."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return {line for line in result.stdout.splitlines() if line.strip()}


def _modified_tracked_files(root: Path) -> list[str]:
    """Repo-relative paths of tracked files with uncommitted changes.

    Both staged and unstaged (`git diff --name-only HEAD`). Returns `[]` when
    git is unavailable or the repo has no commits yet — the caller only uses
    this to widen the set of paths it stages, so an empty answer is safe.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_tag_message(
    root: Path, cz_config: dict[str, object], tag: str, version: str
) -> str:
    """Message for the annotated release tag.

    An annotated tag carries a message, so it should say what shipped rather
    than restate its own name — `git show <tag>` and `git tag -n99` then
    display the release notes without anyone opening the changelog.

    Precedence: an explicit `annotated_tag_message` wins (the repo asked for a
    fixed message); otherwise `Release <tag>` plus this version's changelog
    section when it can be located; otherwise `Release <tag>` alone. Extraction
    is best-effort — a tag with a thin message beats a failed release.
    """
    configured = cz_config.get("annotated_tag_message")
    if isinstance(configured, str) and configured.strip():
        return configured

    subject = f"Release {tag}"
    body = changelog_section(root, cz_config, version)
    return f"{subject}\n\n{body}" if body else subject


def changelog_section(
    root: Path, cz_config: dict[str, object], version: str
) -> str | None:
    """The changelog body for `version`, or None if it can't be located.

    Matches the first `## ` heading mentioning the version and returns the
    lines up to the next `## `. Tolerant of the heading styles commitizen
    emits (`## v1.2.0 (2026-07-28)`, `## 1.2.0`).
    """
    name = cz_config.get("changelog_file")
    changelog = root / (name if isinstance(name, str) and name else "CHANGELOG.md")

    # `changelog_file` is repo-controlled config, and `root / name` happily
    # accepts `../../secrets.md` or an absolute path — /ship would then read
    # outside the repo and copy whatever matched a `## <version>` heading into
    # the annotated tag message, which gets pushed. `bumped_files()` already
    # drops escaping paths through `relative_to(root)`; this is that same guard
    # in the one place in this file that lacked it. `resolve()` follows
    # symlinks, so a changelog symlinked out of the tree is caught too.
    #
    # Escaping degrades the tag message rather than failing the release: this
    # function is best-effort by contract, and a thin tag beats a refused one.
    try:
        changelog.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None

    try:
        lines = changelog.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and version in line:
            start = i + 1
            break
    if start is None:
        return None

    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    body = "\n".join(lines[start:end]).strip()
    return body or None


def resolve_tag(
    root: Path, cz: list[str], cz_config: dict[str, object], version: str
) -> str:
    """The tag name commitizen itself would use for `version`.

    `tag_format` is commitizen's syntax, not this script's. It accepts more
    variables than the four rendered below — `$prerelease`, `$devrelease` —
    and cz used the real format to compute the version and the changelog. A
    tag rendered by a second, partial formatter is exactly the provenance
    break this script exists to prevent: git would carry `v1.2.3$prerelease`
    while cz's history says `v1.2.3`. So ask the tool that owns the format.

    `cz version --project --tag` prints the tag for the version currently in
    the project — which, run AFTER the files-only bump, is the new one. It
    also honours a non-default `version_provider`, which local rendering
    cannot see.

    Falls back to local `string.Template` rendering when the query fails or
    returns something unusable (empty output, or whitespace — cz reports "no
    project information" on stderr and prints nothing). A thin tag beats
    aborting a release whose bump commit has already landed; the fallback
    announces itself rather than swapping the tag silently.
    """
    try:
        result = subprocess.run(
            [*cz, "version", "--project", "--tag"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        local = render_tag(cz_config, version)
        info(f"`cz version --project --tag` failed ({exc}); using local tag {local}")
        return local

    tag = result.stdout.strip()
    if not tag or any(ch.isspace() for ch in tag):
        local = render_tag(cz_config, version)
        info(
            "`cz version --project --tag` returned no usable tag "
            f"({tag!r}); using local tag {local}"
        )
        return local
    return tag


def render_tag(cz_config: dict[str, object], version: str) -> str:
    """Local fallback for `tag_format` — only used when cz cannot be asked.

    Deliberately partial: it knows `$version`/`$major`/`$minor`/`$patch` and
    leaves anything else as a literal. `resolve_tag` is the real answer.
    """
    fmt = cz_config.get("tag_format")
    if not isinstance(fmt, str) or not fmt.strip():
        fmt = DEFAULT_TAG_FORMAT
    parts = (version.split("-", 1)[0].split(".") + ["0", "0", "0"])[:3]
    return string.Template(fmt).safe_substitute(
        version=version,
        major=parts[0],
        minor=parts[1],
        patch=parts[2],
    )


def _current_version(root: Path, pyproject: Path, cz: list[str]) -> str | None:
    """Version cz considers current — the config field, or ask cz's provider."""
    if version := _read_pyproject_version(pyproject):
        return version
    # Non-default `version_provider` (pep621, uv, …) keeps the version
    # elsewhere; cz itself is the only reliable reader.
    try:
        result = subprocess.run(
            [*cz, "version", "--project"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def wipe_tasks_completed(root: Path, pyproject: Path) -> None:
    """Remove `## Completed (...)` sections from TASKS.md after a successful bump."""
    tasks = root / "TASKS.md"
    if not tasks.exists():
        return

    content = tasks.read_text(encoding="utf-8")
    # Tier-1 only: a repo that graduated to GitHub Issues leaves TASKS.md as a
    # migration tombstone — its completion record lives in the Issues tab.
    if "qute-tasks: migrated-to-github" in content:
        return

    pattern = re.compile(
        r"^## Completed\b[^\n]*\n.*?(?=^## |^---\s*$|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    new_content, n = pattern.subn("", content)
    if n == 0:
        return

    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    tasks.write_text(new_content, encoding="utf-8")

    version = _read_pyproject_version(pyproject) or "release"
    try:
        subprocess.run(["git", "add", "TASKS.md"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore(tasks): wipe Completed after v{version}"],
            cwd=root,
            check=True,
        )
        info(f"wiped {n} Completed section(s) from TASKS.md")
    except subprocess.CalledProcessError:
        info("TASKS.md sweep skipped (git add/commit failed — check working tree)")


def _read_pyproject_version(pyproject: Path) -> str | None:
    version = _read_cz_config(pyproject).get("version")
    return version if isinstance(version, str) else None


def _read_cz_config(pyproject: Path) -> dict[str, object]:
    """The `[tool.commitizen]` table, or `{}` if absent/unreadable."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        return _read_cz_config_regex(pyproject)

    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return _read_cz_config_regex(pyproject)

    tool = data.get("tool")
    cz = tool.get("commitizen") if isinstance(tool, dict) else None
    return cz if isinstance(cz, dict) else {}


def _read_cz_config_regex(pyproject: Path) -> dict[str, object]:
    """Fallback parse of the keys /ship needs, for interpreters without tomllib."""
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return {}
    block = re.search(r"^\[tool\.commitizen\]\n(.*?)(?=^\[|\Z)", content, re.S | re.M)
    if not block:
        return {}
    text = block.group(1)

    config: dict[str, object] = {}
    for key in ("version", "tag_format", "changelog_file", "annotated_tag_message"):
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text, re.MULTILINE)
        if m:
            config[key] = m.group(1)
    vf = re.search(r"^version_files\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if vf:
        config["version_files"] = re.findall(r'"([^"]+)"', vf.group(1))
    return config


BUMP_DIRTY_REASON = (
    "A release must be cut from a clean tree — the bump commit stages whole\n"
    "files, so these edits would land inside the release commit and inside the\n"
    "annotated tag that points at it."
)

TAG_DIRTY_REASON = (
    "A release tag must be cut from a clean tree. The tag NAME is rendered from\n"
    "`tag_format` and its message is built from the changelog — and commitizen\n"
    "reads both from the WORKING TREE, not from the commit being tagged. So an\n"
    "uncommitted edit here changes the tag that gets pushed, under a version the\n"
    "released commit never declared."
)


def check_clean_worktree(
    root: Path, *, dry_run: bool = False, why: str = BUMP_DIRTY_REASON
) -> int:
    """Refuse to release when tracked files carry uncommitted changes.

    Mirrors the gate `release-plugin.sh` already applies in plugin mode, in
    both check and spirit: ANY modified tracked file blocks, not just the
    configured `version_files`. The bump commit stages whole files, so an
    unrelated edit would ride into the commit that the release tag points at,
    and consumers pin that tag. Releases come from a clean tree.

    `--tag` runs this too, for a different reason — hence `why`, so the refusal
    explains the situation the caller is actually in rather than lecturing a
    tag-only run about the bump commit it is not making.

    Untracked files are deliberately ignored (`--untracked-files=no`, same as
    plugin mode): a lockfile, scratch output, or a stray build artifact is
    routine and must not be able to block a release. It is also sound for the
    tag path: cz cannot read a version or a format out of a file the project
    does not track.

    `--dry-run` reports instead of refusing. A dry run answers "what would
    ship" and creates neither commit nor tag, so a dirty tree cannot
    contaminate anything — and checking the next version mid-edit is exactly
    when a dry run earns its keep.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo, or no git on PATH. Nothing to protect here; the
        # commit/tag steps later on fail loudly by themselves.
        return 0

    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if not dirty:
        return 0

    if dry_run:
        info("working tree has uncommitted tracked changes:")
        for line in dirty:
            print(f"  {line}")
        info("dry run — reporting only; a real release refuses until these are clean.")
        return 0

    print("ship: error: working tree has uncommitted tracked changes:", file=sys.stderr)
    for line in dirty:
        print(f"  {line}", file=sys.stderr)
    print(
        f"\n{why}\n"
        "Commit or stash them first, then re-run:\n"
        "  git commit -am '...'   # or: git stash push -- <paths>\n"
        "Untracked files are ignored and never block a release.",
        file=sys.stderr,
    )
    return 1


def check_forbidden_paths(root: Path) -> int:
    """Refuse to bump if any tracked file lives under a forbidden path."""
    paths = list(UNIVERSAL_FORBIDDEN)
    extras = root / ".claude" / "forbidden-paths.txt"
    if extras.exists():
        for line in extras.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                paths.append(line)

    violations: list[tuple[str, int]] = []
    for p in paths:
        try:
            result = subprocess.run(
                ["git", "ls-files", p],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        files = [f for f in result.stdout.splitlines() if f]
        if files:
            violations.append((p, len(files)))

    if not violations:
        return 0

    print("ship: error: forbidden paths are tracked in this branch:", file=sys.stderr)
    for p, n in violations:
        print(f"  - {p} ({n} files)", file=sys.stderr)
    print(
        "\nThese paths are skill-generated artifacts that must not reach main.\n"
        "Strip them before shipping, e.g.:\n"
        f"  git rm -r {' '.join(p for p, _ in violations)}\n"
        "  git commit -m 'chore: strip skill artifacts before release'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
