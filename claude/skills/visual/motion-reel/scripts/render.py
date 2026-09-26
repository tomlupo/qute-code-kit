# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.40"]
# ///
"""Render a motion-reel project through headless Chrome.

    uv run render.py info   PROJECT              cue sheet + timing -> PROJECT/cues.json
    uv run render.py check  PROJECT              every quarter second + every cut, one sample,
                                                 nothing saved: fails on any script error
    uv run render.py sheets PROJECT              review contact sheets -> PROJECT/review/
    uv run render.py frames PROJECT [--sub 8]    every frame -> PROJECT/frames/f_00000.png
    uv run render.py still  PROJECT --t 12.5     one full-resolution frame -> PROJECT/review/

PROJECT holds reel.js and fonts.css (see new_reel.py). The harness page is served
from this skill, so a project never carries a copy of it. Chrome comes from
$MOTION_REEL_CHROME, a system install, or Playwright's own Chromium (installed on
first use). Exits non-zero when the page reports an error or a frame is missing.
"""

import argparse
import base64
import functools
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HARNESS = Path(__file__).resolve().parent.parent / "assets" / "render.html"
CHROMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
MAC_CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
SHEET_FRACTIONS = [0.06, 0.18, 0.31, 0.44, 0.57, 0.7, 0.83, 0.96]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def translate_path(self, path):
        if urlparse(path).path == "/__harness.html":
            return str(HARNESS)
        return super().translate_path(path)


def serve(project):
    srv = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(project))
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def chrome_path():
    if os.environ.get("MOTION_REEL_CHROME"):
        return os.environ["MOTION_REEL_CHROME"]
    for name in CHROMES:
        if shutil.which(name):
            return shutil.which(name)
    return next((p for p in MAC_CHROMES if Path(p).exists()), None)


def launch(p):
    args = ["--disable-gpu", "--force-color-profile=srgb"]
    exe = chrome_path()
    if exe:
        return p.chromium.launch(executable_path=exe, args=args)
    try:
        return p.chromium.launch(args=args)
    except Exception as e:  # Playwright's Chromium is not installed yet
        if "Executable doesn't exist" not in str(e):
            raise
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )
        return p.chromium.launch(args=args)


def open_page(p, port, errors):
    browser = launch(p)
    page = browser.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    # every console error fails the run: a missing fonts.css is a 404, not a warning
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(f"http://127.0.0.1:{port}/__harness.html")
    page.wait_for_function(
        "window.READY === true || !!window.READY_ERR", timeout=120000
    )
    err = page.evaluate("window.READY_ERR || null")
    if err:
        raise SystemExit(f"reel.js failed to start:\n{err}")
    return browser, page


def save_png(data_url, path):
    path.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))


def worker(job):
    port, frames, out, sub = job
    from playwright.sync_api import sync_playwright

    errors, done = [], 0
    with sync_playwright() as p:
        browser, page = open_page(p, port, errors)
        for f in frames:
            save_png(
                page.evaluate("([f, s]) => renderFrame(f, s)", [f, sub]),
                out / f"f_{f:05d}.png",
            )
            done += 1
        browser.close()
    return done, errors


def with_page(project, fn):
    from playwright.sync_api import sync_playwright

    port, errors = serve(project), []
    with sync_playwright() as p:
        browser, page = open_page(p, port, errors)
        result = fn(page)
        browser.close()
    if errors:
        raise SystemExit("page errors:\n  " + "\n  ".join(errors))
    return result


def cmd_info(project, a):
    info = with_page(project, lambda page: page.evaluate("window.INFO"))
    out = project / "cues.json"
    out.write_text(json.dumps(info, indent=1))
    print(
        f"wrote {out}: {info['dur']:.2f} s, {info['frames']} frames at {info['fps']} fps, {len(info['scenes'])} scenes"
    )


def cmd_sheets(project, a):
    review = project / "review"
    review.mkdir(exist_ok=True)

    def run(page):
        info = page.evaluate("window.INFO")
        fps, written = info["fps"], []
        scenes = info["scenes"]
        for k in range(0, len(scenes), 2):
            frames = [
                round((sc["start"] + fr * sc["dur"]) * fps)
                for sc in scenes[k : k + 2]
                for fr in SHEET_FRACTIONS
            ]
            frames = [min(f, info["frames"] - 1) for f in frames]
            path = review / f"sheet-{k + 1}-{min(k + 2, len(scenes))}.png"
            save_png(
                page.evaluate("([fr, c, s]) => sheet(fr, c, s)", [frames, 4, a.sub]),
                path,
            )
            written.append(path)
        return written

    for path in with_page(project, run):
        print("wrote", path)


def cmd_check(project, a):
    """Render the whole timeline sparsely: a quarter-second grid plus two seconds around
    every scene boundary, where transitions draw two scenes at once. Review sheets sample
    eight frames a scene; a script error between two samples passes them and still
    breaks the full render."""

    def run(page):
        info = page.evaluate("window.INFO")
        fps, total = info["fps"], info["frames"]
        frames = set(range(0, total, max(1, fps // 4)))
        for sc in info["scenes"]:
            b = round(sc["start"] * fps)
            frames.update(range(max(0, b - fps), min(total, b + fps)))
        frames = sorted(frames)
        return len(frames), page.evaluate("fr => probe(fr)", frames)

    n, failures = with_page(project, run)
    if failures:
        first = "\n  ".join(f"frame {x['f']}: {x['error']}" for x in failures[:5])
        raise SystemExit(f"check: {len(failures)} of {n} frames throw\n  {first}")
    print(f"check: {n} frames rendered, no script errors")


def cmd_still(project, a):
    review = project / "review"
    review.mkdir(exist_ok=True)
    path = review / f"still-{a.t:.3f}.png"

    def run(page):
        fps = page.evaluate("window.INFO.fps")
        save_png(
            page.evaluate("([f, s]) => renderFrame(f, s)", [round(a.t * fps), a.sub]),
            path,
        )

    with_page(project, run)
    print("wrote", path)


def cmd_frames(project, a):
    info = with_page(project, lambda page: page.evaluate("window.INFO"))
    total = info["frames"]
    frames = list(range(total)) if not a.range else parse_range(a.range)
    out = project / "frames"
    if not a.range and out.exists():
        shutil.rmtree(out)
    out.mkdir(exist_ok=True)
    port, workers = serve(project), max(1, min(a.workers, len(frames)))
    t0 = time.time()
    print(f"rendering {len(frames)} frames, {a.sub} sub-frames each, {workers} workers")
    with mp.get_context("spawn").Pool(workers) as pool:
        results = pool.map(
            worker, [(port, frames[w::workers], out, a.sub) for w in range(workers)]
        )
    done = sum(r[0] for r in results)
    errors = [e for r in results for e in r[1]]
    print(f"rendered {done} frames in {time.time() - t0:.0f} s -> {out}")
    if errors:
        raise SystemExit("page errors:\n  " + "\n  ".join(sorted(set(errors))))
    missing = [f for f in frames if not (out / f"f_{f:05d}.png").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} frames missing, first {missing[:5]}")


def parse_range(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            lo, hi = map(int, part.split("-"))
            out += range(lo, hi + 1)
        elif part:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("mode", choices=["info", "check", "sheets", "frames", "still"])
    ap.add_argument("project", type=Path)
    ap.add_argument(
        "--sub",
        type=int,
        default=None,
        help="motion-blur sub-frames (default 8 for frames/still, 1 for sheets)",
    )
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--range", default="", help="frames only: e.g. 0-299,600")
    ap.add_argument("--t", type=float, default=0.0, help="still only: time in seconds")
    a = ap.parse_args()
    project = a.project.resolve()
    if not (project / "reel.js").exists():
        raise SystemExit(f"{project} has no reel.js — scaffold one with new_reel.py")
    if a.sub is None:
        a.sub = 1 if a.mode == "sheets" else 8
    modes = {
        "info": cmd_info,
        "check": cmd_check,
        "sheets": cmd_sheets,
        "frames": cmd_frames,
        "still": cmd_still,
    }
    modes[a.mode](project, a)


if __name__ == "__main__":
    main()
