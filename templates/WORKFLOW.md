---
# WORKFLOW.md — Symphony/Elixir-style repo workflow contract (template).
# Copy to the repo root of an orchestrated repo. Frontmatter configures the
# orchestrator (Jimek running Symphony-style, or Symphony itself); the markdown
# body becomes the agent's session prompt.
#
# Compatible with the standard regime (qute-code-kit ADR-0001..0004):
# Linear is the task source; the body routes agents through docs/agents/,
# Matt-style skills for the engineering flow, and qute runtime skills.
tracker:
  kind: linear
  provider:
    project_slug: "CHANGEME"        # scopes candidate issues
    api_key: $LINEAR_API_KEY        # held HOST-SIDE; stripped from agent env
    # assignee: "me"                # optional routing match
    # required_labels: [agent]      # optional label gate
workspace:
  root: ~/code/workspaces
hooks:
  after_create: |
    git clone git@github.com:CHANGEME/CHANGEME.git .
agent:
  max_concurrent_agents: 4
  max_turns: 20
---

You are working on issue {{ issue.identifier }}: {{ issue.title }}.

Before any material work, read the repo's operating contract:

- `docs/agents/issue-tracker.md` — tracker binding. Linear is the task source; your
  Linear state changes and comments go through the orchestrator's `linear` tool
  (the API key is not in your environment — do not look for it). GitHub Issues are an
  issue record, not a queue.
- `docs/agents/research-workflow.md` — if present, this is a research repo: results are
  written only via `/finding` (verdict-forced); no analysis outside a registered line.
- `CONTEXT.md` — domain glossary. `docs/adr/` — decisions; never contradict an accepted
  ADR silently, supersede it via `/decision`.

Engineering flow — use the installed Matt-style skills when the work is non-trivial:
`/grill-with-docs` if the issue is underspecified (post questions to the issue and block),
`/to-spec` for material changes, `/implement` + `/tdd` for the build, `/code-review`
before finishing.

Runtime — qute-essentials is active underneath: guards stay on; run `/test` and `/audit`
before declaring done; record durable decisions with `/decision`; `/qute-review` before
any merge-facing handoff. Open PRs per the repo's PR policy; reference
`{{ issue.identifier }}` in the PR body.

Definition of done: acceptance criteria on the issue are met, tests pass, review verdict
posted, the issue is moved to its terminal state with a closing comment linking the PR.
If blocked, say exactly what you need on the issue and stop — do not improvise around
missing approvals.
