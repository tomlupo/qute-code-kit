---
name: wtf
description: >-
  Activate when the user expresses frustration, anger, or incredulity at assistant or LLM
  behavior — says "wtf," "are you serious," "you ignored me," "wrong again," "this is useless,"
  or reacts with caps or profanity to output quality. Acknowledges the failure briefly, extracts
  concrete issues, proposes the smallest fix, then records the failure across three guardrail tiers:
  feedback memory (judgment), CLAUDE.md rule (structural), and a hookify rule (deterministic
  enforcement) when the failure is pattern-catchable.
  Triggers: wtf, are you serious, you ignored, wrong again, hallucination, broken, useless, this is wrong.
argument-hint: "[what went wrong]"
---

# /wtf

Handle user frustration by acknowledging the failure, extracting concrete issues, and permanently recording what went wrong to prevent recurrence.

## Step 1: Respond

1. **Acknowledge in one line** — name what failed (wrong output, ignored instruction, hallucination) without minimizing or over-apologizing.
2. **Extract** — reply with 1–3 specific bullets: what was asked, what was delivered instead, what "correct" looks like.
3. **Propose** — offer the smallest concrete next step: one command, one restatement of the constraint, one factual re-check with tools. If the subject is reviewable (code, text, plan), offer `/gbu` once.

**Do not**: long apologies, explaining how LLMs work, arguing the user shouldn't be upset, matching hostility, or padding with reassurances.

## Step 2: Record the failure as a feedback memory

After responding, write a `feedback` type memory to the project's auto-memory system (the memory directory referenced in the system prompt under "auto memory").

File name format: `feedback_<short_slug>.md`

```markdown
---
name: <short label, e.g. "feedback_ignored_constraint">
description: <one-line: what behavior to avoid — used to match future situations>
type: feedback
---

<Clear rule: what to stop doing or always do>

**Why:** <What the user said went wrong in this session>
**How to apply:** <When this rule kicks in — be specific>
```

Then add a pointer line to `MEMORY.md` in the same directory:

```
- [Title](feedback_<slug>.md) — one-line hook
```

If an existing memory already covers the same failure, update it instead of creating a duplicate.

## Step 3: Update CLAUDE.md if warranted

Check if the failure maps to a rule that belongs in the project's `CLAUDE.md`:

- **Add a rule** if: the failure was a repeatable anti-pattern, Claude violated a stated preference, or a specific behavior should always/never happen in this project.
- **Skip** if: the failure was a one-time mistake, pure factual error, or already documented in CLAUDE.md.

If adding, append to the most relevant existing section in CLAUDE.md (or create a `## Conventions` section if none fits). Keep the rule under 2 lines — imperative voice.

## Step 4: Offer a hookify rule if pattern-catchable

Memory and CLAUDE.md are model-side guardrails — both depend on me recalling and applying them. For failures that match a deterministic pattern, a `hookify` rule adds a third tier: the harness blocks or warns regardless of model judgment.

Offer a hookify rule **only if all three hold**:

1. **Tool + input is regex-matchable** — a specific event (`bash`, `file`, `prompt`, `stop`) plus a regex on the command/path/text catches the failure cleanly.
2. **Low false-positive rate** — the regex won't fire on legitimate uses you'd dismiss every time. False positives erode signal until rules get ignored.
3. **High-cost recurrence** — the consequence is bad enough to justify a permanent guardrail.

If any one is false, **stop at memory + CLAUDE.md**. Do not propose hookify for verbosity, tone, missing context, or other model-behavior failures — they aren't pattern-catchable and the rule thicket they create costs more than it saves.

If all three hold, propose the rule and write it at:

- **Project-scoped**: `<project_root>/.claude/hookify.<slug>.local.md` — when the rule applies to one repo
- **User-scoped**: `~/.claude/hookify.<slug>.local.md` — when the rule applies everywhere

Format:

```markdown
---
name: <kebab-case-slug>
enabled: true
event: <bash|file|prompt|stop>
pattern: <python regex>
action: <warn|block>
---

<Short message: what failed last time, what to do instead.>
```

Default to `action: warn` unless the user explicitly wants a hard block. Hookify rules take effect immediately on the next tool call — no restart needed.

**Triage examples:**
- "you ran `rm -rf` without checking the path" → all three hold → **hookify** (`event: bash`, `pattern: rm\s+-rf`, `action: warn`)
- "you edited `/home/prod/` files directly instead of via `sudo -u prod`" → all three hold → **hookify** (`event: file`, pattern matches the prod path)
- "you summarized at the end again" → not pattern-catchable → **memory only**
- "you used the wrong variable name" → too narrow, false-positives → **memory only**
- "you pushed to main without `/ship`" → catchable, but `/ship` already gates this → **CLAUDE.md note only**

## Step 5: Follow-up action

After acknowledging and recording — default to action, not therapy. Choose based on context:

**If there is a concrete technical failure** (wrong output, broken code, failed test, bad plan):
- Do not wait to be re-asked. Immediately move to fix it.
- Re-read the relevant file(s) with fresh eyes, re-run the command, or re-check the logic.
- State what you are doing: "Re-reading X to find what I missed."
- Use `/test` to run tests if the failure involved code.

**If the failure was a violated instruction** (ignored constraint, wrong style, did what was told not to):
- Re-read the relevant section of CLAUDE.md or the user's message.
- Re-execute the task with the constraint applied.
- Do not ask for permission to retry — just do it and show the result.

**If the user only needed to vent** (no actionable technical object):
- One sentence: "Heard — tell me when you want to continue on X."
- Do not offer `/gbu` or debugging if there is nothing concrete to review.

**Never**: ask "what would you like me to do now?" after a `/wtf` — the user already told you what they wanted; do it correctly this time.
