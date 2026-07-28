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


def _ship_module(name: str = "ship_branch_under_test"):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, SHIP_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ConductorReleaseBranch(unittest.TestCase):
    """`conductor.yml`'s `release.branch` wins over the house default.

    The release tool and the dispatch policy must not silently disagree about
    which branch releases — that disagreement is the whole drift class ADR-0008
    is about. /ship READS the key; it does not own the contract.
    """

    def test_reads_this_repos_own_contract(self):
        """Not a fixture: the real conductor.yml this repo ships with."""
        mod = _ship_module()
        self.assertEqual(mod.conductor_release_branch(REPO_ROOT), "main")

    def test_declared_branch_overrides_the_default(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "conductor.yml").write_text(
                "version: 1\nrelease:\n  branch: trunk\n  tagPattern: 'v*'\n",
                encoding="utf-8",
            )
            self.assertEqual(mod.conductor_release_branch(root), "trunk")

    def test_conductor_yaml_extension_also_read(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "conductor.yaml").write_text(
                "release:\n  branch: shipping\n", encoding="utf-8"
            )
            self.assertEqual(mod.conductor_release_branch(root), "shipping")

    def test_no_contract_and_no_release_block_return_none(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertIsNone(mod.conductor_release_branch(root))
            (root / "conductor.yml").write_text(
                "version: 1\nbaseBranch: main\n", encoding="utf-8"
            )
            self.assertIsNone(mod.conductor_release_branch(root))

    YAML_WITH_A_DECOY = (
        "# a comment\n"
        "worktree:\n"
        "  release:\n"
        "    branch: not-this-one\n"
        "release:\n"
        "  branch: shipline   # trailing comment\n"
        "  tagPattern: 'v*'\n"
    )

    def test_only_the_top_level_release_block_counts(self):
        mod = _ship_module()
        self.assertEqual(
            mod._release_branch_from_yaml(self.YAML_WITH_A_DECOY), "shipline"
        )

    def test_the_same_answer_without_pyyaml(self):
        """ship.py runs under whatever interpreter run-hook finds — no deps.

        `sys.modules["yaml"] = None` makes `import yaml` raise ImportError,
        which is exactly the state a missing or broken PyYAML puts the process
        in. If the fallback scanner ever regresses, the two answers diverge.
        """
        mod = _ship_module()
        with mock.patch.dict(sys.modules, {"yaml": None}):
            with self.assertRaises(ImportError):
                import yaml  # noqa: F401
            self.assertEqual(
                mod._release_branch_from_yaml(self.YAML_WITH_A_DECOY), "shipline"
            )
            self.assertIsNone(mod._release_branch_from_yaml("version: 1\n"))


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


def make_repo(root: Path, *, version: str = "0.1.0") -> None:
    """A minimal commitizen-configured repo on `main`, tagged at `version`."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    git(root, "config", "commit.gpgsign", "false")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n\n'
        "[tool.commitizen]\n"
        'name = "cz_conventional_commits"\n'
        f'version = "{version}"\n'
        'tag_format = "v$version"\n'
        'version_files = ["pyproject.toml:version"]\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat: initial")
    git(root, "tag", "-a", f"v{version}", "-m", f"Release v{version}")


def make_pep621_repo(root: Path) -> None:
    """A repo where cz keeps NO version of its own — `[project]` is the source.

    `version_provider = "pep621"` is a supported, ordinary commitizen setup, and
    the one where reading only `[tool.commitizen] version` finds nothing.
    """
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    git(root, "config", "commit.gpgsign", "false")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo621"\nversion = "0.1.0"\n'
        'requires-python = ">=3.11"\ndependencies = []\n\n'
        "[tool.commitizen]\n"
        'name = "cz_conventional_commits"\n'
        'version_provider = "pep621"\n'
        'tag_format = "v$version"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("# demo621\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat: initial")
    git(root, "tag", "-a", "v0.1.0", "-m", "Release v0.1.0")


def make_two_stage(base: Path) -> tuple[Path, Path]:
    """`(bare origin, working clone)` with `main` + `dev` both published.

    A real remote, not a mock: everything `--tag` asserts (fetch, remote-sync,
    tag absence on the remote, the push itself) is git talking to git.
    """
    origin = base / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
        check=True,
        capture_output=True,
    )
    work = base / "work"
    make_repo(work)
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main")
    git(work, "push", "-q", "origin", "--tags")
    git(work, "checkout", "-q", "-b", "dev")
    git(work, "push", "-q", "-u", "origin", "dev")
    return origin, work


def feature_commit(root: Path, name: str = "feature.py") -> None:
    (root / name).write_text("X = 1\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", f"feat: add {name}")


def cz_env(root: Path) -> dict[str, str] | None:
    """PATH exposing git + a real cz, or None if commitizen is unreachable."""
    bindir = _outside_bindir(root)
    if not _install_cz_shim(bindir):
        return None
    return _ship_env(bindir)


class ModeSelection(unittest.TestCase):
    """The branch selects the act. Flags override the act, never the branch.

    Unit-level table over `resolve_mode`; the end-to-end classes below prove
    the same rules against real repos.
    """

    def topo(self, current, *, release="main", integration="dev", in_git=True):
        mod = _ship_module()
        return mod, mod.Topology(release, integration, current, in_git)

    def test_integration_branch_bumps_only(self):
        mod, topo = self.topo("dev")
        self.assertEqual(mod.resolve_mode(topo, None), (mod.MODE_BUMP_ONLY, None))

    def test_release_branch_of_a_single_stage_repo_bumps_and_tags(self):
        mod, topo = self.topo("main", integration=None)
        self.assertEqual(mod.resolve_mode(topo, None), (mod.MODE_BUMP_AND_TAG, None))

    def test_release_branch_of_a_two_stage_repo_refuses_and_names_the_flag(self):
        mod, topo = self.topo("main")
        mode, refusal = mod.resolve_mode(topo, None)
        self.assertIsNone(mode)
        self.assertIn("/ship --tag", refusal)
        self.assertIn("--bump-and-tag", refusal)

    def test_any_other_branch_refuses(self):
        for integration in ("dev", None):
            with self.subTest(integration=integration):
                mod, topo = self.topo("feat/thing", integration=integration)
                mode, refusal = mod.resolve_mode(topo, None)
                self.assertIsNone(mode)
                self.assertIn("feat/thing", refusal)
                self.assertIn("nothing was written", refusal.lower())

    def test_an_override_does_not_unlock_a_feature_branch(self):
        """Overrides pick the ACT. A feature branch still has no release."""
        mod, topo = self.topo("feat/thing")
        for requested in (mod.MODE_BUMP_ONLY, mod.MODE_BUMP_AND_TAG, mod.MODE_TAG):
            with self.subTest(requested=requested):
                self.assertIsNone(mod.resolve_mode(topo, requested)[0])

    def test_bump_only_is_available_on_either_branch(self):
        """It writes no tag, so it cannot put one on the wrong branch."""
        for current in ("dev", "main"):
            with self.subTest(current=current):
                mod, topo = self.topo(current)
                self.assertEqual(
                    mod.resolve_mode(topo, mod.MODE_BUMP_ONLY)[0], mod.MODE_BUMP_ONLY
                )

    def test_every_tag_creating_override_is_confined_to_the_release_branch(self):
        """Review blocker on PR #88 (third round), and a real one.

        `--bump-and-tag` used to be accepted on the integration branch, which
        left the incident's exact shape reachable behind one flag: a tag cut on
        `dev`, naming a commit a squash-merge never makes an ancestor of
        `main`. An override that reintroduces the failure the change removes is
        that failure, explicitness notwithstanding — and it serves no case, the
        hotfix it exists for being cut ON the release branch.
        """
        mod, dev = self.topo("dev")
        for requested in (mod.MODE_TAG, mod.MODE_BUMP_AND_TAG):
            with self.subTest(requested=requested):
                mode, refusal = mod.resolve_mode(dev, requested)
                self.assertIsNone(mode)
                self.assertIn("`main`", refusal)
                self.assertIn("squash-merge", refusal)

        # Both remain available where a tag legitimately belongs.
        _, main = self.topo("main")
        self.assertEqual(mod.resolve_mode(main, mod.MODE_TAG)[0], mod.MODE_TAG)
        self.assertEqual(
            mod.resolve_mode(main, mod.MODE_BUMP_AND_TAG)[0], mod.MODE_BUMP_AND_TAG
        )

    def test_detached_head_is_not_a_branch(self):
        mod, topo = self.topo(None)
        mode, refusal = mod.resolve_mode(topo, None)
        self.assertIsNone(mode)
        self.assertIn("detached", refusal)

    def test_outside_a_git_repo_behaviour_is_unchanged(self):
        """No branch to select on, and no git to tag with — today's path."""
        mod, topo = self.topo(None, in_git=False)
        self.assertEqual(mod.resolve_mode(topo, None), (mod.MODE_BUMP_AND_TAG, None))

    def test_the_declared_release_branch_is_the_one_that_counts(self):
        mod, topo = self.topo("master", release="master", integration=None)
        self.assertEqual(mod.resolve_mode(topo, None)[0], mod.MODE_BUMP_AND_TAG)
        mod, topo = self.topo("main", release="master", integration=None)
        self.assertIsNone(mod.resolve_mode(topo, None)[0])


class TopologyDetection(unittest.TestCase):
    """Two-stage is derived from `origin/dev`; the release branch from config."""

    def test_no_remote_dev_is_single_stage(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            topo = mod.resolve_topology(root)
            self.assertTrue(topo.in_git)
            self.assertEqual(topo.current, "main")
            self.assertEqual(topo.release, "main")
            self.assertIsNone(topo.integration)
            self.assertFalse(topo.two_stage)

    def test_a_local_dev_branch_alone_is_not_two_stage(self):
        """ADR-0008 §5 says `origin/dev`. A stale local branch is not topology."""
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "branch", "dev")
            self.assertIsNone(mod.resolve_topology(root).integration)

    def test_published_dev_makes_the_repo_two_stage(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            topo = mod.resolve_topology(work)
            self.assertEqual(topo.integration, "dev")
            self.assertEqual(topo.current, "dev")
            self.assertTrue(topo.two_stage)

    def test_conductor_release_branch_overrides_the_house_default(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            (root / "conductor.yml").write_text(
                "release:\n  branch: master\n", encoding="utf-8"
            )
            self.assertEqual(mod.resolve_topology(root).release, "master")

    def test_a_master_repo_releases_from_master(self):
        """`main` is the house rule, not a precondition for having a release.

        Three repos in this fleet are `master` with no `main` and no contract
        (atlas, qute-platform, forgejo-review-kit). Resolving to a branch that
        does not exist would refuse every branch in them — a release tool that
        cannot release.
        """
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "branch", "-m", "main", "master")
            topo = mod.resolve_topology(root)
            self.assertEqual(topo.release, "master")
            self.assertTrue(topo.release_exists)
            self.assertEqual(mod.resolve_mode(topo, None)[0], mod.MODE_BUMP_AND_TAG)

    def test_main_wins_when_a_repo_carries_both(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "branch", "master")
            self.assertEqual(mod.resolve_topology(root).release, "main")

    def test_a_declaration_wins_over_a_branch_that_exists(self):
        """The contract is authoritative even for a branch not checked out yet."""
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            (root / "conductor.yml").write_text(
                "release:\n  branch: release/stable\n", encoding="utf-8"
            )
            topo = mod.resolve_topology(root)
            self.assertEqual(topo.release, "release/stable")
            self.assertTrue(topo.release_exists)

    def test_no_recognisable_release_branch_says_so(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "checkout", "-q", "-b", "trunk")
            git(root, "branch", "-D", "main")
            topo = mod.resolve_topology(root)
            self.assertFalse(topo.release_exists)
            mode, refusal = mod.resolve_mode(topo, None)
            self.assertIsNone(mode)
            self.assertIn("cannot tell which branch this repo releases from", refusal)
            self.assertIn("release:", refusal)
            self.assertIn("branch:", refusal)

    def test_a_release_branch_that_exists_only_on_the_remote_counts(self):
        """`git clone -b dev` never creates a local `main` — origin's is it.

        The ordinary shape of a two-stage checkout: the clone has
        `refs/heads/dev` and `refs/remotes/origin/main`, and nothing else names
        the release branch. Looking only at local heads would resolve "no
        release branch" and refuse the bump.
        """
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, _ = make_two_stage(base)
            clone = base / "clone"
            subprocess.run(
                ["git", "clone", "-q", "-b", "dev", str(origin), str(clone)],
                check=True,
                capture_output=True,
            )
            self.assertEqual(
                git(clone, "branch", "--list", "--format=%(refname:short)").split(),
                ["dev"],
            )
            topo = mod.resolve_topology(clone)
            self.assertEqual(topo.release, "main")
            self.assertTrue(topo.release_exists)
            self.assertEqual(topo.integration, "dev")
            self.assertEqual(mod.resolve_mode(topo, None)[0], mod.MODE_BUMP_ONLY)

    def test_detached_head_reports_no_branch(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "checkout", "-q", "--detach", "HEAD")
            topo = mod.resolve_topology(root)
            self.assertTrue(topo.in_git)
            self.assertIsNone(topo.current)

    def test_a_plain_directory_is_not_a_repo(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod.resolve_topology(Path(d)).in_git)


class FeatureBranchWritesNothing(unittest.TestCase):
    """A refusal that has already written is not a refusal.

    The gate therefore runs before first-time setup, which legitimately edits
    `pyproject.toml` and creates `CHANGELOG.md` — the state this test would
    catch if the gate ever moved below it.
    """

    def test_python_mode_refuses_and_leaves_the_tree_exactly_as_it_was(self):
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            git(work, "checkout", "-q", "-b", "feat/thing")
            feature_commit(work)
            before_head = git(work, "rev-parse", "HEAD")
            before_toml = (work / "pyproject.toml").read_text(encoding="utf-8")
            before_tags = git(work, "tag", "--list")

            result = run_ship(["patch"], work)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("feat/thing", result.stderr)
            self.assertIn("nothing was written", result.stderr.lower())
            self.assertEqual(before_head, git(work, "rev-parse", "HEAD"))
            self.assertEqual(
                before_toml, (work / "pyproject.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(before_tags, git(work, "tag", "--list"))
            self.assertFalse((work / "CHANGELOG.md").exists())
            self.assertFalse((work / ".venv").exists())
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")

    def test_dry_run_on_a_feature_branch_also_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            git(work, "checkout", "-q", "-b", "feat/thing")
            result = run_ship(["--dry-run"], work)
            self.assertEqual(result.returncode, 1)
            self.assertIn("feat/thing", result.stderr)
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")

    def test_plugin_mode_refuses_before_the_release_script_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            PluginModeDispatch._make_marketplace(root, ["demo"])
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "release-plugin.sh").write_text(
                "#!/bin/sh\necho RELEASED\nexit 0\n", encoding="utf-8"
            )
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "chore: marketplace")
            git(root, "checkout", "-q", "-b", "feat/thing")

            result = run_ship(["patch"], root)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertNotIn("RELEASED", result.stdout)
            self.assertIn("plugin releases are cut on `main`", result.stderr)

    def test_plugin_mode_on_the_release_branch_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            PluginModeDispatch._make_marketplace(root, ["demo"])
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "release-plugin.sh").write_text(
                "#!/bin/sh\necho RELEASED\nexit 0\n", encoding="utf-8"
            )
            result = run_ship(["patch"], root)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("RELEASED", result.stdout)


class TwoStageBumpOnly(unittest.TestCase):
    """The integration branch produces a bump commit and NO tag."""

    def test_bump_on_dev_commits_and_creates_no_tag(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            _, work = make_two_stage(base)
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(work)
            before_head = git(work, "rev-parse", "HEAD").strip()

            result = run_ship([], work, env=env)
            out = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=out)

            # A commit happened...
            self.assertNotEqual(before_head, git(work, "rev-parse", "HEAD").strip())
            self.assertIn("bump: version 0.1.0", git(work, "log", "-1", "--pretty=%s"))
            self.assertIn('version = "0.2.0"', git(work, "show", "HEAD:pyproject.toml"))
            self.assertIn("CHANGELOG.md", git(work, "show", "--name-only", "HEAD"))
            # ...and no tag did. This is the whole point.
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])
            # The report names the next step rather than leaving it to docs.
            self.assertIn("NO tag was created", out)
            self.assertIn("/ship --tag", out)
            self.assertIn("`main`", out)

    def test_bump_and_tag_is_refused_on_dev_end_to_end(self):
        """No flag reopens the path that cuts a release tag on `dev`."""
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(work)
            head = git(work, "rev-parse", "HEAD").strip()

            result = run_ship(["--bump-and-tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("squash-merge", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])
            self.assertEqual(head, git(work, "rev-parse", "HEAD").strip())
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")

    def test_bump_and_tag_is_a_hotfix_path_on_the_release_branch(self):
        """The case the override exists for: bump AND tag ON `main`."""
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            git(work, "checkout", "-q", "main")
            feature_commit(work, "hotfix.py")

            result = run_ship(["--bump-and-tag"], work, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertEqual(
                sorted(git(work, "tag", "--list").split()), ["v0.1.0", "v0.2.0"]
            )

    def test_bump_only_override_on_a_single_stage_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)
            result = run_ship(["--bump-only"], root, env=env)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertEqual(git(root, "tag", "--list").split(), ["v0.1.0"])
            self.assertIn("bump: version", git(root, "log", "-1", "--pretty=%s"))


class SingleStageIsUnchanged(unittest.TestCase):
    """A repo with no `origin/dev` must behave exactly as it did before."""

    def test_release_branch_bumps_and_tags_in_one_act(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)

            result = run_ship([], root, env=env)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            self.assertEqual(
                sorted(git(root, "tag", "--list").split()), ["v0.1.0", "v0.2.0"]
            )
            # Annotated, on the bump commit, and nothing pushed anywhere.
            self.assertEqual(
                git(
                    root, "cat-file", "-t", git(root, "rev-parse", "v0.2.0").strip()
                ).strip(),
                "tag",
            )
            self.assertEqual(
                git(root, "rev-list", "-n", "1", "v0.2.0").strip(),
                git(root, "rev-parse", "HEAD").strip(),
            )
            self.assertIn("git push --follow-tags", result.stdout)

    def test_a_master_only_repo_still_ships(self):
        """End-to-end proof of the regression the candidate list prevents."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "branch", "-m", "main", "master")
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)

            result = run_ship([], root, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(root, "tag", "--list").split())

    def test_a_feature_branch_of_a_master_repo_is_still_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "branch", "-m", "main", "master")
            git(root, "checkout", "-q", "-b", "feat/thing")
            result = run_ship([], root)
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("`master`", result.stderr)

    def test_a_remote_without_dev_is_still_single_stage(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin = base / "origin.git"
            subprocess.run(
                ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
                check=True,
                capture_output=True,
            )
            work = base / "work"
            make_repo(work)
            git(work, "remote", "add", "origin", str(origin))
            git(work, "push", "-q", "origin", "main")
            git(work, "push", "-q", "origin", "--tags")
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(work)

            result = run_ship([], work, env=env)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(work, "tag", "--list").split())
            # Bump-and-tag does not push; the caller does.
            self.assertNotIn("v0.2.0", git(origin, "tag", "--list").split())


class TagCompletesTheRelease(unittest.TestCase):
    """`/ship --tag` on the release branch, after a SQUASH merge.

    The squash is the incident: it creates a new commit on the release branch,
    so a tag cut on `dev` is never an ancestor of `main`. Doing the tag here,
    afterwards, is what makes squash-merging a release PR safe again.
    """

    def _bumped_and_squash_merged(self, base: Path) -> tuple[Path, Path, dict]:
        origin, work = make_two_stage(base)
        env = cz_env(work)
        if env is None:
            self.skipTest("commitizen not reachable via `cz` or `uv`")
        feature_commit(work)
        result = run_ship([], work, env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        git(work, "push", "-q", "origin", "dev")
        git(work, "checkout", "-q", "main")
        git(work, "merge", "--squash", "dev")
        git(work, "commit", "-q", "-m", "feat: release 0.2.0")
        git(work, "push", "-q", "origin", "main")
        return origin, work, env

    def test_tag_is_created_annotated_pushed_and_on_the_release_branch(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))

            result = run_ship(["--tag"], work, env=env)
            out = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=out)

            self.assertIn("v0.2.0", git(work, "tag", "--list").split())
            self.assertEqual(
                git(
                    work, "cat-file", "-t", git(work, "rev-parse", "v0.2.0").strip()
                ).strip(),
                "tag",
            )
            # Pushed — the tag exists on the remote, still annotated.
            self.assertIn("v0.2.0", git(origin, "tag", "--list").split())
            self.assertEqual(
                git(
                    origin, "cat-file", "-t", git(origin, "rev-parse", "v0.2.0").strip()
                ).strip(),
                "tag",
            )
            # And the assertion the release-tag-guard workflow makes on push:
            # the tagged commit IS an ancestor of the release branch, despite
            # the squash. Cutting the tag on `dev` would fail this.
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(work),
                    "merge-base",
                    "--is-ancestor",
                    "v0.2.0^{commit}",
                    "origin/main",
                ],
                check=True,
                capture_output=True,
            )
            # The changelog body rode along into the tag message.
            self.assertIn("v0.2.0", git(work, "tag", "-n1", "--list", "v0.2.0"))

    def test_refuses_when_the_branch_is_ahead_of_its_remote(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            feature_commit(work, "unpushed.py")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("does not match", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])
            self.assertNotIn("v0.2.0", git(origin, "tag", "--list").split())

    def test_refuses_when_the_branch_is_behind_its_remote(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, work, env = self._bumped_and_squash_merged(base)
            # Someone else pushes to main; we have not pulled.
            other = base / "other"
            subprocess.run(
                ["git", "clone", "-q", str(origin), str(other)],
                check=True,
                capture_output=True,
            )
            git(other, "config", "user.email", "other@example.com")
            git(other, "config", "user.name", "Other")
            git(other, "config", "commit.gpgsign", "false")
            feature_commit(other, "theirs.py")
            git(other, "push", "-q", "origin", "main")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("does not match", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    # Both tag-absence tests assert /ship's OWN wording, not the substring
    # "already exists". git says that too — `git tag -a` on an existing tag and
    # `git push` of a diverged one both do — so a test keyed on it passes when
    # the precondition has been deleted and git happens to catch the fallout
    # afterwards. That is a test measuring git, and it survived exactly this
    # mutation before being tightened.
    REFUSAL = "bump again before tagging again"

    def test_refuses_when_the_tag_already_exists_locally(self):
        """A hand-cut, UNPUSHED tag. Only the local check can see this one."""
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            git(work, "tag", "-a", "v0.2.0", "-m", "hand-cut")
            self.assertNotIn("v0.2.0", git(origin, "tag", "--list").split())

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn(self.REFUSAL, result.stderr)
            self.assertNotIn("v0.2.0", git(origin, "tag", "--list").split())

    def test_refuses_a_tag_that_exists_only_on_the_remote(self):
        """The fetch is load-bearing: a tag pushed elsewhere still counts.

        Nothing local knows about `v0.2.0` when this starts. It is caught only
        because step 1 fetches `--tags` before step 4 reads the local refs — so
        this test fails if the fetch is ever dropped, which is precisely the
        reason the local check is allowed to be the only one.
        """
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            git(work, "tag", "-a", "v0.2.0", "-m", "Release v0.2.0")
            git(work, "push", "-q", "origin", "v0.2.0")
            remote_tag_object = git(origin, "rev-parse", "v0.2.0").strip()
            git(work, "tag", "-d", "v0.2.0")
            self.assertNotIn("v0.2.0", git(work, "tag", "--list").split())

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn(self.REFUSAL, result.stderr)
            # The only v0.2.0 in this repo is the one the fetch brought back —
            # /ship created no tag object of its own.
            self.assertEqual(
                git(work, "rev-parse", "v0.2.0").strip(), remote_tag_object
            )

    def test_refuses_when_the_remote_cannot_be_reached(self):
        """`--tag` pushes; it cannot verify or publish anything offline."""
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, work, env = self._bumped_and_squash_merged(base)
            git(work, "remote", "set-url", "origin", str(base / "vanished.git"))

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("could not fetch", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    def test_refuses_when_the_named_version_is_not_the_one_at_the_tip(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))

            result = run_ship(["--tag", "9.9.9"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("9.9.9", result.stderr)
            self.assertIn("0.2.0", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    def test_refuses_when_the_working_tree_disagrees_with_the_tip(self):
        """The tag names a COMMIT; an uncommitted bump is not in it."""
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            toml = work / "pyproject.toml"
            toml.write_text(
                toml.read_text(encoding="utf-8").replace("0.2.0", "0.3.0"),
                encoding="utf-8",
            )

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("0.3.0", result.stderr)
            self.assertIn("0.2.0", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    def test_refuses_on_the_integration_branch(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            git(work, "checkout", "-q", "dev")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("belongs on `main`", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    def test_refuses_when_no_remote_is_unambiguously_the_publisher(self):
        """Review blocker on PR #88 (second round), and a real one.

        Several remotes and no `origin` used to resolve to None, which
        `ship_tag` read as "local-only repo" — so it announced no remote was
        configured, skipped the fetch AND the sync check, created the tag, and
        did not push it. A release that looks cut and is not: the exact
        silent-late failure this change exists to end.
        """
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, work, env = self._bumped_and_squash_merged(base)
            git(work, "remote", "rename", "origin", "upstream")
            git(work, "remote", "add", "fork", str(base / "fork.git"))

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("cannot tell which remote", result.stderr)
            self.assertIn("upstream", result.stderr)
            self.assertIn("fork", result.stderr)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])

    def test_a_single_non_origin_remote_is_unambiguous(self):
        """One remote is not a guess — it is the only answer."""
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, work, env = self._bumped_and_squash_merged(base)
            git(work, "remote", "rename", "origin", "upstream")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(origin, "tag", "--list").split())

    def test_a_repo_with_no_remote_at_all_tags_locally(self):
        """No remote is a legitimate state; ambiguity is not."""
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            origin, work, env = self._bumped_and_squash_merged(base)
            git(work, "remote", "remove", "origin")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("no git remote is configured", result.stdout)
            self.assertIn("v0.2.0", git(work, "tag", "--list").split())

    def test_dry_run_asserts_everything_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))

            result = run_ship(["--tag", "--dry-run"], work, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("would create annotated tag `v0.2.0`", result.stdout)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])
            self.assertNotIn("v0.2.0", git(origin, "tag", "--list").split())
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")
            self.assertFalse((work / ".venv").exists())

    def test_tag_and_an_increment_are_contradictory(self):
        with tempfile.TemporaryDirectory() as d:
            origin, work, env = self._bumped_and_squash_merged(Path(d))
            result = run_ship(["--tag", "minor"], work, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(git(work, "tag", "--list").split(), ["v0.1.0"])


class InFlightBumpGuard(unittest.TestCase):
    """A declared-but-untagged version blocks the next bump.

    cz computes the increment from the last TAG, so a second bump in that
    window reads a baseline one release behind. The refusal is sticky by
    design, which is why it must name both ways out.
    """

    def test_a_second_bump_refuses_and_names_both_exits(self):
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(work)
            self.assertEqual(run_ship([], work, env=env).returncode, 0)
            head_after_bump = git(work, "rev-parse", "HEAD").strip()
            feature_commit(work, "second.py")

            result = run_ship([], work, env=env)

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("already in flight", result.stderr)
            # Both exits, named.
            self.assertIn("/ship --tag", result.stderr)
            self.assertIn("git revert", result.stderr)
            # And the bump commit it points at is the real one.
            self.assertIn(head_after_bump[:7], result.stderr)
            # It refused before ANYTHING wrote — including first-time setup,
            # which edits pyproject.toml. A refusal that dirties the tree sends
            # the next run into the clean-tree gate for an unrelated reason.
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")
            self.assertNotIn(
                'version = "0.3.0"',
                (work / "pyproject.toml").read_text(encoding="utf-8"),
            )
            # ...and it stays refused for the SAME reason on a second attempt.
            again = run_ship([], work, env=env)
            self.assertEqual(again.returncode, 1)
            self.assertIn("already in flight", again.stderr)
            self.assertEqual(git(work, "status", "--porcelain").strip(), "")

    def test_a_first_release_is_not_blocked(self):
        """No release tags at all is the initial state, not an abandoned bump."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "tag", "-d", "v0.1.0")
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)

            result = run_ship([], root, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(root, "tag", "--list").split())

    def test_unrelated_tags_do_not_forfeit_the_first_release_exception(self):
        """`nightly-*` is not this repo's release series."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "tag", "-d", "v0.1.0")
            git(root, "tag", "-a", "nightly-2026-07-28", "-m", "nightly")
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)

            result = run_ship([], root, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(root, "tag", "--list").split())

    def test_a_pep621_repo_is_guarded_too(self):
        """Review blocker on PR #88, and a real one.

        Under `version_provider = "pep621"` commitizen keeps no version of its
        own, so reading only `[tool.commitizen] version` returns None — and a
        guard handed None does not fire. The repos that declare their version
        the standard way would have been the ones with no protection. This is
        the end-to-end proof against a real cz using that provider.
        """
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_pep621_repo(root)
            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(root)

            first = run_ship(["--bump-only"], root, env=env)
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            self.assertIn('version = "0.2.0"', git(root, "show", "HEAD:pyproject.toml"))
            self.assertEqual(git(root, "tag", "--list").split(), ["v0.1.0"])

            feature_commit(root, "second.py")
            second = run_ship(["--bump-only"], root, env=env)

            self.assertEqual(second.returncode, 1, msg=second.stdout + second.stderr)
            self.assertIn("already in flight", second.stderr)
            self.assertIn("v0.2.0", second.stderr)
            self.assertEqual(git(root, "status", "--porcelain").strip(), "")

    def test_the_declared_version_reader_sees_every_declaration_style(self):
        """Unit twin: the guard is only as good as the version it is handed."""
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_pep621_repo(root)
            pyproject = root / "pyproject.toml"
            # No cz reachable, so this proves the FILE read finds it — not a
            # subprocess fallback that happens to be available on this host.
            self.assertEqual(
                mod.declared_version(root, pyproject, ["definitely-not-cz-xyz"]),
                "0.1.0",
            )
            # ...and the guard therefore fires on it.
            pyproject.write_text(
                pyproject.read_text(encoding="utf-8").replace("0.1.0", "0.2.0"),
                encoding="utf-8",
            )
            self.assertEqual(
                mod.check_bump_in_flight(
                    root,
                    ["definitely-not-cz-xyz"],
                    mod._read_cz_config(pyproject),
                    mod.declared_version(root, pyproject, ["definitely-not-cz-xyz"]),
                ),
                1,
            )

    def test_a_prefix_free_tag_format_still_recognises_a_first_release(self):
        """Review blocker on PR #88 (second round), and a real one.

        `tag_format = "$version"` is a supported config that renders bare
        semver tags. The series matcher used to be the glob
        `tag.replace(version, "*")`, which there collapses to `*` — every tag
        in the repo — so a stray `nightly-*` made a FIRST release look like an
        abandoned bump. The `v$version` test passed throughout, because `v*`
        happens to exclude it.
        """
        mod = _ship_module()
        cfg = {"tag_format": "$version"}
        no_cz = ["definitely-not-a-real-binary-xyz"]  # forces local rendering
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            git(root, "tag", "-d", "v0.1.0")
            git(root, "tag", "-a", "nightly-2026-07-28", "-m", "nightly")

            # Only unrelated tags -> first release, not an abandoned bump.
            self.assertEqual(mod.check_bump_in_flight(root, no_cz, cfg, "0.2.0"), 0)

            # A real release tag in the series -> the guard fires again.
            git(root, "tag", "-a", "0.1.0", "-m", "Release 0.1.0")
            self.assertEqual(mod.check_bump_in_flight(root, no_cz, cfg, "0.2.0"), 1)
            # ...and stands down once the declared version IS tagged.
            self.assertEqual(mod.check_bump_in_flight(root, no_cz, cfg, "0.1.0"), 0)

    def test_the_series_matcher_reads_the_shape_around_the_version(self):
        mod = _ship_module()
        for tag, version, yes, no in [
            ("v0.1.0", "0.1.0", ["v0.1.0", "v10.2.3", "v1.0.0rc1"], ["nightly-1", "v"]),
            ("0.1.0", "0.1.0", ["0.1.0", "2.0.0"], ["nightly-2026-07-28", "deploy-3"]),
            (
                "release-0.1.0",
                "0.1.0",
                ["release-1.2.3"],
                ["0.1.0", "release-x", "prerelease-1.2.3"],
            ),
        ]:
            with self.subTest(tag=tag):
                matches = mod._release_tag_matcher(tag, version)
                for t in yes:
                    self.assertTrue(matches(t), f"{t} should match {tag}")
                for t in no:
                    self.assertFalse(matches(t), f"{t} should not match {tag}")

    def test_a_tagged_declared_version_proceeds(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            self.assertEqual(
                mod.check_bump_in_flight(
                    root, [sys.executable, "-c", "pass"], {}, "0.1.0"
                ),
                0,
            )

    def test_the_guard_is_local_only_when_there_is_no_remote(self):
        """Offline / remoteless must not block a release (unit-level)."""
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            self.assertIsNone(mod._remote_name(root))
            # 0.9.0 declared, only v0.1.0 tagged -> in flight, refused.
            self.assertEqual(
                mod.check_bump_in_flight(
                    root, [sys.executable, "-c", "pass"], {}, "0.9.0"
                ),
                1,
            )

    def test_tag_mode_is_the_way_out_and_is_not_itself_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            _, work = make_two_stage(Path(d))
            env = cz_env(work)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            feature_commit(work)
            self.assertEqual(run_ship([], work, env=env).returncode, 0)
            git(work, "push", "-q", "origin", "dev")
            git(work, "checkout", "-q", "main")
            git(work, "merge", "--squash", "dev")
            git(work, "commit", "-q", "-m", "feat: release")
            git(work, "push", "-q", "origin", "main")

            result = run_ship(["--tag"], work, env=env)

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("v0.2.0", git(work, "tag", "--list").split())


class VersionAtTip(unittest.TestCase):
    """ "Declared at the tip" is a claim about the COMMIT, not the tree."""

    def test_reads_the_committed_version_not_the_working_tree(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            toml = root / "pyproject.toml"
            toml.write_text(
                toml.read_text(encoding="utf-8").replace("0.1.0", "9.9.9"),
                encoding="utf-8",
            )
            self.assertEqual(mod._version_at_tip(root, toml), "0.1.0")

    def test_falls_back_to_the_project_table(self):
        """`version_provider = "pep621"` keeps no cz version of its own."""
        mod = _ship_module()
        self.assertEqual(
            mod._declared_version_in_toml(
                '[project]\nname = "x"\nversion = "2.3.4"\n\n'
                '[tool.commitizen]\nversion_provider = "pep621"\n'
            ),
            "2.3.4",
        )

    def test_the_commitizen_version_wins_when_both_are_present(self):
        mod = _ship_module()
        self.assertEqual(
            mod._declared_version_in_toml(
                '[project]\nversion = "1.0.0"\n\n[tool.commitizen]\nversion = "2.0.0"\n'
            ),
            "2.0.0",
        )

    def test_no_commits_yields_none(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(
                ["git", "init", "-q", "-b", "main", str(root)],
                check=True,
                capture_output=True,
            )
            (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            self.assertIsNone(mod._version_at_tip(root, root / "pyproject.toml"))


class LockfileRefresh(unittest.TestCase):
    """The lock is refreshed into the bump commit, best-effort."""

    def test_an_untracked_lockfile_is_left_alone(self):
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            (root / "uv.lock").write_text("# scratch\n", encoding="utf-8")
            mod.refresh_lockfile(root)
            self.assertEqual(
                (root / "uv.lock").read_text(encoding="utf-8"), "# scratch\n"
            )

    def test_a_failing_refresh_warns_instead_of_raising(self):
        """Best-effort by contract: a resolver failure must not block a bump."""
        mod = _ship_module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            make_repo(root)
            # Tracked lock, but a pyproject `uv lock` cannot resolve (no
            # [project] name/version is fine; a bogus dependency is not).
            (root / "uv.lock").write_text("# stale\n", encoding="utf-8")
            git(root, "add", "uv.lock")
            git(root, "commit", "-q", "-m", "chore: lock")
            toml = root / "pyproject.toml"
            toml.write_text(
                toml.read_text(encoding="utf-8").replace(
                    'version = "0.1.0"\n\n[tool.commitizen]',
                    'version = "0.1.0"\n'
                    'requires-python = ">=3.11"\n'
                    'dependencies = ["this-package-does-not-exist-qck349"]\n\n'
                    "[tool.commitizen]",
                    1,
                ),
                encoding="utf-8",
            )
            if not shutil.which("uv"):
                self.skipTest("uv not on PATH")
            mod.refresh_lockfile(root)  # must not raise
            self.assertEqual(
                (root / "uv.lock").read_text(encoding="utf-8"), "# stale\n"
            )

    @unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
    def test_a_tracked_lockfile_is_refreshed_into_the_bump_commit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "repo"
            root.mkdir(parents=True)
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test")
            git(root, "config", "commit.gpgsign", "false")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "demo"\nversion = "0.1.0"\n'
                'requires-python = ">=3.11"\ndependencies = []\n\n'
                "[tool.commitizen]\n"
                'name = "cz_conventional_commits"\n'
                'version = "0.1.0"\n'
                'tag_format = "v$version"\n'
                'version_files = ["pyproject.toml:version"]\n',
                encoding="utf-8",
            )
            (root / "demo.py").write_text("X = 1\n", encoding="utf-8")
            subprocess.run(
                ["uv", "lock"], cwd=root, check=True, capture_output=True, text=True
            )
            self.assertIn(
                'version = "0.1.0"', (root / "uv.lock").read_text(encoding="utf-8")
            )
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "feat: initial")
            git(root, "tag", "-a", "v0.1.0", "-m", "Release v0.1.0")
            feature_commit(root)

            env = cz_env(root)
            if env is None:
                self.skipTest("commitizen not reachable via `cz` or `uv`")
            # uv must be reachable for the refresh itself.
            uv = shutil.which("uv")
            bindir = Path(env["PATH"].split(":")[0])
            if not (bindir / "uv").exists():
                (bindir / "uv").symlink_to(uv)

            result = run_ship([], root, env=env)
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            committed = git(root, "diff", "--name-only", "HEAD~1", "HEAD").split()
            self.assertIn("uv.lock", committed)
            self.assertIn('version = "0.2.0"', git(root, "show", "HEAD:uv.lock"))
            # Nothing left dirty — the lock landed IN the release commit.
            self.assertEqual(
                git(root, "status", "--porcelain", "--untracked-files=no").strip(), ""
            )


if __name__ == "__main__":
    unittest.main()
