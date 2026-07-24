---
name: research-repin
description: >-
  Move a research line's engine pin to a new SHA (or the engine's HEAD), re-lock, re-run
  the line's reproduction-marked tests, and refresh its data_inputs.yaml hashes — so
  updating a pin is one auditable command, not a hand-edit that silently drifts. Use when
  the user says "repin X", "bump the engine pin", "update line X to engine head", or when
  /research-status flags a stale pin. Implements ADR-0007 #3 (/research-repin).
argument-hint: "<line> [--to <sha|engine-head>]"
---

# /research-repin

Advance a line's Model C engine pin deliberately. Pairs with `/research-status` (which
flags stale pins) and `/research-freeze` (which snapshots the data plane).

## Contract

Input: `research/<line>/pyproject.toml` pinning the engine to a 40-char SHA. Output: the
pin moved to the requested SHA, `uv.lock` refreshed, the line's `reproduction`-marked
tests re-run green (or the drift surfaced), and `data_inputs.yaml` hashes refreshed
against the new engine tree.

## Behavior

1. **Resolve target SHA.** `--to <sha>` uses it verbatim (must be 40-hex). `--to
   engine-head` (default) resolves `git -C <engine-root> rev-parse origin/<default-branch>`
   using the engine repo from `.research-config.yaml::pin_targets` and
   `staleness.default_branch`. Report the old → new SHA and the commit count between them.
2. **Edit the pin.** Rewrite the `git+…@<sha>` for each `pin_target` in the line's
   `pyproject.toml`. Stage by path.
3. **Re-lock.** `uv lock` in the line dir (per-line venv, ADR-0002 Model C).
4. **Re-run reproduction tests.** `uv run pytest tests/ -m reproduction` in the line dir.
   Green → the pin move is safe. Red → STOP: the engine change moved the numbers; report
   the diff and let the author decide (accept the new golden, or hold the pin).
5. **Refresh hashes.** Re-run `/research-freeze <line>` (or its hash loop) so
   `data_inputs.yaml` reflects the new engine tree; a changed input hash is exactly the
   rename/schema signal the pin alone would have hidden.
6. **Report.** Old/new SHA, commit lag closed, reproduction test result, and any input
   whose hash changed. Do not commit unless asked — leave a clean staged diff.

## Refusals / guards

- Never force a red reproduction to green by loosening tolerances or editing the golden
  without the author's decision — a moved number after a repin is a finding, not a nuisance.
- Never repin a `live-data` / `historical` line's data plane into `pinned` shape; those
  classes are honest about being unpinnable.

<!-- TODO(executable body): factor the pin-rewrite + lock + test loop into a helper
     (e.g. scripts/research/repin.py) when the first consumer adopts this; the contract
     above is the spec. Kept declarative for now (ADR-0007 #3, best-effort scaffold). -->
