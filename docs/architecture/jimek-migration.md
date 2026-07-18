# Jimek migration plan — GitHub verbs move out of qute-essentials

Companion to [ADR-0001](../adr/0001-matt-planning-spine-qute-runtime.md) and
[ADR-0003](../adr/0003-task-tracking-tiers-linear-jimek.md). This is a **relocation, not a
deprecation**: `/qute-coder` and `/qute-reviewer` are how Jimek's agents/workers talk to
GitHub — they belong with the conductor.

## Target split

```text
qute-essentials (stays)          jimek (receives)
  /qute-review  — local-first      /qute-coder       — open PRs as qute-coder[bot]
  /test /audit  — verification     /qute-reviewer    — post qute-review[bot] verdicts
  /ship         — release          jimek-onboard     — repo onboarding (already Jimek-branded)
  /decision     — ADRs             .github/qute-pr.yml — PR policy mapping
  /task         — task-store ops   review-gate CI + pr-flow-guard orchestration
  guards/hooks  — safety           GitHub App token logic (gh-apps creds)
```

Jimek's operating model: reads `jimek.yml`/`jimek.yaml` for *how* to run a declared
agentic workflow; **monitors Linear for assigned tasks** for *what* to pick up (the fleet
board moves from GitHub to Linear). GitHub PR/review posting is one verb family inside
that conductor, not its identity.

## Order

1. Jimek grows the verb family (PR create, review post, gate check) with the same App
   identities and machine-readable output — implemented in the dispatcher/jimek repo,
   not here.
2. The `.github/qute-pr.yml` policy contract and review-gate CI template move with it
   (one unit — skills, policy, and gate are never split across owners).
3. qute-essentials drops `qute-coder`, `qute-reviewer`, `jimek-onboard`, and the
   `pr-flow-guard` hook in a minor-major bump; README stops listing them.
4. Until step 1 exists, **nothing changes**: the skills stay fully supported in qute.
   Do not delete working GitHub-flow pieces before Jimek replacements are proven.
