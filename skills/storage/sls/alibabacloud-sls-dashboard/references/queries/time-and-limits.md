# Time, step, and result limits

Configure `chart.search.start`, `end` and `timeSpanType` together using the
[Time forms](#time-forms) table for rolling, calendar and fixed windows.

The dashboard's time selection applies unless display.basicOptions.fixedTime selects the
chart's own configured window. search.timeFrom supplies a chart-relative window, and
timeShift moves that window. Both apply to all visible queries, including log queries in
mixed panels.

search.interval sets a minimum metric interval; maxDataPoints participates in
metric step calculation. For `datasource=metricstore`, query-level `interval` sets
the sampling step for bare range PromQL only. Instant queries do not use it, and
SQL containing `promql_query` or `promql_query_range` retains its own function and
step. Bare PromQL dynamic variable candidate queries against `metricstore` use
instant mode, so they do not use this step; SQL-wrapped candidates keep their SQL
function. Read [Metricstore](../datasources/metricstore.md) for query behavior.

The sampling step controls spacing between evaluated points; a PromQL rate window such
as `[5m]` controls how far each evaluation looks back. Instant queries answer a
point-in-time question; a reducer over a range answers a different question. Lower point
counts can hide short-lived behavior; document intentional reductions.

For candidate-query filter inheritance, see [variables](../features/variables.md).
For navigation time settings, see [actions](../features/actions.md).

## Search parameters

Paths are relative to `chart.search`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `start` | string or number | Yes | None | Window start; use the forms below. |
| `end` | string or number | Yes | None | now, absolute, or Unix seconds. |
| `timeSpanType` | string | Yes | None | Empty string for presets/absolute timestamps; custom for custom durations. |
| `interval` | string or null | No | Automatic | Minimum metric interval, such as 15s or 1m; does not limit SQL rows. |
| `maxDataPoints` | number or null | No | — | Target metric point count used in step calculation. |
| `timeFrom` | string or null | No | None | Relative panel window, such as 1h; applies to all visible queries in the panel. |
| `timeShift` | string or null | No | None | Shift the effective window backward by this duration, such as 1h. |

## Time forms

| Window | start | end | timeSpanType |
| --- | --- | --- | --- |
| Rolling preset | -60s, -300s, -900s, -3600s, -14400s, -86400s, -604800s, -2592000s | now | "" |
| Complete preset period | Same preset seconds | absolute | "" |
| Calendar-to-now | today, yesterday, daybeforeyesterday, thisweek, previousweek, thismonth, previousmonth, thisquarter, thisyear | now | "" |
| Complete calendar period | today, yesterday, daybeforeyesterday, week, previousweek, thismonth, previousmonth, thisquarter, thisyear | absolute | "" |
| Fixed historical window | Unix seconds | Unix seconds | "" |
| Custom rolling window | Negative duration, such as -2h or -15m | now | custom |
| Custom complete period | Negative duration, such as -2h or -15m | absolute | custom |

`week` selects a complete week; `thisweek` is the calendar-to-now form.

## Result budgets and timestamps

SQL `LIMIT` caps analytic result rows. For a long table grouped by time and
category, budget for buckets × series: 60 buckets with 20 series each require
1,200 rows. Set a limit that accommodates both dimensions;
use coarser buckets or fewer series when the row budget is too large. A wide table
with one column per series needs one row per returned bucket. Read
[SQL time trends](sql.md#time-trends) for query examples and time functions.

Metricstore query `limit` likewise counts rows across series and samples; it is
not a series count or `maxDataPoints`. Neither step settings nor `maxDataPoints`
replace SQL `LIMIT` or bound raw-log results. Raw-log `line`/`offset` control log
retrieval and pagination, not SQL result limits.

Prefer numeric Unix seconds for returned time fields. If returning formatted
timestamps, include the full date and time rather than only `HH:mm`, which loses
the date across multi-day windows.
