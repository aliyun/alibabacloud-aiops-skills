# Function Selection Guide

Choose a function category by scenario, then read the corresponding YAML in this skill.

## High-Frequency Categories

- Aggregation: `./functions/aggregate.yaml`
- String processing: `./functions/string.yaml`
- Regex matching: `./functions/regex.yaml`
- Date/time handling: `./functions/datetime.yaml`
- Type conversion: `./functions/type_conversion.yaml`
- Conditional logic: `./functions/conditional.yaml`
- JSON extraction: `./functions/json.yaml`
- Math operations: `./functions/math.yaml`
- URL parsing: `./functions/url.yaml`
- Array / Map: `./functions/array.yaml`, `./functions/map.yaml`
- Window analysis: `./functions/window.yaml`
- Funnel analysis: `./functions/window_funnel.yaml`
- Lambda expressions: `./functions/lambda.yaml`

## Language Differences

- **SQL + SPL both support**: string, regex, datetime, type conversion, conditional, JSON, math, URL, encoding, hash, array, Map, and most other basic functions
- **SQL only**: window functions, bitwise operations, geospatial functions, HyperLogLog, statistical functions, funnel functions
- **SPL only**: `ip_to_province`, `ip_to_city`, `ip_to_country`, `ip_to_geo`

## Key Reminders

- Always `cast()` or `try_cast()` before numeric comparison
- Use `try_cast()` to avoid entire-row failures on conversion errors
- Prefer `date_trunc()` or `date_format()` for time-based grouping
- Prefer `json_extract()` / `json_extract_scalar()` for JSON fields
- For SPL escape handling, prefer `ascii_escape`, `ascii_unescape`, `unicode_unescape`
- SPL and SQL function capabilities are not always identical — when in doubt, consult the corresponding function YAML

## Common Templates

### Type Conversion
```sql
* | SELECT count(*) FROM log WHERE cast(status as BIGINT) >= 500
```

```spl
* | where try_cast(status as BIGINT) >= 500
```

### JSON Extraction
```sql
* | SELECT json_extract_scalar(payload, '$.user.id') AS user_id, count(*) FROM log GROUP BY user_id
```

### Regex Extraction
```sql
* | SELECT regexp_extract(message, 'code:(\d+)', 1) AS code, count(*) FROM log GROUP BY code
```

### SPL Geo Analysis
```spl
* | extend province = ip_to_province(client_ip) | stats pv = count(*) by province
```

## Source YAMLs

- `./functions/overview.yaml`
- `./functions/README.md`
- `./functions/*.yaml`
