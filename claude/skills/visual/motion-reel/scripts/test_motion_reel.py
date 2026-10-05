"""Offline tests for the disk guards in render.py and encode.py (TOM-1222).
No Chrome and no real ffmpeg: the page and ffmpeg are stubbed.
Run: python -m pytest test_motion_reel.py"""

import argparse
import json
import sys
from collections import namedtuple
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import encode
import render

Usage = namedtuple("Usage", "total used free")

INFO = {"w": 1920, "h": 1080, "fps": 60, "dur": 56.25, "frames": 3375, "scenes": []}


class Reached(Exception):
    """The render went past the disk check."""


def frames_args(project):
    return argparse.Namespace(sub=8, workers=2, project=project)


def stub_render(monkeypatch, free):
    monkeypatch.setattr(render, "with_page", lambda project, fn: (INFO, 2_000_000))
    monkeypatch.setattr(render.shutil, "disk_usage", lambda p: Usage(0, 0, free))

    def serve(project):
        raise Reached

    monkeypatch.setattr(render, "serve", serve)


def test_frames_refuses_when_disk_too_small(tmp_path, monkeypatch):
    stub_render(monkeypatch, free=2**30)
    old = tmp_path / "frames" / "f_00000.png"
    old.parent.mkdir()
    old.write_bytes(b"old frame")
    with pytest.raises(SystemExit) as e:
        render.cmd_frames(tmp_path, frames_args(tmp_path))
    msg = str(e.value)
    # 2 x 2.0 MB sample > 1.25 B/px floor: 4,000,000 x 3,375 frames = 12.6 GiB
    assert "12.6 GiB" in msg, msg
    assert "1.0 GiB free" in msg, msg
    # refused before the render started, and before the old frames were deleted
    assert [p.name for p in old.parent.iterdir()] == ["f_00000.png"]


def test_frames_proceeds_when_disk_holds_them(tmp_path, monkeypatch):
    stub_render(monkeypatch, free=20 * 2**30)
    with pytest.raises(Reached):
        render.cmd_frames(tmp_path, frames_args(tmp_path))


def test_frames_bytes_uses_pixel_floor_for_a_blank_sample():
    assert render.frames_bytes(INFO, 1000) == int(1.25 * 1920 * 1080 * 3375)


STUB = """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if "null" in args:
    sys.stderr.write("frame=    %s fps=0\\n" % os.environ.get("STUB_FRAMES", "3"))
    sys.exit(0)
if args[-2] == "-i":  # probe: input only, no output
    sys.stderr.write("Duration: 00:00:00.05\\n")
    sys.exit(1)
with open(args[-1], "wb") as f:
    f.write(b"NEW" * 100)
sys.exit(1 if os.environ.get("STUB_FAIL") else 0)
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    stub = tmp_path / "ffmpeg"
    stub.write_text(STUB)
    stub.chmod(0o755)
    monkeypatch.setattr(encode, "ffmpeg", lambda: str(stub))
    proj = tmp_path / "reel-project"
    (proj / "frames").mkdir(parents=True)
    for f in range(3):
        (proj / "frames" / f"f_{f:05d}.png").write_bytes(b"png")
    (proj / "cues.json").write_text(json.dumps({"fps": 60, "frames": 3}))
    return proj.resolve()


def test_failed_encode_keeps_previous_videos(project, monkeypatch):
    (project / "reel-master.mp4").write_bytes(b"OLD-MASTER")
    (project / "reel.mp4").write_bytes(b"OLD-SHARE")
    monkeypatch.setenv("STUB_FAIL", "1")
    with pytest.raises(SystemExit) as e:
        encode.encode(project, "reel", 29.0)
    assert "ffmpeg exited 1" in str(e.value)
    assert (project / "reel-master.mp4").read_bytes() == b"OLD-MASTER"
    assert (project / "reel.mp4").read_bytes() == b"OLD-SHARE"
    assert list(project.glob("*.part.*")) == []


def test_frame_count_mismatch_keeps_previous_videos(project, monkeypatch):
    (project / "reel-master.mp4").write_bytes(b"OLD-MASTER")
    (project / "reel.mp4").write_bytes(b"OLD-SHARE")
    monkeypatch.delenv("STUB_FAIL", raising=False)
    monkeypatch.setenv("STUB_FRAMES", "2")
    with pytest.raises(SystemExit) as e:
        encode.encode(project, "reel", 29.0)
    assert "decodes to 2 frames, expected 3" in str(e.value)
    assert (project / "reel-master.mp4").read_bytes() == b"OLD-MASTER"
    assert (project / "reel.mp4").read_bytes() == b"OLD-SHARE"
    assert list(project.glob("*.part.*")) == []


def test_failed_first_encode_leaves_no_final_file(project, monkeypatch):
    monkeypatch.setenv("STUB_FAIL", "1")
    with pytest.raises(SystemExit):
        encode.encode(project, "reel", 29.0)
    assert sorted(p.name for p in project.iterdir()) == ["cues.json", "frames"]


def test_normal_encode_writes_the_same_final_names(project, monkeypatch):
    monkeypatch.delenv("STUB_FAIL", raising=False)
    (project / "reel-master.mp4").write_bytes(b"OLD-MASTER")
    encode.encode(project, "reel", 29.0)
    assert (project / "reel-master.mp4").read_bytes() == b"NEW" * 100
    assert (project / "reel.mp4").read_bytes() == b"NEW" * 100
    assert list(project.glob("*.part.*")) == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
