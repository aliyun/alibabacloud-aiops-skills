# OTTL — log context paths

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/contexts/ottllog/README.md
>
> Path expressions valid inside `transformprocessor.log_statements` and `filterprocessor.logs.log_record`. Cross-context references (e.g., span paths in a log statement) are rejected.

## Cache

| Path | Type |
|---|---|
| `log.cache` | `pcommon.Map` |
| `log.cache["k"]` | string / bool / int64 / float64 / map / slice / bytes / nil |

## Resource

| Path | Type |
|---|---|
| `resource` | resource object |
| `resource.attributes` | map |
| `resource.attributes["k"]` | scalar/map/slice/bytes/nil |
| `resource.dropped_attributes_count` | int64 |

## Instrumentation Scope

| Path | Type |
|---|---|
| `instrumentation_scope` | scope object |
| `instrumentation_scope.name` | string |
| `instrumentation_scope.version` | string |
| `instrumentation_scope.dropped_attributes_count` | int64 |
| `instrumentation_scope.attributes` | map |
| `instrumentation_scope.attributes["k"]` | scalar/map/slice/bytes/nil |

## Log record

| Path | Type |
|---|---|
| `log.attributes` | map |
| `log.attributes["k"]` | scalar/map/slice/bytes/nil |
| `log.event_name` | string |
| `log.trace_id` / `log.trace_id.string` | TraceID / string |
| `log.span_id` / `log.span_id.string` | SpanID / string |
| `log.time_unix_nano` | int64 |
| `log.observed_time_unix_nano` | int64 |
| `log.time` | time.Time |
| `log.observed_time` | time.Time |
| `log.severity_number` | int64 |
| `log.severity_text` | string |
| `log.body` | any |
| `log.body["k"]` | (map index) scalar/map/slice/bytes/nil |
| `log.body[i]` | (slice index) scalar/map/slice/bytes/nil |
| `log.body.string` | string |
| `log.dropped_attributes_count` | int64 |
| `log.flags` | int64 |

## Embedded otelcol context

`otelcol.*` paths from `ottlotelcol` are also accessible.

## Notes

- All integers ↔ `int64`; all doubles ↔ `float64`.
- For nil checks on IDs, compare against an empty SpanID/TraceID, e.g. `SpanID(0x0000000000000000)`.

## Severity number enums

| Symbol | Value |
|---|---|
| `SEVERITY_NUMBER_UNSPECIFIED` | 0 |
| `SEVERITY_NUMBER_TRACE`–`TRACE4` | 1–4 |
| `SEVERITY_NUMBER_DEBUG`–`DEBUG4` | 5–8 |
| `SEVERITY_NUMBER_INFO`–`INFO4` | 9–12 |
| `SEVERITY_NUMBER_WARN`–`WARN4` | 13–16 |
| `SEVERITY_NUMBER_ERROR`–`ERROR4` | 17–20 |
| `SEVERITY_NUMBER_FATAL`–`FATAL4` | 21–24 |

## Examples

```
# Promote nested body fields, raise severity
set(log.attributes["http.status_code"], log.body["status"]) where log.body["status"] != nil
set(log.severity_number, SEVERITY_NUMBER_ERROR) where log.body["status"] >= 500
set(log.severity_text, "ERROR") where log.severity_number == SEVERITY_NUMBER_ERROR
set(log.attributes["service.name"], resource.attributes["service.name"])

# Prefix the body string for warnings; drop debug attrs below INFO
set(log.body.string, Concat(["[", log.severity_text, "] ", log.body.string], ""))
  where log.severity_number >= SEVERITY_NUMBER_WARN
delete_key(log.attributes, "debug_payload")
  where log.severity_number < SEVERITY_NUMBER_INFO
```
