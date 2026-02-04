---
name: clawdbot-booking-analysis
description: Analyze restaurant/venue booking websites and produce safe, step-by-step automation instructions and API maps. Use for requests like "verify booking flow", "document booking process", or "prepare bot instructions" without finalizing bookings.
---

# Booking Site Analysis (Clawdbot)

## Goals

- Identify the booking flow and required inputs.
- Map API endpoints and request/response shapes.
- Stop before any final booking or payment confirmation.
- Produce a concise instruction set suitable for automation.

## Safety Rules

- Do not submit final booking confirmation or payment.
- If a temporary booking is created, stop immediately and report it.
- Avoid destructive actions and do not cancel unless requested.
- Respect site terms; prefer read-only checks where possible.

## Workflow

1. Confirm scope and stop point.
   - Default stop: availability check or temporary booking only.
   - Ask if the user wants to go further.

2. Identify front-end entry points.
   - Fetch base HTML and locate JS bundles.
   - Extract configuration constants (base URL, API base).

3. Enumerate API endpoints.
   - Search bundles for `/api/` strings and request helpers.
   - List endpoints with method and required fields.

4. Validate with safe live calls.
   - Run `search` or `searchSingleRestaurant` with minimal payloads.
   - Capture any required headers (e.g., `Device-Locale`).
   - If necessary, run `temporaryBooking` only, then stop.

5. Document results.
   - Provide flow diagram in text (search -> availability -> temp -> pre-confirm -> confirm).
   - Include payload shapes and required fields.
   - Call out auth/session requirements and anti-bot hints (if seen).

## Output Template (Markdown)

Use this structure for the final report:

- Summary (1-3 bullets)
- Flow (ordered list)
- Endpoints (table or bullets with method + path + notes)
- Required fields (per step)
- Observed constraints (time windows, min/max guests, etc.)
- Automation notes (headers, cookies, risk points)

## Bundled Resources

- `scripts/safe_probe.py`: Safe HTML/bundle probe and optional availability POST.
- `references/flow-checklist.md`: Minimal checklist to prevent accidental confirmation.

## Tooling Notes

- Prefer `rg` for bundle searches and `curl` for HTML/JS fetches.
- If network access is restricted, request permission before live calls.
- Keep any captured tokens or identifiers out of the output unless necessary.
