# /// script
# requires-python = ">=3.10"
# dependencies = ["imageio-ffmpeg>=0.5"]
# ///
"""Encode a motion-reel project, and check what came out.

    uv run encode.py PROJECT [--name reel] [--max-mb 29]
        frames/ + audio.wav -> NAME-master.mp4 (H.264 CRF 14) and NAME.mp4, the lowest
        CRF that fits under --max-mb (for chat uploads with a size cap)
    uv run encode.py review VIDEO [--out DIR]
        a 4x4 contact sheet pulled from the ENCODED file, to review what ships

Both outputs are decoded again and their frame count is compared with cues.json;
a mismatch exits non-zero. ffmpeg comes from PATH or from imageio-ffmpeg.
"""

import argparse
import json
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
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args], check=True
    )


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
    info = json.loads((project / "cues.json").read_text())
    fps, expected = info["fps"], info["frames"]
    frames = sorted((project / "frames").glob("f_*.png"))
    if len(frames) != expected:
        raise SystemExit(
            f"expected {expected} frames in {project / 'frames'}, found {len(frames)} — run render.py frames"
        )
    audio = project / "audio.wav"
    src = ["-framerate", str(fps), "-i", str(project / "frames" / "f_%05d.png")]
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

    master, share = project / f"{name}-master.mp4", project / f"{name}.mp4"
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


def review(video, out_dir, n=16):
    out_dir.mkdir(parents=True, exist_ok=True)
    total = decoded_frames(video)
    picks = [round((k + 0.5) * total / n) for k in range(n)]
    sel = "+".join(f"eq(n\\,{p})" for p in picks)
    out = out_dir / f"{video.stem}-sheet.png"
    run(
        [
            "-i",
            str(video),
            "-vf",
            f"select='{sel}',scale=480:270,tile=4x{(n + 3) // 4}",
            "-frames:v",
            "1",
            "-fps_mode",
            "vfr",
            str(out),
        ]
    )
    print(f"wrote {out}: frames {picks}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        ap = argparse.ArgumentParser(prog="encode.py review")
        ap.add_argument("video", type=Path)
        ap.add_argument("--out", type=Path, default=None)
        a = ap.parse_args(sys.argv[2:])
        review(a.video.resolve(), (a.out or a.video.resolve().parent / "review"))
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
