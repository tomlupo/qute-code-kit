# /// script
# requires-python = ">=3.10"
# ///
"""Scaffold a motion-reel project.

    uv run new_reel.py DIR [--family "Inter:wght@100..900" --family "DM Mono:wght@400;500"]

Copies reel.js and score.py from the skill's templates, downloads the fonts, and
writes make.sh, which runs every later step. Run again on an existing project, it
keeps every file already there: --force writes them all again, --family changes
only the fonts.

    ./make.sh sheets    check the whole timeline, then review contact sheets
    ./make.sh all       check, frames with motion blur, soundtrack, video, review sheet
    ./make.sh info | check | frames | audio | encode | review    one step at a time
    ./make.sh still 12.5                         one frame at full size, before the render
    ./make.sh review --at 12.5 [--crop W:H:X:Y]  one frame of the encoded video
"""

import argparse
import shlex
import stat
import subprocess
import sys
from pathlib import Path

from project_files import present, write_file

SKILL = Path(__file__).resolve().parent.parent
MAKE = """#!/usr/bin/env bash
# motion-reel project. Every step reads reel.js (picture) and score.py (sound).
USAGE="usage: ./make.sh [sheets|all|info|check|frames|audio|encode|review|still SECONDS]"
set -euo pipefail
cd "$(dirname "$0")"
SCRIPTS={scripts}
NAME={name}
run() {{ uv run --quiet "$SCRIPTS/$1" "${{@:2}}"; }}
case "${{1:-all}}" in
  info)   run render.py info . ;;
  check)  run render.py info . && run render.py check . ;;
  sheets) run render.py info . && run render.py check . && run render.py sheets . ;;
  frames) run render.py info . && run render.py check . && run render.py frames . ;;
  audio)  run render.py info . && run synth.py . ;;
  encode) run encode.py . --name="$NAME" ;;
  review) run encode.py review "./$NAME.mp4" "${{@:2}}" ;;
  still)  run render.py still . --t "${{2:?$USAGE}}" ;;
  all)    run render.py info . && run render.py check . && run render.py frames . && run synth.py . \\
            && run encode.py . --name="$NAME" && run encode.py review "./$NAME.mp4" ;;
  *) echo "$USAGE" >&2; exit 2 ;;
esac
"""


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("dir", type=Path)
    ap.add_argument(
        "--family",
        action="append",
        help="css2 font family spec, repeatable (default: Inter + DM Mono)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="write reel.js, score.py, make.sh and the fonts even if present",
    )
    a = ap.parse_args()
    d = a.dir.resolve()
    d.mkdir(parents=True, exist_ok=True)
    for src, dst in (
        ("reel-template.js", "reel.js"),
        ("score-template.py", "score.py"),
    ):
        target = d / dst
        if present(target) and not a.force:  # a dangling link counts: never followed
            print(f"kept existing {target}")
            continue
        write_file(target, (SKILL / "assets" / src).read_bytes(), d)
        print(f"wrote {target}")
    make = d / "make.sh"
    if present(make) and not a.force:
        # never suggest --force here: it also writes reel.js and score.py over the film
        print(f"kept existing {make} (delete it and re-run to write a fresh one)")
    else:
        # shell-quoted: a directory name is data, never code
        paths = {
            "scripts": shlex.quote(str(SKILL / "scripts")),
            "name": shlex.quote(d.name),
        }
        write_file(make, MAKE.format(**paths), d)
        make.chmod(make.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"wrote {make}")
    if a.family or a.force or not present(d / "fonts.css"):
        fam = [x for f in (a.family or []) for x in ("--family", f)]
        sys.stdout.flush()  # our lines first, then fonts.py's
        subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "fonts.py"), str(d), *fam],
            check=True,
        )
    else:  # reel.js's FAM names these fonts; a silent default would break that link
        print(f"kept existing {d / 'fonts.css'} (pass --family to change the fonts)")
    print(
        f"\nnext:\n  cd {shlex.quote(str(d))}\n  ./make.sh sheets      # then look at review/*.png\n  ./make.sh all"
    )


if __name__ == "__main__":
    main()
