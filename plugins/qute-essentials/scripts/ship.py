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
  /ship [<plugin>] <patch|minor|major|X.Y.Z>         # Plugin: delegate to release-plugin.sh

Detects mode by repo root:
  .claude-plugin/marketplace.json → plugin mode
  pyproject.toml                  → python mode
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
    parsed, leftover = parser.parse_known_args(args)
    parsed.version = None
    for a in leftover:
        if SEMVER_RE.match(a):
            parsed.version = a
        elif a in BUMP_KINDS:
            parsed.increment = a
        else:
            parser.error(f"unknown argument: {a}")
    return parsed


def ship_python(root: Path, pyproject: Path, args: list[str]) -> int:
    parsed = parse_python_args(args)

    # 1. Forbidden-paths check — now enforced in `main()`, before mode
    #    dispatch, so plugin mode gets it too. Not repeated here.

    # 2. Clean-tree gate. Deliberately BEFORE setup: setup legitimately writes
    #    to pyproject.toml / CHANGELOG.md, so checking afterwards would trip on
    #    its own edits. Everything from here on is either a write or a commit.
    #    Under --dry-run this reports the dirty paths instead of refusing —
    #    nothing it produces can be contaminated, since it creates nothing.
    if rc := check_clean_worktree(root, dry_run=parsed.dry_run):
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

    message = (
        string.Template(BUMP_MESSAGE)
        .safe_substitute(current_version=old_version or "?", new_version=new_version)
        .strip()
    )
    if rc := git_commit_bump(root, pyproject, cz_config, message):
        return rc

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


def check_clean_worktree(root: Path, *, dry_run: bool = False) -> int:
    """Refuse to bump when tracked files carry uncommitted changes.

    Mirrors the gate `release-plugin.sh` already applies in plugin mode, in
    both check and spirit: ANY modified tracked file blocks, not just the
    configured `version_files`. The bump commit stages whole files, so an
    unrelated edit would ride into the commit that the release tag points at,
    and consumers pin that tag. Releases come from a clean tree.

    Untracked files are deliberately ignored (`--untracked-files=no`, same as
    plugin mode): a lockfile, scratch output, or a stray build artifact is
    routine and must not be able to block a release.

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
        "\nA release must be cut from a clean tree — the bump commit stages whole\n"
        "files, so these edits would land inside the release commit and inside the\n"
        "annotated tag that points at it. Commit or stash them first, then re-run:\n"
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
