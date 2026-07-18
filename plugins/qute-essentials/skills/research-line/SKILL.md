---
name: research-line
description: >-
  Open, resume, or register a research line under research/<line>/ per the standard research
  regime (lines + dated findings + generated index). Use when starting a new investigation,
  resuming an unregistered one, or when the user says "new research line", "start researching X",
  "open a line for X". Stamps from research/_template/ when present, sets line README frontmatter
  (status: active), and refuses to let analysis start in an unregistered directory.
argument-hint: "<line-name> [--one-off] [--question \"...\"]"
---

# /research-line

Open or resume a research line. The line is the atom of continuous research; findings
accumulate inside it via `/finding`.

## Behavior

1. **Load the regime.** Read `docs/agents/research-workflow.md` if present — it is the
   repo's contract and wins over this skill's defaults. If absent, offer to stamp it from
   the qute-code-kit template before proceeding.
2. **Locate or create** `research/<line-name>/`:
   - Exists and registered → resume: report line status, last finding, open tracker items.
   - Exists but unregistered (no README frontmatter) → register it: add frontmatter
     (`status: active`, `question`, `started`), create `findings/` and `scratch/` if missing.
   - New → stamp from `research/_template/` when present (else minimal: `README.md`,
     `findings/`, `scratch/`, `.gitignore`). Per-line `pyproject.toml` + engine pin when
     the repo uses Model C (detect from sibling lines).
3. **Line README frontmatter** (the index is generated from this — keep it accurate):

   ```yaml
   ---
   line: <line-name>
   status: active   # active | paused | concluded | abandoned | superseded
   question: "One sentence: what this line investigates"
   started: YYYY-MM-DD
   tracker: <issue/task ref, e.g. LIN-123 or #45>
   ---
   ```

4. **Link the tracker.** Check `docs/agents/issue-tracker.md`; if the line has no tracker
   ref, offer to create one via `/task` (or record the existing Linear/GitHub ref).
5. **`--one-off`** (production repos): route to `reports/YYYY-MM-DD-<line-name>/` instead —
   one-off analyses are deliverables, not lines. Say so explicitly.
6. **Report**: line path, status, and the rule reminder — *results are written only via
   `/finding`; scratch lives in `<line>/scratch/` and is deletable.*

## Refusals

- Analysis requested in a dir under `research/` with no line registration → register first
  (one command, no ceremony), don't just proceed.
- A new line whose `question` duplicates an existing line's → point at the existing line
  and its findings before opening a duplicate.
