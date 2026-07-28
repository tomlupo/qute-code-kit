"""Smoke tests for the qute-essentials /ship script.

Covers mode dispatch, arg parsing, and forbidden-path behavior. Most of it
does not exercise commitizen; `BumpCommitCompleteness` does, and skips itself
when neither `cz` nor `uv` can reach it.

Run from the repo root:
    python3 -m unittest tests.test_ship
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIP_PY = REPO_ROOT / "plugins" / "qute-essentials" / "scripts" / "ship.py"


def run_ship(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SHIP_PY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})},
    )


class HelpAndDispatch(unittest.TestCase):
    def test_help_short_circuits_before_mode_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_ship(["--help"], Path(td))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Usage", result.stdout)

    def test_short_help_flag(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_ship(["-h"], Path(td))
        self.assertEqual(result.returncode, 0)
        self.assertIn("plugin mode", result.stdout)

    def test_no_project_type_fails_with_message(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_ship([], Path(td))
        self.assertEqual(result.returncode, 1)
        self.assertIn("no supported project type", result.stderr)

    def test_package_json_redirects_to_gstack(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "package.json").write_text("{}")
            result = run_ship([], Path(td))
        self.assertEqual(result.returncode, 1)
        self.assertIn("gstack ship", result.stderr)

    def test_cargo_toml_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "Cargo.toml").write_text("")
            result = run_ship([], Path(td))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Rust", result.stderr)


class PluginModeDispatch(unittest.TestCase):
    @staticmethod
    def _make_marketplace(td: Path, plugins: list[str]) -> None:
        (td / ".claude-plugin").mkdir()
        (td / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps(
                {
                    "name": "test-marketplace",
                    "plugins": [{"name": n, "version": "0.1.0"} for n in plugins],
                }
            )
        )

    def test_empty_marketplace_fails(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._make_marketplace(td, [])
            result = run_ship(["patch"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no plugins", result.stderr)

    def test_multi_plugin_requires_name(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._make_marketplace(td, ["a", "b"])
            result = run_ship(["patch"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("multiple plugins", result.stderr)

    def test_unknown_plugin_name_rejected(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._make_marketplace(td, ["a"])
            result = run_ship(["c", "patch"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not in marketplace", result.stderr)

    def test_bad_bump_spec_rejected(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._make_marketplace(td, ["a"])
            result = run_ship(["bogus"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be patch|minor|major", result.stderr)

    def test_explicit_semver_accepted_format(self):
        # Exercises only the validation path; we expect failure at the
        # release-plugin.sh step (no such script in tmpdir).
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._make_marketplace(td, ["a"])
            result = run_ship(["1.2.3"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release-plugin.sh", result.stderr)
        self.assertNotIn("must be patch", result.stderr)


class PythonModeArgs(unittest.TestCase):
    def _bare_pyproject(self, td: Path) -> None:
        (td / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.1.0"\n')

    def test_unknown_arg_rejected(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._bare_pyproject(td)
            result = run_ship(["--frobnicate"], td)
        self.assertNotEqual(result.returncode, 0)


class ForbiddenPaths(unittest.TestCase):
    """The gate belongs to /ship, not to one of its modes.

    It used to run inside `ship_python()` only, so plugin mode dispatched
    straight to release-plugin.sh and released with skill artifacts tracked —
    while SKILL.md advertised the refusal as a property of /ship. qute-code-kit
    is itself a plugin-mode repo, so it had no protection at all. Same defect
    shape as the untracked-file and dry-run bugs on this PR: a rule enforced in
    one place and absent in its twin.
    """

    def test_extras_file_parsed_with_comments(self):
        # Module-level import (path acrobatics) of check_forbidden_paths.
        sys.path.insert(0, str(SHIP_PY.parent))
        try:
            from ship import UNIVERSAL_FORBIDDEN  # noqa: F401
        finally:
            sys.path.pop(0)
        self.assertIn(".claude/handoffs", UNIVERSAL_FORBIDDEN)

    @staticmethod
    def _repo_with_forbidden_path(root: Path) -> None:
        subprocess.run(
            ["git", "init", "-q", "-b", "main", str(root)],
            check=True,
            capture_output=True,
        )
        handoffs = root / ".claude" / "handoffs"
        handoffs.mkdir(parents=True)
        (handoffs / "session.md").write_text("leaked\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(root), "add", "-A"], check=True, capture_output=True
        )

    def test_plugin_mode_refuses_when_a_forbidden_path_is_tracked(self):
        """The actual gap: plugin mode never reached the check at all."""
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._repo_with_forbidden_path(td)
            PluginModeDispatch._make_marketplace(td, ["demo"])
            # A release script that shouts if it runs — the point is that the
            # release must not happen, not merely that the command exits 1.
            scripts = td / "scripts"
            scripts.mkdir()
            (scripts / "release-plugin.sh").write_text(
                "#!/bin/sh\necho RELEASED\nexit 0\n", encoding="utf-8"
            )

            result = run_ship(["patch"], td)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("forbidden paths are tracked", result.stderr)
            self.assertIn(".claude/handoffs", result.stderr)
            self.assertNotIn("RELEASED", result.stdout)

    def test_python_mode_still_refuses(self):
        """Moving the gate must not drop the mode that already had it."""
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._repo_with_forbidden_path(td)
            (td / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
            )
            result = run_ship(["patch"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden paths are tracked", result.stderr)

    def test_unsupported_repo_hears_about_the_repo_not_the_paths(self):
        """Ordering: project-type detection first, or the error misleads."""
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            self._repo_with_forbidden_path(td)
            result = run_ship(["patch"], td)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no supported project type", result.stderr)
        self.assertNotIn("forbidden paths", result.stderr)


class CleanWorktreeGate(unittest.TestCase):
    """A release must be cut from a clean tree (independent review, PR #84).

    `git add -- <version files>` in the bump commit stages WHOLE files, so an
    unrelated local edit would ride into the release commit and end up inside
    the annotated tag consumers pin. Plugin mode has always refused a dirty
    tree (`release-plugin.sh`); Python mode now matches it.
    """

    @staticmethod
    def _ship_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("ship_under_test", SHIP_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _init_repo(root: Path) -> None:
        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            )

        git("init", "-q", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n'
            "[tool.commitizen]\n"
            'version = "0.1.0"\n'
            'version_files = ["src/x/__init__.py:__version__"]\n',
            encoding="utf-8",
        )
        (root / "src" / "x").mkdir(parents=True)
        (root / "src" / "x" / "__init__.py").write_text(
            '__version__ = "0.1.0"\n', encoding="utf-8"
        )
        (root / "README.md").write_text("# x\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "chore: init")

    def test_clean_tree_passes(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            self.assertEqual(mod.check_clean_worktree(root), 0)

    def test_modified_version_file_blocks(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "src" / "x" / "__init__.py").write_text(
                '__version__ = "0.1.0"\nDEBUG = True\n', encoding="utf-8"
            )
            self.assertEqual(mod.check_clean_worktree(root), 1)

    def test_modified_non_version_file_also_blocks(self):
        """Matches release-plugin.sh: the whole tracked tree must be clean."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "README.md").write_text("# x\nscratch\n", encoding="utf-8")
            self.assertEqual(mod.check_clean_worktree(root), 1)

    def test_untracked_file_does_not_block(self):
        """`--untracked-files=no`: lockfiles and scratch output are routine."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "scratch.log").write_text("noise\n", encoding="utf-8")
            (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
            self.assertEqual(mod.check_clean_worktree(root), 0)

    def test_staged_change_blocks(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "new.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "new.py"],
                check=True,
                capture_output=True,
            )
            self.assertEqual(mod.check_clean_worktree(root), 1)

    def test_dry_run_reports_instead_of_refusing(self):
        """A dry run writes no commit and no tag, so it cannot be contaminated."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "README.md").write_text("# x\ndirty\n", encoding="utf-8")
            self.assertEqual(mod.check_clean_worktree(root, dry_run=True), 0)

    def test_non_git_directory_is_not_blocked(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(mod.check_clean_worktree(Path(d)), 0)

    def test_cli_refuses_and_names_the_dirty_path(self):
        """End-to-end: refusal happens before setup writes or cz runs."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "src" / "x" / "__init__.py").write_text(
                '__version__ = "0.1.0"\nDEBUG = True\n', encoding="utf-8"
            )
            before = (root / "pyproject.toml").read_text(encoding="utf-8")
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            result = run_ship(["patch"], root)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("uncommitted tracked changes", result.stderr)
            self.assertIn("src/x/__init__.py", result.stderr)
            self.assertIn("commit or stash", result.stderr.lower())
            # Nothing was written and nothing was committed.
            self.assertEqual(
                before, (root / "pyproject.toml").read_text(encoding="utf-8")
            )
            after = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(head, after)


class TagRendering(unittest.TestCase):
    """The tag git creates must be the tag commitizen thinks it cut.

    Regression guard for the second review round on PR #84: `render_tag()`
    re-rendered `tag_format` with only $version/$major/$minor/$patch, so a
    config using $prerelease or $devrelease baked those literals into the tag
    name while cz had used the real format to compute the changelog. /ship now
    asks cz for the tag (`cz version --project --tag`) and only falls back to
    local rendering when cz cannot answer.
    """

    @staticmethod
    def _ship_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("ship_tag_under_test", SHIP_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # -- fallback behaviour (no commitizen needed) --------------------------

    def test_falls_back_locally_when_cz_is_missing(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            tag = mod.resolve_tag(
                Path(d), ["definitely-not-a-real-binary-xyz"], {}, "1.2.3"
            )
        self.assertEqual(tag, "v1.2.3")

    def test_falls_back_locally_when_cz_prints_nothing(self):
        """cz reports 'no project information' on stderr and prints no tag."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            tag = mod.resolve_tag(
                Path(d),
                [sys.executable, "-c", "pass"],
                {"tag_format": "release-$version"},
                "1.2.3",
            )
        self.assertEqual(tag, "release-1.2.3")

    def test_rejects_output_that_is_not_a_single_token(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            tag = mod.resolve_tag(
                Path(d),
                [sys.executable, "-c", "print('No project information here.')"],
                {},
                "1.2.3",
            )
        self.assertEqual(tag, "v1.2.3")

    def test_uses_cz_output_verbatim(self):
        """Whatever cz prints IS the tag — no second-guessing the format."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            tag = mod.resolve_tag(
                Path(d),
                [sys.executable, "-c", "print('v3.0.0')"],
                {"tag_format": "v$minor.$major.$patch$prerelease"},
                "0.3.0",
            )
        self.assertEqual(tag, "v3.0.0")
        self.assertNotIn("$", tag)

    # -- end-to-end against real commitizen --------------------------------

    def _release(self, tag_format: str, root: Path) -> str:
        """Build a repo with `tag_format`, run /ship, return the created tag."""

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        (root / "src" / "demo").mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            "[project]\n"
            'name = "demo"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.11"\n'
            "dependencies = []\n\n"
            "[dependency-groups]\n"
            'dev = ["commitizen"]\n\n'
            "[tool.commitizen]\n"
            'name = "cz_conventional_commits"\n'
            'version = "0.1.0"\n'
            'version_files = ["pyproject.toml:version"]\n'
            f'tag_format = "{tag_format}"\n',
            encoding="utf-8",
        )
        (root / "src" / "demo" / "__init__.py").write_text("", encoding="utf-8")
        git("init", "-q", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        git("config", "commit.gpgsign", "false")
        git("add", "-A")
        git("commit", "-q", "-m", "chore: init")
        (root / "src" / "demo" / "core.py").write_text("X = 1\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "feat: add X")

        result = run_ship([], root)
        if result.returncode != 0:
            self.skipTest(
                f"commitizen unavailable for end-to-end tag test: {result.stderr[-400:]}"
            )
        tags = [t for t in git("tag", "--list").splitlines() if t]
        self.assertEqual(len(tags), 1, msg=f"tags={tags}\n{result.stdout}")
        # The tag git created must be exactly what cz reports for the project.
        reported = subprocess.run(
            ["uv", "run", "cz", "version", "--project", "--tag"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(tags[0], reported)
        # Always annotated — `git push --follow-tags` skips lightweight tags.
        self.assertEqual(
            git("cat-file", "-t", git("rev-parse", tags[0]).strip()).strip(), "tag"
        )
        return tags[0]

    @unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
    def test_default_tag_format(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._release("v$version", Path(d)), "v0.2.0")

    @unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
    def test_custom_prefix_tag_format(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                self._release("release-$version", Path(d)), "release-0.2.0"
            )

    @unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
    def test_tag_format_with_a_variable_the_local_renderer_lacks(self):
        """The actual bug: `$prerelease` used to survive into the tag name."""
        mod = self._ship_module()
        fmt = "v$minor.$major.$patch$prerelease"
        with tempfile.TemporaryDirectory() as d:
            tag = self._release(fmt, Path(d))
        self.assertNotIn("$", tag)
        self.assertEqual(tag, "v2.0.0")
        # And prove the old local-only renderer would have gotten it wrong.
        self.assertEqual(
            mod.render_tag({"tag_format": fmt}, "0.2.0"), "v2.0.0$prerelease"
        )


class TestAutoBumpWorkflowDetection(unittest.TestCase):
    """Setup must not install a second version writer, and must flag one.

    Regression guard for a real incident (dm-evo, 2026-07): setup installed a
    release.yml that ran `cz bump` on push to main — /ship's own job. Both ran,
    every release double-bumped, and because the CI bump landed on main as a
    commit dev never saw, the branches diverged for two months. That surfaced
    as a stale lockfile breaking all of CI and a CHANGELOG conflict where
    resolving toward dev would have deleted a release from the record.
    """

    @staticmethod
    def _setup_mod():
        import importlib.util

        path = (
            Path(__file__).resolve().parents[1]
            / "plugins/qute-essentials/scripts/ship_setup.py"
        )
        spec = importlib.util.spec_from_file_location("ship_setup_under_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _write_workflow(self, root: Path, body: str, name: str = "release.yml") -> None:
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True, exist_ok=True)
        (wf / name).write_text(body, encoding="utf-8")

    def test_flags_a_push_triggered_cz_bump(self):
        mod = self._setup_mod()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_workflow(
                root,
                "on:\n  push:\n    branches: [main]\njobs:\n  s:\n    steps:\n"
                "      - run: cz bump --yes\n",
            )
            self.assertTrue(mod._warn_if_autobump_workflow(root))

    def test_ignores_workflow_dispatch_only(self):
        """The neutered form — how a repo disables it without deletion.

        Deleting is not enough: setup recreates a MISSING release.yml, which
        would restore the auto-bump. An inert file is the stable state, so it
        must not be reported as a duplicate writer.
        """
        mod = self._setup_mod()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_workflow(
                root,
                "on:\n  workflow_dispatch:\njobs:\n  noop:\n    steps:\n"
                "      - run: echo 'inert — cz bump lives in /ship'\n",
            )
            self.assertFalse(mod._warn_if_autobump_workflow(root))

    def test_ignores_ordinary_push_ci_without_a_bump(self):
        mod = self._setup_mod()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write_workflow(
                root,
                "on:\n  push:\n    branches: [main]\njobs:\n  t:\n    steps:\n"
                "      - run: pytest\n",
                name="tests.yml",
            )
            self.assertFalse(mod._warn_if_autobump_workflow(root))

    def test_no_workflows_directory_is_not_an_error(self):
        mod = self._setup_mod()
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod._warn_if_autobump_workflow(Path(d)))

    def test_setup_does_not_create_a_release_workflow(self):
        """The core fix: setup must no longer install a competing writer."""
        src = (
            Path(__file__).resolve().parents[1]
            / "plugins/qute-essentials/scripts/ship_setup.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("created .github/workflows/release.yml", src)


def _install_cz_shim(bindir: Path) -> bool:
    """Put a real `cz` in `bindir`. False if commitizen cannot be reached.

    ship.py prefers `uv run cz` whenever uv is on PATH, which inside a
    throwaway project means resolving commitizen into a fresh `.venv` from a
    pyproject that never declared it. The test therefore hides uv from ship.py
    (see `_ship_env`) and hands it a `cz` on PATH instead — either the real one
    or a shim over `uv tool run`, which resolves from uv's cache.
    """
    real = shutil.which("cz")
    if real:
        launcher = f'exec "{real}" "$@"'
    else:
        uv = shutil.which("uv")
        if not uv:
            return False
        launcher = f'exec "{uv}" tool run --from commitizen cz "$@"'
    shim = bindir / "cz"
    shim.write_text(f"#!/bin/sh\n{launcher}\n", encoding="utf-8")
    shim.chmod(0o755)
    return (
        subprocess.run(
            [str(shim), "version"], capture_output=True, text=True
        ).returncode
        == 0
    )


def _outside_bindir(root: Path, *, with_uv: bool = False) -> Path:
    """A bin dir holding ONLY the tools a test means to expose.

    Two independent reasons it works this way.

    OUTSIDE the repo: inside it, the shim would itself be an untracked file in
    the tree these tests assert is untouched — the harness would be creating
    the very noise it checks for.

    FIRST on PATH, ahead of the system dirs: a host with a global commitizen
    must not change what these tests prove. The system dirs still follow,
    because the cz shim is a `uv tool run` wrapper that needs `realpath` and
    `dirname` — a PATH of this directory alone breaks cz with exit 127 rather
    than testing anything. Shadowing is enough for the tests that need a cz
    PRESENT; the one that needs cz ABSENT checks the resulting PATH itself.
    `git` is linked because ship.py shells out to it.
    """
    bindir = root.parent / f"{root.name}-bin"
    bindir.mkdir(exist_ok=True)
    for tool in ("git", *(("uv",) if with_uv else ())):
        src = shutil.which(tool)
        if src and not (bindir / tool).exists():
            (bindir / tool).symlink_to(src)
    return bindir


def _ship_env(bindir: Path) -> dict[str, str]:
    """PATH with the bin dir shadowing the system dirs — see `_outside_bindir`."""
    return {"PATH": f"{bindir}:/usr/bin:/bin"}


class BumpCommitCompleteness(unittest.TestCase):
    """The bump commit must contain EVERY file cz rewrote — and only those.

    Regression guard for the third review round on PR #84. `bumped_files()`
    re-expands the `version_files` globs to decide what to `git add`, so any
    drift between its expansion and commitizen's leaves a rewritten file
    unstaged: the tag then points at a partial release, where `pyproject.toml`
    says 0.2.0 and a package `__version__` still says 0.1.0.

    The review that raised it assumed cz expands `**` recursively and /ship did
    not. It is the other way round — cz resolves `version_files` with a bare
    `iglob()` (`commitizen.bump._resolve_files_and_regexes`), so `**` matches
    one path component for BOTH, and globbing recursively here would stage
    files cz never touched. These tests pin the behaviour in both directions,
    against the real cz rather than against either assumption.
    """

    VERSION_LITERAL = '__version__ = "0.1.0"\n'

    def _git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _init_repo(self, root: Path) -> None:
        """A repo whose version_files glob spans two nested directories.

        Layout under `src/**/*.py`:
          src/alpha/__init__.py      matched   (depth 1)
          src/beta/__init__.py       matched   (depth 1, second directory)
          src/alpha/deep/inner.py    unmatched (depth 2, tracked)
        """
        self._git(root, "init", "-q", "-b", "main")
        self._git(root, "config", "user.email", "test@example.com")
        self._git(root, "config", "user.name", "Test")
        self._git(root, "config", "commit.gpgsign", "false")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "probe"\nversion = "0.1.0"\n\n'
            "[tool.commitizen]\n"
            'name = "cz_conventional_commits"\n'
            'version = "0.1.0"\n'
            'tag_format = "v$version"\n'
            "annotated_tag = true\n"
            'version_files = [\n    "pyproject.toml:version",\n'
            '    "src/**/*.py:__version__",\n]\n',
            encoding="utf-8",
        )
        for rel in (
            "src/alpha/__init__.py",
            "src/beta/__init__.py",
            "src/alpha/deep/inner.py",
        ):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.VERSION_LITERAL, encoding="utf-8")
        (root / "README.md").write_text("# probe\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "-m", "feat: initial")
        self._git(root, "tag", "v0.1.0")
        # Something for cz to compute an increment from.
        (root / "README.md").write_text("# probe\nmore\n", encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "-m", "feat: add a thing")

    def test_every_file_cz_rewrote_lands_in_the_bump_commit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = _outside_bindir(root)
            if not _install_cz_shim(bindir):
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            self._init_repo(root)

            # Untracked, at depth 2 — invisible to cz's non-recursive glob and
            # deliberately allowed past the clean-tree gate. If /ship ever
            # globs recursively, `git add` sweeps this into the release.
            scratch = root / "src" / "alpha" / "deep" / "scratch.py"
            scratch.write_text("SCRATCH = True\n", encoding="utf-8")

            result = run_ship(["minor"], root, env=_ship_env(bindir))
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            # THE assertion: nothing cz rewrote was left behind. The tracked
            # tree was clean before the bump (the gate enforces it), so any
            # modified tracked file still dirty here is a file cz rewrote and
            # /ship failed to stage — a partial release under a release tag.
            leftover = self._git(
                root, "status", "--porcelain", "--untracked-files=no"
            ).strip()
            self.assertEqual(
                leftover,
                "",
                msg=f"cz rewrote files the bump commit does not contain:\n{leftover}",
            )

            committed = set(
                self._git(root, "diff", "--name-only", "HEAD~1", "HEAD").split()
            )
            self.assertEqual(
                committed,
                {
                    "CHANGELOG.md",
                    "pyproject.toml",
                    "src/alpha/__init__.py",
                    "src/beta/__init__.py",
                },
                msg=f"unexpected bump-commit contents: {sorted(committed)}",
            )

            # The COMMITTED content carries the new version, not just the
            # worktree — `git add` of the wrong path would still commit, and
            # only reading out of the commit catches that.
            for rel in ("src/alpha/__init__.py", "src/beta/__init__.py"):
                self.assertIn(
                    '__version__ = "0.2.0"',
                    self._git(root, "show", f"HEAD:{rel}"),
                    msg=f"{rel} was committed without the bumped version",
                )
            self.assertIn(
                'version = "0.2.0"', self._git(root, "show", "HEAD:pyproject.toml")
            )

            # cz left the depth-2 files alone; so must /ship.
            self.assertNotIn("src/alpha/deep/inner.py", committed)
            self.assertNotIn("src/alpha/deep/scratch.py", committed)
            self.assertEqual(
                (root / "src" / "alpha" / "deep" / "inner.py").read_text(
                    encoding="utf-8"
                ),
                self.VERSION_LITERAL,
            )

            # The release tag points at that complete commit.
            self.assertEqual(
                self._git(root, "rev-list", "-n", "1", "v0.2.0").strip(),
                self._git(root, "rev-parse", "HEAD").strip(),
            )

    def test_untracked_file_matching_the_glob_stays_out_of_the_release(self):
        """A broad glob must not sweep scratch into the commit and the tag.

        `check_clean_worktree` deliberately lets untracked files through, so
        one CAN be sitting in the tree at bump time — and `src/*/*.py` matches
        it, which means cz rewrites it too. Staging it would put scratch inside
        the annotated tag consumers pin. The same run covers the first-release
        case: `CHANGELOG.md` is equally untracked and MUST be staged, so this
        pins the exemption as well as the rule.
        """
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = _outside_bindir(root)
            if not _install_cz_shim(bindir):
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            self._init_repo(root)

            # Depth 1 — squarely inside `src/**/*.py` as cz expands it.
            scratch = root / "src" / "gamma" / "matched_scratch.py"
            scratch.parent.mkdir(parents=True)
            scratch.write_text("SCRATCH = True\n", encoding="utf-8")
            self.assertIn(
                "?? src/gamma/matched_scratch.py",
                self._git(root, "status", "--porcelain", "--untracked-files=all"),
            )
            self.assertFalse((root / "CHANGELOG.md").exists())

            result = run_ship(["minor"], root, env=_ship_env(bindir))
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            committed = set(
                self._git(root, "diff", "--name-only", "HEAD~1", "HEAD").split()
            )
            self.assertNotIn("src/gamma/matched_scratch.py", committed)
            # Still untracked afterwards — not staged, not committed, not
            # quietly added to the index for the next commit to pick up.
            self.assertIn(
                "?? src/gamma/matched_scratch.py",
                self._git(root, "status", "--porcelain", "--untracked-files=all"),
            )
            # The exemption: a first release's brand-new changelog does ship.
            self.assertIn("CHANGELOG.md", committed)

    @staticmethod
    def _ship_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("ship_under_test", SHIP_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_bumped_files_excludes_untracked_but_keeps_the_changelog(self):
        """Unit twin: one filter, both sources, one exemption."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "src" / "gamma").mkdir(parents=True)
            (root / "src" / "gamma" / "matched_scratch.py").write_text(
                "SCRATCH = True\n", encoding="utf-8"
            )
            (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            files = set(
                mod.bumped_files(
                    root,
                    root / "pyproject.toml",
                    {"version_files": ["src/*/*.py:__version__"]},
                )
            )
            self.assertIn("src/alpha/__init__.py", files)  # tracked, matched
            self.assertNotIn("src/gamma/matched_scratch.py", files)  # untracked
            self.assertIn("CHANGELOG.md", files)  # untracked, exempt

    def test_changelog_exemption_survives_every_spelling_of_the_path(self):
        """The exemption is keyed on the normalized path, not on config text.

        Sixth review round on PR #84, and the bug was mine from the round that
        added the exemption: candidates were normalized through
        `resolve().relative_to(root)` while the exemption stayed raw config
        text, so it only matched when a repo spelled `changelog_file`
        canonically. `./CHANGELOG.md` and `docs/../CHANGELOG.md` are ordinary
        valid spellings, and under them a FIRST release — where the changelog
        is untracked precisely because cz had just created it — committed
        without the changelog cz wrote. A partial release, which is the whole
        thing this function exists to prevent.
        """
        mod = self._ship_module()
        for configured in ("CHANGELOG.md", "./CHANGELOG.md", "docs/../CHANGELOG.md"):
            with self.subTest(changelog_file=configured):
                with tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    self._init_repo(root)
                    # Untracked: cz created it moments ago on a first release.
                    (root / "CHANGELOG.md").write_text(
                        "# Changelog\n", encoding="utf-8"
                    )
                    files = set(
                        mod.bumped_files(
                            root,
                            root / "pyproject.toml",
                            {"changelog_file": configured},
                        )
                    )
                    self.assertIn("CHANGELOG.md", files)

    def test_changelog_exemption_handles_a_nested_path(self):
        """A changelog somewhere other than the repo root is still exempt."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs" / "CHANGES.md").write_text("# Changelog\n", encoding="utf-8")
            files = set(
                mod.bumped_files(
                    root,
                    root / "pyproject.toml",
                    {"changelog_file": "docs/CHANGES.md"},
                )
            )
            self.assertIn("docs/CHANGES.md", files)

    def test_a_changelog_outside_the_repo_is_not_exempted_in(self):
        """The exemption must not become a way back out of the repo.

        `changelog_file` is repo-controlled config; an escaping path gets no
        exemption and no staging, the same answer `changelog_section()` gives
        when asked to read one.
        """
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "repo"
            root.mkdir()
            self._init_repo(root)
            (base / "outside.md").write_text("# Changelog\n", encoding="utf-8")
            files = set(
                mod.bumped_files(
                    root, root / "pyproject.toml", {"changelog_file": "../outside.md"}
                )
            )
            self.assertFalse(any("outside" in f for f in files), files)

    def test_a_rewritten_file_no_pattern_resolved_is_staged_anyway(self):
        """The backstop, isolated: dirty tracked file, glob that cannot see it.

        This is the failure mode the glob alone cannot rule out — whatever cz
        rewrote, the bump commit must contain. The clean-tree gate guarantees a
        dirty tracked file at this point came from cz, so it is staged even
        though no `version_files` pattern resolves to it.
        """
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "src" / "alpha" / "deep" / "inner.py").write_text(
                '__version__ = "0.2.0"\n', encoding="utf-8"
            )
            files = set(
                mod.bumped_files(
                    root,
                    root / "pyproject.toml",
                    {"version_files": ["src/*/__init__.py:__version__"]},
                )
            )
            self.assertIn("src/alpha/deep/inner.py", files)

    def test_untracked_files_are_never_staged_by_the_backstop(self):
        """Scratch is not a release artifact — only the changelog is exempt."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            (root / "src" / "alpha" / "deep" / "scratch.py").write_text(
                "SCRATCH = True\n", encoding="utf-8"
            )
            files = set(mod.bumped_files(root, root / "pyproject.toml", {}))
            self.assertNotIn("src/alpha/deep/scratch.py", files)

    def test_bumped_files_mirrors_cz_glob_expansion(self):
        """Unit-level twin of the above; runs without commitizen installed."""
        mod = self._ship_module()

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            files = set(
                mod.bumped_files(
                    root,
                    root / "pyproject.toml",
                    {"version_files": ["pyproject.toml:version", "src/**/*.py"]},
                )
            )
            self.assertIn("src/alpha/__init__.py", files)
            self.assertIn("src/beta/__init__.py", files)
            # cz's `iglob` stops at one component; expanding recursively here
            # would stage a file cz never rewrote.
            self.assertNotIn("src/alpha/deep/inner.py", files)


class DryRunIsReadOnlyThroughCz(unittest.TestCase):
    """`--dry-run` must not write, and `uv run cz` writes before cz runs.

    Fourth review round on PR #84. The branch advertises "a dry run leaves the
    working tree exactly as it found it", but Python mode reached commitizen
    via `uv run cz` whenever uv was on PATH — and uv materializes `.venv`
    (measured against uv 0.11.3: `--no-sync` and `--no-sync --frozen` both
    still print "Creating virtual environment at: .venv") before cz executes.
    So `/ship --dry-run` in a configured repo with no `.venv` wrote to the tree
    just by being asked what would ship.
    """

    _init_repo = BumpCommitCompleteness._init_repo
    _git = BumpCommitCompleteness._git
    _ship_module = staticmethod(BumpCommitCompleteness._ship_module)
    VERSION_LITERAL = BumpCommitCompleteness.VERSION_LITERAL

    def _assert_tree_untouched(self, root: Path) -> None:
        self.assertFalse((root / ".venv").exists(), ".venv was created by a dry run")
        self.assertFalse(
            (root / "uv.lock").exists(), "uv.lock was written by a dry run"
        )
        self.assertEqual(
            self._git(root, "status", "--porcelain").strip(),
            "",
            "a dry run left changes in the working tree",
        )

    def test_dry_run_refuses_rather_than_letting_uv_write(self):
        """uv reachable, cz not: stop with a read-only message, write nothing."""
        uv = shutil.which("uv")
        if not uv:
            self.skipTest("uv not installed")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._init_repo(root)
            # PATH with uv and provably no cz — the exact shape that used to
            # silently degrade to `uv run cz`.
            bindir = _outside_bindir(root, with_uv=True)
            env = _ship_env(bindir)
            # This test is about cz being ABSENT, so prove it is rather than
            # assuming the host has no global commitizen.
            if shutil.which("cz", path=env["PATH"]):
                self.skipTest("host has a global cz on PATH; absence not testable")

            result = run_ship(["--dry-run"], root, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("cannot simulate the bump without writing", result.stderr)
            self.assertIn("uv sync", result.stderr)
            self._assert_tree_untouched(root)

    def test_dry_run_simulates_with_a_preexisting_cz_and_writes_nothing(self):
        """The happy path still answers the question — without touching the tree."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = _outside_bindir(root)
            if not _install_cz_shim(bindir):
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            self._init_repo(root)

            result = run_ship(["--dry-run"], root, env=_ship_env(bindir))

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("dry run complete", result.stdout + result.stderr)
            self._assert_tree_untouched(root)
            # And it really simulated: no bump commit, no tag.
            self.assertEqual(self._git(root, "tag", "--list").split(), ["v0.1.0"])
            self.assertIn(
                "feat: add a thing", self._git(root, "log", "-1", "--pretty=%s")
            )

    def test_resolve_cz_never_returns_uv_run_under_dry_run(self):
        """The rule itself: a dry run only ever executes a cz that exists.

        PATH is controlled for every assertion. `resolve_cz` deliberately DOES
        fall back to a `cz` on PATH, so on a host with a global commitizen an
        ambient-PATH version of this test would fail while the code behaved
        exactly as designed — the test would be measuring the machine.
        """
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = root / "bin"
            bindir.mkdir()

            # Nothing reachable: a dry run gives up rather than letting uv write.
            with mock.patch.dict(os.environ, {"PATH": str(bindir)}):
                self.assertIsNone(
                    mod.resolve_cz(root, dry_run=True),
                    "dry run resolved a cz in a project that has none",
                )

            # uv reachable, cz still not: STILL gives up. This is the assertion
            # the blocker was about — `uv run cz` must never be the dry-run
            # answer, however available uv is.
            fake_uv = bindir / "uv"
            fake_uv.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_uv.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": str(bindir)}):
                self.assertIsNone(mod.resolve_cz(root, dry_run=True))
                # ...while a real bump is allowed to make uv build the env.
                self.assertEqual(
                    mod.resolve_cz(root, dry_run=False), ["uv", "run", "cz"]
                )

            # cz reachable: the dry run uses THAT, not `uv run`.
            fake_cz = bindir / "cz"
            fake_cz.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_cz.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": str(bindir)}):
                self.assertEqual(mod.resolve_cz(root, dry_run=True), [str(fake_cz)])

    def test_dry_run_prefers_the_projects_own_venv_cz(self):
        """`.venv/bin/cz` wins: the dry run predicts the release it simulates."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            venv_cz = root / ".venv" / "bin" / "cz"
            venv_cz.parent.mkdir(parents=True)
            venv_cz.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            venv_cz.chmod(0o755)
            self.assertEqual(mod.resolve_cz(root, dry_run=True), [str(venv_cz)])

    def test_a_non_executable_venv_cz_is_not_used(self):
        """A file at `.venv/bin/cz` that cannot run is not a cz."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = root / "bin"
            bindir.mkdir()
            venv_cz = root / ".venv" / "bin" / "cz"
            venv_cz.parent.mkdir(parents=True)
            venv_cz.write_text("not a program\n", encoding="utf-8")
            venv_cz.chmod(0o644)
            # Empty PATH, so "not used" cannot be satisfied by a host cz.
            with mock.patch.dict(os.environ, {"PATH": str(bindir)}):
                self.assertIsNone(mod.resolve_cz(root, dry_run=True))


class ChangelogPathContainment(unittest.TestCase):
    """`changelog_file` must not read outside the repo into the tag message.

    Fifth review round on PR #84. `bumped_files()` already dropped escaping
    paths via `relative_to(root)`; `changelog_section()` did not, so a
    repo-controlled `pyproject.toml` could point `changelog_file` outside the
    tree and have whatever sat under a `## <version>` heading copied into the
    annotated tag message — which gets pushed.

    Thin threat model (running /ship in an untrusted repo already runs its
    `uv run cz`), but the same rule was enforced in one place and absent in its
    twin, inside one file. Escaping degrades the message; it never fails the
    release.
    """

    @staticmethod
    def _ship_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("ship_under_test", SHIP_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    SECRET = "# Changelog\n\n## 1.2.0\n\nSECRET-OUTSIDE-THE-REPO\n"

    def test_relative_escape_returns_none(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "outside.md").write_text(self.SECRET, encoding="utf-8")
            root = base / "repo"
            root.mkdir()
            self.assertIsNone(
                mod.changelog_section(
                    root, {"changelog_file": "../outside.md"}, "1.2.0"
                )
            )

    def test_absolute_path_outside_the_repo_returns_none(self):
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            outside = base / "outside.md"
            outside.write_text(self.SECRET, encoding="utf-8")
            root = base / "repo"
            root.mkdir()
            self.assertIsNone(
                mod.changelog_section(root, {"changelog_file": str(outside)}, "1.2.0")
            )

    def test_symlink_out_of_the_repo_returns_none(self):
        """`resolve()` follows the link, so the escape is caught by content."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "outside.md").write_text(self.SECRET, encoding="utf-8")
            root = base / "repo"
            root.mkdir()
            (root / "CHANGELOG.md").symlink_to(base / "outside.md")
            self.assertIsNone(mod.changelog_section(root, {}, "1.2.0"))

    def test_the_secret_never_reaches_the_tag_message(self):
        """End of the chain: the tag degrades to its subject, nothing leaks."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "outside.md").write_text(self.SECRET, encoding="utf-8")
            root = base / "repo"
            root.mkdir()
            message = mod.build_tag_message(
                root, {"changelog_file": "../outside.md"}, "v1.2.0", "1.2.0"
            )
            self.assertEqual(message, "Release v1.2.0")
            self.assertNotIn("SECRET-OUTSIDE-THE-REPO", message)

    def test_a_changelog_inside_the_repo_still_works(self):
        """The guard must not break the ordinary case it wraps."""
        mod = self._ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "docs" / "CHANGES.md").write_text(
                "# Changelog\n\n## 1.2.0\n\n- did a thing\n\n## 1.1.0\n\n- older\n",
                encoding="utf-8",
            )
            body = mod.changelog_section(
                root, {"changelog_file": "docs/CHANGES.md"}, "1.2.0"
            )
            self.assertEqual(body, "- did a thing")
            self.assertNotIn("older", body)


if __name__ == "__main__":
    unittest.main()
