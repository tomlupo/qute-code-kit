---
description: "Capture an idea to docs/ideas/ and add it to TASKS.md Later section"
---

# /flow:idea

Capture a new idea and file it properly.

## Behavior

When the user invokes `/flow:idea [description]`:

1. **Create the idea file**:
   - Path: `docs/ideas/YYYY-MM-DD-<slug>.md` (date from today, slug from description)
   - Use the template from `${CLAUDE_PLUGIN_ROOT}/templates/idea.md`
   - Fill in the description from the argument, or ask the user if no argument given

2. **Ensure directories exist**:
   ```bash
   mkdir -p docs/ideas
   ```

3. **Update TASKS.md**:
   - If `TASKS.md` doesn't exist, create it from `${CLAUDE_PLUGIN_ROOT}/templates/TASKS.md`
   - Add the idea to the `## Later` section: `- [ ] <description> -> docs/ideas/YYYY-MM-DD-<slug>.md`

4. **Confirm** with the file path and a one-line summary.

## Arguments

- `[description]` — (Optional) Short description of the idea. If omitted, ask the user.
