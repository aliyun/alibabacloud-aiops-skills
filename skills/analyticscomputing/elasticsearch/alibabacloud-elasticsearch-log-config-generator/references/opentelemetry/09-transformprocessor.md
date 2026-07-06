# OpenTelemetry transformprocessor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/transformprocessor/README.md

Modifies telemetry using OTTL (OpenTelemetry Transformation Language). Full OTTL reference is local — see `18-ottl-overview.md` (statements/contexts), `19-ottl-functions.md` (grammar + editor/converter catalog), and `20-ottl-log-paths.md` (paths and severity enums for `log_statements`).

## Top-Level Structure

```yaml
transform:
  error_mode: ignore                   # ignore | silent | propagate
  trace_statements:   []
  metric_statements:  []
  log_statements:     []
```

## error_mode

| Mode | Behavior |
|------|----------|
| `ignore` | Logs error, continues (recommended default). |
| `silent` | Skips silently. |
| `propagate` | Drops payload. |

## OTTL Path Prefixes

| Signal | Allowed Path Prefixes |
|--------|------------------------|
| `trace_statements` | `resource`, `scope`, `span`, `spanevent` |
| `metric_statements` | `resource`, `scope`, `metric`, `datapoint` |
| `log_statements` | `resource`, `scope`, `log` |

## Sample log_statements

### Basic — set fields, rewrite attributes

```yaml
transform:
  error_mode: ignore
  log_statements:
    - set(log.severity_text, "FAIL") where log.body == "request failed"
    - replace_all_matches(log.attributes, "/user/*/list/*", "/user/{userId}/list/{listId}")
    - set(log.body, log.attributes["http.route"])
```

### Advanced — JSON body parsing with global condition

```yaml
transform:
  error_mode: ignore
  log_statements:
    - conditions:
        - IsMap(log.body) and log.body["object"] != nil
      statements:
        - merge_maps(log.cache, ParseJSON(log.body), "upsert")
        - set(log.attributes["attr1"], log.cache["attr1"])
```

### Setting Elasticsearch mapping mode (commonly used with elasticsearchexporter)

```yaml
transform:
  log_statements:
    - context: scope
      statements:
        - set(attributes["elastic.mapping.mode"], "otel")
```
