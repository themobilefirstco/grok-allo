---
name: allo-receptionist
description: >-
  Configure and operate the Allo AI receptionist that answers inbound calls. Use
  when setting up or editing the agent, voice, prompt, hours, transfer rules,
  knowledge websites, calendars, or taking it live/offline. Triggers on "AI
  receptionist", "AI agent", "set up the receptionist", "take it offline",
  "transfer rules", "receptionist knowledge", "change its voice".
metadata:
  author: Allo
  short-description: Set up and manage the AI receptionist.
---

# Allo — AI receptionist

Every write here can change live call handling. Confirm before status changes and
destructive deletes.

## Guides first

If the MCP exposes resources, read them before a full setup:

- `allo-mcp://guides/ai-receptionist-setup`
- `allo-mcp://guides/ai-receptionist-prompt`

## Tool map

| Tool | Role |
|---|---|
| `allo_list_numbers` | Pick the line |
| `allo_get_agent` | Read full config (always before update) |
| `allo_update_agent` | Business details, voice, hours, capabilities, transfer rules, calendars, knowledge text |
| `allo_set_agent_prompt` | Objective / personality / behaviors (and optional sections) |
| `allo_set_agent_status` | `ACTIVE` (answers) vs `FORWARDING` (does not) — high-consequence |
| `allo_list_voices` | Voice catalog |
| `allo_list_calendars` / `allo_get_calendar` | Booking targets |
| `allo_add_agent_knowledge_website` | Add a page to answer from |
| `allo_set_agent_knowledge_website_status` | Disable without delete |
| `allo_delete_agent_knowledge` | Permanent remove — high-consequence |

## Merge rules (critical)

From Allo MCP docs:

- **Scalars merge** — omit a field and it keeps its value (name, voice, greeting…).
- **Collections replace** — `capabilities`, `business_hours`, `transfer_rules`,
  `scheduling.calendars` replace the whole set if sent. Read with `allo_get_agent`
  and send back everything you want to keep.

`allo_set_agent_prompt` replaces the whole prompt — resend every section you are
keeping.

## Setup order

1. Choose `allo_number`.
2. Read current config (`allo_get_agent`).
3. Ask the user for: agent name, language/voice, tone, goal (receptionist /
   support / lead qualify / appointment), when it should pick up, must-ask
   questions, transfer rules, knowledge (site URLs vs pasted facts).
4. Apply `allo_update_agent` then `allo_set_agent_prompt`.
5. Add knowledge websites if they have public pages.
6. Confirm before `allo_set_agent_status=ACTIVE`.

Calendar OAuth connect and document upload stay in the Allo app — say so when
needed; you can still attach already-connected calendars via scheduling maps.

## Transfer rules

Phrase `description` as the **caller's reason** ("billing questions"), not an
instruction to the model. Targets must not loop back to the same receptionist
line.

When asked to remove knowledge: **offer disable before delete** via `allo_set_agent_knowledge_website_status`. Delete with `allo_delete_agent_knowledge` is permanent / not undoable.
