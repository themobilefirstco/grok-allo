---
description: Allô team phone performance report with period-over-period comparison
argument-hint: "[period, e.g. last week | this month] [optional: rep names]"
---

Build an Allô team performance report for: **$ARGUMENTS**
(default to last week, whole team, if empty).

Use the `allo-analytics` skill. Read-only.

1. Resolve the period to explicit dates and pick the prior equivalent period as
   the comparison.
2. `allo_list_users` if specific reps were named, to resolve IDs.
3. `allo_get_team_analytics` — all relevant `user_ids` in **one** call, with
   `compare_date_from`/`compare_date_to` set.
4. `allo_get_team_outbound_analytics` for the funnel and leaderboard over the
   same range. If a conversion tag wasn't specified, either ask which tag defines
   a conversion or state the one you used.
5. If a metric moved sharply, drill into the calls behind it with `extend=items`
   and a `stage`, and read a few to explain why.

Report as: headline → what moved → who drove it → caveats → what to watch.

Only report metrics Allô actually returned. Call out small denominators rather
than crowning a rep with a perfect rate on three dials.
