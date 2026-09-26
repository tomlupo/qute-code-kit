# /// script
# requires-python = ">=3.10"
# dependencies = ["imageio-ffmpeg>=0.5"]
# ///
"""Encode a motion-reel project, and check what came out.

    uv run encode.py PROJECT [--name reel] [--max-mb 29]
        frames/ + audio.wav -> NAME-master.mp4 (H.264 CRF 14) and NAME.mp4, the lowest
        CRF that fits under --max-mb (for chat uploads with a size cap)
    uv run encode.py review VIDEO [--out DIR] [--at 12.5 [--crop W:H:X:Y]]
        a 4x4 contact sheet pulled from the ENCODED file, to review what ships;
        with --at, one full-size frame of it instead, to read small type 1:1

Both outputs are decoded again and their frame count is compared with cues.json;
a mismatch exits non-zero. ffmpeg is imageio-ffmpeg's own build, never one from
PATH: an older system ffmpeg lacks options this script uses.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

COLOR = [
    "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
]  # fmt: skip
CRF_LADDER = [14, 16, 18, 20, 22, 24]


def ffmpeg():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True
    )


def fresh(out, args, hint=""):
    """ffmpeg into a new file, which then replaces `out`. ffmpeg can exit 0 having
    written nothing (a seek past the end), and an old image must never pass for one of
    the video just encoded. `-update 1` makes the image muxer take the path as a name,
    not a pattern, so a % in the project's path cannot send the image elsewhere."""
    part = out.with_name(out.stem + ".part" + out.suffix)
    part.unlink(missing_ok=True)
    try:
        run([*args, "-update", "1", str(part)])
    except subprocess.CalledProcessError:
        part.unlink(missing_ok=True)
        raise
    if not part.exists() or part.stat().st_size == 0:
        part.unlink(missing_ok=True)
        raise SystemExit(f"ffmpeg wrote no {out.name}{hint}")
    os.replace(part, out)


def decoded_frames(video):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", str(video), "-map", "0:v", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    counts = re.findall(r"frame=\s*(\d+)", r.stderr)
    return int(counts[-1]) if counts else 0


def probe(video):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", str(video)], capture_output=True, text=True
    )
    return " | ".join(
        ln.strip()
        for ln in r.stderr.splitlines()
        if re.search(r"Duration|Video:|Audio:", ln)
    )


def encode(project, name, max_mb):
    if Path(name).name != name or name in ("", ".", ".."):
        raise SystemExit(f"--name {name!r} must be a file name, not a path")
    master, share = project / f"{name}-master.mp4", project / f"{name}.mp4"
    for out in (master, share):  # a symlink must not carry the video out of the project
        if out.resolve().parent != project:
            raise SystemExit(f"{out} resolves to {out.resolve()}, outside {project}")
    info = json.loads((project / "cues.json").read_text())
    fps, expected = info["fps"], info["frames"]
    frames = sorted((project / "frames").glob("f_*.png"))
    if len(frames) != expected:
        raise SystemExit(
            f"expected {expected} frames in {project / 'frames'}, found {len(frames)} — run render.py frames"
        )
    audio = project / "audio.wav"
    # the frame pattern is ffmpeg syntax: a % in the project's path must stay literal
    pattern = str(project / "frames").replace("%", "%%") + "/f_%05d.png"
    src = ["-framerate", str(fps), "-i", pattern]
    if audio.exists():
        src += ["-i", str(audio)]
    else:
        print("no audio.wav — encoding a silent video", file=sys.stderr)

    def one(out, crf, abr):
        a = ["-c:a", "aac", "-b:a", abr, "-shortest"] if audio.exists() else ["-an"]
        run(
            [
                *src,
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                str(crf),
                *COLOR,
                *a,
                "-movflags",
                "+faststart",
                str(out),
            ]
        )

    # new files, never written in place through a hard link to one elsewhere; only now,
    # after the name, link and frame-count checks, so an encode refused there keeps the
    # old videos (an input ffmpeg itself rejects, such as a broken audio.wav, does not)
    for out in (master, share):
        out.unlink(missing_ok=True)
    one(master, 14, "320k")
    for crf in CRF_LADDER:
        if crf == 14:
            shutil.copyfile(master, share)
        else:
            one(share, crf, "256k")
        size = share.stat().st_size / 2**20
        print(f"  crf {crf}: {size:.1f} MiB")
        if size <= max_mb:
            break
    for out in (master, share):
        n = decoded_frames(out)
        print(
            f"{out.name}: {out.stat().st_size / 2**20:.1f} MiB, {n} frames decoded | {probe(out)}"
        )
        if n != expected:
            raise SystemExit(f"{out.name} decodes to {n} frames, expected {expected}")
    if (
        size > max_mb
    ):  # the capped copy is the promise of this step: missing it is a failure
        raise SystemExit(
            f"{share.name} is {size:.1f} MiB even at CRF {CRF_LADDER[-1]}, over --max-mb {max_mb}: shorten the reel, lower GRAIN, or raise the cap"
        )


def review(video, out_dir, at=None, crop=None, n=16):
    out_dir.mkdir(parents=True, exist_ok=True)
    # --at: one frame of the encoded file at full size, to read small type 1:1
    if at is not None:
        out = out_dir / f"{video.stem}-{at:.3f}.png"
        vf = ["-vf", f"crop={crop}"] if crop else []
        args = ["-ss", str(at), "-i", str(video), "-frames:v", "1", *vf]
        fresh(out, args, hint=": is --at past the end?")
        print(f"wrote {out}")
        return
    total = decoded_frames(video)
    picks = [round((k + 0.5) * total / n) for k in range(n)]
    sel = "+".join(f"eq(n\\,{p})" for p in picks)
    out = out_dir / f"{video.stem}-sheet.png"
    tile = f"select='{sel}',scale=480:270,tile=4x{(n + 3) // 4}"
    fresh(out, ["-i", str(video), "-vf", tile, "-frames:v", "1", "-fps_mode", "vfr"])
    print(f"wrote {out}: frames {picks}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        ap = argparse.ArgumentParser(prog="encode.py review")
        ap.add_argument("video", type=Path)
        ap.add_argument("--out", type=Path, default=None)
        ap.add_argument("--at", type=float, help="one full-size frame at this second")
        ap.add_argument("--crop", help="with --at: W:H:X:Y, e.g. 1100:560:760:300")
        a = ap.parse_args(sys.argv[2:])
        if a.crop and a.at is None:
            ap.error("--crop needs --at")
        # absolute, not resolved: a linked video still reviews into its own project
        video = a.video.absolute()
        review(video, a.out or video.parent / "review", a.at, a.crop)
        return
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("project", type=Path)
    ap.add_argument("--name", default="reel")
    ap.add_argument("--max-mb", type=float, default=29.0)
    a = ap.parse_args()
    encode(a.project.resolve(), a.name, a.max_mb)


if __name__ == "__main__":
    main()
