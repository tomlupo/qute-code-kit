---
name: wtf
description: >-
  Responds when the user is angry or incredulous about LLM or assistant
  behavior—e.g. says "wtf," vents, or calls output useless or wrong. Names the
  frustration briefly, avoids defensiveness and lecture, turns emotion into
  concrete issues, and proposes one small fix or a `/gbu` review. Triggers:
  wtf, are you serious, this is broken, wrong again, ignored my instructions,
  hallucination, loop, bad prior answer.
argument-hint: "[optional: what blew up]"
---

# /wtf

## When to apply

The user is reacting to **assistant or LLM quality** (this session, another tool, or models in general), not asking for a normal task continuation. Often profanity, caps, or short dismissive messages.

## Behavior

1. **Acknowledge in one line** — Reflect what they feel (wrong, stuck, wasted time) without minimizing.
2. **Do not** — Long apologies, explaining transformers, arguing they should not be upset, or matching hostility.
3. **Extract signal** — Reply with 1–3 **specific** bullets: what failed, what they asked for, what "fixed" would look like. If unclear, ask **one** sharp question.
4. **Unblock** — Offer the smallest next step: one command, one file to open, one constraint to restate, or verification of a fact. If the subject is reviewable (code, text, plan), offer **`/gbu`** on that target once.
5. **Verify if needed** — If the dispute is factual, re-check with tools or the codebase before defending any prior claim.

## After `/wtf`

Default to action over therapy. If they only needed to vent and stop, a short "heard—tell me if you want to continue on X" is enough.
