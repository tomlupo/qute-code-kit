# Tracker binding

<!-- qute-tracker: linear team=TOM -->

## Task source — Linear

**Linear is the task source** (ADR-0004): all work items — tasks, planning,
priority, agent assignment — live in Linear (team `TOM`). Jimek monitors Linear for
assigned tasks; `conductor.yml` (stamped by `/setup-qute-repo` Step 4) declares how
work runs in Jimek-managed repos. Humans and agents pull work from Linear only.

- Auth: `LINEAR_API_KEY` env var (personal API key) — interactive/local sessions only.
- qute `/task` and `/repo-status` route here automatically via the marker above.
- **Orchestrated workspaces** (Jimek / Symphony-Elixir style): the API key is held
  host-side and stripped from your environment by design — use the orchestrator's
  advertised `linear` tool for state changes and comments, not the qute backend.

## GitHub Issues — issue record only

GitHub Issues on this repo track **issues, not tasks**: bugs, defects, technical debt
attached to the code. An issue becomes work only when a Linear task references it
("fix issue #X"). Never pull work from the Issues list directly. File records with
`/task ... --to github`.

## Specs and plans

Specs, PRDs and ticket breakdowns live **in Linear**, not in the repo tree. Nothing
under `docs/specs/` is committed.

Treat that as the rule, not as something a tool will catch for you. `/ship` does
carry a forbidden-paths check covering `docs/specs/`, and it now runs before mode
dispatch so plugin-mode repos (this one included) get it too — but it is a
backstop that fires at release time, long after the artefact was written and
reviewed. The tree stays clean because the artefacts are never written into it,
which is why the rule is stated here rather than left to enforcement.

## Ideas

Ideas go to Linear (label `research` for research ideas) — never to `RESEARCH_IDEAS.md`,
session notes, or files inside the repo tree.
