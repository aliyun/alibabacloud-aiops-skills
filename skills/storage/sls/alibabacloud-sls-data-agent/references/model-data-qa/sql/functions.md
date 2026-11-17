# SLS function reference

## `compare` and `ts_compare`

Use these functions to compare scalar, grouped, or time-series results over historical periods of equal length.

- Compute aggregate values in an inner query before calling `compare/ts_compare`. Do not nest aggregate functions directly or nest these comparison functions within each other.
- The offset unit is seconds. For one offset, `diff[1]/diff[2]/diff[3]` are the current value, historical value, and ratio, respectively; `ts_compare` returns the historical Unix time in `diff[4]`. Do not reuse this array layout for multiple offsets.
- `ts_compare` groups by only one timestamp column. Interpret ratios and zero baselines from the actual results; do not directly interpret the ratio as a growth rate.

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

## `__time__` and bucketing

Use these for trends and fixed-width time buckets.

- `__time__` is in Unix seconds. Use `date_trunc('<unit>', __time__)` for calendar units and `from_unixtime(__time__ - __time__ % 300)` for fixed five-minute buckets.

## JSON

When extracting JSON content, `json_extract` returns JSON and `json_extract_scalar` returns `varchar`.

## RE2 regular expressions

`regexp_like`, `regexp_extract`, and `regexp_replace` use RE2 and do not support lookaround or backreferences within patterns.

Use one backslash for `\d` in SQL strings, for example `regexp_extract(<field>, 'code:(\d+)', 1)`. Shell or JSON escaping must preserve the final query bytes; do not send repeated backslashes to SLS.

## Approximate aggregates

Use `approx_distinct(x)` and `approx_percentile(x, p)` to estimate distinct counts or quantiles, where `p` is in `0..1`, for example `0.99` for P99.

## IP geolocation

Use the SQL functions `ip_to_province`, `ip_to_city`, `ip_to_country`, `ip_to_provider`, and `ip_to_geo` to analyze location or provider by IP. Unparseable values may return NULL.
