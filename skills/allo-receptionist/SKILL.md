---
name: allo-receptionist
description: >-
  Configure and operate the Allo AI receptionist (AI phone agent) that answers
  inbound calls. Use when the user wants to view or change the receptionist's
  instructions, prompt, voice, or settings, take it online/offline, or manage the
  websites it uses as knowledge. Triggers on "AI receptionist", "AI agent",
  "answering service", "take the receptionist offline", "change what the
  receptionist says", "add this website to its knowledge", "change its voice".
metadata:
  author: Allo
  short-description: Manage the AI receptionist's config, status, voice, and knowledge.
---

# Allo — AI receptionist

The receptionist answers inbound calls when the team can't. **Every write here
changes live call handling immediately.** There is no staging step and no undo.
Treat this skill as higher-consequence than anything else in the plugin.

## Tools

| Tool | Effect |
|---|---|
| `allo_get_agent` | Read current configuration |
| `allo_update_agent` | Change configuration |
| `allo_set_agent_prompt` | Replace the instructions |
| `allo_set_agent_status` | Bring online / take offline |
| `allo_list_voices` | Available voices |
| `allo_add_agent_knowledge_website` | Add a site to its knowledge |
| `allo_set_agent_knowledge_website_status` | Enable / disable a source |
| `allo_delete_agent_knowledge` | **Delete a source — destructive, not undoable** |

## Always read before you write

Call `allo_get_agent` first, every time, without exception. It gives you three
things you need: the current values (so you can show a real before/after), the
fields you must not clobber, and the actual state (so you don't "take it offline"
when it's already offline).

Never construct an update from the user's words alone. Start from current
configuration and change only what they asked about.

## Changing the prompt

The prompt is what the receptionist says and how it behaves on real customer
calls. `allo_set_agent_prompt` **replaces** it.

1. Read the current prompt.
2. If the user wants a modification ("also mention our hours", "be more
   concise"), produce the **edited full prompt** based on the current one — do
   not write a fresh prompt from scratch and quietly drop everything that was
   there.
3. Show the change before applying. A diff-style before/after for small edits,
   or the full new prompt for a rewrite.
4. Apply after the user agrees.

If the user asks for a wholesale replacement, confirm that's what they mean —
"this will replace the current instructions entirely" — and show what's being
lost.

## Status changes

`allo_set_agent_status` is one call with an outsized effect. Confirm first, and
make the consequence concrete rather than abstract:

> "Taking the receptionist offline means inbound calls to that line will no
> longer be answered by it. Want me to go ahead?"

Check current status first — if it's already in the requested state, say so
instead of making a redundant write. When bringing it back online, confirm it's
configured (has a prompt and voice) rather than silently enabling an empty agent.

## Voice and configuration

`allo_list_voices` before any voice change — voice identifiers come from that
list, never from the user's description. If they say "something warmer", show
them the available options and let them pick rather than guessing a mapping.

For other configuration via `allo_update_agent`, read the tool schema and change
only the fields in scope. Report what changed in plain language.

## Knowledge sources

The receptionist can draw on websites you add.

- `allo_add_agent_knowledge_website` — adding a site means its content informs
  what the receptionist tells customers. Confirm the exact URL, and flag if it's
  a domain the user may not have meant (a competitor, a staging site).
- `allo_set_agent_knowledge_website_status` — **the reversible lever.** Disabling
  stops a source being used without losing it.
- `allo_delete_agent_knowledge` — permanent.

**Offer disable before delete.** When the user says "remove this" or "stop using
this", that usually means "stop using it", not "destroy it". Ask which they mean:

> "I can disable it — the receptionist stops using it but it stays saved — or
> delete it permanently. Which do you want?"

Before any delete, name the exact source and confirm. Never delete more than one
source in a single confirmation, and never infer which source they meant when
several could match — list the candidates and ask.

## Scopes

Receptionist capabilities depend on the workspace plan and the connection's
granted scopes, and may not be present for every user. Check `allo_get_me` if a
call fails. On an authorization error, say the connection may not have the
required permission and suggest checking workspace permissions or reconnecting —
never expose the underlying authorization detail.

## Reporting

After any change, state plainly what is now true: "The receptionist is offline",
"Its instructions now include your holiday hours", "That knowledge source is
disabled but still saved." The user should never have to re-read the config to
find out what you did.
