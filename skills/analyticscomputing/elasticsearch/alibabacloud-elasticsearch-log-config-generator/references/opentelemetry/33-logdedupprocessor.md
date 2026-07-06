# log_dedup processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/logdedupprocessor/README.md
>
> Aggregates duplicate log records within a window into one record carrying a count. Identity = same body + resource attributes + severity + log attributes. Type was renamed `logdedup` → `log_dedup`.

## Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `interval` | duration | `10s` | Aggregation window; counter resets each cycle. |
| `log_count_attribute` | string | `log_count` | Attribute name for the dedup count on emitted records. |
| `timezone` | string | `UTC` | IANA zone applied to observed-timestamp attributes. |
| `conditions` | []string | `[]` | OTTL expressions; only logs with at least one condition true are eligible. Non-matching logs pass through. |
| `include_fields` | []string | `[]` | Restrict dedup match to listed body/attribute fields. Mutually exclusive with `exclude_fields`. |
| `exclude_fields` | []string | `[]` | Drop these fields from the match (and from emitted output). |

OTTL paths in `conditions` should carry the context prefix (`log.attributes["foo"]`, `resource.attributes["bar"]`); the un-prefixed form is deprecated.

The body can't be excluded wholesale; sub-fields can. Nested paths use `.`; literal dot in a name is escaped `\.`.

## Emitted record

Carries:

- The configured `log_count_attribute` (count of merged records).
- `first_observed_timestamp`, `last_observed_timestamp` (in the configured timezone).
- ObservedTimestamp + Timestamp = emission time, **not** the originals.

## Example

```yaml
processors:
  log_dedup:
    interval: 60s
    log_count_attribute: dedup_count
    timezone: 'America/Los_Angeles'
    conditions:
      - log.attributes["ID"] == 1
      - resource.attributes["service.name"] == "my-service"
```

To dedup only on a subset of fields, swap `conditions` for `include_fields` (e.g., `attributes.id`, `attributes.name`) or use `exclude_fields` to ignore noisy fields like `body.timestamp`, `attributes.host\.name`.

## When to use

- Repetitive INFO/heartbeat logs that flood ES indices.
- Bursty error logs from the same service+message — keep one record + count.

Place after parsing (so attributes are populated) and before batching.
