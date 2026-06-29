# engineering/workflow — structured PRD → slice → PR skills

Centralized, reusable engineering-workflow skills. Adapted from
[mattpocock/skills](https://github.com/mattpocock/skills) (engineering set) and
hardened against real failures on dm-evo (2026-06-14). Live in `qute-skills` so any
project consumes them by **symlink** — edit once here, every project gets it.

## The pipeline

```
idea → to-prd → grill → to-slices → triage → tdd → one PR per slice
```

| Skill | Role |
|---|---|
| `to-prd` | synthesize context → PRD (as a tracker epic) |
| `grill` | adversarial one-question-at-a-time stress test |
| `to-slices` | decompose into **file-disjoint** slices (one PR each) |
| `triage` | assign tracker status + dispatch; never parallel-dispatch same-module slices |
| `tdd` | 3 execution variants (deterministic-TDD / methodology-gate / exploratory-spike); merge only on green CI |

## The one rule that matters most

**Slices must touch DISJOINT files.** Sequential work that builds one module = ONE
task, never N slices. Orchestrators auto-advance child slices off bare `dev` (no
branch stacking, no merge-wait), so same-file slices collide — every PR add/add-conflicts.
A 6-slice same-module fan-out became 12 colliding PRs on dm-evo; the 1-task-per-module
redo worked first try. (Full rule in `to-slices/SKILL.md`.)

## Adopting in a new project

1. **Symlink the skills** into the project's `.claude/skills/` (or your `~/.claude/skills/`):
   ```bash
   for s in to-prd grill to-slices triage tdd; do
     ln -sfn "$HOME/workspace/projects/qute-skills/engineering/workflow/$s" \
       "<project>/.claude/skills/$s"
   done
   ```
2. **Provide two project-local binding docs** (the skills reference these, project-relative):
   - `docs/engineering-workflow.md` — the project's master spec (stages, TDD variants,
     gotchas). dm-evo-lab's is the worked reference.
   - `docs/agents/issue-tracker.md` — the **tracker binding** (which tracker, project
     ids, status mapping, dispatch contract). dm-evo-lab binds to Paperclip; another
     project binds to GitHub Issues / Linear / local-md. The skills are tracker-agnostic;
     only this binding is project-specific.

## Provenance

dm-evo reference: `dm-evo-lab/docs/{engineering-workflow,agents/issue-tracker}.md`.
Hard-won lessons banked as feedback memories (`feedback_vertical_slices_disjoint_files`,
`feedback_paperclip_create_needs_policy`).
