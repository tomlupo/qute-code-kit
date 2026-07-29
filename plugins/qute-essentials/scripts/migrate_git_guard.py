#!/usr/bin/env python3
"""Migrate a repo off the hand-copied `git-workflow-guard` and stamp its config.

`/setup-qute-repo` step 9 calls this instead of describing an edit, because both
halves of the job are the kind that goes wrong quietly:

  1. **The legacy copy is not merely redundant — it is WRONG.** Three repos
     (quantbox, quantbox-live, quantbox-lab) carry the 2026-06-18 original of
     `.claude/hooks/git-workflow-guard.py`, byte-identical across all three. It
     predates the fix for resolving which repo a `git -C <path>` command
     actually targets, so left in place next to the plugin guard it does not
     merely double up: the buggy copy can produce a FALSE BLOCK the plugin copy
     would not. "It's just an old duplicate" is the reading to reject.
  2. **Unwiring it is a surgical edit, not a rewrite.** `.claude/settings.json`
     in those repos is not dedicated to this hook — other hooks live in the same
     event lists. So exactly the entries whose command names the legacy script
     are removed; every sibling entry keeps its structure and key order, and —
     because the file is re-emitted at its own detected indent — its bytes too,
     for the canonically formatted JSON the house writes (an unusual layout
     would be normalised; parse-and-reindent cannot preserve one),
     and containers that go empty are pruned rather than left as `[]` / `{}`
     litter that later reads as "a hook used to be here".

What it does, in one pass, idempotently:

  * removes `.claude/hooks/git-workflow-guard.py`;
  * removes the entries in `.claude/settings.json` (and `settings.local.json`)
    whose `command` references it, pruning emptied containers;
  * stamps a MINIMAL `.claude/git-guard.json` when absent — minimal because the
    plugin guard supplies the house defaults (`main`, plus `dev` iff `origin/dev`
    exists), so a repo that wants them commits `{}` and a field only appears
    when it says something the default does not. The one field that must be
    spelled out even though it looks like an absence is
    `"integration_branch": null` — quantbox-live genuinely has no integration
    branch, and an omission there would let default detection resurrect `dev`.

Idempotence is the point, not a nicety: re-running `/setup-qute-repo` is the
mechanism by which repos stay in step with the regime, so a repo with no legacy
copy and a repo already migrated must both come out of this a no-op — and an
existing `.claude/git-guard.json` is NEVER rewritten, because the repo's own
answer outranks the stamp.

    python3 migrate_git_guard.py [--repo PATH] [--check] [--json]
                                 [--protected-branch NAME]
                                 [--integration-branch NAME|none|auto]
                                 [--release-tool TEXT] [--no-stamp]

    --check                  report what would change; write nothing.
    --integration-branch     `auto` (default) leaves the field out and lets the
                             guard detect `dev`; `none` writes an explicit
                             `null`; a name writes that name (omitted anyway if
                             it is what detection would have produced).

Exit code is 0 when the repo ends in the migrated state, 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

LEGACY_HOOK = Path(".claude/hooks/git-workflow-guard.py")
CONFIG = Path(".claude/git-guard.json")
# The enforcement layer, imported rather than mirrored: it owns what a branch
# field may say, and the stamper must not be able to write a config it refuses.
PRE_PUSH_GUARD = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "hooks"
    / "pre-push-branch-guard"
)
SETTINGS_FILES = ("settings.json", "settings.local.json")

# House defaults, kept in lockstep with the plugin guard + `pre-push` (both read
# the same file). A stamped field that merely repeats one of these is noise that
# later reads as a deliberate choice, so the stamper omits it.
DEFAULT_PROTECTED = "main"
DEFAULT_INTEGRATION = "dev"

# What marks an entry as the legacy wiring: its command names the legacy script.
# Matched on the basename so every spelling of the path is caught —
# `$CLAUDE_PROJECT_DIR/.claude/hooks/...`, `./.claude/hooks/...`, an absolute
# path, `uv run` in front of it — while `not-git-workflow-guard.py` and
# `git-workflow-guard.py.bak` are NOT it (see `_names_legacy_script`).
# The plugin's own copy of the guard is never referenced from a repo's
# settings.json (it is wired by the plugin's `hooks.json`), so this cannot match
# the replacement it is clearing the way for.
LEGACY_BASENAME = "git-workflow-guard.py"

# Tokens that put the NEXT token in command position. Anything starting with
# `python` is treated as an interpreter too (python3, python3.12, python3.exe).
# The list is deliberately short: a wrapper missing from it costs a missed
# unwiring (visible: a hook command pointing at a deleted file), while a flag
# wrongly on it would cost a deleted live hook.
_WRAPPERS = frozenset(
    {
        "uv",
        "uvx",
        "run",
        "exec",
        "env",
        "bash",
        "sh",
        "zsh",
        "node",
        "deno",
        "bun",
        "poetry",
        "pdm",
        "hatch",
        "pipx",
        "nice",
        "time",
        "sudo",
        "command",
    }
)


# ------------------------------------------------------------------ git


def git_out(repo: Path, *args: str):
    out = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def remote_branch_exists(repo: Path, branch: str) -> bool:
    """Whether `origin/<branch>` exists — the guard's own detection, mirrored.

    Mirrored rather than imported so the stamper's notion of "this is the
    default anyway, omit it" cannot drift from the reader's notion of what the
    default resolves to. A test asserts the two agree.
    """
    return (
        git_out(
            repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"
        )
        is not None
    )


# ------------------------------------------------------------------ json i/o


def detect_indent(text: str) -> int | str:
    """The indent `json.dumps` needs to reproduce `text`'s shape.

    A settings file the house wrote is 2-space-indented JSON, and re-emitting it
    with the same indent makes every untouched line byte-identical — which is
    what lets a caller diff the result and see ONLY the removal.
    """
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped == "}":
            continue
        lead = len(line) - len(stripped)
        if lead:
            if line[:lead] == "\t" * lead:
                return "\t"
            return lead
    return 2


def dump_like(data, original: str) -> str:
    out = json.dumps(data, indent=detect_indent(original), ensure_ascii=False)
    return out + "\n" if original.endswith("\n") else out


# ------------------------------------------------------- legacy detection


def _names_legacy_script(command: str) -> bool:
    """Whether `command` runs the legacy guard — matched per TOKEN, not per substring.

    A raw `LEGACY_BASENAME in command` is a false-positive generator, and its
    failure mode is removal: `.claude/hooks/not-git-workflow-guard.py` contains
    the basename, so an unrelated hook would be unwired and — if it were the only
    one in its group — its whole container pruned. This step deletes things; the
    match has to be exact.

    So the command is split into tokens and a token qualifies only when its
    BASENAME is exactly the legacy script. Basename rather than the full
    `.claude/hooks/…` path, because the file's location is not the thing that
    identifies it — a repo that moved it still needs it gone.

    TWO splits, unioned. `shlex.split` handles the quoting the real entries use
    (`python3 "$CLAUDE_PROJECT_DIR/…"`), but in POSIX mode it also *eats*
    backslashes as escapes, which silently turns a Windows-spelled
    `.claude\\hooks\\git-workflow-guard.py` into one unrecognisable word — a
    miss, i.e. legacy wiring left armed. So a backslash-folded whitespace split
    is checked as well. Both are conservative in the same direction: a token
    still has to END in exactly this basename.

    And the token has to be in COMMAND POSITION, resolved by scanning FORWARD:
    consume leading wrappers/interpreters and their option flags, and the first
    remaining token is what runs. That reads `python3 -u <script>`,
    `uv run <script>` and `bash -lc <script>` as invocations — the reviewer's
    misses, which would have left an entry pointing at a file this step deletes
    — while `python3 other.py --target git-workflow-guard.py` and
    `echo git-workflow-guard.py` stop at `other.py` / `echo` and name the file
    as DATA. Scanning forward is what separates the two; scanning backward over
    flags cannot, because `--target <value>` looks exactly like `-u <script>`.

    An option that takes a SEPARATE value (`uv run --with pytest <script>`) can
    still fool it into stopping at the value. That residue is a miss, never a
    wrong deletion, and `migrate()` reports leftover mentions so a human sees it.
    """

    def _named_in_command_position(tokens: list[str]) -> bool:
        def basename(token: str) -> str:
            return PurePosixPath(token.strip("\"'").replace("\\", "/")).name

        index = 0
        while index < len(tokens):
            name = basename(tokens[index])
            if name == LEGACY_BASENAME:
                return True
            if tokens[index].startswith("-"):
                index += 1  # an option to the wrapper we already consumed
                continue
            if name in _WRAPPERS or name.startswith("python"):
                index += 1  # a wrapper: whatever follows may still be the script
                continue
            return False  # a real command that is not the legacy script
        return False

    splits: list[list[str]] = []
    try:
        splits.append(shlex.split(command))
    except ValueError:
        # Unbalanced quotes — the fallback below still covers it.
        pass
    splits.append(command.replace("\\", "/").split())
    return any(_named_in_command_position(tokens) for tokens in splits)


def _is_legacy_hook_entry(entry) -> bool:
    if not isinstance(entry, dict):
        return False
    command = entry.get("command")
    if not isinstance(command, str):
        return False
    return _names_legacy_script(command)


def strip_legacy_wiring(data):
    """Remove legacy hook entries from a parsed settings dict.

    Returns `(changed_data, removed_commands)`. Pruning is bottom-up: an entry
    goes, then its matcher group if that leaves no hooks, then the event list if
    that leaves no groups, then `hooks` itself. Anything not on that chain is
    left exactly as found — this walks the structure it understands and refuses
    to guess at the rest.
    """
    removed: list[str] = []
    if not isinstance(data, dict):
        return data, removed
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return data, removed

    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            kept_entries = []
            for entry in group["hooks"]:
                if _is_legacy_hook_entry(entry):
                    removed.append(entry["command"])
                else:
                    kept_entries.append(entry)
            if not kept_entries:
                # The group existed only to carry this hook — dropping it beats
                # leaving `{"matcher": "Bash", "hooks": []}`, which reads as a
                # deliberate empty matcher to the next person and to the harness.
                continue
            group["hooks"] = kept_entries
            kept_groups.append(group)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]

    if not hooks:
        del data["hooks"]
    return data, removed


# ------------------------------------------------------------- stamping


class BranchRejected(Exception):
    """A branch argument the enforcement layer would refuse. Carries its words."""


def _pre_push_module():
    """The `pre-push` guard script itself, imported — NOT a reimplementation.

    Same reasoning as `install_pre_push_guard._guard_module`. A stamper that
    validated branch names with its own copy of the rules would drift from the
    reader the moment either side learned something, and the drift's shape is
    always the same: this script exits 0 having written a config that makes
    every push in the repo fail. So the validation IS the reader's validation.
    """
    spec = importlib.util.spec_from_loader(
        "qute_pre_push_guard_for_migrate",
        importlib.machinery.SourceFileLoader(
            "qute_pre_push_guard_for_migrate", str(PRE_PUSH_GUARD)
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def normalise_branch_arg(repo: Path, key: str, value: str) -> str:
    """`value` as the guard would read it, or `BranchRejected` with its message.

    `--integration-branch refs/remotes/origin/dev` used to be stamped verbatim:
    exit 0, "migrated", and then `pre-push` raising `ConfigError` on every push.
    `refs/heads/dev` is the mirror case — legal, but it must be normalised here
    so the file says what both layers agree it says.
    """
    try:
        guard = _pre_push_module()
        normalised = guard._branch_field(repo, {key: value}, key, allow_null=False)
    except Exception as exc:  # ConfigError, or the import itself failing
        raise BranchRejected(f"--{key.replace('_', '-')}: {exc}") from exc
    return normalised


def desired_config(
    repo: Path,
    protected: str | None,
    integration: str | None,
    integration_mode: str,
    release_tool: str | None,
) -> dict:
    """The MINIMAL config expressing this repo's answer.

    Minimal means: a field appears only when leaving it out would mean something
    else. `{}` is the correct, complete config for a repo that wants the house
    defaults — the guard supplies them, and repeating them in the file is how a
    default silently becomes a per-repo decision nobody made.
    """
    cfg: dict = {}
    # Normalise BEFORE the "is this the default anyway?" comparison, so
    # `--protected-branch refs/heads/main` is recognised as `main` and omitted
    # rather than stamped as a qualified ref nobody asked for.
    #
    # Gated on `is not None`, NOT on truthiness. `--integration-branch ""` is a
    # value the user supplied, and skipping validation for it let the empty
    # string through to the stamp — where `"" != detected` made it a field, and
    # `pre-push` rejects an empty branch field on every push. "Falsy" and "not
    # given" are different things exactly where it costs the most.
    if protected is not None:
        protected = normalise_branch_arg(repo, "protected_branch", protected)
    if integration_mode == "name":
        integration = normalise_branch_arg(repo, "integration_branch", integration)

    if protected and protected != DEFAULT_PROTECTED:
        cfg["protected_branch"] = protected

    detected = (
        DEFAULT_INTEGRATION if remote_branch_exists(repo, DEFAULT_INTEGRATION) else None
    )
    if integration_mode == "none":
        # Only redundant when detection would ALSO have produced no integration
        # branch. Where `origin/dev` exists, omitting this is the difference
        # between "no integration branch" and "dev" — quantbox-live's case.
        if detected is not None:
            cfg["integration_branch"] = None
    elif integration_mode == "name":
        if integration != detected:
            cfg["integration_branch"] = integration
    # `auto`: say nothing, let the guard detect.

    if release_tool:
        cfg["release_tool"] = release_tool
    return cfg


# ------------------------------------------------------------------ core


def _config_file_kind(cfg_path: Path):
    """What is sitting at the config path: None (absent), "regular", or a phrase.

    `lstat`, not `is_file()`, and deliberately the same test `pre-push` makes:
    `is_file()` follows symlinks and answers False for a BROKEN one, so a repo
    carrying a tracked `.claude/git-guard.json` symlink reads as opted in to
    anyone looking at `git ls-files`, is refused by `pre-push` on every push, and
    would have been waved through here as either "absent" (stamp over it) or
    "already present" (report the repo migrated). Both answers are wrong.
    """
    try:
        st = os.lstat(cfg_path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        return f"unreadable ({exc})"
    if stat.S_ISREG(st.st_mode):
        return "regular"
    if stat.S_ISLNK(st.st_mode):
        try:
            target = os.readlink(cfg_path)
        except OSError:
            target = "?"
        return f"a symlink (-> {target})"
    if stat.S_ISDIR(st.st_mode):
        return "a directory"
    return "not a regular file"


def _inside(repo: Path, path: Path) -> bool:
    """Whether `path` still resolves inside `repo`.

    A `.claude` symlinked out of the tree would make "clean up the repo" edit
    something else; this script refuses rather than following.
    """
    try:
        return repo.resolve() in path.resolve().parents
    except OSError:
        return False


def _plan_config(
    repo: Path,
    result: dict,
    notes: list,
    problems: list,
    *,
    stamp: bool,
    protected: str | None,
    integration: str | None,
    integration_mode: str,
    release_tool: str | None,
):
    """Decide the config outcome WITHOUT writing. Returns `(path, text)` or None.

    Separated from `migrate` so the whole decision — is the existing file usable,
    is the path contained, are the branch arguments ones the reader accepts — is
    made before anything is deleted. Every failure here is a refusal, and a
    refusal has to cost nothing.
    """
    cfg_path = repo / CONFIG
    # Order matters. `_config_file_kind` uses `lstat` and follows nothing, so it
    # is the specific diagnosis; containment (which RESOLVES, and so follows a
    # symlink to wherever it goes) would otherwise answer "outside the repo" for
    # a config symlink and hide the real problem behind a vaguer one.
    cfg_kind = _config_file_kind(cfg_path)
    if cfg_kind not in (None, "regular"):
        # Present but not a regular file. `pre-push` reads this path with
        # `lstat` and raises `ConfigError` on exactly this case — it refuses the
        # push rather than quietly guarding nothing — so a migrator that used
        # `is_file()` (which FOLLOWS symlinks, and answers False for a broken
        # one) would report a repo migrated while every push in it fails. The
        # two layers read one file; they have to agree on what "present" means.
        problems.append(
            f"{CONFIG} is {cfg_kind}, not a regular file — `pre-push` refuses every push in this "
            "state. Replace it with a real file (or delete it to opt the repo out) and re-run; "
            "not overwriting it here, because whatever it points at was somebody's decision"
        )
        return None
    if not _inside(repo, cfg_path):
        # The stamp is the one write that CREATES a path rather than editing one
        # that exists, and therefore the one that needs the containment check
        # most: with `.claude` symlinked out of the tree, `mkdir(parents=True)` +
        # `write_text` would follow it and stamp a config into some other repo,
        # which then looks opted in to a guard nobody armed there. Checked
        # against the RESOLVED path, so it holds whether the symlink is
        # `.claude` itself or an ancestor of it.
        problems.append(
            f"{CONFIG} resolves outside {repo} (a symlinked .claude?); refusing to stamp it"
        )
        return None
    if cfg_kind == "regular":
        result["config_existing"] = cfg_path.read_text(encoding="utf-8")
        notes.append(f"{CONFIG} already present — left as the repo wrote it")
        return None
    if not stamp:
        # `--no-stamp` and no config: the repo is NOT opted in, and saying
        # nothing here let the summary claim "config already in place" — the one
        # sentence that would make a reader stop looking for the reason both
        # guard layers are inert in that repo.
        notes.append(
            f"{CONFIG} absent and --no-stamp given — this repo is NOT opted in; both guard layers are a no-op here"
        )
        return None
    try:
        cfg = desired_config(
            repo, protected, integration, integration_mode, release_tool
        )
    except BranchRejected as exc:
        # Refusing beats stamping: a config `pre-push` rejects makes EVERY push
        # in the repo fail, and it would have been written by the step whose
        # report says the repo is now migrated.
        problems.append(f"nothing stamped — {exc}")
        return None
    rendered = json.dumps(cfg, indent=2) + "\n"
    result["config_stamped"] = rendered
    result["actions"].append(f"stamp {CONFIG} = {json.dumps(cfg)}")
    return cfg_path, rendered


def migrate(
    repo: Path,
    *,
    check: bool = False,
    stamp: bool = True,
    protected: str | None = None,
    integration: str | None = None,
    integration_mode: str = "auto",
    release_tool: str | None = None,
) -> dict:
    actions: list[str] = []
    notes: list[str] = []
    problems: list[str] = []
    result = {
        "repo": str(repo),
        "legacy_hook_removed": False,
        "wiring_removed": [],
        "config_stamped": None,
        "config_existing": None,
        "actions": actions,
        "notes": notes,
        "problems": problems,
        "changed": False,
    }

    # ---- config: PLAN FIRST, write last.
    #
    # Everything below this block deletes something. A config argument the
    # enforcement layer refuses used to be discovered AFTER the legacy hook and
    # its wiring were already gone — exit 1, and a repo with no agent-side guard,
    # no legacy guard, and no config: strictly less protected than before it was
    # "migrated", by the step whose job is the opposite. So the config is decided
    # before anything is removed, and a refusal aborts having touched nothing.
    pending_stamp = _plan_config(
        repo,
        result,
        notes,
        problems,
        stamp=stamp,
        protected=protected,
        integration=integration,
        integration_mode=integration_mode,
        release_tool=release_tool,
    )
    if problems:
        return result

    # ---- legacy hook file
    hook = repo / LEGACY_HOOK
    if hook.is_file():
        if not _inside(repo, hook):
            problems.append(
                f"{LEGACY_HOOK} resolves outside {repo}; refusing to remove it"
            )
        else:
            result["legacy_hook_removed"] = True
            actions.append(
                f"remove {LEGACY_HOOK} (2026-06-18 hand copy, superseded by the plugin guard)"
            )
            if not check:
                hook.unlink()
                parent = hook.parent
                try:
                    next(parent.iterdir())
                except StopIteration:
                    parent.rmdir()
                    actions.append(f"remove now-empty {parent.relative_to(repo)}/")
                except OSError:
                    pass

    # ---- settings wiring
    for name in SETTINGS_FILES:
        path = repo / ".claude" / name
        if not path.is_file():
            continue
        if not _inside(repo, path):
            problems.append(
                f".claude/{name} resolves outside {repo}; refusing to edit it"
            )
            continue
        original = path.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
        except ValueError as exc:
            problems.append(f".claude/{name} is not valid JSON ({exc}); left untouched")
            continue
        data, removed = strip_legacy_wiring(data)
        if removed:
            result["wiring_removed"].extend(f".claude/{name}: {c}" for c in removed)
            actions.append(
                f"unwire {len(removed)} legacy hook entr{'y' if len(removed) == 1 else 'ies'} from .claude/{name}"
            )
            if not check:
                path.write_text(dump_like(data, original), encoding="utf-8")
        if LEGACY_BASENAME in json.dumps(data):
            # The matcher is deliberately conservative — it will not delete an
            # entry that merely MENTIONS the script — so anything still naming it
            # after the pass is either a legitimate mention or an invocation
            # shape the matcher did not recognise. Either way the file it names
            # is about to be gone, so say so instead of leaving it to be found by
            # a hook that stops working.
            notes.append(
                f".claude/{name} still mentions {LEGACY_BASENAME} after unwiring — check it by hand; "
                "if it is an invocation, that entry now points at a deleted file"
            )

    # ---- config: the write planned above, performed last
    if pending_stamp and not check:
        cfg_path, rendered = pending_stamp
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(rendered, encoding="utf-8")

    result["changed"] = bool(
        result["legacy_hook_removed"]
        or result["wiring_removed"]
        or result["config_stamped"]
    )
    return result


def render(result: dict, check: bool) -> str:
    lines = [f"repo: {result['repo']}"]
    if not result["changed"] and not result["problems"]:
        lines.append(
            "nothing to do — no legacy guard copy, no legacy wiring, nothing to stamp"
        )
    verb = "would " if check else ""
    for action in result["actions"]:
        lines.append(f"  {verb}{action}")
    # Notes are observations, not planned work — prefixing them with "would "
    # (as an earlier version did) reported "would … already present", which
    # reads as a pending change and is exactly the false confidence this script
    # exists to avoid.
    for note in result["notes"]:
        lines.append(f"  note: {note}")
    for problem in result["problems"]:
        lines.append(f"  PROBLEM: {problem}")
    lines.append(
        "status: "
        + ("PROBLEM" if result["problems"] else ("PLANNED" if check else "OK"))
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-stamp", dest="stamp", action="store_false")
    ap.add_argument("--protected-branch")
    ap.add_argument(
        "--integration-branch",
        default="auto",
        help="`auto` (detect `dev`), `none` (explicit null), or a branch name",
    )
    ap.add_argument("--release-tool")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"not a directory: {repo}", file=sys.stderr)
        return 1

    raw = args.integration_branch
    if raw == "auto":
        mode, integration = "auto", None
    elif raw in ("none", "null"):
        mode, integration = "none", None
    else:
        mode, integration = "name", raw

    result = migrate(
        repo,
        check=args.check,
        stamp=args.stamp,
        protected=args.protected_branch,
        integration=integration,
        integration_mode=mode,
        release_tool=args.release_tool,
    )
    print(json.dumps(result, indent=2) if args.json else render(result, args.check))
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
