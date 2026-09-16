---
name: allo-search
description: >-
  Search Allo conversations, calls, SMS, and transcripts. Use when the user wants
  to find specific calls, missed calls, unread threads, keyword hits in
  transcripts, contact history, or to tag / mark conversations. Triggers on
  "search calls", "find conversations", "missed calls", "what did they say",
  "calls tagged", "unread", "last call with".
metadata:
  author: Allo
  short-description: Search and read calls, SMS, and transcripts.
---

# Allo — search conversations

Primary tools: `allo_search_conversation_items`, `allo_list_conversations`,
`allo_get_conversation_item`, `allo_batch_get_conversation_items`,
`allo_mark_conversation`, `allo_list_tags`, `allo_add_call_tags`,
`allo_remove_call_tag`.

## Core loop

1. **Narrow** with `allo_search_conversation_items` (filters + optional keyword).
2. Count first: `size=1` and read `pagination.total_count` before fetching pages.
3. Fetch a small page (`size` 10–20). Prefer `allo_batch_get_conversation_items`
   over many single gets.
4. Ask before `extend=transcript` — transcripts are large.

## Useful filters

| Intent | How |
|---|---|
| Missed / unanswered inbound | `direction=INBOUND`, `result=VOICEMAIL` (no `MISSED` enum — say you used voicemail as proxy) |
| Keyword in transcript/SMS | `search="…"`, `sort=RELEVANCE` |
| One contact | `contact_number` in E.164 |
| One line | `allo_number` (from `allo_list_numbers`) |
| Tags | keys from `allo_list_tags`, not display names |
| Unread | `unread=true` |

Keyword terms are AND'd with prefix matching — start with one distinctive word.

## Listing by contact

`allo_list_conversations` requires `allo_number`. Use it for inbox-style "what's
new on this line", then drill into items with search/get.

## Tagging and mark read

Tagging is a write. For one clear call the user named, apply tags. For bulk:
validate → summarize → confirm → execute → report.

Mark read/unread/archive with `allo_mark_conversation`.

## Answer shape

Lead with the count and date range you used, then the most relevant few items in
plain language (who, when, outcome, one-line takeaway). Offer to open transcripts
or draft follow-ups — do not send SMS from this skill unless the user clearly
moves to sending (then use `allo-sms`).
