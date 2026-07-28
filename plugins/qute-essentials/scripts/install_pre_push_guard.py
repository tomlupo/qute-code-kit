#!/usr/bin/env python3
"""Install (and then actually VERIFY) the qute pre-push branch guard in a repo.

`/setup-qute-repo` calls this instead of pasting install commands, because the
two things that go wrong here both go wrong silently:

  1. **Wrong world.** A repo that sets `core.hooksPath` makes git ignore
     `.git/hooks` entirely — so `pre-commit install --hook-type pre-push`
     succeeds, writes a file, and installs nothing that will ever run. The
     inverse mistake (dropping a file in `.githooks/` in a repo that has no
     `core.hooksPath`) is equally invisible.
  2. **Reporting the command instead of the outcome.** "Ran the installer, done"
     is not evidence. A hook that silently is not installed is worse than no
     hook, because it manufactures confidence.

So this script detects the world, installs accordingly, and then proves the
result by driving the hook through **git's own resolved hook path** with
synthetic ref lines, checking for the guard's trace marker in the output. What
it prints is a measurement, not a claim.

    python3 install_pre_push_guard.py [--repo PATH] [--mechanism auto|native|pre-commit]
                                      [--adopt-existing] [--opt-in] [--check] [--json]

    --check            verify only; install nothing
    --opt-in           create `.claude/git-guard.json` as `{}` if absent (house
                       defaults). Without an opt-in file the guard is inert and
                       verification says so.
    --adopt-existing   in the native world, move a pre-existing foreign
                       `pre-push` into `pre-push.d/00-legacy-pre-push` and put
                       the qute dispatcher in front of it. Without this flag a
                       foreign hook is left alone and install reports `blocked`.

Exit code is 0 when the final state is what was asked for, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "hooks"
GUARD_SRC = TEMPLATES / "pre-push-branch-guard"
DISPATCHER_SRC = TEMPLATES / "pre-push"

# Where the guard script itself lives inside the target repo. ONE canonical
# location for both worlds, next to the `.claude/git-guard.json` it reads.
GUARD_DEST = Path(".claude/hooks/pre-push-branch-guard")

DISPATCHER_MARKER = "qute-pre-push-dispatcher v1"
PC_CONFIG = ".pre-commit-config.yaml"
PC_MARKER = "qute-pre-push-branch-guard v1"
MARKER = "QUTE_PRE_PUSH_GUARD"
ZERO = "0" * 40

PC_BLOCK = f"""
# {PC_MARKER} — stamped by /setup-qute-repo
-   repo: local
    hooks:
    -   id: qute-pre-push-branch-guard
        name: refuse pushes to guarded branches
        entry: {GUARD_DEST}
        language: script
        stages: [pre-push]
        always_run: true
        pass_filenames: false
        verbose: true
"""


def git(repo: Path, *args: str, check: bool = False):
    out = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out


def git_out(repo: Path, *args: str):
    out = git(repo, *args)
    return out.stdout.strip() if out.returncode == 0 else None


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_if_needed(dest: Path, content: str, executable: bool = False) -> str:
    """Write `content` to `dest`; return created | updated | unchanged."""
    if dest.exists() and dest.read_text(encoding="utf-8") == content:
        if executable and not os.access(dest, os.X_OK):
            make_executable(dest)
            return "updated"
        return "unchanged"
    verb = "updated" if dest.exists() else "created"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    if executable:
        make_executable(dest)
    return verb


# ---------------------------------------------------------------- detection


def detect_world(repo: Path) -> dict:
    """Which installation world this repo is in.

    `core.hooksPath` wins unconditionally: when it is set, git does not look at
    `.git/hooks` at all, so a pre-commit-framework install there is a no-op no
    matter what `.pre-commit-config.yaml` says.
    """
    hooks_path = git_out(repo, "config", "--get", "core.hooksPath")
    resolved = git_out(repo, "rev-parse", "--git-path", "hooks/pre-push")
    hook_file = (repo / resolved).resolve() if resolved else None
    has_pc_config = (repo / PC_CONFIG).is_file()
    pc_bin = shutil.which("pre-commit")

    if hooks_path:
        world = "hooksPath"
    elif has_pc_config:
        world = "pre-commit"
    else:
        world = "native"

    return {
        "world": world,
        "core_hooks_path": hooks_path,
        "hook_file": str(hook_file) if hook_file else None,
        "pre_commit_config": has_pc_config,
        "pre_commit_bin": pc_bin,
    }


def choose_mechanism(world: dict, requested: str) -> str:
    if requested != "auto":
        return requested
    if world["world"] == "pre-commit" and world["pre_commit_bin"]:
        return "pre-commit"
    return "native"


# ----------------------------------------------------------------- install


def install_native(repo: Path, world: dict, adopt: bool, actions: list) -> bool:
    """Put the dispatcher at the path git will actually invoke."""
    hook_file = Path(world["hook_file"])
    hook_file.parent.mkdir(parents=True, exist_ok=True)

    if hook_file.exists():
        existing = hook_file.read_text(encoding="utf-8", errors="replace")
        if DISPATCHER_MARKER in existing:
            actions.append(
                f"dispatcher {write_if_needed(hook_file, DISPATCHER_SRC.read_text(), True)}: {hook_file}"
            )
            return True
        if not adopt:
            actions.append(
                f"BLOCKED: {hook_file} already exists and is not the qute "
                "dispatcher. Re-run with --adopt-existing to move it to "
                "pre-push.d/00-legacy-pre-push and chain it behind the guard."
            )
            return False
        legacy_dir = hook_file.parent / "pre-push.d"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy = legacy_dir / "00-legacy-pre-push"
        if legacy.exists():
            actions.append(f"BLOCKED: {legacy} already exists; refusing to overwrite")
            return False
        hook_file.rename(legacy)
        make_executable(legacy)
        actions.append(f"adopted existing pre-push -> {legacy}")

    actions.append(
        f"dispatcher {write_if_needed(hook_file, DISPATCHER_SRC.read_text(), True)}: {hook_file}"
    )
    return True


def install_pre_commit(repo: Path, world: dict, actions: list) -> bool:
    cfg = repo / PC_CONFIG
    if not cfg.is_file():
        actions.append(f"BLOCKED: no {PC_CONFIG} in {repo}")
        return False
    if not world["pre_commit_bin"]:
        actions.append("BLOCKED: `pre-commit` is not on PATH")
        return False

    def _validate():
        return subprocess.run(
            [world["pre_commit_bin"], "validate-config", PC_CONFIG],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )

    text = cfg.read_text(encoding="utf-8")
    if PC_MARKER in text:
        actions.append(f"{PC_CONFIG}: guard entry already present")
    else:
        # Validate BEFORE appending. Blaming our own block for a config that
        # was already broken would send whoever runs this on a hunt for a bug
        # that isn't there.
        was_valid = _validate().returncode == 0
        backup = text
        cfg.write_text(text.rstrip("\n") + "\n" + PC_BLOCK, encoding="utf-8")
        check = _validate()
        if check.returncode != 0:
            if was_valid:
                cfg.write_text(backup, encoding="utf-8")
                actions.append(
                    f"BLOCKED: appending the guard entry made {PC_CONFIG} "
                    f"invalid ({check.stdout.strip() or check.stderr.strip()}); "
                    "reverted. Add the entry by hand under `repos:`."
                )
                return False
            actions.append(
                f"WARNING: {PC_CONFIG} was ALREADY invalid before this ran "
                "— guard entry appended anyway; fix the pre-existing error or "
                "no pre-commit hook will run at all."
            )
        else:
            actions.append(f"{PC_CONFIG}: guard entry added")

    inst = subprocess.run(
        [world["pre_commit_bin"], "install", "--hook-type", "pre-push"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    actions.append(
        f"pre-commit install --hook-type pre-push -> rc={inst.returncode} "
        f"{(inst.stdout or inst.stderr).strip()}"
    )
    return inst.returncode == 0


# ------------------------------------------------------------------ verify


def _is_pre_commit_shim(hook_file: Path) -> bool:
    try:
        head = hook_file.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return False
    return "pre-commit" in head and "hook-impl" in head


def _probe(repo: Path, hook_file: Path, line: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, QUTE_PRE_PUSH_GUARD_TRACE="1")
    # PRE_COMMIT_ALLOW_NO_CONFIG keeps the probe meaningful if the framework
    # shim is present but the config was removed.
    env.setdefault("PRE_COMMIT_ALLOW_NO_CONFIG", "1")
    return subprocess.run(
        [str(hook_file), "origin", "probe://verify"],
        cwd=str(repo),
        input=line + "\n",
        capture_output=True,
        text=True,
        env=env,
    )


def verify(repo: Path, world: dict) -> dict:
    """Drive the hook through git's resolved path and measure what it does."""
    result = {"reachable": False, "checks": [], "coverage": {}, "ok": False}
    hook_file = Path(world["hook_file"]) if world["hook_file"] else None

    if hook_file is None or not hook_file.exists():
        result["checks"].append(
            ("hook present at git's resolved path", False, str(hook_file))
        )
        return result
    if not os.access(hook_file, os.X_OK):
        result["checks"].append(("hook is executable", False, str(hook_file)))
        return result
    result["checks"].append(
        ("hook present + executable at git's resolved path", True, str(hook_file))
    )

    cfg_path = repo / ".claude" / "git-guard.json"
    if not cfg_path.is_file():
        result["checks"].append(
            (
                "repo opted in (.claude/git-guard.json)",
                False,
                "guard is installed but INERT — no config file, so it guards nothing",
            )
        )
        return result

    protected, integration = _resolve_branches(repo, cfg_path)

    head = git_out(repo, "rev-parse", "HEAD")
    if not head:
        result["checks"].append(
            ("repo has a commit to probe with", False, "empty repo")
        )
        return result

    # 1. update to the protected branch must refuse, and the refusal must carry
    #    the guard's own marker — that is what proves OUR script ran, rather
    #    than something else in the chain failing.
    p = _probe(
        repo, hook_file, f"refs/heads/probe {head} refs/heads/{protected} {head}"
    )
    out = p.stdout + p.stderr
    refused = p.returncode != 0 and f"{MARKER}: refuse {protected}" in out
    result["reachable"] = f"{MARKER}:" in out
    result["checks"].append(
        (
            f"push to protected branch '{protected}' is refused",
            refused,
            f"rc={p.returncode}"
            + (
                "" if result["reachable"] else " (guard marker absent — hook never ran)"
            ),
        )
    )
    result["coverage"]["protected_update"] = refused

    # 2. integration branch, when the repo has one.
    if integration:
        p = _probe(
            repo, hook_file, f"refs/heads/probe {head} refs/heads/{integration} {head}"
        )
        out = p.stdout + p.stderr
        ok = p.returncode != 0 and f"{MARKER}: refuse {integration}" in out
        result["checks"].append(
            (
                f"push to integration branch '{integration}' is refused",
                ok,
                f"rc={p.returncode}",
            )
        )
        result["coverage"]["integration_update"] = ok

    # 3. feature branch must pass through.
    p = _probe(
        repo, hook_file, f"refs/heads/qute-probe {head} refs/heads/qute-probe {head}"
    )
    ok = p.returncode == 0
    result["checks"].append(
        ("push to a feature branch is allowed", ok, f"rc={p.returncode}")
    )
    result["coverage"]["feature_allowed"] = ok

    # 4. deletion of a guarded branch. Native sees it; the pre-commit framework
    #    drops all-zero local shas before any hook runs, so this measures
    #    coverage rather than correctness.
    p = _probe(repo, hook_file, f"(delete) {ZERO} refs/heads/{protected} {head}")
    out = p.stdout + p.stderr
    del_refused = p.returncode != 0 and f"{MARKER}: refuse {protected}" in out
    result["coverage"]["delete_guarded"] = del_refused
    if del_refused:
        detail = ""
    elif _is_pre_commit_shim(hook_file):
        detail = (
            "KNOWN GAP of the pre-commit framework: it drops ref lines whose "
            "local sha is all zeros before running any hook, so branch "
            "deletions never reach the guard. Only the native hook path sees "
            "them."
        )
    else:
        detail = "unexpected — the native hook path should see deletions"
    result["checks"].append(
        (f"deletion of '{protected}' is refused", del_refused, detail)
    )

    required = ["protected_update", "feature_allowed"]
    if integration:
        required.append("integration_update")
    result["ok"] = all(result["coverage"].get(k) for k in required)
    return result


def _resolve_branches(repo: Path, cfg_path: Path):
    """Mirror of the guard's config resolution, for probe construction."""
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    protected = raw.get("protected_branch") or "main"
    if "integration_branch" in raw:
        integration = raw["integration_branch"] or None
    else:
        exists = (
            git(
                repo, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/dev"
            ).returncode
            == 0
        )
        integration = "dev" if exists else None
    if integration == protected:
        integration = None
    return protected, integration


# -------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument(
        "--mechanism", choices=["auto", "native", "pre-commit"], default="auto"
    )
    ap.add_argument("--adopt-existing", action="store_true")
    ap.add_argument("--opt-in", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    start = Path(args.repo).resolve()
    top = git_out(start, "rev-parse", "--show-toplevel")
    if not top:
        print(f"not a git repo: {start}", file=sys.stderr)
        return 1
    repo = Path(top)

    actions: list[str] = []
    world = detect_world(repo)
    mechanism = choose_mechanism(world, args.mechanism)
    installed = True

    if not args.check:
        if args.opt_in:
            cfg_path = repo / ".claude" / "git-guard.json"
            if not cfg_path.is_file():
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text("{}\n", encoding="utf-8")
                actions.append("created .claude/git-guard.json ({} — house defaults)")

        dest = repo / GUARD_DEST
        actions.append(
            f"guard script {write_if_needed(dest, GUARD_SRC.read_text(), True)}: {GUARD_DEST}"
        )

        if mechanism == "pre-commit":
            installed = install_pre_commit(repo, world, actions)
        else:
            installed = install_native(repo, world, args.adopt_existing, actions)
        # core.hooksPath may have been created; re-resolve before verifying.
        world = detect_world(repo)

    ver = verify(repo, world)
    ok = installed and ver["ok"]

    report = {
        "repo": str(repo),
        "world": world["world"],
        "core_hooks_path": world["core_hooks_path"],
        "mechanism": mechanism,
        "hook_file": world["hook_file"],
        "actions": actions,
        "verification": {
            "reachable": ver["reachable"],
            "checks": [
                {"name": n, "pass": p, "detail": d} for n, p, d in ver["checks"]
            ],
            "coverage": ver["coverage"],
        },
        "ok": ok,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"repo:       {repo}")
        print(
            f"world:      {world['world']}"
            + (
                f" (core.hooksPath={world['core_hooks_path']})"
                if world["core_hooks_path"]
                else ""
            )
        )
        print(f"mechanism:  {mechanism}")
        print(f"hook file:  {world['hook_file']}")
        for a in actions:
            print(f"  - {a}")
        print("verification (driven through git's own resolved hook path):")
        for name, passed, detail in ver["checks"]:
            print(
                f"  [{'PASS' if passed else 'FAIL'}] {name}"
                + (f"  — {detail}" if detail else "")
            )
        print(f"result:     {'OK' if ok else 'NOT OK'}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
