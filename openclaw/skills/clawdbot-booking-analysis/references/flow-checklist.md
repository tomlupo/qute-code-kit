# Booking Flow Checklist (Safe)

Use this checklist to avoid accidental confirmations.

1. Scope lock
   - Confirm stop point: availability or temporary booking only.
   - Note if login is required for any step.

2. Site entry points
   - Base HTML and bundle list collected.
   - Config/constants extracted (base URL, API base).

3. Endpoint map
   - Search endpoints for availability.
   - Identify temp booking, pre-confirm, confirm.
   - Identify payment URLs (if any).

4. Safe live calls
   - Search or availability request run with minimal payload.
   - Verify required headers (locale, auth).
   - If temp booking created, stop and report.

5. Output
   - Flow ordering captured.
   - Required fields per step listed.
   - Risks and stop conditions stated.
