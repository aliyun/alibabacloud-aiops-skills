# Field Naming & Index Conventions

> Source: `loongcollector-oncall/knowledge/base/collection-config/field-naming-and-index.md`. Index type mapping and anti-patterns: `index-coupling.md`.

## 1. Naming rules

- snake_case for all field names.
- One primary name per semantic field (avoid `service`/`serviceName` coexisting).
- Event time -> `__time__`; business time -> `*_time` or `*_ts`.
- Avoid reserved prefixes/suffixes (e.g. `__tag__:`).
- **Default no leading underscore**: `user_id`/`action`/`cost_ms`; use leading underscore only when the user explicitly wants to keep legacy field names.
- **Prefix defaults to empty string**: set `Prefix=""` on `processor_json` / `processor_parse_json_native` so JSON keys map directly to field names (avoids `_user_id` etc.).

## 2. Common fields

- Dimensions: `service`, `env`, `host`, `namespace`, `pod_name`, `container_name`, `cluster_id`, `region`.
- Trace/request: `trace_id`, `span_id`, `request_id`, `user_id` (desensitized), `client_ip`, `method`, `path`, `status_code` (numeric), `latency_ms` (numeric), `bytes_in`, `bytes_out`.
- Log semantics: `level`, `message`, `raw_message` (optional), `module`, `event_type`, `error_code`, `error_message`.

## 3. Parse mapping examples

- `content` -> `message` (business body after successful parse).
- `status` -> `status_code` (text status unified to numeric semantic).
- `req_time` -> `latency_ms` (unify units; avoid s/ms mix).

## 4. Index priority

- High: `service`, `env`, `level`, `trace_id`, `request_id`, `status_code`.
- K8s: `namespace`, `pod_name`, `container_name`, `cluster_id`.
- Optional: `module`, `error_code`, `client_ip`.

## 5. Full-text index template (the `--line` object of create/update-index)

```json
{
  "token": [",", " ", "\t", "\n", ":", "=", "\"", "'"],
  "caseSensitive": false,
  "chn": true
}
```

Field index (`--keys`) must match the fields processors actually output. HTTP status code fields default to `long` (see field-type table in `index-coupling.md`).
Floating-point fields use SLS index type `double`; `float` is a user-facing semantic alias, not a valid SLS index type.
`includeChinese` is not a valid SLS CLI index field; use `chn`.
