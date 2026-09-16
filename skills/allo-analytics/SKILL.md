---
name: allo-analytics
description: >-
  Team and outbound phone performance from Allo. Use for connect rates, answer
  rates, call volume, talk time, dial funnel, conversions, rep leaderboards, best
  times to call, or period comparisons. Triggers on "connect rate", "answer
  rate", "top rep", "team performance", "outbound", "how did we do this week",
  "best time to call".
metadata:
  author: Allo
  short-description: Team KPIs, outbound funnel, and rep leaderboards.
---

# Allo — analytics

Two tools cover almost every performance question. Prefer them over paging through
calls.

| Tool | Use for |
|---|---|
| `allo_get_team_analytics` | Total calls, talk time, answer rate; per-user / per-number breakdown |
| `allo_get_team_outbound_analytics` | Dial funnel (DIAL → CONNECTED → CONVERSATION → CONVERSION), time series, heatmap, leaderboard |

## How to call

1. Resolve dates to explicit `YYYY-MM-DD` and state the range you used.
2. For comparisons, pass `compare_date_from` / `compare_date_to` in the **same**
   call — do not loop per day or per rep.
3. Pass multiple `user_ids` **or** multiple `allo_numbers` to compare; never both.
4. Outbound conversions are defined by `tags` (keys from `allo_list_tags`). Ask
   which tag means "converted" if they care about conversion rate.
5. Optional: `extend=items` + `stage` on outbound analytics to drill into the
   calls behind a funnel stage.

## Answer shape

Lead with the headline metric they asked for, then comparison vs prior period if
requested, then top movers. Use a small table for leaderboards. If a metric is
not in the payload, say it is unavailable — do not invent CRM revenue numbers.

Report **only what Allo returns**. Never invent revenue, close rate, or cost per lead.
