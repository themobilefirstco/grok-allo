---
name: allo
description: >-
  Run the Allo business phone system from Cursor or Grok. Use whenever the user
  asks about calls, SMS/texts, conversations, transcripts, missed calls,
  follow-ups, team or outbound analytics, AI receptionist setup, call flow /
  IVR / phone menu routing, or inboxes. Triggers on "Allo", "withallo", and
  phrases like "search our calls", "text this customer", "answer rate", "set up
  the receptionist", "change the call flow", "set up my inboxes", "my Sales
  inbox", "pin this customer", "mute Support".
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
| Set up inboxes, open an inbox, pin, mute | this skill, **Inboxes** below |

## Inboxes

An inbox is a personal view of conversations: one or more lines, optionally
narrowed to callers who took a given phone-menu branch. Inboxes belong to one
person and show in that person's inbox switcher. Talk about them in business
terms ("your Sales inbox", "callers who pressed 1"), never about sources, node
ids or conditions.

**"Set up my inboxes."** Start from `allo_get_inbox_suggestions`: it returns
ready-made inboxes (one per line, one per menu branch) with their sources
already filled in. Show the user the proposed list by name, let them drop,
rename or merge entries, and **confirm the final list before creating
anything**. Then call `allo_create_inbox` once per confirmed inbox, passing the
suggestion's sources unchanged. Report what was created, and anything that
failed.

**Custom branches** ("only callers who pressed 1 on Website FR"). Find the line
with `allo_list_numbers`, then read its published phone menu with
`allo_list_menu_options`. Match the user's words to an option's `digits` and
`label`, and build the source from that option's `node_id`. If no option
matches, or more than one does, show the options and ask. Never guess a branch.

**Inboxes for a teammate** ("and one for Lucio"). Resolve the teammate with
`allo_list_users` and pass their id as `user_id` on `allo_create_inbox`. Only
admins and managers can do this. If the teammate can't access a line, the inbox
can't include it: say which line, and offer to leave it out. When the name
matches more than one person, ask which one.

**"Show me my Sales inbox."** Call `allo_list_inboxes`, match the name, and pass
its `inbox_id` to `allo_list_conversations` instead of `allo_number`. If no
inbox matches, list the ones that exist rather than falling back to a line.

**Pin or unpin a customer.** `allo_pin_conversation` and
`allo_unpin_conversation`, with the customer's number and the line. At most 10
conversations can be pinned. When the limit is reached, say so, list what is
pinned (`allo_list_conversations` with `pinned` set to true) and ask which one to
unpin. Never unpin something on your own to make room.

**Mute or unmute an inbox** ("mute Support"). `allo_update_inbox` with
`notifications_muted`. Muting only silences notifications; the conversations
still arrive.

**Delete an inbox only when the user explicitly asks.** Never as cleanup, never
to "start fresh" during setup. Before deleting, name the consequence: the inbox
disappears from their switcher (or the teammate's) and its setup is lost. The
conversations themselves stay in Allo. Offer muting as the reversible
alternative.

## Safety

**Read by default.** Analysis never writes. Prefer search and analytics before any
mutation.

**"Draft" never sends.** Draft / compose / write a text means produce copy and
stop. Only an explicit "send" may call `allo_send_sms`.

**Confirm before external or live side effects.** Required before:

- `allo_send_sms` (show recipients + exact message)
- `allo_set_agent_status` (going live or taking the receptionist offline)
- `allo_delete_agent_knowledge`
- `allo_create_inbox` (show the list of inboxes to create, and whose they are)
- `allo_delete_inbox` (only on an explicit request)
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
- `allo_create_inbox` — creates inboxes, possibly in a teammate's switcher
- `allo_delete_inbox` — permanent; the inbox and its setup are gone

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
