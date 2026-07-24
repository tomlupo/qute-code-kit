# ADR-0006: qute-essentials ↔ qute-platform contract realignment

**Status:** Accepted
**Date:** 2026-07-24

## Supersedes

[ADR-0005](0005-qute-jimek-boundary-governance-modes.md) — keeps its two governance
modes (standalone / jimek-managed), its tier-is-merge-authority rule (§3), and its
resolved sub-decisions (**independence is a separate reviewing *agent*, not an
identity**; **one review core = Matt base + quant layer**). It **replaces** ADR-0005's
component split (§2), its "board writes via `POST /board/status`" (§7), and its
path-to-target claims that never landed (`qute-coder`/`qute-reviewer` still ship in
essentials; `dispatcher/review.py` was never created). Builds on
[ADR-0001](0001-matt-planning-spine-qute-runtime.md) (Matt spine / qute runtime),
[ADR-0003](0003-task-tracking-tiers-linear-jimek.md),
[ADR-0004](0004-linear-task-source-github-issues-record.md).

## Context

A cross-repo audit (2026-07-24) of qute-essentials (v3.3.0) against qute-platform
(`master`, no `dispatcher/` dir; the dispatcher is now `services/jimek` on `:8002`,
old `:8001` **retired 2026-07-23 per platform ADR-0003**) found the two repos had
drifted off a contract that was never pinned in one place:

- **Two disagreeing board-write contracts.** `board` → `linear-post` → `:8002/post`
  (live); `task`/`setup-qute-repo` → `fleet-track` → `:8001/board/*` (**retired, no
  successor**).
- **A retired review endpoint still selectable.** `qute-reviewer` documents
  `dispatcher` mode + a `:8001/review` auto-probe; only `local` mode works.
- **A "single source" review core that isn't shared.** `qute-review` cites
  `dispatcher/review.py` loading `review-core.md`; that file does not exist and the
  platform reviewer carries a divergent *inlined* prompt.
- **Ownership contradiction.** ADR-0005 declared `qute-coder`/`qute-reviewer` jimek's
  ("don't re-add here"), yet both skills physically ship in the essentials plugin and
  the manifest omits them.
- **`:8001` referenced three ways**, no canonical port map; platform's own CLAUDE.md
  still says "dispatcher — pending migration."

Root cause: the essentials↔platform coupling is real and correct (a portable client
calling infra services over a contract), but the **contract was asserted independently
on both sides**, so both drifted. The fix is not to merge the repos — that only
relocates the drift — but to **pin the contract once and align both sides to it**.

## Decision

### 1. The boundary, in one sentence

> **qute-essentials = portable review/task *methodology* that degrades gracefully with
> no secrets. qute-platform/jimek = the *App identities and gateway* that make agent
> writes and reviews structurally independent/attributable when present.**

Essentials never requires platform to function; platform capabilities are optional
enhancements that light up when their creds/verbs are installed.

### 2. Collapse `qute-review` + `qute-reviewer` → one `qute-review` skill

`qute-reviewer` is **retired** and folded into `qute-review`. The single skill:

- **Independence is session-based** — the review runs in a session separate from the
  author (ADR-0005's resolved sub-decision, reaffirmed). Codex-first, Claude fallback.
  Matt's review skill as the base + a quant layer + house quirks; handles general and
  quant repos.
- `review-core.md` (in `skills/qute-review/`) is the **single methodology source**,
  version-marked (`qute-review-core vN`). Owner: essentials.
- **Final step = post the verdict, degradable:**
  - **qute-review[bot] App verb present** (`~/bin/qute_reviewer_post.sh`, installed by
    platform) → post as the App → independence is *structural* (author ≠ reviewer by
    construction; the review gate passes automatically).
  - **No App** → post via `gh pr review`, tagged `[session: <name>]`. The tag **is** the
    independence marker — author shows `[agent:…]`/human, reviewer shows `[session:…]`,
    and author ≠ reviewer is visible on the PR with no App at all.

The essentials skill cites the **real** reader of `review-core.md`
(`agent-kit/bin/qute_reviewer_post.sh`), never the non-existent `dispatcher/review.py`.

### 3. `qute-coder` leaves essentials → platform/jimek

Its only purpose is "an **agent** opens a PR **as** `qute-coder[bot]`" so the gate has
author ≠ reviewer — pure App transport, agent-only, secret-bearing, with no useful
degraded form (a human/session just runs `gh pr create`; no skill needed). It ships
from jimek alongside its `~/bin` verb and the App creds. The essentials plugin drops
the skill; the manifest `description` is corrected to the actual shipped set.

### 4. Board writes: two lanes, no gateway

The retired `:8001/board/*` rich-field gateway is **not** reinstated.

| Writer | Path | Identity |
|---|---|---|
| **Agents** (fleet / headless / cron) | `linear-post` → `:8002/post` (comment + issue-create) | `[agent: <name>]`, server-stamped |
| **Interactive sessions** | Linear MCP directly | `[session: <name>]` |

`fleet-track`'s **write verbs are retired** (backend gone); it is no longer the agent
board path. `task`/`setup-qute-repo` are repointed to this two-lane model. The prior
"never the raw Linear API" absolute is corrected: *agents* hold no Linear key; *sessions*
use the Linear MCP.

### 5. Tasks stay tiered: TASKS.md for simple repos, Linear recommended

`setup-qute-repo` defaults to Linear; offers TASKS.md for the simple-tool repo type.
`task` auto-detects. When the backend is Linear, the two-lane write contract (§4) applies.

### 6. Provenance rule — one identity tag on every automated write

Every automated write to a shared record carries a leading identity tag. **One
resolution rule, followed by every implementation** (this is the anti-drift keystone):

> `QUTE_AGENT_NAME` set → `[agent: $QUTE_AGENT_NAME]`; otherwise
> `[session: <name-or-cwd-basename>]`.

Enforced structurally on every lane:

| Lane | Enforcement |
|---|---|
| `linear-post` (`:8002/post`) | server-side stamp/validate |
| Linear MCP (sessions) | **essentials `provenance` hook** (below) |
| `gh pr review` / PR create (local) | essentials hook; + verb-injection when the platform App verbs run |

### 7. The provenance hook ships in essentials, toggled by `/guard`

A `PreToolUse` hook on **write** tools (Linear MCP `save_issue`/`save_comment`/
`save_document`/`save_status_update`; `Bash` matching `gh pr (review|comment|create)`).
Behavior: **idempotent auto-inject** — if a valid leading tag is present, no-op; else
prepend the tag per §6's rule. Fail-safe: on unresolved identity inject
`[session: <cwd-basename>]` rather than block. Shipped as a new `provenance` guard in the
existing `/guard` set (lakera, langfuse, secrets, audit, destructive), **on by default**.
Portable and secret-free — closes the one lane server-side stamping can't reach (direct
MCP writes), so no lane relies on convention alone.

### 8. Canonical contract map (single source; platform CLAUDE.md is authoritative)

| Surface | Host:port / endpoint | CLI / verb | Env | Status |
|---|---|---|---|---|
| Dispatcher (`services/jimek`) | `:8002` `/post`, `/linear/webhook`, `/health`, `/sessions`, `/agents` | `linear-post` | `DISPATCHER_POST_URL`, `JIMEK_ENV`→`JIMEK_SHARED_TOKEN` | current |
| api-bridge gateway | `:8080` | — | — | current |
| api-bridge MCP | `:8200` → `https://bridge.qute.tech/mcp` | — | — | current |
| Independent review post | (GitHub, no port) | `~/bin/qute_reviewer_post.sh` (`local` mode) | `QUTE_GH_APPS_DIR`, `QUTE_REVIEW_MODE=local`, `QUTE_REVIEW_CORE` | current |
| Bot PR author | (GitHub, no port) | `~/bin/qute_coder_pr.sh` / `qute_coder_flow.sh` | `QUTE_GH_APPS_DIR`, `QUTE_ASSIGN_TO` | current (jimek) |
| ~~Old dispatcher~~ | ~~`:8001` `/board/*`, `/review`, `/sessions/*`~~ | ~~`fleet-track` writes~~ | — | **RETIRED 2026-07-23** |

Essentials skills **reference** this map; they do not re-assert ports. Every `:8001`
mention in both repos is purged except the ADR-0003 tombstone.

## Consequences

- **Essentials skill set:** `qute-review` (absorbs `qute-reviewer`), `board`, `task`,
  `setup-qute-repo`, guards (+ `provenance`) stay; `qute-reviewer` retired; `qute-coder`
  leaves. Requires a minor/major plugin bump (a skill is removed).
- **Two identity-tag implementations** (essentials hook + platform verbs) must both obey
  §6's one rule — specified here so they agree by construction, not by luck.
- **review-core sync:** platform's reviewer must *load* `review-core.md` (env > checkout >
  embedded fallback) instead of an inlined copy; if an embedded fallback is kept, a CI
  drift-check on the version marker is required.
- **`review-core.md`'s last line must stay exactly** `BLOCKER if something must change
  before merge.` — jimek uses it as a transcript-scrub sentinel.
- Platform CLAUDE.md, the `:8001` agent-kit rules (`agent-comms`, `session-lifecycle`,
  `pr-identity`), and the orphaned `dispatcher*.service` units are corrected/removed.

## Path to target state

1. **This ADR + canonical map.** (done)
2. **Essentials:** collapse `qute-review`; remove `qute-coder`; repoint `task`/
   `setup-qute-repo`; add the `provenance` hook + guard; fix the manifest; purge `:8001`.
3. **Platform (source-only, no deploy until tested):** correct CLAUDE.md + the canonical
   map; add the shared identity resolver and wire `linear-post`/`qute_coder`/
   `qute_reviewer` to it; make the reviewer load `review-core.md`; retire `fleet-track`
   write verbs; delete orphaned `:8001` units/rules; land the `qute-coder` skill in jimek.
4. **Verify:** review-gate green on a test PR in each mode (App present / App absent);
   confirm `[agent:]`/`[session:]` tags land on all lanes.

Steps 3–4 touch token-minting / review-posting infra — implemented as source, **not
deployed**; test against live App creds before `install-runtime.sh`.
