"""Smoke tests for the qute-essentials /ship script.

Covers mode dispatch, arg parsing, and forbidden-path behavior. Does not
exercise commitizen — that requires uv/cz and is verified end-to-end via
actual releases.

Run from the repo root:
    python3 -m unittest tests.test_ship
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIP_PY = REPO_ROOT / "plugins" / "qute-essentials" / "scripts" / "ship.py"


def run_ship(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SHIP_PY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
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
    def test_extras_file_parsed_with_comments(self):
        # Module-level import (path acrobatics) of check_forbidden_paths.
        sys.path.insert(0, str(SHIP_PY.parent))
        try:
            from ship import UNIVERSAL_FORBIDDEN  # noqa: F401
        finally:
            sys.path.pop(0)
        self.assertIn(".claude/handoffs", UNIVERSAL_FORBIDDEN)


if __name__ == "__main__":
    unittest.main()


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
