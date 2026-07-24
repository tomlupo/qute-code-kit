"""ref_resolver — new-name-first path resolver for engine reference data.

A quant lab reads reference data (``config/reference/*.csv``,
``data/processed/*.parquet``) from a *live sibling checkout* of its engine repo.
When the engine renames a file (``fund_master.csv`` -> ``instrument_master.csv``)
every hard-coded path breaks even though the engine SHA is pinned — the data plane
is not in the pip package.

Declare the candidate names new-first and this resolver returns whichever exists in
the given checkout, so a rename in flight doesn't break the line. Promote the winning
name into ``data_inputs.yaml`` once the rename settles.

Proven pattern: dm-evo-lab ``research/selection-l2-taxonomy/ref_compat.py`` (TOM-132),
generalised here so no line reinvents it.
"""

from __future__ import annotations

from pathlib import Path


def resolve(engine_root: Path, *candidates: str) -> Path:
    """Return the first candidate that exists under ``engine_root`` (new name first).

    Falls back to the last candidate when none exist, so a read fails with a clear
    ``FileNotFoundError`` on a known path rather than a silent ``None``.
    """
    if not candidates:
        raise ValueError("resolve() needs at least one candidate path")
    for rel in candidates:
        p = engine_root / rel
        if p.exists():
            return p
    return engine_root / candidates[-1]
