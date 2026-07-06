# Filebeat Processors

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filtering-enhancing-data

Two filtering layers:
1. **Input-level** (`include_lines`, `exclude_lines`, `exclude_files`).
2. **Global processors** at the top level of the config — run before output.

## Execution model

Processors run sequentially in declaration order. Place destructive operations (`drop_fields`, `rename`) **last** so earlier processors still see the fields they need.

## Conditional `when`

```yaml
processors:
  - drop_event:
      when:
        regexp:
          message: '^DBG:'
  - drop_event:
      when:
        contains:
          source: 'test'
```

Supported condition types: `equals`, `contains`, `regexp`, `range`, `network`, `has_fields`, `or`, `and`, `not`. Full syntax incl. `range` shorthand, named CIDR ranges, and `if`/`then`/`else` form: see `11-conditions.md`.

## Common processors

| Processor | Purpose |
|---|---|
| `add_host_metadata` | Adds host info (hostname, OS, IP). |
| `add_cloud_metadata` | Detects AWS/GCP/Azure metadata. |
| `add_kubernetes_metadata` | Adds k8s pod/container metadata. |
| `add_docker_metadata` | Adds Docker container metadata. |
| `add_fields` | Adds static fields. |
| `drop_fields` | Removes specified fields. |
| `drop_event` | Conditionally drops event. |
| `rename` | Renames fields. |
| `decode_json_fields` | Parses stringified JSON in a field. |
| `dissect` | Tokenize unstructured strings. |
| `timestamp` | Parse timestamps from a field. |
| `fingerprint` | Computes hash from selected fields. |
| `community_id` | Network flow community ID. |
| `script` | Run custom JS/JavaScript on events. |

## Decode JSON example

Input event has a stringified JSON field:

```json
{ "outer": "value", "inner": "{\"data\": \"value\"}" }
```

```yaml
filebeat.inputs:
  - type: filestream
    paths: [input.json]
    parsers:
      - ndjson:
          target: ""

processors:
  - decode_json_fields:
      fields: [inner]
```

## Multi-processor sample

```yaml
processors:
  # 1) Add host context first so later processors can use it
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_cloud_metadata: ~

  # 2) Decode embedded JSON
  - decode_json_fields:
      fields: [message]
      target: json
      max_depth: 2

  # 3) Conditional drops
  - drop_event:
      when:
        regexp:
          message: '^DBG:'

  # 4) Field modifications (LAST)
  - rename:
      fields:
        - {from: "outer", to: "event.outer"}
  - drop_fields:
      fields: [unwanted_field]
```

## Key rules

1. Per-input options for simple per-input filtering; processors for global transformations.
2. Order matters; destructive ops last.
3. `when` clause can use any condition type.
