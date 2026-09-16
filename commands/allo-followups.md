---
description: Find Allô calls that still need a follow-up
argument-hint: "[date range, e.g. yesterday | this week]"
---

Find the calls in my Allô workspace that still need a follow-up for:
**$ARGUMENTS** (default to the last 7 days if empty).

Use the `allo` and `allo-call-intelligence` skills. This is **read-only** —
do not send, tag, or mark anything.

1. Resolve the date range explicitly.
2. Find candidates: inbound calls that went to voicemail, and unread
   conversations. Count before fetching.
3. For each candidate contact, check with a `contact_number` search whether a
   later outbound call or SMS already handled it. Exclude the handled ones.
4. Read summaries for the remainder to judge what the follow-up is about.

Present a prioritized list: contact, when they called, what they appear to want,
and why it's still open. Put the most time-sensitive first, and say how you
judged priority.

Then offer next steps — drafting texts or tagging the set — but take no action
until I say so.
