# OpenTelemetry attributesprocessor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/attributesprocessor/README.md
> Status: beta for traces, metrics, logs.

The attributes processor modifies attributes on logs/spans/metrics via an ordered list of actions, with optional include/exclude filtering.

## Actions

| Action | Purpose |
|--------|---------|
| `insert` | Add a new attribute only when the key is absent. |
| `update` | Change an attribute only when the key already exists. |
| `upsert` | Insert if missing, update if present. |
| `delete` | Remove an attribute (by `key` and/or `pattern`). |
| `hash` | Replace an attribute's value with its SHA1 hash. |
| `extract` | Apply a regex with named capture groups to a source `key`. |
| `convert` | Cast an attribute to `int`, `double`, or `string` via `converted_type`. |

### Value sources for insert/update/upsert

- **`value`** — literal.
- **`from_attribute`** — copy from another attribute on the same record.
- **`from_context`** — pull from request context. Prefix `metadata.` for receiver metadata (requires `include_metadata: true`); prefix `auth.` for authenticator data; `client.address` for caller address.
- **`default_value`** — fallback when primary source yields nothing.

## Include / Exclude Filtering

When both are present, `include` evaluated first, then `exclude`. `match_type` is `strict` or `regexp`.

### Log selectors

- `log_bodies` — string body match.
- `log_severity_texts` — severity text match list.
- `log_severity_number: { min: <int>, match_undefined: <bool> }`.
- `attributes: [{key, value?}]`.
- `resources: [{key, value?}]`.
- `libraries: [{name, version?}]`.

## Log Examples

### Redact / enrich attributes

```yaml
processors:
  attributes/logs:
    actions:
      - key: user.email
        action: hash
      - key: password
        action: delete
      - key: env
        value: production
        action: upsert
      - key: tenant_id
        from_context: metadata.tenant
        default_value: default-tenant
        action: upsert
```

### Extract structured fields

```yaml
processors:
  attributes/parse:
    actions:
      - key: log.message
        pattern: '^user=(?P<user_id>\w+)\s+op=(?P<operation>\w+)$'
        action: extract
```

### Filter to ERROR+ logs from one service

```yaml
processors:
  attributes/error_logs:
    include:
      match_type: strict
      log_severity_number:
        min: 17        # SeverityNumberError
        match_undefined: false
      resources:
        - key: service.name
          value: payments
    actions:
      - key: alert
        value: true
        action: insert
```
