# SLS Function Reference

## `compare` and `ts_compare`

Use these functions to compare scalar values, groups, or time series across historical periods of equal length.

- Calculate aggregate values in an inner query before calling `compare/ts_compare`. Do not nest aggregate functions directly inside them or nest these functions within each other.
- Offsets are in seconds. For a single offset, `diff[1]/diff[2]/diff[3]` are the current value, historical value, and ratio, respectively; `ts_compare` adds the historical Unix time in `diff[4]`. Do not reuse this array layout for multiple offsets.
- `ts_compare` groups by only one timestamp column. Interpret ratios and zero baselines from the actual results; do not directly treat the ratio as a growth rate.

Scalar comparison:

```sql
<search-prefix> | SELECT diff[1] AS current_value,
                 diff[2] AS previous_value,
                 diff[3] AS ratio
FROM (
  SELECT compare(metric_value, <offset_seconds>) AS diff
  FROM (SELECT <aggregate> AS metric_value FROM log) aggregated
) compared
```

Time-series comparison:

```sql
<search-prefix> | SELECT bucket,
                 diff[1] AS current_value,
                 diff[2] AS previous_value,
                 diff[3] AS ratio,
                 diff[4] AS previous_unix_time
FROM (
  SELECT bucket, ts_compare(metric_value, <offset_seconds>) AS diff
  FROM (
    SELECT date_trunc('<unit>', __time__) AS bucket,
           <aggregate> AS metric_value
    FROM log
    GROUP BY bucket
  ) aggregated
  GROUP BY bucket
) compared
ORDER BY bucket
```

## `__time__` and Bucketing

Use time buckets for trends and fixed-width intervals.

- `__time__` is in Unix seconds. Use `date_trunc('<unit>', __time__)` for calendar-based units and `from_unixtime(__time__ - __time__ % 300)` for fixed five-minute buckets.

## JSON

When extracting JSON content, `json_extract` returns JSON and `json_extract_scalar` returns `varchar`.

## RE2 Regular Expressions

`regexp_like`, `regexp_extract`, and `regexp_replace` use RE2, which does not support lookaround or backreferences within patterns.

Use a single backslash for `\d` in SQL strings, for example `regexp_extract(<field>, 'code:(\d+)', 1)`. Account for shell or JSON escaping based on the final query bytes; do not send duplicate backslashes to SLS.

## Approximate Aggregations

Use `approx_distinct(x)` for estimated distinct counts and `approx_percentile(x, p)` for estimated percentiles, where `p` is in `0..1`; for example, P99 uses `0.99`.

## IP Geolocation

For region or carrier analysis by IP address, use `ip_to_province`, `ip_to_city`, `ip_to_country`, `ip_to_provider`, or `ip_to_geo`. Unresolvable values may return NULL.
