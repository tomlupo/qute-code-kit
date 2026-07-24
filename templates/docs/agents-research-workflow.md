# Research workflow

<!-- Copy to docs/agents/research-workflow.md in a research/lab repo.
     This is the standard research regime (qute-code-kit ADR-0002).
     Skills that enforce it: /research-line, /finding, /research-status, /promote. -->

This repo uses one research regime. Agents: read this before any analysis work.

## The atoms

- **Research line** — `research/<line>/`: a continuous investigation (e.g. `selection`,
  `taa`). Long-lived. Own `pyproject.toml` + lockfile pinned to an engine SHA where
  applicable (Model C). Line status lives in the line's `README.md` frontmatter:
  `status: active | paused | concluded | abandoned | superseded`, plus a
  `reproducibility_class` (see below) that the gate enforces on conclude.
- **Finding** — `research/<line>/findings/YYYY-MM-DD-<verdict>-<slug>.md`: a discrete
  result within a line. Verdict is in the filename and frontmatter:
  `confirmed | refuted | inconclusive | superseded`.
- **Index** — `research/README.md`: generated from line/finding frontmatter by
  `/research-status`. Never hand-edit it.

## Reproducibility contract (ADR-0007)

The engine SHA pin freezes the engine *package*. It does **not** freeze the
engine's generated `data/processed/*.parquet` or `config/reference/*.csv` — a lab
reads those live from the sibling checkout by path, so a rename or schema change
floats straight through the pin. Every line therefore declares a
`reproducibility_class` and (where applicable) a hashed data manifest.

Set `reproducibility_class` in the line README frontmatter to one of four classes.
The gate (`check_research_pins.py`) enforces the "gate on conclude" column only at
`status: concluded` — active/paused lines iterate live; the contract binds at
conclusion.

| Class | When to use | Gate on conclude |
|---|---|---|
| `pinned` | Default. Reproducible from the engine SHA + hashed data inputs. | `data_inputs.yaml` present with a non-null 64-hex `sha256` on every input, **and** the `provenance` block filled (no `TBD`). |
| `snapshot-frozen` | Inputs can't be re-derived, so they're force-added into the line's `data/` and hashed. | Snapshot input files present under the line **and** a `sha256` for each in `data_inputs.yaml`. |
| `live-data` | Reads an external API / live feed that can't be pinned. | Class set **and** a non-empty `repro_note` explaining why it can't be pinned. |
| `historical` | Concluded before the contract; inputs no longer recoverable. | Class set **and** a `repro_note` documenting the gap honestly. |

Never fabricate hashes for a `historical`/`live-data` line — an honest `repro_note`
is the intended status, not a green-by-pretending one.

The `pinned`/`snapshot-frozen` data plane lives in
[`data_inputs.yaml`](../../research/_template/data_inputs.yaml) (filled by
`/research-freeze` or by hand at conclude); read engine reference data through the
line's `ref_resolver.py` so an in-flight engine rename doesn't break it.

## Finding frontmatter

```yaml
---
line: <line-name>
date: YYYY-MM-DD
verdict: confirmed | refuted | inconclusive | superseded
question: "One sentence: what was tested"
evidence: [path/to/config.yaml, path/to/repro.py, path/to/results.parquet]
# optional gate metrics (autonomous pipeline + serious backtests)
backtest_sharpe: null
dsr_pvalue: null
correlation_max: null
# optional provenance — GATED on conclude for `pinned` lines (ADR-0007). One
# contract: no separate hash-bearing report.md alongside.
provenance:
  engine_commit: <40-hex engine SHA>       # what the result was produced against
  data_inputs: [{path: config/reference/x.csv, sha256: <64-hex>}]
  ran_at: YYYY-MM-DD
repro_note: null    # required instead of hashes for historical / live-data
promoted_to: null   # ADR / PR / wiki slug once promoted
---
```

## Rules of engagement

1. **No analysis outside a registered line.** Start or resume with `/research-line <name>`
   — it stamps from `research/_template/` and registers the line. Scratch work lives only
   in `<line>/scratch/`, and is deletable at any time.
2. **Results are written only via `/finding`.** It forces a verdict and updates the line
   rollup + root index in the same action. No loose dated `.md` files in the line root;
   no `SESSION_*.md`; no parallel `FINDINGS.md` variants.
3. **Every line ends.** Abandoning is fine — record it (`status: abandoned`, or a final
   `inconclusive` finding). Abandoning silently is how research gets lost.
4. **Ideas go to the tracker** declared in `docs/agents/issue-tracker.md` — never to
   `RESEARCH_IDEAS.md`, `research-topics.md`, or notes inside line dirs.
5. **Deliverables are not research.** Audience-facing outputs (decks, one-pagers,
   dashboards, one-off analyses) go to `reports/<YYYY-MM-DD-slug or topic>/`, dated.
   Machine run outputs go to `artifacts/`. App prototypes graduate to their own repo.
6. **Promotion is explicit.** A confirmed, material finding goes through `/promote`:
   ADR in `docs/adr/` + production PR (or wiki concept / plugin), and the finding's
   `promoted_to` is filled.

## Health

`/research-status` is the drift detector: index vs. dirs mismatch, lines silent for
N weeks, loose dated files, missing verdicts, non-research dirs under `research/`.
Run it when you feel lost; trust its regenerated index over memory.
