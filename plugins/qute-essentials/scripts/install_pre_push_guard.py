#!/usr/bin/env python3
"""Install (and then actually VERIFY) the qute pre-push branch guard in a repo.

`/setup-qute-repo` calls this instead of pasting install commands, because
everything that goes wrong here goes wrong SILENTLY:

  1. **Wrong path.** A repo that sets `core.hooksPath` makes git ignore
     `.git/hooks` entirely, so anything dropped there never runs; the inverse
     mistake is equally invisible. The path is therefore never guessed — it is
     `git rev-parse --git-path hooks/pre-push`, git's own answer.
  2. **A weaker mechanism that looks like the strong one.** The pre-commit
     framework's `pre-push` stage drops ref lines whose local sha is all zeros
     (branch deletions never reach any hook) and exposes only the first
     pushable ref of a multi-ref push. For the layer whose entire purpose is
     that it holds, that is a defect, not a tradeoff — so `auto` NEVER selects
     it, even in a repo full of pre-commit hooks. pre-commit keeps working: its
     generated shim is relocated behind the dispatcher, which replays the ref
     lines to it.
  3. **Editing outside the repo you were pointed at.** A `core.hooksPath` can
     resolve anywhere — `/home/me/.githooks`, `../shared-hooks` — and then that
     one file is shared by every repo pointed at it: the second repo to be
     "installed" silently inherits the first one's hook. This is judged on the
     RESOLVED PATH, not on which config file set it: `git config --local
     core.hooksPath /home/me/.githooks` is exactly as shared as the global
     form. Scope tells you who wrote the setting; only the path tells you who
     is affected. A path outside the repo is refused by default — and so is a
     destination the repo checked in as a SYMLINK, which is the same escape
     through a third door. All of it is enforced in ONE place (`WriteGate`),
     structurally: every write walks down from an approved root with
     `O_NOFOLLOW` per component, so leaving the approved area is unreachable
     rather than merely checked for.
  4. **Reporting the command instead of the outcome.** "Ran the installer,
     done" is not evidence. A hook that silently is not installed is worse than
     no hook, because it manufactures confidence.

So this script resolves the path, installs, and then proves the result by
driving the hook through that same path with synthetic ref lines — including a
deletion and a multi-ref push — and checking for the guard's trace marker in
the output. What it prints is a measurement, not a claim, and missing coverage
FAILS rather than warns.

    python3 install_pre_push_guard.py [--repo PATH] [--mechanism auto|native|pre-commit]
                                      [--adopt-existing] [--allow-shared-hooks-path]
                                      [--opt-in] [--check] [--json]

    --check                     verify only; install nothing
    --opt-in                    create `.claude/git-guard.json` as `{}` if
                                absent (house defaults). Without an opt-in file
                                the guard is inert and verification says so.
    --adopt-existing            move a pre-existing hand-authored `pre-push`
                                into `pre-push.d/00-legacy-pre-push` and put the
                                qute dispatcher in front of it. Without this
                                flag such a hook is left alone and install
                                reports BLOCKED. (pre-commit's *generated* shim
                                is relocated without the flag — it is a
                                regenerable artifact and it keeps running.)
    --allow-shared-hooks-path   permit writing to a hook path that resolves
                                OUTSIDE this repository, i.e. a file shared by
                                every repo pointed at it.
    --mechanism pre-commit      escape hatch for a repo that genuinely cannot
                                take the native slot. Verification then FAILS on
                                the coverage that mode cannot provide.

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


class WriteRefused(Exception):
    """A write the gate would not perform. Carries the reason for the report."""


class WriteGate:
    """The ONE place this installer is allowed to modify the filesystem.

    Review found three separate doors out of the repo: a `core.hooksPath`
    inherited from global config, a repo-LOCAL `core.hooksPath` naming a
    directory outside the tree, and a destination the repo itself had checked
    in as a SYMLINK pointing anywhere. Three findings, one bug — "wrote outside
    the repository it was pointed at" — so they get one enforcement point
    rather than three checks that every future call site has to remember.

    The rule is structural, not a comparison. Every write starts at an APPROVED
    ROOT and walks down one path component at a time, opening each with
    `O_NOFOLLOW`; `..` and empty components are rejected outright. A symlink
    cannot be traversed and a parent cannot be escaped, so "ended up outside an
    approved root" is not a mistake a caller can make — it is unreachable. That
    also removes the check-then-write window a resolve-and-compare would leave:
    the descriptor the content is written to IS the one that was validated.

    Approved roots are the repo's own worktree / git dir / common dir, plus —
    only when the operator passed --allow-shared-hooks-path — the out-of-tree
    hooks directory they explicitly accepted. Nothing else is writable, and the
    roots are fixed before the first byte is written.
    """

    def __init__(self, roots):
        self.roots = []
        for root in roots:
            try:
                self.roots.append(Path(root).resolve())
            except OSError:
                continue

    def _rel_parts(self, dest: Path):
        """(root, [components]) for `dest`, or refuse.

        Prefix matching is LEXICAL (`normpath`, no `resolve`) on purpose: a
        resolved comparison would follow the very symlinks this exists to stop,
        and would call a symlinked path "inside the repo" because its target is.
        """
        dest = Path(os.path.normpath(str(Path(dest).absolute())))
        for root in self.roots:
            if dest == root or root in dest.parents:
                parts = dest.relative_to(root).parts
                if any(p in ("", os.pardir) for p in parts):
                    raise WriteRefused(f"{dest} escapes {root}")
                return root, list(parts)
        roots = ", ".join(str(r) for r in self.roots) or "(none)"
        raise WriteRefused(
            f"refusing to write {dest}: it is outside every directory this "
            f"install is allowed to touch ({roots})"
        )

    @staticmethod
    def _describe_open_failure(name: str, dir_fd: int, exc: OSError) -> str:
        try:
            st = os.lstat(name, dir_fd=dir_fd)
            if stat.S_ISLNK(st.st_mode):
                try:
                    target = os.readlink(name, dir_fd=dir_fd)
                except OSError:
                    target = "?"
                return (
                    f"{name!r} is a SYMLINK (-> {target}). Refusing to write "
                    "through it — a repository must not be able to redirect "
                    "this installer's writes to a path of its choosing."
                )
        except OSError:
            pass
        return f"{name!r} could not be opened safely: {exc}"

    def _descend(self, dest: Path, create_dirs: bool):
        """Open the parent directory of `dest`, refusing any symlinked step."""
        root, parts = self._rel_parts(dest)
        if not parts:
            raise WriteRefused(f"refusing to write the root itself: {root}")
        fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in parts[:-1]:
                while True:
                    try:
                        nxt = os.open(
                            part,
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd,
                        )
                        break
                    except FileNotFoundError:
                        if not create_dirs:
                            raise
                        os.mkdir(part, 0o755, dir_fd=fd)
                    except OSError as exc:
                        raise WriteRefused(
                            self._describe_open_failure(part, fd, exc)
                        ) from exc
                os.close(fd)
                fd = nxt
        except Exception:
            os.close(fd)
            raise
        return fd, parts[-1]

    def write(self, dest: Path, content: str, executable: bool = False) -> str:
        """Write `content` to `dest`; return created | updated | unchanged."""
        dir_fd, name = self._descend(dest, create_dirs=True)
        try:
            existing = None
            try:
                rfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
            except FileNotFoundError:
                rfd = None
            except OSError as exc:
                raise WriteRefused(
                    self._describe_open_failure(name, dir_fd, exc)
                ) from exc
            if rfd is not None:
                with os.fdopen(rfd, "r", encoding="utf-8", errors="replace") as fh:
                    existing = fh.read()

            if existing == content:
                if executable:
                    st = os.stat(name, dir_fd=dir_fd)
                    if not st.st_mode & stat.S_IXUSR:
                        self._chmod_exec(dir_fd, name)
                        return "updated"
                return "unchanged"

            verb = "updated" if existing is not None else "created"
            try:
                wfd = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                    0o644,
                    dir_fd=dir_fd,
                )
            except OSError as exc:
                raise WriteRefused(
                    self._describe_open_failure(name, dir_fd, exc)
                ) from exc
            with os.fdopen(wfd, "w", encoding="utf-8") as fh:
                fh.write(content)
            if executable:
                self._chmod_exec(dir_fd, name)
            return verb
        finally:
            os.close(dir_fd)

    def _chmod_exec(self, dir_fd: int, name: str) -> None:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
        try:
            mode = os.fstat(fd).st_mode
            os.fchmod(fd, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        finally:
            os.close(fd)

    def make_executable(self, dest: Path) -> None:
        dir_fd, name = self._descend(dest, create_dirs=False)
        try:
            self._chmod_exec(dir_fd, name)
        finally:
            os.close(dir_fd)

    def rename(self, src: Path, dst: Path) -> None:
        """Move a hook within the approved roots, refusing symlinked ends."""
        src_fd, src_name = self._descend(src, create_dirs=False)
        try:
            st = os.lstat(src_name, dir_fd=src_fd)
            if stat.S_ISLNK(st.st_mode):
                raise WriteRefused(
                    f"{src} is a symlink; refusing to adopt it into the hook "
                    "chain. Replace it with a real file first."
                )
            dst_fd, dst_name = self._descend(dst, create_dirs=True)
            try:
                os.rename(src_name, dst_name, src_dir_fd=src_fd, dst_dir_fd=dst_fd)
            finally:
                os.close(dst_fd)
        finally:
            os.close(src_fd)


# ---------------------------------------------------------------- detection


def is_pre_commit_shim(path: Path) -> bool:
    """Is `path` a hook script generated by `pre-commit install`?

    Matched on the banner pre-commit writes into every generated hook plus the
    `hook-impl` entry point it dispatches to — two markers, so a hand-written
    hook that merely mentions pre-commit is not mistaken for a regenerable
    artifact. Deliberately NOT matched on pre-commit's template-ID hashes:
    those change every time the template changes, and a guard that stops
    recognising the shim after a pre-commit upgrade would silently fall back to
    treating it as a foreign hook.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
    return "generated by pre-commit" in text and "hook-impl" in text


def _repo_boundaries(repo: Path) -> list:
    """Every directory that legitimately belongs to THIS repo.

    The worktree itself, its `$GIT_DIR`, and the common dir — the last because
    `.git/hooks` lives in the common dir, so in a linked worktree the default
    hook path resolves into the main checkout's `.git`. That is shared between
    worktrees of one repo, which is git's own default and not the sharing this
    guard is about.
    """
    out = []
    for args in (
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--absolute-git-dir"),
        ("rev-parse", "--path-format=absolute", "--git-common-dir"),
    ):
        got = git_out(repo, *args)
        if got:
            try:
                out.append(Path(got).resolve())
            except OSError:
                pass
    return out


def hook_path_is_inside_repo(repo: Path, hook_file: Path) -> bool:
    """Does the hook git will run belong to this repo, or is it shared?

    THE rule, and the only one: judge the resolved PATH, never the config scope
    that named it. `core.hooksPath = /home/me/.githooks` set with
    `git config --local` is exactly as shared as the same value set globally —
    every repo pointed at that directory gets the same hook file, and the
    second repo to be "installed" silently inherits the first one's. Scope
    tells you who wrote the setting; only the path tells you who is affected.
    """
    try:
        resolved = hook_file.resolve()
    except OSError:
        return False
    for boundary in _repo_boundaries(repo):
        if resolved == boundary or boundary in resolved.parents:
            return True
    return False


def detect_world(repo: Path) -> dict:
    """Which installation world this repo is in, and who owns the hook slot.

    `core.hooksPath` wins unconditionally — when it is set, git does not look at
    `.git/hooks` at all — so the hook path is always git's own answer
    (`rev-parse --git-path`), never a guess. Whether writing there is a per-repo
    install is then decided by `hook_path_is_inside_repo`, on the resolved path
    alone. `--show-origin` is captured for the refusal message (it tells a human
    which config file to go edit) and for nothing else.
    """
    effective = git_out(repo, "config", "--get", "core.hooksPath")
    origin = git_out(repo, "config", "--show-origin", "--get", "core.hooksPath")

    resolved = git_out(repo, "rev-parse", "--git-path", "hooks/pre-push")
    hook_file = (repo / resolved).resolve() if resolved else None
    has_pc_config = (repo / PC_CONFIG).is_file()
    pc_bin = shutil.which("pre-commit")

    slot_owner = "empty"
    if hook_file and hook_file.exists():
        text = hook_file.read_text(encoding="utf-8", errors="replace")
        if DISPATCHER_MARKER in text:
            slot_owner = "qute"
        elif is_pre_commit_shim(hook_file):
            slot_owner = "pre-commit"
        else:
            slot_owner = "foreign"

    # After `pre-commit install --hook-type pre-push` reclaims the slot, our
    # dispatcher is moved to `<slot>.legacy` — which pre-commit's shim runs
    # FIRST, with the raw stdin, and whose exit code it ORs into its own. That
    # layout still gives the guard full fidelity; the installer must recognise
    # it instead of reinstalling on top.
    legacy_is_qute = False
    if hook_file:
        legacy = hook_file.with_name(hook_file.name + ".legacy")
        legacy_is_qute = legacy.is_file() and DISPATCHER_MARKER in legacy.read_text(
            encoding="utf-8", errors="replace"
        )

    return {
        "world": "hooksPath" if effective else "native",
        "core_hooks_path": effective,
        "hook_path_location": (
            "in-repo"
            if hook_file and hook_path_is_inside_repo(repo, hook_file)
            else "outside-repo"
        ),
        "hooks_path_origin": origin,
        "hook_file": str(hook_file) if hook_file else None,
        "slot_owner": slot_owner,
        "legacy_is_qute": legacy_is_qute,
        "pre_commit_config": has_pc_config,
        "pre_commit_bin": pc_bin,
    }


def choose_mechanism(world: dict, requested: str) -> str:
    """Always native unless explicitly overridden.

    The pre-commit framework's `pre-push` stage cannot see the full push: it
    drops ref lines whose local sha is all zeros (so branch deletions never
    reach any hook) and exposes only the first pushable ref of a multi-ref
    push. That is a fine tradeoff for a convenience hook and an unacceptable
    one for the layer whose whole job is that it holds — so `auto` never picks
    it. `--mechanism pre-commit` remains available for a repo that genuinely
    cannot take the native slot, and verification FAILS there rather than
    warning, so nobody is told they are protected when they are not.
    """
    if requested != "auto":
        return requested
    return "native"


# ----------------------------------------------------------------- install


def _shared_hook_refusal(repo: Path, world: dict) -> str:
    """Say what was actually detected, not just that something was refused.

    A message that reads "refusing, pass --allow-shared-hooks-path" without
    naming what makes the path shared is a message people paste past.
    """
    hook_file = Path(world["hook_file"])
    hook_dir = hook_file.parent
    lines = [
        "BLOCKED: this would not be a per-repo install.",
        f"    git runs:        {hook_file}",
        f"    this repo is at: {repo}",
        "    the hook path resolves OUTSIDE the repository, so that one file is",
        "    shared by every repository pointed at it.",
        f"    core.hooksPath = {world['core_hooks_path']}",
    ]
    if world["hooks_path_origin"]:
        # `--show-origin` prints "<origin>\t<value>"; the origin half names the
        # config file a human has to go edit. It is relative to the cwd git ran
        # in (this repo) for the repo's own config, so resolve before judging —
        # calling the repo's own `.git/config` "outside this repo" would be a
        # lie in the one message that has to be trusted.
        src = world["hooks_path_origin"].split("\t")[0]
        lines.append(f"    set in:          {src}")
        if src.startswith("file:"):
            src_path = Path(src[len("file:") :]).expanduser()
            if not src_path.is_absolute():
                src_path = repo / src_path
            external = not hook_path_is_inside_repo(repo, src_path)
        else:
            external = True
        if external:
            lines.append(
                "                     (that config file is outside this repo — "
                "EVERY repository"
            )
            lines.append(
                "                     reading it and not overriding "
                "core.hooksPath is affected)"
            )

    # Cheap, concrete evidence of who else is already sharing this directory:
    # whatever is sitting in it right now.
    try:
        siblings = sorted(p.name for p in hook_dir.iterdir())
    except OSError:
        siblings = []
    if siblings:
        lines.append(
            f"    already in that dir: {', '.join(siblings[:8])}"
            + (" …" if len(siblings) > 8 else "")
        )
        if "pre-push" in siblings:
            lines.append(
                "                     a pre-push hook is ALREADY there — another "
                "repo put it"
            )
            lines.append(
                "                     there, and this repo has been inheriting it."
            )
    lines += [
        "  Fix it one of two ways:",
        "    - point this repo at a hooks dir inside its own tree:",
        "        git config --local core.hooksPath .githooks",
        "    - or accept the shared edit deliberately:",
        "        --allow-shared-hooks-path",
    ]
    return "\n  ".join(lines)


def install_native(
    repo: Path, world: dict, adopt: bool, gate: WriteGate, actions: list
) -> bool:
    """Put the dispatcher at the path git will actually invoke.

    The containment decision has already been made by `main()` — it is encoded
    in `gate`'s approved roots, before anything was written. There is no
    "is this allowed" check here on purpose: a rule re-stated at each call site
    is a rule that will be forgotten at the next one.
    """
    hook_file = Path(world["hook_file"])

    if world["slot_owner"] == "pre-commit" and world["legacy_is_qute"]:
        # pre-commit reclaimed the slot after a previous install. The guard
        # still runs, with raw stdin, from `<slot>.legacy`. Refresh it in place
        # rather than fighting for the slot back.
        legacy = hook_file.with_name(hook_file.name + ".legacy")
        actions.append(
            f"pre-commit holds the slot and chains the guard from {legacy.name} "
            f"(raw stdin, exit code honoured) — dispatcher "
            f"{gate.write(legacy, DISPATCHER_SRC.read_text(), True)}"
        )
        actions.append(
            "NOTE: `pre-commit install -f --hook-type pre-push` DELETES that "
            "legacy hook and would remove the guard. Re-run this installer "
            "(or `--check`) after any -f install."
        )
        return True

    if hook_file.exists() and world["slot_owner"] != "qute":
        if world["slot_owner"] == "pre-commit":
            # A generated, regenerable artifact — relocating it into the chain
            # keeps every pre-commit hook running, so this does not need the
            # --adopt-existing ceremony a hand-authored hook does. It is still
            # reported loudly.
            dest_name = "50-pre-commit"
            note = (
                "relocated pre-commit's generated shim into the chain; its "
                "hooks still run, behind the guard. `pre-commit uninstall` "
                "will no longer find it — delete the file to disable it."
            )
        elif not adopt:
            actions.append(
                f"BLOCKED: {hook_file} already exists and is not the qute "
                "dispatcher. Re-run with --adopt-existing to move it to "
                "pre-push.d/00-legacy-pre-push and chain it behind the guard."
            )
            return False
        else:
            dest_name = "00-legacy-pre-push"
            note = "adopted the repo's existing pre-push hook"

        legacy = hook_file.parent / "pre-push.d" / dest_name
        if legacy.exists():
            actions.append(f"BLOCKED: {legacy} already exists; refusing to overwrite")
            return False
        gate.rename(hook_file, legacy)
        gate.make_executable(legacy)
        actions.append(f"{note} -> {legacy}")

    actions.append(
        f"dispatcher {gate.write(hook_file, DISPATCHER_SRC.read_text(), True)}: {hook_file}"
    )
    if world["pre_commit_config"]:
        actions.append(
            "NOTE: this repo uses pre-commit. A later `pre-commit install "
            "--hook-type pre-push` moves the dispatcher to <slot>.legacy, "
            "where it still runs with raw stdin — but `-f` DELETES it. Re-run "
            "with --check after any pre-commit install to confirm coverage."
        )
    return True


def install_pre_commit(repo: Path, world: dict, gate: WriteGate, actions: list) -> bool:
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
        gate.write(cfg, text.rstrip("\n") + "\n" + PC_BLOCK)
        check = _validate()
        if check.returncode != 0:
            if was_valid:
                gate.write(cfg, backup)
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

    # 4. deletion of a guarded branch. This is REQUIRED coverage, not a note:
    #    the pre-commit framework drops all-zero local shas before running any
    #    hook, so failing it means the guard is running in the weaker mode and
    #    the whole verification must fail. Warning here would leave someone
    #    believing they are protected when they are not.
    p = _probe(repo, hook_file, f"(delete) {ZERO} refs/heads/{protected} {head}")
    out = p.stdout + p.stderr
    del_refused = p.returncode != 0 and f"{MARKER}: refuse {protected}" in out
    result["coverage"]["delete_guarded"] = del_refused
    if del_refused:
        detail = ""
    elif is_pre_commit_shim(hook_file):
        detail = (
            "the pre-commit framework drops ref lines whose local sha is all "
            "zeros before running any hook, so branch deletions never reach "
            "the guard. Install at the native hook path instead."
        )
    else:
        detail = "unexpected — the native hook path should see deletions"
    result["checks"].append(
        (f"deletion of '{protected}' is refused", del_refused, detail)
    )

    # 5. a multi-ref push must be judged on EVERY ref, not just the first. The
    #    pre-commit adapter returns after the first pushable ref, so a guarded
    #    destination hidden behind a feature branch slips through it.
    multi = (
        f"refs/heads/qute-probe {head} refs/heads/qute-probe {head}\n"
        f"refs/heads/probe {head} refs/heads/{protected} {head}"
    )
    p = _probe(repo, hook_file, multi)
    out = p.stdout + p.stderr
    multi_ok = p.returncode != 0 and f"{MARKER}: refuse {protected}" in out
    result["coverage"]["multi_ref"] = multi_ok
    result["checks"].append(
        (
            f"multi-ref push hiding '{protected}' behind a feature branch is refused",
            multi_ok,
            ""
            if multi_ok
            else "only the first pushable ref was judged — the weaker mode",
        )
    )

    required = ["protected_update", "feature_allowed", "delete_guarded", "multi_ref"]
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
    ap.add_argument(
        "--allow-shared-hooks-path",
        action="store_true",
        help="permit writing to a hook path that resolves OUTSIDE this "
        "repository, i.e. a file shared by every repo pointed at it",
    )
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
        # ------------------------------------------------------------------
        # Decide WHERE we may write before writing anything at all. The first
        # version wrote the guard script and the opt-in config before reaching
        # the containment rule, which made the rule decorative: by the time it
        # refused the hook path, two files were already on disk. The approved
        # roots are settled here, once, and handed to the gate.
        # ------------------------------------------------------------------
        roots = _repo_boundaries(repo)
        if world["hook_path_location"] == "outside-repo":
            if not args.allow_shared_hooks_path:
                actions.append(_shared_hook_refusal(repo, world))
                installed = False
            else:
                approved = Path(world["hook_file"]).parent
                roots.append(approved)
                actions.append(
                    f"--allow-shared-hooks-path: {approved} approved as a write "
                    "target even though it is outside this repo"
                )
        gate = WriteGate(roots)

        if installed:
            try:
                if args.opt_in:
                    cfg_path = repo / ".claude" / "git-guard.json"
                    if not cfg_path.is_file():
                        gate.write(cfg_path, "{}\n")
                        actions.append(
                            "created .claude/git-guard.json ({} — house defaults)"
                        )

                dest = repo / GUARD_DEST
                actions.append(
                    f"guard script {gate.write(dest, GUARD_SRC.read_text(), True)}: "
                    f"{GUARD_DEST}"
                )

                if mechanism == "pre-commit":
                    actions.append(
                        "WARNING: --mechanism pre-commit was requested. That path "
                        "cannot see branch deletions or the tail of a multi-ref "
                        "push; verification below will FAIL on that missing "
                        "coverage rather than warn about it."
                    )
                    installed = install_pre_commit(repo, world, gate, actions)
                else:
                    installed = install_native(
                        repo, world, args.adopt_existing, gate, actions
                    )
            except WriteRefused as exc:
                actions.append(f"BLOCKED: {exc}")
                installed = False

        # core.hooksPath may have been created; re-resolve before verifying.
        world = detect_world(repo)

    ver = verify(repo, world)
    ok = installed and ver["ok"]

    report = {
        "repo": str(repo),
        "world": world["world"],
        "core_hooks_path": world["core_hooks_path"],
        "hook_path_location": world["hook_path_location"],
        "hooks_path_origin": world["hooks_path_origin"],
        "mechanism": mechanism,
        "hook_file": world["hook_file"],
        "slot_owner": world["slot_owner"],
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
                f" (core.hooksPath={world['core_hooks_path']},"
                f" hook_path={world['hook_path_location']})"
                if world["core_hooks_path"]
                else ""
            )
        )
        print(f"mechanism:  {mechanism}")
        print(f"hook file:  {world['hook_file']} (currently: {world['slot_owner']})")
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
