# filter processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/filterprocessor/README.md
>
> Drops telemetry whose OTTL conditions match. Conditions inside a section are OR-ed. OTTL grammar/functions live in `18`–`20-ottl-*.md`.

## Top-level

```yaml
processors:
  filter:
    error_mode: ignore   # ignore (default) | silent | propagate
    log_conditions:    [...]
    metric_conditions: [...]
    trace_conditions:  [...]
```

`error_mode`:

| Mode | When OTTL errors |
|---|---|
| `ignore` (default) | Log + skip condition + continue. |
| `silent` | Skip condition silently. |
| `propagate` | Drop the payload upstream. |

(`processor.filter.defaultErrorModeIgnore` feature gate is on by default to keep `ignore` as default.)

## Contexts

- **Logs**: `resource`, `scope`, `log`
- **Traces**: `resource`, `scope`, `span`, `spanevent`
- **Metrics**: `resource`, `scope`, `metric`, `datapoint`

Hierarchical evaluation: higher-level drops short-circuit lower-level checks. Drop all spanevents → span keeps. Drop all datapoints → metric drops.

## Advanced grouped form

```yaml
processors:
  filter:
    error_mode: propagate
    trace_conditions:
      - context: span
        error_mode: ignore
        conditions:
          - IsRootSpan()
      - conditions:
          - spanevent.attributes["grpc"] == true
```

`context` is normally inferred from the path prefix; setting it explicitly is rarely needed.

## Metrics-only OTTL helpers

- `HasAttrKeyOnDatapoint(key)` — true if any datapoint has the key.
- `HasAttrOnDatapoint(key, value)` — true if any datapoint has the (key, value) pair.

Both require `metrics.metric` context.

## Legacy

The pre-0.146 `traces`/`logs`/`metrics.{include,exclude}` and nested `resource`/`record` forms are deprecated. Migrate everything to `*_conditions`.

## Log examples

Drop below WARN:

```yaml
processors:
  filter/severity:
    error_mode: ignore
    log_conditions:
      - log.severity_number < SEVERITY_NUMBER_WARN
```

Drop by namespace and health-check route:

```yaml
processors:
  filter/by_attribute:
    error_mode: ignore
    log_conditions:
      - resource.attributes["k8s.namespace.name"] == "dev"
      - log.attributes["http.route"] == "/healthz"
```

Drop noisy bodies:

```yaml
processors:
  filter/noisy_bodies:
    error_mode: ignore
    log_conditions:
      - IsMatch(log.body, ".*password.*")
      - IsMatch(log.body, ".*heartbeat.*") and log.severity_number < SEVERITY_NUMBER_ERROR
```

## Warnings

- Use the most specific condition you can — broad filters silently delete value.
- Dropping spans orphans children and any logs referencing the dropped `span_id`.
- Set `service.telemetry.logs.level: debug` to see per-condition match results.
