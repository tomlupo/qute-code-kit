"""How every motion-reel script writes into a project: never through a link, never out of it.

A generated file is written beside its destination and renamed over it, so nothing is
ever written through a symbolic link. A destination that is itself a link, even a
dangling one, is refused: a link there means someone arranged for the output to land
somewhere else. A directory an output goes into must lie inside the project.
"""

import os
import tempfile
from pathlib import Path


def present(path):
    """Whether anything is at `path`, a dangling link included."""
    return path.exists() or path.is_symlink()


def _inside(path, project):
    root, p = Path(project).resolve(), Path(path).resolve()
    return p == root or root in p.parents


def output_dir(path, project):
    """`path`, created if missing, as a directory inside `project`."""
    if path.is_symlink():
        raise SystemExit(
            f"{path} is a symbolic link: outputs go into the project itself"
        )
    if not _inside(
        path, project
    ):  # checked before mkdir, which would already act there
        raise SystemExit(f"{path} lies outside the project {Path(project).resolve()}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_file(path, data, project):
    """Write `data` (bytes or str) to `path` inside `project`: atomically, never through a link."""
    if path.is_symlink():
        raise SystemExit(
            f"{path} is a symbolic link: remove it, outputs are written as files"
        )
    if not _inside(path.parent, project):
        raise SystemExit(f"{path} lies outside the project {Path(project).resolve()}")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode() if isinstance(data, str) else data)
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(
            tmp, 0o666 & ~umask
        )  # a plain file's mode, not mkstemp's owner-only 0600
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
