# Research workflow

<!-- Copy to docs/agents/research-workflow.md in a research/lab repo.
     This is the standard research regime (qute-code-kit ADR-0002).
     Skills that enforce it: /research-line, /finding, /research-status, /promote. -->

This repo uses one research regime. Agents: read this before any analysis work.

## The atoms

- **Research line** — `research/<line>/`: a continuous investigation (e.g. `selection`,
  `taa`). Long-lived. Own `pyproject.toml` + lockfile pinned to an engine SHA where
  applicable (Model C). Line status lives in the line's `README.md` frontmatter:
  `status: active | paused | concluded | abandoned | superseded`.
- **Finding** — `research/<line>/findings/YYYY-MM-DD-<verdict>-<slug>.md`: a discrete
  result within a line. Verdict is in the filename and frontmatter:
  `confirmed | refuted | inconclusive | superseded`.
- **Index** — `research/README.md`: generated from line/finding frontmatter by
  `/research-status`. Never hand-edit it.

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
