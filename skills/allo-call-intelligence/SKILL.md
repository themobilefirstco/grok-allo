---
name: allo-call-intelligence
description: >-
  Deep analysis of Allô calls, transcripts, and SMS. Use when the user wants to
  find specific conversations, understand what was said on a call, surface
  objections or themes across calls, identify frustrated customers or warm leads,
  find calls needing follow-up, review a contact's history, or tag a set of calls.
  Triggers on "what did they say", "find calls where", "objections", "frustrated
  customers", "needs follow-up", "our last call with", "summarize calls with".
metadata:
  author: Allô
  short-description: Search, read, and reason over call transcripts and SMS.
---

# Allô — call intelligence

Turning raw call data into answers. Read the `allo` skill first for discovery,
safety, and confirmation rules; this skill covers the analysis craft.

## The core loop

Never dump the corpus into context. Work in three stages:

1. **Narrow** — `allo_search_conversation_items` with filters. Start with
   `size=1` to read `pagination.total_count` and learn how big the set is before
   you commit to fetching it.
2. **Deepen** — pull only what you need. `allo_batch_get_conversation_items` for
   a set, `allo_get_conversation_item` for one. Read summaries first; add
   `extend=transcript` only when a summary genuinely can't answer the question.
3. **Synthesize** — answer with attributed evidence and an explicit sample size.

If the candidate set is large, say what you sampled. "I read the 15 longest calls
out of 212" is a good answer. Silently analyzing the first page and presenting it
as the whole picture is not.

## Searching well

Keyword terms are **AND'd with prefix matching** across transcripts, summaries,
and SMS. Practical consequences:

- Fewer, more distinctive terms win. `search="pricing"` beats
  `search="customer asked about our pricing"` — the latter requires every word.
- Prefix matching means `"cancel"` also matches "cancelled", "cancellation".
  Use it: search the stem.
- Always pair `search` with `sort=RELEVANCE`. Without it you get date order and
  the best match may be on page 4.
- Concepts aren't keywords. "Frustrated customers" won't match the word
  "frustrated" often. Search for what people *actually say* — "refund",
  "cancel", "manager", "unacceptable", "still waiting" — then judge sentiment
  from the transcripts you read. Run a few targeted searches rather than one
  abstract one.

Combine filters to cut the set before keywords do the work: `date_from`/`date_to`,
`direction`, `result`, `type` (CALL/SMS/ALL), `user_id`, `allo_number`, `tags`,
`unread`.

## Common intents → filters

| Intent | Approach |
|---|---|
| Missed calls | `direction=INBOUND` + `result=VOICEMAIL` — a proxy, no `MISSED` filter exists. Say so. |
| Needs follow-up | `unread=true`, and/or inbound voicemails with no later outbound to that contact |
| Everything with one contact | `contact_number` (E.164), no keyword |
| A rep's calls | `user_id` from `allo_list_users` |
| Calls on one line | `allo_number` from `allo_list_numbers` |
| Already-classified calls | `tags` with keys from `allo_list_tags` |

For "needs follow-up", check whether a later outbound call or SMS to that contact
exists before calling it unhandled — `contact_number` search returns the full
interaction history for exactly this check.

## Reading a call

Prefer the summary. Go to the transcript when the user asks what was *said*,
wants quotes, or is asking about nuance the summary flattens.

When you report:

- **Attribute.** Tie each claim to a specific call and date.
- **Quote sparingly and accurately.** Don't paraphrase into the transcript words
  that aren't there.
- **Separate fact from inference.** "The customer said the price was too high" is
  a fact. "This is a warm lead" is your judgment — mark it as such.
- **Don't fabricate.** If a transcript is missing, empty, or the call was too
  short to contain the answer, say that.

## Themes across calls

For "what were the biggest objections this week":

1. Narrow to the relevant set (date range, outbound, maybe a tag).
2. Pull a defensible sample with `allo_batch_get_conversation_items` —
   representative, not just the first N.
3. Read summaries, escalating to transcripts for ambiguous ones.
4. Group into themes, count occurrences, rank by frequency, and give a
   representative quote per theme.
5. State the sample size and the range.

Report frequencies as counts over your sample ("6 of the 22 calls I read"), not
as percentages implying full coverage.

## Tagging what you found

Tagging is a write. From the `allo` skill: keys not display names, verify with
`allo_list_tags`, ask if no key matches, and for bulk follow the protocol —
summarize the target set and count, get a go-ahead, execute, then report
including partial failures.

`allo_add_call_tags` takes one call `id` (`cll-…`) plus a list of keys, so bulk
tagging is a loop. Respect the 5 writes/sec limit, and report per-item outcomes.
A 409 `TAG_ALREADY_EXISTS` is a no-op, not an error worth alarming the user about.

Only tag calls you actually validated. If you inferred "warm lead" from a
transcript, show the user which calls and why before applying it.

## Notes, threads, and conversation state

Where the workspace's scopes allow it, findings can be written back into Allô
rather than left in chat:

- Conversation and contact **notes** record a finding on the record itself.
- **Threads** start an internal discussion on a call, SMS, or note, and support
  `@[Name](usr-id)` mentions — useful for routing a follow-up to a teammate.
- `allo_mark_conversation` marks read/unread or archives.

All are writes. Confirm before creating notes or threads on the user's behalf,
and never @-mention a teammate unless the user asked to involve them. Check
`allo_get_me` for the relevant scopes before promising any of this.
