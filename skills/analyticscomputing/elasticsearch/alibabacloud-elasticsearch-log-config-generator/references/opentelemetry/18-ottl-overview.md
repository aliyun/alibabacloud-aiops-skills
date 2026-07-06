# OTTL — OpenTelemetry Transformation Language

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md
>
> Used by `transformprocessor`, `filterprocessor`, `tailsamplingprocessor`, and the routing connector. The README is an overview; grammar and function catalog live in sibling docs (also pulled — see `19-ottl-functions.md`, `20-ottl-log-paths.md`).

## What OTTL is

A small DSL for processing telemetry with OpenTelemetry-native paths and functions.

## Statement structure

```
<function>(<args...>) where <condition>
```

The `where` clause is optional. Example:

```
set(span.attributes["test"], "pass") where span.attributes["test"] == nil
```

## Contexts

Statements are evaluated against a context (one signal at a time). Cross-signal references are rejected.

| Signal | Context |
|---|---|
| Resource | `ottlresource` |
| Instrumentation Scope | `ottlscope` |
| Span | `ottlspan` |
| Span Event | `ottlspanevent` |
| Metric | `ottlmetric` |
| Datapoint | `ottldatapoint` |
| **Log** | **`ottllog`** ← what we use |
| Profile | `ottlprofile` (development) |

Stability: traces, metrics, **logs are beta**; profiles is development.

## Path forms

Within a context, paths address fields:

| Form | Meaning |
|---|---|
| `attributes["k"]` | Attribute on the current record (e.g., the log) |
| `resource.attributes["k"]` | Resource attribute |
| `instrumentation_scope.attributes["k"]` | Scope attribute |
| `body` | Log body (in `ottllog`) |
| `severity_text`, `severity_number`, `time_unix_nano`, `trace_id`, `span_id` | Common log record fields (see `20-ottl-log-paths.md`) |

## Where OTTL is used

- **transform processor** — modify telemetry inline.
- **filter processor** — drop telemetry where a condition matches.
- **tail sampling processor** — sample spans.
- **routing connector** — route between pipelines.

## Worked log examples

```yaml
processors:
  transform:
    log_statements:
      - context: log
        statements:
          - set(attributes["env"], resource.attributes["deployment.environment"])
          - set(severity_text, "ERROR") where IsMatch(body, "(?i)\\berror\\b")
          - delete_key(attributes, "internal_token")
          - replace_pattern(body, "password=[^ ]+", "password=***")
```

```yaml
processors:
  filter:
    logs:
      log_record:
        - 'severity_number < SEVERITY_NUMBER_INFO'
        - 'attributes["env"] == "test"'
```

## Troubleshooting

Set `service.telemetry.logs.level: debug` to print the `TransformContext` before/after each statement and which condition matched. Output is verbose.

## See also

- `19-ottl-functions.md` — full function catalog (set, delete_key, replace_pattern, IsMatch, ParseJSON, …).
- `20-ottl-log-paths.md` — exhaustive list of paths inside the `ottllog` context.
