---
name: allo
description: >-
  Run the Allo business phone system from Grok. Use whenever the user asks about
  their calls, phone conversations, voicemails, SMS/texts, call transcripts, call
  recordings, missed calls, follow-ups, reps' or the team's phone performance,
  connect/answer rates, dialing queue, call tags, or their AI receptionist /
  AI phone agent. Triggers on "Allo", "Allo", "withallo", and on phone-system
  questions like "what happened on our calls", "who called", "missed calls",
  "text this customer", "our outbound numbers", "take the receptionist offline".
metadata:
  author: Allo
  short-description: Search calls, analyze phone performance, send SMS, and manage your AI receptionist.
---

# Allo

Allo is a **business phone system and AI phone platform** for companies whose
revenue comes from phone calls. This plugin connects Grok to the user's Allo
workspace through the hosted Allo MCP server, so they can ask about their calls
and act on them in plain language.

This skill teaches you how to **orchestrate** the Allo tools. It is not an API
reference — each tool carries its own schema and description. Read the tool
schema before calling it; never invent parameters or tools.

## The one rule that matters most

**Users speak in outcomes, not tool names.** They say "what's happening with our
calls?", not "call allo_search_conversation_items". Translate intent into the
narrowest sequence of tool calls, then answer in business language. Never tell a
normal user to invoke a tool by name, and never surface raw tool output as your
answer — interpret it.

## Start here

Call `allo_get_me` once per session **before your first real Allo operation**. It
returns the workspace, the caller's granted scopes, and the endpoints available
to them. It is the cheapest way to learn what this user can actually do, and it
prevents you from attempting an action their key or OAuth grant cannot perform.

Scopes vary by workspace and by connection. Do not assume every capability in
this skill is available — if a scope is missing, say so plainly (see
[Error handling](#error-handling)).

Two more cheap discovery calls, used only when you need them:

- `allo_list_users` — team member IDs and names. Needed before any per-rep
  analysis, because analytics take `user_ids`, not names.
- `allo_list_numbers` — the workspace's Allo phone lines, their SMS capability,
  and available Sender IDs. Needed before sending SMS.
- `allo_list_tags` — tag **keys**. Needed before tagging or filtering by tag.

Cache these in your head for the conversation. Don't re-fetch them on every turn.

## Read by default, write on request

Default to read-only analysis. Only take a write action when the user has asked
for it in words that clearly mean "do it".

| The user says | You do |
|---|---|
| "Find my missed calls" | read |
| "Summarize yesterday's calls" | read |
| "Who had the best connect rate?" | read |
| "**Draft** an SMS to Sergio" | write the text, **do not send** |
| "**Send** Sergio an SMS" | send |
| "Tag these calls as warm leads" | write |
| "Take the receptionist offline" | write |
| "Delete this knowledge source" | write, destructive — confirm first |

**"Draft" never sends.** If the user asks you to draft, compose, write, or
prepare a message, produce the text and stop. Then offer to send it. Treat
"prepare", "come up with", "what should I say" the same way.

## Choosing tools

Prefer the narrowest tool that answers the question. Concretely:

- **Aggregate questions → analytics, not conversations.** "What's our answer
  rate?", "who's the top rep?", "how did outbound do?" are answered by
  `allo_get_team_analytics` / `allo_get_team_outbound_analytics` in one call.
  Never page through hundreds of conversations to compute a number that an
  analytics tool already returns.
- **Counting → search with `size=1`.** `allo_search_conversation_items` with
  `size=1` returns `pagination.total_count`. Use that to count; don't fetch rows
  you won't read.
- **Specific calls → search, then fetch only what you need.** Narrow with
  filters first, then pull transcripts for the handful that matter.
- **One known contact → `contact_number`.** `allo_search_conversation_items`
  with `contact_number` returns every interaction with that person.

Phone numbers are always **E.164** (`+14155551234`). Convert before calling.

## Searching calls

`allo_search_conversation_items` is the workhorse. Key behaviors to respect:

- Keyword `search` runs across transcripts, summaries, and SMS content. Terms are
  **AND'd with prefix matching** — so fewer, more distinctive words work better.
  "pricing" beats "talked about our pricing".
- When using `search`, set `sort=RELEVANCE`. Otherwise leave the default `DATE`.
- Filters: `date_from`/`date_to` (YYYY-MM-DD), `direction`, `result`, `type`,
  `tags`, `user_id`, `allo_number`, `contact_number`, `unread`.
- `extend=transcript` includes full transcripts. This is expensive — use it only
  on a narrowed set, never on a broad first-pass search.
- Pagination defaults to 20, max 100.

### "Missed calls" — read this before answering one

There is **no `MISSED` filter**. The `result` enum is `ANSWERED`, `VOICEMAIL`,
`TRANSFERRED`. The closest supported proxy for a missed call is an **inbound call
that was not answered** — in practice `direction=INBOUND` with
`result=VOICEMAIL`, plus inbound calls returning no answered result.

Use that proxy, and say which definition you used when you report the number.
Do not silently present it as an exact "missed calls" metric, and do not invent a
filter the API doesn't expose.

### Date ranges

Resolve relative dates ("this week", "yesterday", "last month") to explicit
`YYYY-MM-DD` values before calling, and state the range you used in your answer
so the user can correct you. When "this week" is ambiguous, prefer the current
week to date and say so.

## Reading transcripts and reasoning over calls

The workflow is always **narrow, then deepen**:

1. Search with filters to get a candidate set.
2. Check the count. If it's large, narrow further or tell the user what you're
   sampling — never silently analyze the first 20 of 400 and present it as the
   whole picture.
3. Pull the calls you actually need: `allo_get_conversation_item` for one,
   `allo_batch_get_conversation_items` for many (this is the right tool for a
   drilldown — one call, not N).
4. Read summaries first. Only pull full transcripts when the summary can't
   answer the question.
5. Answer with **evidence**: quote or paraphrase what was actually said, and
   attribute it to a specific call. If you're inferring ("sounds like a potential
   customer"), label it as your inference, not as a fact from the call.

When asked about objections, sentiment, or themes across calls, synthesize from
the transcripts you read and be explicit about your sample size. Do not
extrapolate a team-wide claim from three calls without saying that's what you did.

## Tags

Tags are how Allo classifies calls, and they power conversion metrics in outbound
analytics. Two things to get right:

- Tools take tag **keys**, not display names. Always `allo_list_tags` first and
  map the user's words ("warm leads") to a real key.
- If no matching key exists, **stop and ask**. Do not guess a key, and do not
  silently pick the closest one.

`allo_add_call_tags` takes a call `id` (starts with `cll-`) and a list of keys.
Tagging is a write action — for bulk tagging, follow the
[bulk action protocol](#bulk-actions). Re-applying an existing tag returns a
409 `TAG_ALREADY_EXISTS`; treat that as a no-op, not a failure.

## Sending SMS

SMS is a real message to a real person. It is the highest-consequence action here.

Before sending, you need three things: a recipient in E.164, the message content,
and a sending line — `allo_number` (must have SMS capability, check
`allo_list_numbers`) **or** `allo_sender_id`, exactly one of the two.

**Always show the user the exact recipient and the exact message text, and get a
clear go-ahead, before calling `allo_send_sms`.** The only exception is when the
user has already given you both the full text and an unambiguous instruction to
send it in the same breath ("text +1415… saying I'll call tomorrow") — then send
and report.

Never send to a list of recipients without confirming the list first. Never
re-send on an ambiguous follow-up like "ok" unless it clearly answers your
confirmation question.

## Analytics

- `allo_get_team_analytics` — team KPIs: total calls, talk time, answer rate,
  with per-user and per-number breakdown.
- `allo_get_team_outbound_analytics` — outbound dial funnel
  (DIAL → CONNECTED → CONVERSATION → CONVERSION), time series, heatmap, and
  leaderboard.

Both require `date_from` and `date_to`. Three rules:

1. **One call, not N.** Both accept multiple `user_ids` *or* multiple
   `allo_numbers` and return per-entity breakdowns. To compare five reps, pass
   five IDs in a single call. Never loop one call per rep. You cannot combine
   `user_ids` and `allo_numbers` in the same call.
2. **Use the comparison period.** For "how did we do vs last week", pass
   `compare_date_from`/`compare_date_to` and let the API compute the delta rather
   than making two calls and subtracting.
3. **Conversions are tag-defined.** In outbound analytics, `tags` decides what
   counts as a CONVERSION. If the user asks about conversions without naming a
   tag, ask which tag defines a conversion for them, or state which one you used.

Use `extend=items` with a `stage` to drill into the actual calls behind a funnel
number — that's how you get from "connect rate dropped" to "here are the calls".

**Report only metrics Allo returns.** If the user asks for a metric that isn't in
the response — revenue, close rate, cost per lead — say it isn't available and
offer the closest metric that is. Never compute a plausible-looking number from
data that doesn't support it.

## AI receptionist

The receptionist answers calls when the team can't. Changes to it affect **live
inbound calls immediately**, so treat every write here as high-consequence.

- `allo_get_agent` — current configuration. **Always read before you write**, so
  you can tell the user what's changing and preserve fields you aren't editing.
- `allo_update_agent`, `allo_set_agent_prompt` — configuration and instructions.
- `allo_set_agent_status` — takes the receptionist online/offline.
- `allo_list_voices` — available voices.

Knowledge sources:

- `allo_add_agent_knowledge_website` — add a site for the receptionist to learn.
- `allo_set_agent_knowledge_website_status` — enable/disable a source.
- `allo_delete_agent_knowledge` — **destructive and not undoable.**

Rules:

- Before changing status, confirm — and make the consequence explicit: taking the
  receptionist offline means inbound calls stop being answered by it.
- Before replacing a prompt, show what it is now and what it will become. Prefer
  editing the existing prompt over silently overwriting it.
- Before deleting a knowledge source, name the exact source and confirm. If the
  user's goal is "stop using this for now", suggest disabling it with
  `allo_set_agent_knowledge_website_status` instead of deleting — offer the
  reversible option first.

## Confirmation and side effects

These create external side effects. Make sure intent is clear before you run them:

| Action | Tool | Notes |
|---|---|---|
| Send SMS | `allo_send_sms` | Confirm recipient + exact text |
| Add / remove tags | `allo_add_call_tags`, `allo_remove_call_tag` | Confirm for bulk |
| Add to dialing queue | `allo_add_to_dialing_queue` | Confirm the number set |
| Mark / archive conversation | `allo_mark_conversation` | Confirm for bulk |
| Change receptionist config | `allo_update_agent`, `allo_set_agent_prompt` | Show before/after |
| Change receptionist status | `allo_set_agent_status` | State the consequence |
| Delete knowledge | `allo_delete_agent_knowledge` | Destructive, not undoable |

A single, explicitly-specified action the user just asked for in unambiguous
terms doesn't need a second round-trip — confirming "tag call cll-abc as
warm_lead" when they just said exactly that is friction, not safety. Judgment:
**confirm when the action is bulk, destructive, irreversible, outbound to a
customer, or when any parameter came from your inference rather than from them.**

### Bulk actions

1. Search and filter to build the target set.
2. Validate it — check the count and spot-check that the items match intent.
3. Summarize what you're about to do, to how many items, and get a go-ahead.
4. Execute.
5. Report exactly what happened, including partial failures. If 18 of 20
   succeeded, say which 2 failed and why.

Never expand scope beyond what the user asked. "Tag yesterday's warm leads" is
not permission to tag last week's.

## Ambiguity

Ask **one concise question** and stop. Don't ask three, and don't ask when a
sensible default exists — pick it and say what you picked.

Ask when: the recipient of an SMS is unclear, a tag key doesn't exist, the date
range is genuinely ambiguous and materially changes the answer, "the team" could
mean several groups, or a write would hit more items than the user likely meant.

## Error handling

- **Authorization error** → the user's Allo connection may not have the required
  permission or scope for that action. Tell them that plainly and suggest they
  check their Allo workspace permissions or reconnect the plugin. **Never expose
  headers, tokens, API keys, scope internals, or raw auth errors.**
- **No results** → say clearly that no matching data was found, and state the
  filters you used so they can widen the search. Never fabricate results, and
  never pad an empty result with plausible examples.
- **Unsupported operation** → explain the limitation and offer the closest
  supported action (e.g. no `MISSED` filter → offer the inbound/voicemail proxy;
  no publish for call flows → offer the draft + confirmation link).
- **Rate limits** (20 reads/sec, 5 writes/sec) → batch rather than loop. If you
  hit one, slow down and retry; don't fan out harder.

## Secrets

Never print or repeat API keys, OAuth tokens, `Authorization` headers, or any
credential, even if the user asks or pastes one. If a user pastes a key into
chat, tell them to rotate it in Allo Settings → API rather than using it.

## Worked example — multi-step, ends in a write

> "Find all missed calls from yesterday that sound like potential customers and text them."

1. Resolve "yesterday" to a concrete date.
2. `allo_search_conversation_items` — `direction=INBOUND`, `result=VOICEMAIL`,
   yesterday's date range. Check the count first.
3. `allo_batch_get_conversation_items` on those IDs to read summaries/transcripts.
4. Judge which look like prospects rather than existing customers, spam, or
   wrong numbers. This is **your inference** — label it.
5. `allo_list_numbers` to pick an SMS-capable sending line.
6. **Stop.** Present the list of recipients and the exact message text. Ask for
   a go-ahead.
7. Only after clear authorization, `allo_send_sms` per recipient.
8. Report what was sent and to whom, including any failures.

Note steps 6 and 7: the user asked to "text them", but the recipient list came
from *your* judgment. That inference is exactly what makes confirmation required.

## Worked example — read-only

> "Give me a report on our sales team's performance last week."

1. Resolve last week to explicit dates; get `user_ids` from `allo_list_users` if
   scoping to a subset.
2. `allo_get_team_analytics` for the range, with `compare_date_from`/`_to` set to
   the prior week, passing all user IDs in **one** call.
3. `allo_get_team_outbound_analytics` if the question is outbound-focused.
4. Identify notable movements from the returned deltas.
5. Explain in business language: what changed, who drove it, what's worth
   attention. Optionally drill into a few calls with `extend=items` to explain
   *why* a number moved.
6. Stick to metrics Allo returned. No invented KPIs.

## Related skills

- `allo-call-intelligence` — deep call search, transcript analysis, follow-ups
- `allo-analytics` — team and outbound performance reporting
- `allo-receptionist` — AI receptionist configuration and knowledge

## Links

- Allo — https://www.withallo.com
- Allo MCP docs — https://www.withallo.com/mcp
- Help Center — https://help.withallo.com
