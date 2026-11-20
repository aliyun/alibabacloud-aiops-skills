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

A Logstore statement uses `search | SELECT ...`; without a search predicate, use `* |`:

```sql
* | select count(*) as requests
```

Single quotes delimit strings; double quotes delimit special field names, including
the whole dotted name `"properties.agent_version"`. Further details are in
[search syntax](../../query/index-search.md#basic-syntax),
[SQL syntax](../../query/sql/README.md#basic-syntax) and
[index requirements](../../index/index-configuration.md#query-behavior).

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
For row budgets and timestamp formats, see [time, step and result limits](time-and-limits.md#result-budgets-and-timestamps).
SQL `LIMIT` controls analytic rows; its [pagination rules](../../query/sql/README.md#result-limits-and-pagination)
differ from raw-log `line`/`offset`.

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

For URL-path rankings, `split_part(uri, '?', 1)` removes query parameters before
grouping. A [complete ranking example](../../query/sql/README.md#examples) shows this pattern.

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

For function definitions, see [IP geolocation](../../query/sql/functions/ip_geo.yaml)
and [geographic functions](../../query/sql/functions/geo.yaml).

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

[Scan SQL](../../query/sql/sql-scan.md) can inspect details without indexed analytics;
it does not create indexes. A bounded detail query can return chart-ready aliases:

```sql
* | set session mode=scan;
SELECT __time__ AS time, level, message
ORDER BY __time__ DESC
LIMIT 100
```

For execution and result precision, see [query execution](../../query/query-execution.md#logstore).
