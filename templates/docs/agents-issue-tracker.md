# Tracker binding

<!-- Copy to docs/agents/issue-tracker.md. This file follows Matt Pocock's
     setup-matt-pocock-skills convention: skills (his and qute's) read it to know
     where work lives. The HTML marker below is the machine-readable declaration —
     qute's pulse.sh engine routes on it; the prose is for agents and humans.

     Marker forms (keep exactly one):
       <!-- qute-tracker: linear team=ABC -->
       <!-- qute-tracker: github -->
       <!-- qute-tracker: tasks-md -->
-->

<!-- qute-tracker: linear team=CHANGEME -->

## Task source — Linear

**Linear is the task source** (qute-code-kit ADR-0004): all work items — tasks, planning,
priority, agent assignment — live in Linear (team `CHANGEME`). Jimek monitors Linear for
assigned tasks; `jimek.yml` declares how declared workflows run. Humans and agents pull
work from Linear only.

- Auth: `LINEAR_API_KEY` env var (personal API key).
- qute `/task` and `/repo-status` route here automatically via the marker above.

## GitHub Issues — issue record only

GitHub Issues on this repo track **issues, not tasks**: bugs, defects, technical debt
attached to the code. An issue becomes work only when a Linear task references it
("fix issue #X"). Never pull work from the Issues list directly. File records with
`/task ... --to github`.

## Ideas

Ideas go to Linear (label `research` for research ideas) — never to `RESEARCH_IDEAS.md`,
session notes, or files inside the repo tree.

<!-- For simple repos: replace the marker with `qute-tracker: tasks-md` and delete the
     Linear/GitHub sections — the TASKS.md checklist is then the task source. -->
