---
name: llm-external-review
description: Get second opinions from external AI models (Codex, Gemini) via their CLIs. Use for code review, architecture review, debugging help, or brainstorming. Triggers - "ask codex", "ask gemini", "get a second opinion", "external review".
allowed-tools: Read, Glob, Grep, Task
---

# External LLM Review

Get a second opinion from Codex or Gemini. You gather context from the codebase, formulate a thorough question, then delegate the CLI call to a subagent.

Your job is to be an excellent *questioner* — gather thorough context and ask precise questions so the external model can give its best answer.

## When to Use Which Model

| Use case | Model | Why |
|----------|-------|-----|
| Code review, debugging, bug hunting | **Codex** | Purpose-built for code tasks |
| Architecture, design review | **Gemini** | Large context window, strong reasoning |
| Brainstorming, exploring alternatives | **Gemini** | Good at divergent thinking |
| Want two perspectives | **Both** | Run each, compare answers |

## Workflow

### Phase 1: Gather context

Use Read, Glob, and Grep to collect everything the external model will need. It cannot see your files — you must include all relevant code, configs, and patterns inline in the question.

- Read the files under discussion
- Grep for related patterns, callers, or usages
- Glob to find related test files, configs, or types

### Phase 2: Formulate the question

Compose a self-contained question with all code and context inline. Follow the "Writing Effective Questions" guidelines below.

### Phase 3: Invoke the external model

Delegate the CLI call to a Task subagent. Do not run shell commands directly.

**Codex:**

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: "Write the following question to /tmp/question.txt, then run: cat /tmp/question.txt | codex exec -o /tmp/reply.txt --full-auto. Return the full contents of /tmp/reply.txt.\n\nQuestion:\n<the question>",
  description: "Run Codex CLI"
)
```

**Gemini:**

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: "Write the following question to /tmp/question.txt, then run: gemini \"$(cat /tmp/question.txt)\" > /tmp/reply.txt. Return the full contents of /tmp/reply.txt.\n\nQuestion:\n<the question>",
  description: "Run Gemini CLI"
)
```

### Phase 4: Present findings

Read the subagent's response and present it to the user in this format:

- **Model used:** Codex / Gemini
- **Question summary:** one-line summary of what was asked
- **External model's response:** the full response, unedited
- **Follow-up suggestions:** if the response was vague or incomplete, suggest how to refine the question

Do not editorialize or substitute your own analysis for the external model's response.

## Writing Effective Questions

**Include complete code.** Don't say "review my function" — paste the actual code. External models can't see your files.

**State the specific problem.** "This crashes on empty input" is better than "please review."

**Add constraints.** "We need to support Python 3.8+" or "This runs in a Lambda with 128MB RAM" helps the model give relevant advice.

**Include the spec.** If you're implementing an algorithm or protocol, paste the relevant spec section.

**Be direct about what you want.** "Find bugs", "suggest a better data structure", "is this thread-safe?" — specific questions get specific answers.

## CLI Reference

### Codex
- Install: `npm i -g @openai/codex`
- Auth: `codex login`
- `--full-auto` lets it run without prompts
- Pipe the question via stdin, capture output with `-o`
- Good at: precise code analysis, finding bugs, suggesting fixes

### Gemini
- Install: https://github.com/google-gemini/gemini-cli
- Auth: `gemini /auth`
- Pass the question content as a CLI argument
- Good at: big-picture analysis, long documents, architectural reasoning

## Practical Tips

- **Iterate.** If the first answer is vague, gather more context and write a follow-up question referencing the previous reply.
- **Compare models.** Run the same question through both Codex and Gemini, then synthesize.

## If a CLI Is Not Installed

Tell the user how to install it. Do NOT fall back to doing the review yourself — the point is to get a different model's perspective.

- **Codex**: `npm i -g @openai/codex`, then `codex login`
- **Gemini**: Install from https://github.com/google-gemini/gemini-cli, then `gemini /auth`

## Remember

You are Claude. This skill exists to get opinions from OTHER AI models. Do not substitute your own review.
