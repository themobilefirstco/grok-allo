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
narrowed to callers who took given phone-menu branches, plus optional filters.
Inboxes belong to one person and show in that person's inbox switcher. Talk
about them in business terms ("your Sales inbox", "callers who pressed 1"),
never about sources, node ids or conditions. A user can have at most 50.

**"Set up my inboxes."** Start from `allo_get_inbox_suggestions`. Each
suggestion has a ready `source` (a line, with its menu conditions already
filled in), but not always a name: whole-line suggestions never have one, and
some menu branches don't either. For an unnamed suggestion, name it after its
line (the line's name from `allo_list_numbers`), adding the menu choice for a
branch ("Website FR, pressed 2"), or ask the user what to call it. Show the user
the proposed list with those names, let them drop or rename entries, and
**confirm the final list before creating anything**. Then call
`allo_create_inbox` once per confirmed inbox, with the suggestion's `source` as
its only source, unchanged. Report what was created, and anything that
failed.

**Custom branches** ("only callers who pressed 1 on Website FR"). Find the line
with `allo_list_numbers`, then read its published phone menu with
`allo_list_menu_options`. Match the user's words to an option's `digits` and
`label`. Each option carries a ready `condition`; use it as is. If no option
matches, or more than one does, show the options and ask. Never guess a branch.
If the line has no menu options at all, tell the user that line needs a
published call flow with a phone menu before it can be split by menu choice.

To combine several options on the same line ("1 or 2 on Website FR"), merge
them into **one** condition: take the first option's `condition` and append
the other options' `branches` to its `branches`. Never send two conditions for
the same line's menu; Allo rejects that. Use one source per line.

**Inboxes for a teammate** ("and one for Lucio"). Resolve the teammate with
`allo_list_users` and pass their id as `user_id` on `allo_create_inbox`. Only
admins and managers can do this. Suggestions take no teammate, so for a
teammate either reuse a suggestion's `source` on a line the teammate can
access, or build it: a whole line (empty `conditions`) or a condition from
`allo_list_menu_options`. Every line must be one the teammate can access **and**
sit in a workspace you manage. Lines the teammate has in other workspaces stay
hidden from you and are kept as they are when you edit the inbox; an edit that
leaves no line in a workspace you manage is refused as an invalid source, so
keep at least one. If Allo says a line isn't allowed, the inbox can't include
it. With one source, name that line and offer to leave it
out; with several, the error doesn't say which, so ask the user which lines the
teammate works rather than claiming to know. When the name matches more than
one person, ask which one.

**"Show me my Sales inbox."** Call `allo_list_inboxes`, match the name, and pass
its `inbox_id` to `allo_list_conversations` instead of `allo_number`. The result
already applies the inbox's saved filters, so don't filter again. Unread is not
an inbox filter: never save "unread only" on an inbox. When the user wants
unread conversations, pass `unread` set to true on the listing. Each row
carries `pinned`, so you can say which customers are pinned without another
call. Each row
carries its own `allo_number`: an inbox can span several lines, so to pin,
reply or text from that list, use the row's `allo_number`, never a guess. If no
inbox matches, list the ones that exist rather than falling back to a line. If
an inbox you just created comes back as not found, retry once, and only when
listing its conversations; anywhere else, not found means not found.

**Pin or unpin a customer.** `allo_pin_conversation` and
`allo_unpin_conversation`, with the customer's number and the line. At most 10
conversations can be pinned. When the limit is reached, say so, list what is
pinned and ask which one to unpin. Listing pinned conversations needs a line or
an inbox, so get the lines from `allo_list_numbers` and call
`allo_list_conversations` with `pinned` set to true for each. Never unpin
something on your own to make room.

**Mute or unmute an inbox** ("mute Support"). `allo_update_inbox` with
`notifications_muted`. Muting only silences notifications; the conversations
still arrive.

**When Allo says no:**

- Inbox limit reached (50): say so and ask which inbox they no longer need.
  Never delete one to make room.
- Invalid filters: say which filter didn't work and offer to create the inbox
  without it.
- Invalid source: rebuild it from the suggestion or menu option. Only merge
  branches as described above; never change node_ids or digits.
- An inbox that can't be listed here (Allo says the feature or a contact filter
  isn't supported, or the contact filter is too large): tell the user plainly,
  and suggest opening that inbox in the Allo app.

**Delete an inbox only when the user explicitly asks.** Never as cleanup, never
to "start fresh" during setup. Before deleting, confirm the inbox by name and
whose it is (theirs or a named teammate's), and name the consequence: the inbox
disappears from that person's switcher and its setup is lost. The
conversations themselves stay in Allo. Offer muting as the reversible
alternative.
If deleting a teammate's inbox is refused, the inbox includes lines outside
the user's workspace: explain that, and suggest the teammate deletes it
themselves.

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
