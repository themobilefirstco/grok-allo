---
name: allo-call-flow
description: >-
  Design or edit Allo inbound call flows (IVR / phone menu / ring rules). Use when
  the user wants a phone menu, business-hours routing, ring the team, voicemail,
  forward, or AI receptionist steps in the call flow. Triggers on "call flow",
  "IVR", "phone menu", "press 1 for sales", "ring the team", "inbound routing",
  "missed call handling".
metadata:
  author: Allo
  short-description: Draft inbound call flows and hand off the publish link.
---

# Allo — call flow

Tools: `allo_get_call_flow`, `allo_save_call_flow_draft`. Scope:
`PHONE_NUMBERS_READ` / `PHONE_NUMBERS_WRITE`.

## Product facts

- A call flow is the path after Incoming call: menus, announcements, ring,
  business hours splits, voicemail, forwards, AI receptionist, hang up.
- Call flows may be **beta** and not enabled for every team — if tools 404 or the
  user has no Call flow section, say so.
- In the Allo web designer, Save publishes to the next call. **Over MCP you only
  save a draft** — live routing does not change until a human opens the
  confirmation link and publishes.

## Workflow

1. Resolve `allo_number` via `allo_list_numbers`.
2. `allo_get_call_flow` with `status=draft` (and published if needed) to learn the
   current `definition`, `lock_version`, and shape (camelCase tree rooted at
   `entryNodeId` / `entry_node_id` as returned).
3. Describe the desired journey in plain language and confirm with the user.
4. Build a full `definition` document (do not send a partial tree unless the API
   allows — prefer read-modify-write of the whole draft).
5. `allo_save_call_flow_draft` with `definition`, and pass `lock_version` /
   `base_published_version` when the get response provided them.
6. Always return the `confirmation_url` verbatim and state clearly: **not live
   until they publish in the Allo app**.

## Steps the product supports (for planning with the user)

Incoming call (required root), Phone menu, Play announcement, Ring this line,
Business hours, Contact property, Voicemail, Forward to a number, Forward to
another line, AI receptionist, Go to, Hang up.

Forced branches: Phone menu → No selection; Ring → If missed; Business hours →
Open/Closed; Contact property → Match/No match.

## Safety

- Never claim the flow is live after an MCP save.
- Never invent node schemas — mirror the structure returned by `allo_get_call_flow`.
- If unsure of a field, re-fetch the draft rather than guessing.
