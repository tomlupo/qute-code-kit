---
name: board
description: Linear board identity + write conventions (ADR-0003, qute-platform). Use whenever a session is about to create/update/comment on a Linear issue, or asks "how do I post to the board", "file this on Linear", "comment on TOM-xxx as the agent". Governs WHO authors the write — interactive sessions via the Linear MCP with a [session:] first line; agents/one-shots/crons via linear-post with the Dispatcher app identity — and forbids using Tom's bare identity for automated writes.
---

# Board — Linear write identity conventions

One rule decides everything: **who is writing?**

| Writer | Path | Attribution |
|---|---|---|
| Tom himself | Linear MCP / UI | none — bare authorship IS the attribution |
| Interactive session (Tom present, this session) | Linear MCP (as Tom's user) | first line of the body: `[session: <name-or-cwd>]` |
| Fleet agent, one-shot, cron, any headless run | `linear-post` CLI → Dispatcher app | `[agent: <name>] ` prefix, enforced server-side |

**Invariant this preserves:** a Linear item authored by Tom's user with no
prefix always means Tom typed it. Never post automated content as bare Tom.

## Interactive sessions (the common case here)

Use the Linear MCP tools directly (`save_issue`, `save_comment`, …). Rules:

- Any write the *session* initiates (not dictated verbatim by Tom) starts with
  `[session: <name>]` on its own first line. Derive `<name>` from the session
  name if set, else the cwd basename (e.g. `[session: qute-platform]`).
- When Tom dictates the content and it reads as him ("comment: looks good,
  merging"), post it verbatim — no prefix; that's Tom speaking through a tool.
- Reads need no ceremony — query freely.

## Headless / agent writes

Never use the MCP (it authors as Tom). Use the CLI:

```bash
linear-post --agent coach --issue TOM-123 "note text"      # comment
linear-post --agent quark --team TOM --title "…" -          # new issue, body on stdin
```

It posts via the Dispatcher service (:8002 `/post`) with the app identity;
the `[agent: <name>] ` prefix is added server-side — don't add it yourself.
The surface is deliberately tiny (comment + issue create). If you find
yourself wanting more from it, that's the signal you're in an interactive
context — use the MCP.

## Reference

ADR-0003 in qute-platform (`docs/adr/0003-dispatcher-routes-by-agent-label-
jimek-is-conductor.md`) — Dispatcher routing, app identity, and this split.
