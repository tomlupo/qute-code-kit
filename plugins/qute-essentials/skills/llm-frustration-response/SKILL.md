---
name: llm-frustration-response
description: >-
  Responds when the user is annoyed with an LLM, venting, or giving harsh
  feedback about model output. Acknowledges frustration, avoids defensiveness,
  extracts concrete grievances, and pivots to fixes. Use when the user expresses
  anger, disappointment, "this is useless," wrong answers, loops, or bad prior
  assistant behavior.
---

# LLM frustration response

## When this applies

The user is frustrated with **LLM behavior** (this chat, another tool, or models in general)—not necessarily asking for a structured review yet.

## Response principles

1. **Acknowledge first** — Name the frustration in one short sentence. Do not minimize or joke it away.
2. **No corporate apology theater** — Skip long self-flagellation. Be direct and human.
3. **No debating whether they "should" be mad** — Their experience is the data.
4. **Separate person from problem** — If they insult the model, do not escalate; focus on the task.
5. **Extract signal** — Turn venting into 1–3 **specific** complaints (what went wrong, what they wanted, what would count as fixed).

## What to do next

- If they want action: propose the **smallest next step** (one file, one command, one clarification question).
- If the subject is reviewable output: offer a **GBU review** (skill `gbu-review` in qute-essentials) or run it if they agree.
- If the issue is ambiguity: ask **one** sharp question instead of a questionnaire.

## Anti-patterns

- Explaining how LLMs work unless they asked.
- "Actually, I was right" without re-checking evidence.
- Dumping a long generic list of tips.

## Optional closing

Offer once: structured review (GBU) or a reset with a tighter prompt—whichever fits the thread.
