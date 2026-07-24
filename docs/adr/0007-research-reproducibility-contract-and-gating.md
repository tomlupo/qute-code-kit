# ADR-0007: Reproducibility contract and gating for research lines

**Status:** Proposed
**Date:** 2026-07-24

## Builds on

[ADR-0002](0002-standard-research-regime.md) — keeps its atoms (line → finding →
generated index), its verdict/status vocabularies, and its skill-not-doctrine
enforcement. ADR-0002 deliberately scoped reproducibility *out* ("`REPRODUCIBILITY.md`
keeps owning reproduced/drifted state separately"). This ADR fills that deferred gap:
it makes reproducibility a **contract the tooling enforces**, not a per-repo `.md`
convention.

## Context

A 2026-07-24 audit of dm-evo-lab (11 research lines) surfaced failures that trace to
one root, and the root is in the regime, not the repo:

**The regime sells the engine SHA pin as the reproducibility contract, but a quant
lab's real dependency surface is `engine SHA + the engine's generated data/config +
freshness`, and only the first edge is pinned or gated.** Model C pins the engine
*Python package* via `git+…@<sha>`. But a quant-package's `data/processed/*.parquet`
and `config/reference/*.csv` are not in the pip package — they are generated / DVC /
gitignored artifacts. So every line reads them from the **live sibling checkout by
filesystem path** (`Path(__file__).parents[N] / "<engine-repo>"`), and a rename or
schema change in the engine's data floats straight through the pin.

Observed consequences in dm-evo-lab:
- A `fund_master.csv → instrument_master.csv` rename in the engine broke **6 scripts**
  regardless of the pin.
- All 11 lines pinned the *same* engine SHA, **498 commits / ~2.3 months** behind the
  engine's default branch, with **no staleness signal**.
- **6 of 11 lines** carry `TBD` provenance while the structural CI gate stays green —
  because the gate (`check_research_pins.py`) validates pin *format* + file existence,
  not provenance completeness or input snapshotting. "Green" ≠ "reproducible".
- Live-data lines (external-API fetches) have no first-class status; the binary
  "reproducible-from-pin OR not" acceptance rule forces an ad-hoc "not promotable" note.

**This is regime-general, not a dm-evo-lab defect.** quantbox-lab — the second repo on
this regime — uses the identical live-sibling-path pattern
(`HERE.parents[2] / "quantbox-datasets" / …`) and will break on the next
`quantbox-datasets` rename in exactly the same way. The vault autonomous pipeline
inherits the same finding schema. A clean-onboarded repo would carry these gaps too.

## Decision

Extend the regime's reproducibility contract from *"pin the engine SHA"* to *"pin the
engine SHA + hash the data it reads"*, and move enforcement from a manual LLM review
into the deterministic gate. Five changes, in dependency order (1 and 2 are the core;
3–5 are follow-ups):

**1. Data-input manifest as a first-class scaffold primitive.**
`research/_template/` ships a `data_inputs.yaml` (and an optional `ref_resolver.py`).
Each line declares the engine files it consumes and their `sha256` at pin time:
```yaml
# research/<line>/data_inputs.yaml
engine: <engine-repo>          # dm-evo, quantbox-datasets, …
inputs:
  - path: config/reference/instrument_master.csv
    sha256: <hash-at-pin>
  - path: data/processed/fund_prices/fund_prices.parquet
    sha256: <hash-at-pin>
```
This makes the data plane part of the contract instead of an unpinned live read.
dm-evo-lab already hand-rolled the resolver half of this (`ref_compat.py`) on one line
to survive the rename; this promotes the proven pattern into the kit so no repo
reinvents it.

**2. Deterministic provenance-on-conclude gate.**
Extend `check_research_pins.py` so that for any line whose README is
`status: concluded`, it additionally asserts: (a) `data_inputs.yaml` exists with
non-null hashes, and (b) the finding/line provenance fields are filled (no `TBD`, no
`snapshot: false`). Pure YAML/regex — no LLM. A line **cannot go green as concluded
while unreproducible**. This is the highest-leverage change: it turns "reproducible"
from a claim into a gate. (Active/paused lines are exempt — live iteration is allowed
to read the sibling; the contract binds at conclusion.)

**3. Ship the two skills the template already promises.**
The `_template` comments reference `scaffold-research` / `freeze-research` skills that
were never built. Ship them:
- `/research-repin <line> [--to <sha|engine-head>]` — edit the pyproject SHA, `uv lock`,
  re-run the `reproduction`-marked tests, refresh `data_inputs` hashes.
- `/research-freeze <line>` — snapshot declared inputs into `<line>/data/` force-added
  past `.gitignore`, record hashes. Freezing becomes one command, not a manual convention.

**4. Pin-staleness in the drift detector.**
Extend `/research-status` (already reports index/verdict/silent-line drift) to run
`git rev-list --count <pin>..<engine-default-branch>` per line and flag anything past a
threshold (commits or days). This is what would have surfaced the 498-commit lag with
zero manual effort. Additive.

**5. Unify provenance into the finding contract + add a reproducibility class.**
Stock finding frontmatter is `evidence: [paths]` with no hashes; consumer repos
(dm-evo) compensated by bolting a separate hash-bearing `report.md` + provenance block
alongside, creating a two-contract tension. Fold provenance into the stock schema — an
optional-but-gated-on-conclude block (`engine_commit`, `data_inputs: [{path, sha256}]`,
`ran_at`) — and add `reproducibility_class: pinned | snapshot-frozen | live-data` to the
line README. One contract; and live-data lines get a first-class honest status instead
of an ad-hoc note.

## Consequences

- (+) A concluded line is reproducible **by construction** — the data plane is hashed
  and gated, not read live-and-hoped.
- (+) Engine renames surface as a hash mismatch at gate time, not a silent runtime break
  weeks later.
- (+) Pin rot is visible (staleness in `/research-status`) and cheap to fix
  (`/research-repin`).
- (+) One provenance contract across lab repos and the vault pipeline; live-data
  research stops being a second-class citizen.
- (−) Migration cost in dm-evo-lab and quantbox-lab: author `data_inputs.yaml` per line,
  backfill hashes, adopt the unified frontmatter. `/research-freeze` + `/research-status`
  drive it, but it is real per-line work.
- (−) Snapshotting inputs adds repo weight (force-added CSVs/parquets). Mitigated by
  scoping to *concluded* lines only; active lines stay live.
- (−) The gate needs a canonical home first (see Rollout).

## Rollout

1. **Give the gate a source of truth.** `check_research_pins.py` currently has **no
   canonical copy in the kit** — it is copy-distributed to consumer repos
   (dm-evo-lab, quantbox-lab) that have already drifted. Land one authoritative copy in
   the kit (under `plugins/qute-essentials/` or `templates/research/`) that
   `setup-qute-repo` stamps, so change #2 is made once, not per repo.
2. Land **1 + 2** (contract + gate) first — they are the core; 3–5 are optional without
   them.
3. Ship **3, 4, 5** as follow-ups; each is independently useful.
4. dm-evo-lab and quantbox-lab pick the changes up on their next `setup-qute-repo`
   re-run — which is also the cleanest way to align those repos, since conformance then
   *inherits* the hardening instead of being hand-patched.

## Open questions

- Staleness threshold default (commits vs days; per-line override in `.research-config.yaml`?).
- Whether `data_inputs.yaml` hashes should be verified against a live sibling at gate
  time (catches drift early, but requires the sibling checkout in CI) or only at
  freeze/conclude time (cheaper, looser).
- Whether the maintainer intentionally kept the gate thin (LLM-reviewer-first) — this
  ADR argues the deterministic floor should be raised, but the reviewer layer stays.
