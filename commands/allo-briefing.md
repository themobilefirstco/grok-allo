---
description: Daily Allô briefing — call volume, what needs attention, and follow-ups
argument-hint: "[date range, e.g. today | yesterday | this week]"
---

Give me an Allô phone briefing for: **$ARGUMENTS** (default to today if empty).

Use the `allo` skill. Keep it read-only — take no write actions.

1. Resolve the range to explicit dates and say which range you used.
2. `allo_get_team_analytics` for the range, with the previous equivalent period
   as the comparison, in a single call.
3. Find inbound calls that went unanswered (`direction=INBOUND`,
   `result=VOICEMAIL`) and anything still unread. Count first with `size=1`
   before fetching.
4. Read only the handful that look most consequential.

Report as:

- **Headline** — one or two sentences on how the period went.
- **Volume & answer rate** — with the change vs the comparison period.
- **Needs attention** — unanswered inbound calls and unread conversations worth
  a callback, each with who and why.
- **Notable calls** — anything significant, with attribution.

Flag small samples. Don't invent metrics Allô didn't return. End by offering to
draft follow-up texts — do not send anything.
