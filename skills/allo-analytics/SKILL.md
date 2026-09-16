---
name: allo-analytics
description: >-
  Team and outbound phone performance reporting from Allo. Use when the user asks
  about connect rates, answer rates, call volume, talk time, outbound funnel,
  conversions, rep leaderboards, best times to call, or week-over-week/period
  comparisons. Triggers on "connect rate", "answer rate", "who's the top rep",
  "team performance", "outbound performance", "call volume", "how did we do this
  week", "best time to call".
metadata:
  author: Allo
  short-description: Team KPIs, outbound funnel, and rep performance reporting.
---

# Allo — analytics

Two tools answer nearly every performance question. Reach for them **before**
searching conversations — they aggregate server-side, and paging through calls to
compute a rate that analytics already returns is the most common way to waste a
user's time.

- `allo_get_team_analytics` — total calls, talk time, answer rate, with per-user
  and per-number breakdown.
- `allo_get_team_outbound_analytics` — outbound funnel
  (DIAL → CONNECTED → CONVERSATION → CONVERSION), time series, heatmap,
  leaderboard.

Both require `date_from` and `date_to` (YYYY-MM-DD).

## Four rules

1. **One call, not N.** Both tools accept multiple `user_ids` *or* multiple
   `allo_numbers` and return per-entity breakdowns. Comparing eight reps is one
   call with eight IDs. Never loop. You **cannot** combine `user_ids` and
   `allo_numbers` in the same call — pick the axis the question is about.
2. **Let the API do comparisons.** For "vs last week", pass
   `compare_date_from`/`compare_date_to` rather than making two calls and
   subtracting.
3. **Conversions are tag-defined.** In outbound analytics, the `tags` parameter
   decides what counts as a CONVERSION (e.g. `["meeting_booked"]`). There is no
   universal conversion metric. If the user hasn't named one, either ask which
   tag means "converted" for them, or state the tag you used.
4. **Report only what Allo returns.** Revenue, close rate, pipeline, and cost per
   lead are not Allo metrics. If asked, say so and offer the closest real one.
   Never derive a confident business metric from data that doesn't support it.

## Picking the tool

| Question | Tool |
|---|---|
| "How many calls did we handle?" | team analytics |
| "What's our answer rate?" | team analytics |
| "Who talked the most?" | team analytics (talk time, per-user) |
| "How's outbound doing?" | outbound analytics |
| "Which rep has the best connect rate?" | outbound analytics (leaderboard/funnel) |
| "Are we converting?" | outbound analytics + conversion `tags` |
| "When should we be dialing?" | outbound analytics (heatmap) |
| "Is volume trending up?" | outbound analytics (`granularity` DAY/WEEK/MONTH) |

Resolve `user_ids` via `allo_list_users` and `allo_numbers` via
`allo_list_numbers` — the tools take IDs and E.164 numbers, never names.

## From number to explanation

A report that only restates numbers isn't worth much. Use `extend=items` with a
`stage` (DIAL, CONNECTED, CONVERSATION, CONVERSION) to pull the actual calls
behind a funnel figure, then read a few with
`allo_batch_get_conversation_items`. That is how "connect rate fell 12%" becomes
"most dials went to voicemail after 4pm, and the three that connected all asked
about the new pricing".

Drill down when the user asks *why*, when a metric moved sharply, or when you're
about to recommend an action. Don't drill down by default — it costs calls.

## Writing the report

Lead with the answer, then the evidence:

1. **Headline** — the direct answer in one or two sentences.
2. **What moved** — notable changes, with the comparison period named.
3. **Who/what drove it** — the per-user or per-number breakdown, but only the
   entries that matter. A ten-row table where two rows are interesting is worse
   than naming the two.
4. **Caveats** — small samples, partial periods, missing conversion tags.
5. **What to look at next** — optional, only if genuinely actionable.

Always state the date range you used. Prefer plain language over metric jargon:
"3 in 4 calls got answered, up from 2 in 3 last week" lands better than
"answer rate 74.6% (+8.2pp)". Give the precise figure alongside it when the user
is clearly analytical.

Flag small denominators honestly. A rep with a 100% connect rate on 3 dials is
not your top performer, and saying so is the difference between a report and a
misleading one.
