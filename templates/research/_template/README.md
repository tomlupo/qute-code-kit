---
line: {{NAME}}
status: active                   # active | paused | concluded | abandoned | superseded
reproducibility_class: pinned    # pinned | snapshot-frozen | live-data | historical
question: "{{DESCRIPTION}}"
started: YYYY-MM-DD
tracker: null
# provenance — optional while active; GATED on conclude for `pinned` lines.
# check_research_pins.py requires engine_commit + ran_at filled (no TBD) at
# status: concluded, alongside hashed data_inputs.yaml.
provenance:
  engine_commit: TBD             # 40-hex engine SHA the conclusion was produced against
  ran_at: TBD                    # YYYY-MM-DD the reproduction run was taken
# repro_note — REQUIRED on conclude for `historical` / `live-data` lines *instead of*
# hashes: one honest sentence on why this line cannot be pinned.
repro_note: null
---

# {{NAME}}

{{DESCRIPTION}}

## Reproducibility class

Set `reproducibility_class` in the frontmatter above to one of:

| Class | Meaning | Gate on conclude |
|---|---|---|
| `pinned` | Reproducible from the engine SHA + hashed data inputs. | `data_inputs.yaml` present with a non-null `sha256` on every input, **and** `provenance` filled (no `TBD`). |
| `snapshot-frozen` | Inputs can't be re-derived, so they're force-added into `data/` and hashed. | Snapshot input files present under the line **and** a `sha256` for each in `data_inputs.yaml`. |
| `live-data` | Reads an external API / live feed that can't be pinned. | Class set **and** a non-empty `repro_note` saying why it can't be pinned. |
| `historical` | Concluded before this contract; inputs no longer recoverable. | Class set **and** a `repro_note` documenting the gap honestly. |

The gate (`check_research_pins.py`) enforces this only at `status: concluded`.
Active / paused lines are exempt — iterate live against the sibling checkout; the
contract binds at conclusion. Never fabricate hashes for a `historical`/`live-data`
line — document the gap in `repro_note` instead.

## Data inputs

[`data_inputs.yaml`](data_inputs.yaml) declares every engine file this line reads
and its `sha256` at pin time — the data plane the engine SHA pin does *not* cover.
Fill hashes with `/research-freeze` (or by hand at conclude).

Read engine reference data through [`ref_resolver.py`](ref_resolver.py) so an
in-flight engine rename doesn't break the line:

```python
from ref_resolver import resolve

master = resolve(
    engine_root,
    "config/reference/instrument_master.csv",  # new name first
    "config/reference/fund_master.csv",        # fallback during a rename
)
```

## Pinned dependencies

`pyproject.toml` pins the engine to a 40-char SHA (Model C). `/research-line`
stamps the current SHA; `/research-repin` re-resolves it and refreshes the hashes.

## Findings

Results are written **only** via `/finding` →
`findings/YYYY-MM-DD-<verdict>-<slug>.md`. Scratch work lives in `scratch/` and is
deletable at any time.
