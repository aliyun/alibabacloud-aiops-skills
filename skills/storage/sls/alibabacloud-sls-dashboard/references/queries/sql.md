# Log SQL and Scan SQL for charts

Use Log SQL for indexed aggregation, trends, rankings and detail tables. Preserve fixed
search predicates when adding aggregation or variables. Fields known only from samples
require Scan SQL or [SPL](spl.md) unless indexing is verified. For metric data, read
[MetricsQL](metricsql.md).

## Contents

- [Search and SQL syntax](#search-and-sql-syntax)
- [Time trends](#time-trends)
- [Rankings and table cells](#rankings-and-table-cells)
- [Geographic results](#geographic-results)
- [Historical comparison](#historical-comparison)
- [Scan SQL](#scan-sql)

## Search and SQL syntax

A Logstore statement has the form `search | SELECT ...`: indexed search is on the left,
SQL analytics on the right. Search alone needs no pipe. Without a search predicate, use
`* |` for analytics:

```sql
* | select count(*) as requests
```

Search operators `and`, `or` and `not` are lowercase. Adjacent keywords imply
`and`; use parentheses to make compound conditions explicit:

```text
error timeout
(error or timeout) and not debug
#"connection refused"
```

Double-quote search values containing spaces, colons or hyphens, such as
`message:"request failed"`. The `#"connection refused"` form matches an exact
phrase. Use `:` for text matching; numeric comparisons require a `long` or
`double` field index. Search examples:

```text
status:200
status>=400 and status<500
status in [200 301 302]
host:www.example.*
__source__:10.0.0.1
__topic__:access_log
__tag__:env:prod
```

Wildcards `*` and `?` cannot begin a search term.

In SQL, single quotes delimit strings and double quotes delimit special field
names. Quote a dotted field name as one identifier, not as separate components:

```sql
* | select "properties.agent_version" as agent_version, count(*) as requests
    group by "properties.agent_version"
    order by requests desc
    limit 20
```

Declare returned aliases exactly in Plan `queries[].fields`, and use those aliases in
chart bindings. Convert numeric text before aggregation and handle missing or invalid
input. A ratio needs an explicit numerator, denominator, zero-denominator handling and
output scale; a percentile needs a numeric measure and the intended percentile function.
For dynamic selector candidates, return a `DISTINCT` value column within the intended
scope.

## Time trends

Prefer numeric Unix seconds for time axes. Bucket `__time__` with
`__time__ - __time__ % N`, where `N` is a positive number of seconds: `60`, `300`,
`600`, `1800` and `3600` give 1, 5, 10, 30 and 60-minute buckets.

```sql
* | select __time__ - __time__ % 60 as time, count(*) as requests
    group by time
    order by time
    limit 10000
```

`GROUP BY` does not sort results. For a wide result with one numeric column per
method, use conditional counts:

```sql
* | select __time__ - __time__ % 60 as time,
           count_if(request_method = 'GET') as GET,
           count_if(request_method = 'POST') as POST
    group by time
    order by time
    limit 10000
```

Bind `time` as the X field and `GET`/`POST` as numeric series. A long result instead
returns `time`, a category such as `request_method`, and one numeric measure,
grouped by both time and category; bind the category as the series-splitting field.
Size the row limit for the expected bucket count × series count for long results,
or bucket count for wide results. Read [time, step and result limits](time-and-limits.md)
when choosing the window, interval and result budget. SQL `LIMIT` controls analytic
rows; GetLogsV2 `line`/`offset` do not paginate SQL.

Time functions support conversion and calendar-based calculations:

| Function | Meaning |
| --- | --- |
| `from_unixtime(seconds)` | Convert Unix seconds to a timestamp. |
| `to_unixtime(timestamp)` | Convert a timestamp to Unix seconds. |
| `date_format(timestamp, format)` | Return a formatted time string. |
| `date_trunc(unit, timestamp)` | Truncate to the start of the specified time unit. |
| `date_diff(unit, start, end)` | Return the difference from start to end in the specified unit. |
| `now()` | Return the current timestamp. |

If a result needs formatted timestamps, include the full date, for example
`date_format(from_unixtime(__time__), '%Y-%m-%d %H:%i:%S')`. A time-only label such
as `%H:%i` loses the date and is unsuitable for a multi-day time axis.

## Rankings and table cells

For rankings, sort the measure descending and set a top-N limit.
This example returns request volume and an estimate of distinct client addresses:

```sql
* | select host, count(*) as requests,
           approx_distinct(remote_addr) as distinct_addresses
    group by host
    order by distinct_addresses desc
    limit 10
```

Distinct addresses do not count unique people: clients may share an address or
use several addresses.

Remove query parameters before grouping URL paths so requests to the same path
share a category:

```sql
* | select split_part(uri, '?', 1) as path, count(*) as requests
    group by split_part(uri, '?', 1)
    order by requests desc
    limit 10
```

Replace `uri` with the source URL field.
`split_part` uses a one-based part index, so `1` selects the part before `?`.

Numeric arrays supply table sparklines:

```sql
* | select http_referer, array_agg(body_bytes_sent) as bytes_samples
    from log
    group by http_referer
    limit 100
```

Use a numeric `body_bytes_sent` field and match `fieldOptions[].name` to
`bytes_samples`. This query does not establish array element order: do not present
it as a chronological trend. Read [table options](../charts/tablepro.md) for the numeric
array cell format and index-based X positions.

## Geographic results

IP functions return location fields for geographic aggregation:

| Function | Result |
| --- | --- |
| `ip_to_province(ip)` | Province name. |
| `ip_to_city(ip)` | City name. |
| `ip_to_country(ip)` | Country name. |
| `ip_to_geo(ip)` | Coordinate string in latitude,longitude order. |
| `geohash(geo)` | Geohash encoding of a coordinate string. |

For a province map, return a region and numeric weight:

```sql
* | select ip_to_province(remote_addr) as province, count(*) as requests
    group by province
    order by requests desc
    limit 100
```

Bind `showFieldKey` to `province` and `numFieldKey` to `requests` under the query's
`display.queryOptionMap` entry. Use `ip_to_country(remote_addr)` with the world
map's country-name binding. Read the [China](../charts/chinadistrictmap.md) and
[world](../charts/worlddistrictmap.md) map references for accepted region values.

For point or geographic heat maps, group by coordinates:

```sql
* | select ip_to_geo(remote_addr) as geo, count(*) as requests
    group by geo
    order by requests desc
    limit 1000
```

Bind `longlat` to `geo` and `numFieldKey` to `requests`. Exclude empty or invalid
coordinates before display and bound the point count. If separate coordinates are
needed, `split_part(ip_to_geo(remote_addr), ',', 1)` is latitude and part `2` is
longitude; a geohash is not a replacement for the latitude,longitude string these
maps require. Read [point maps](../charts/geomappro.md) or
[geographic heat layers](../charts/heatmappro.md) for weight and binding behavior.

## Historical comparison

Compare the current request count with the corresponding window 86,400 seconds
(one day) earlier:

```sql
* | select diff[1] as pv,
           diff[2] as previous,
           diff[1] - diff[2] as delta
    from (
      select compare(pv, 86400) as diff
      from (select count(*) as pv from log)
    )
```

`diff[1]` is the current value and `diff[2]` is the previous value. Their subtraction
is an absolute count difference, not a percentage.

## Scan SQL

Use Scan SQL to inspect details without indexed analytics. It does not create
indexes. Keep indexed filtering before the pipe,
then select scan mode explicitly:

```sql
* | set session mode=scan;
SELECT __time__ AS time, level, message
ORDER BY __time__ DESC
LIMIT 100
```

Use fields that exist in the selected logs. Pass the complete statement to
`sls.py query --language sql`; scan mode is part of the statement, not SPL syntax.
