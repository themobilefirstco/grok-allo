---
name: allo-sms
description: >-
  Draft or send SMS from Allo business numbers. Use when the user wants to text a
  contact, follow up after a call, send a reminder, or mass-text from an Allo
  line or Sender ID. Triggers on "send SMS", "text them", "follow-up text",
  "message this number", "draft a text".
metadata:
  author: Allo
  short-description: Draft and send SMS from Allo lines.
---

# Allo — SMS

Tool: `allo_send_sms`. Supporting: `allo_list_numbers`, and search skills to find
the contact number.

## Draft vs send

- **Draft / compose / write** → produce the message text, show who it would go to,
  and **stop**. Do not call `allo_send_sms`.
- **Send / text them now** → confirm recipients + exact body, then call
  `allo_send_sms`.

`allo_send_sms` is high-consequence outbound messaging.

## Before sending

1. Resolve the **from** line: `allo_list_numbers` and pick one with SMS (or a
   Sender ID). Use exactly one of `allo_number` or `allo_sender_id`.
2. Resolve **to** in **E.164** (`+14155551234`). Fix local formats; never guess a
   country code silently — ask if ambiguous.
3. Show the user: from, to (and name if known), full message body.
4. On confirm, send once. Report delivered/queued or the error.

## Limits and product facts (from Allo docs)

- Business plan required to **send**; receiving is free on every plan.
- Country support for send/receive includes US, CA, FR, UK, BE; MMS mainly US/CA.
- Daily segment limits apply (trial vs paid). Long texts use multiple segments.
- French numbers may need a Sender ID for automated messages; US/CA often need
  10DLC registration before first send — if send fails with registration errors,
  say so plainly and point them to Allo number SMS settings.

## Bulk

Never blast a list without confirming the full recipient set and the single
message (or per-recipient drafts). Protocol: validate numbers → summarize count →
confirm → send → report successes and failures.
