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
