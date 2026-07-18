# Proposed-DELETE inventory — `agent:*` labels (ov#177 WAVE-3, step 6)

**Status: PROPOSED. Nothing deleted. Needs Tom's list-approval — the BUILD green-light does not cover the irreversible label delete.**

> ⚠️ **Correction vs. first pass.** My initial analysis (run against a locally
> checked-out tree that was 26 commits behind `origin/master`) concluded the
> `agent:*` label had exactly ONE runtime consumer. The independent review of
> PR #69 caught that current `master` added a SECOND consumer. The inventory
> below reflects the corrected, up-to-date picture.

## The two runtime uses of the `agent:*` label (current master)

1. **Owner seed** (board Agent field) — concern-G board-sync set the board Agent
   field from the first `agent:<x>` label on newly-added issues. **RETIRED by
   PR #69.** After #69 lands+syncs, owner comes from the board Agent field
   (`gh-track assign`), never a label.
2. **dm-evo admission gate** (`BS_REQUIRE_AGENT_REPOS`, default `dm-evo`) — on
   require-agent repos, board-sync auto-adds an issue **only if it carries an
   `agent:<name>` label**, keeping codex-authored dm-evo analysis notes off
   Quark's triage queue. **KEPT by PR #69** — it is a distinct anti-pollution
   feature, not owner tracking. Its comment records that author-based and
   `standalone`-based filters were already tried and rejected.

## What this means for the delete

| Repo | Label | Open | All | Safe to delete after #69 lands+syncs? |
|---|---|---:|---:|---|
| quantbox | `agent:quark` | 3 | 15 | ✅ yes (not a require-agent repo) |
| quantbox-live | `agent:quark` | 0 | 8 | ✅ yes |
| qute-platform | `agent:quark` | 0 | 1 | ✅ yes |
| obsidian-vaults | `agent:quark` | 7 | 29 | ✅ yes |
| obsidian-vaults | `agent:coach` | 1 | 2 | ✅ yes |
| obsidian-vaults | `agent:iris` | 0 | 1 | ✅ yes |
| **dm-evo** | **`agent:quark`** | **2** | **7** | ❌ **BLOCKED** — still the dm-evo admission gate |

7 labels / 5 repos. No `agent:*` labels on atlas, quantbox-datasets,
quantbox-lab, dm-evo-lab, dm-evo-apps, formcheck, qute-code-kit.

## 🚩 DECISION NEEDED (quark → Tom) — the dm-evo admission gate

To delete `agent:quark` on **dm-evo**, its board-admission filter must first be
re-mechanized off the label. Options:

- **(A) — RECOMMENDED. Require a TYPE label instead of `agent:*`.** PR #61 adds a
  TYPE taxonomy (feature/fix/infra/refactor/research/docs/chore) applied by the
  `task` verb. Genuine dm-evo fleet tasks created via `task` carry a TYPE label;
  codex analysis notes don't. Swap `BS_REQUIRE_AGENT_REPOS` to gate on
  "has any TYPE label". Design-aligned with #177; couples to #61 landing +
  backfilling TYPE labels on the 2 open dm-evo tagged issues.
- **(B) Keep `agent:quark` on dm-evo only.** Delete the other 6 labels now; leave
  dm-evo's as the admission signal. Cheapest; leaves one `agent:*` label alive.
- **(C) Author/allowlist filter.** Skip issues authored by the dm-evo-tactical
  job. Rejected once already (notes are authored as tomlupo) — not recommended.

**I did NOT guess a replacement — flagging per the "stop on ambiguity" rule.**

## Pre-delete safety checklist (for the ✅ rows)

1. PR #69 merged **and** re-synced to core (bin-extras deploy path), one live
   tick observed reading the Agent field.
2. For the 13 currently-open tagged issues, confirm the board **Agent field** is
   set (via `gh-track assign`) so no owner signal is lost in the window.
3. Tom signs off on this exact list.

Deleting a label does not close/alter its issues — it only removes the tag; the
board Agent field is unaffected.

## Proposed delete commands (per approved row, DO NOT run yet)

```bash
gh label delete "agent:quark" --repo tomlupo/quantbox --yes
gh label delete "agent:quark" --repo tomlupo/quantbox-live --yes
gh label delete "agent:quark" --repo tomlupo/qute-platform --yes
gh label delete "agent:quark" --repo tomlupo/obsidian-vaults --yes
gh label delete "agent:coach" --repo tomlupo/obsidian-vaults --yes
gh label delete "agent:iris"  --repo tomlupo/obsidian-vaults --yes
# dm-evo: HELD pending the admission-gate decision above.
```
