# /// script
# requires-python = ">=3.10"
# ///
"""Scaffold a motion-reel project.

    uv run new_reel.py DIR [--family "Inter:wght@100..900" --family "DM Mono:wght@400;500"]

Copies reel.js and score.py from the skill's templates, downloads the fonts, and
writes make.sh, which runs every later step:

    ./make.sh sheets    check the whole timeline, then review contact sheets
    ./make.sh all       check, frames with motion blur, soundtrack, video, review sheet
    ./make.sh info | check | frames | audio | encode | review    one step at a time
    ./make.sh still 12.5                         one frame at full size, before the render
    ./make.sh review --at 12.5 [--crop W:H:X:Y]  one frame of the encoded video
"""

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
MAKE = """#!/usr/bin/env bash
# motion-reel project. Every step reads reel.js (picture) and score.py (sound).
USAGE="usage: ./make.sh [sheets|all|info|check|frames|audio|encode|review|still SECONDS]"
set -euo pipefail
cd "$(dirname "$0")"
SCRIPTS="{scripts}"
NAME="{name}"
run() {{ uv run --quiet "$SCRIPTS/$1" "${{@:2}}"; }}
case "${{1:-all}}" in
  info)   run render.py info . ;;
  check)  run render.py info . && run render.py check . ;;
  sheets) run render.py info . && run render.py check . && run render.py sheets . ;;
  frames) run render.py info . && run render.py check . && run render.py frames . ;;
  audio)  run render.py info . && run synth.py . ;;
  encode) run encode.py . --name "$NAME" ;;
  review) run encode.py review "$NAME.mp4" "${{@:2}}" ;;
  still)  run render.py still . --t "${{2:?$USAGE}}" ;;
  all)    run render.py info . && run render.py check . && run render.py frames . && run synth.py . \\
            && run encode.py . --name "$NAME" && run encode.py review "$NAME.mp4" ;;
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
        "--force", action="store_true", help="overwrite reel.js and score.py if present"
    )
    a = ap.parse_args()
    d = a.dir.resolve()
    d.mkdir(parents=True, exist_ok=True)
    for src, dst in (
        ("reel-template.js", "reel.js"),
        ("score-template.py", "score.py"),
    ):
        target = d / dst
        if target.exists() and not a.force:
            print(f"kept existing {target}")
            continue
        shutil.copyfile(SKILL / "assets" / src, target)
        print(f"wrote {target}")
    make = d / "make.sh"
    make.write_text(MAKE.format(scripts=SKILL / "scripts", name=d.name))
    make.chmod(make.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote {make}")
    fam = [x for f in (a.family or []) for x in ("--family", f)]
    subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "fonts.py"), str(d), *fam], check=True
    )
    print(
        f"\nnext:\n  cd {d}\n  ./make.sh sheets      # then look at review/*.png\n  ./make.sh all"
    )


if __name__ == "__main__":
    main()
