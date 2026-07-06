# resource processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/resourceprocessor/README.md
>
> Lighter cousin of `attributesprocessor` — same action grammar, but operates on **resource** attributes (the entity producing telemetry) instead of per-record attributes. Reach for this when you just need to add/rename/drop a few resource keys without OTTL.

## Actions (shared with attributesprocessor)

| Action | Behavior |
|---|---|
| `INSERT` | Add only if key absent. |
| `UPDATE` | Modify existing key. |
| `UPSERT` | Insert if absent, else update. |
| `DELETE` | Remove. |
| `HASH` | Replace existing value with SHA-256 hash. |
| `EXTRACT` | Pull values out via regex into new attributes (see attributesprocessor README for `pattern` syntax). |

## Per-attribute fields

- `key` — target attribute name.
- `value` — literal value (when not using `from_*`).
- `action` — one of the actions above.
- `from_attribute` — copy value from another attribute on the same resource.
- `from_context` — pull from request context (e.g., `metadata.<header>`).
- `default_value` — fallback when source attribute / context value is missing.

## Stability

Beta for traces / metrics / logs; profiles in development.

## Examples

Set fixed value, drop redundant key:

```yaml
processors:
  resource:
    attributes:
      - key: cloud.availability_zone
        value: "zone-1"
        action: upsert
      - key: redundant-attribute
        action: delete
```

Copy from another attribute with a default + pull a tenant from request metadata:

```yaml
processors:
  resource:
    attributes:
      - key: region
        from_attribute: cloud.region
        default_value: "us-east-1"
        action: insert
      - key: tenant_id
        from_context: "metadata.tenant"
        default_value: "default-tenant"
        action: upsert
```

## When to use which

| Need | Use |
|---|---|
| Add/rename one resource attribute | `resource` |
| Add/rename one log-record attribute | `attributes` |
| Conditional (where) or function-rich rewrite (`replace_pattern`, `ParseJSON`, `IsMatch` …) | `transform` (OTTL) |
| Auto-detect host/cloud/k8s metadata | `resourcedetection` |
| Drop telemetry by condition | `filter` |
