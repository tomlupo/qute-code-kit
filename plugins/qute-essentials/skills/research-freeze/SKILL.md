---
name: research-freeze
description: >-
  Snapshot a research line's declared engine data inputs and record their sha256 in
  data_inputs.yaml, so a concluded line is reproducible from a frozen data plane (not a
  live sibling read). Use when concluding a line, when the engine data can't be re-derived
  from the pinned SHA, or when the user says "freeze this line", "snapshot the inputs",
  "lock the data for X". Implements ADR-0007 #3 (/research-freeze).
argument-hint: "<line> [--engine-root <path>]"
---

# /research-freeze

Turn a line's live engine reads into a hashed, frozen data plane. Freezing is one
command, not a manual convention. Pairs with `/research-repin` (moves the SHA) and the
`check_research_pins.py` provenance-on-conclude gate (enforces the hashes).

## Contract

Input: a research line `research/<line>/` with a `data_inputs.yaml` declaring the engine
files it consumes (from the template). Output: every input carries a real 64-hex `sha256`,
and — for `reproducibility_class: snapshot-frozen` — the files themselves are force-added
under `<line>/data/`.

## Behavior

1. **Resolve the line + engine root.** Read `.research-config.yaml` (`pin_targets`,
   `research_root`). The engine checkout is the sibling clone of the pinned engine repo;
   take it from `--engine-root` or resolve the sibling path the line already uses (the
   `ref_resolver.py` candidates / `Path(__file__).parents[N] / "<engine-repo>"`).
2. **Read `data_inputs.yaml`.** For each declared `path`, resolve it in the engine
   checkout through the line's `ref_resolver.resolve(...)` (new name first, so an
   in-flight rename resolves) and confirm it exists. Missing input → stop and report which.
3. **Hash.** Compute `sha256` of each resolved file (stream in chunks) and write it back
   into `data_inputs.yaml` in place, preserving comments/order where practical.
4. **Snapshot (snapshot-frozen only).** When the line's `reproducibility_class` is
   `snapshot-frozen`, copy each input into `<line>/data/<path>` and `git add -f` it past
   `.gitignore`. `pinned` lines skip this — they stay reproducible from the engine SHA.
5. **Provenance.** Fill the line README `provenance` block: `engine_commit` =
   `git -C <engine-root> rev-parse HEAD`, `ran_at` = today (Europe/Warsaw). Leave
   `status` as-is (`/finding` or the author concludes the line).
6. **Verify + report.** Run `check_research_pins.py`; report per-input hash, whether a
   snapshot was force-added, and the engine commit recorded. Do not conclude the line
   here — freezing prepares it; conclusion is a separate, deliberate step.

## Refusals / guards

- Never invent a hash — if an input can't be resolved in the engine checkout, stop and
  say so. For a line that genuinely can't be pinned, the right move is
  `reproducibility_class: live-data | historical` + a `repro_note`, not a fake freeze.
- Never edit engine files; the engine checkout is read-only here.

<!-- TODO(executable body): wire the hash+snapshot loop to a helper script (e.g.
     scripts/research/freeze.py) once the first consumer adopts this; the contract above
     is the spec. Kept declarative for now (ADR-0007 #3, best-effort scaffold). -->
