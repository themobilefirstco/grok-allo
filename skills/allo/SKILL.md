---
name: allo
description: >-
  Run the Allo business phone system from Cursor or Grok. Use whenever the user
  asks about calls, SMS/texts, conversations, transcripts, missed calls,
  follow-ups, team or outbound analytics, AI receptionist setup, or call flow /
  IVR / phone menu routing. Triggers on "Allo", "withallo", and phrases like
  "search our calls", "text this customer", "answer rate", "set up the
  receptionist", "change the call flow".
metadata:
  author: Allo
  short-description: Search calls, send SMS, check analytics, set up receptionist and call flows.
---

# Allo

Allo is a business phone system. This plugin connects to the hosted Allo MCP at
`https://mcp.withallo.com/mcp`. Translate business outcomes into the right tools;
never invent tool names or parameters — read each tool schema before calling.

## The one rule that matters most

**Never tell a normal user to invoke a tool by name.** They say "what's happening
with our calls?", not "call allo_search_conversation_items". Answer in business
language.

## Start here

Call `allo_get_me` once per session before the first real Allo operation. It
returns scopes, team, and endpoints. Adapt to what this connection can do.

Then pick the focused skill:

| User wants… | Skill |
|---|---|
| Find / read calls, SMS, transcripts, missed calls, tags | `allo-search` |
| Draft or send a text | `allo-sms` |
| Answer rate, dials, funnel, leaderboard, talk time | `allo-analytics` |
| Configure or go live with the AI receptionist | `allo-receptionist` |
| Phone menu, ring rules, IVR, inbound routing | `allo-call-flow` |

## Safety

**Read by default.** Analysis never writes. Prefer search and analytics before any
mutation.

**"Draft" never sends.** Draft / compose / write a text means produce copy and
stop. Only an explicit "send" may call `allo_send_sms`.

**Confirm before external or live side effects.** Required before:

- `allo_send_sms` (show recipients + exact message)
- `allo_set_agent_status` (going live or taking the receptionist offline)
- `allo_delete_agent_knowledge`
- Bulk tagging, queue appends, prompt/config replaces
- Publishing implications for call flows (MCP only saves a **draft**)

**Bulk action protocol:** filter → **validate** the set → **summarize** → confirm →
execute → **report exactly what happened**, including failures.

**E.164** for every phone number (`+14155551234`). Use `allo_list_numbers` before
sending SMS to pick a line with SMS capability.

**No invented data.** Empty results stay empty. Metrics Allo does not return are
unavailable, never estimated.

**No secrets.** Never print API keys, tokens, or Authorization headers.

## High-consequence tools (always name the consequence)

- `allo_send_sms` — outbound customer text
- `allo_set_agent_status` — changes live call answering
- `allo_delete_agent_knowledge` — permanent

## Resources the MCP ships

For receptionist setup, read MCP resources when available:

- `allo-mcp://guides/ai-receptionist-setup`
- `allo-mcp://guides/ai-receptionist-prompt`


## Core tools this plugin orchestrates

Mentioned so routing stays concrete (still never tell the user to type these):

- `allo_get_me`
- `allo_search_conversation_items`
- `allo_send_sms`
- `allo_get_team_analytics`
- `allo_set_agent_status`
- `allo_list_tags` — use tag **keys**, not display names

## Errors

Speak plainly when something fails:

- **Authorization error** — missing scope; say what they can still do
- **No results** — empty is empty; do not invent rows
- **Unsupported operation** — capability or plan limit
- **Rate limit** — pause and retry; do not hammer

Never expose Authorization headers, tokens, or API keys.
Never fabricate results.
Do not fabricate metrics, contacts, or transcripts.
