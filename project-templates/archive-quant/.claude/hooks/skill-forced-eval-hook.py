#!/usr/bin/env python3
"""
UserPromptSubmit hook that forces explicit skill evaluation.

This hook ensures that Claude evaluates all available skills before proceeding
with implementation, preventing the common mistake of skipping skill activation.
"""

import sys

HOOK_OUTPUT = """
INSTRUCTION: MANDATORY SKILL ACTIVATION SEQUENCE

Step 1 - EVALUATE (do this in your response):
For each skill in <available_skills>, state: [skill-name] - YES/NO - [reason]

Step 2 - ACTIVATE (do this immediately after Step 1):
IF any skills are YES -> Use Skill(skill-name) tool for EACH relevant skill NOW
IF no skills are YES -> State "No skills needed" and proceed

Step 3 - IMPLEMENT:
Only after Step 2 is complete, proceed with implementation.

CRITICAL: You MUST call Skill() tool in Step 2. Do NOT skip to implementation.
The evaluation (Step 1) is WORTHLESS unless you ACTIVATE (Step 2) the skills.

Example of correct sequence:
- research: NO - not a research task
- svelte5-runes: YES - need reactive state
- sveltekit-structure: YES - creating routes

[Then IMMEDIATELY use Skill() tool:]
> Skill(svelte5-runes)
> Skill(sveltekit-structure)

[THEN and ONLY THEN start implementation]
"""

if __name__ == "__main__":
    # Ensure UTF-8 output for cross-platform compatibility
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(HOOK_OUTPUT)
    sys.exit(0)
