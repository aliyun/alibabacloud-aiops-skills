# Filebeat processors — additional reference

> Sources: per-processor pages under https://www.elastic.co/docs/reference/beats/filebeat/
>
> Companion to `06-processors.md` (overview / ordering / `when`) and `13-filebeat-processors-detail.md` (the most-used processors). This file holds the rest commonly named in log pipelines but not yet detailed.

## community_id

Computes a Wireshark Community ID from network 5-tuple fields. ECS-shaped events need no parameters.

| Field | Notes |
|---|---|
| `fields.source_ip` / `source_port` / `destination_ip` / `destination_port` / `iana_number` / `transport` / `icmp_type` / `icmp_code` | Override input field names when not ECS. |
| `target` | Output field. Default `network.community_id`. |
| `seed` | 16-bit unsigned integer mixed into the hash; default `0`. |

```yaml
- community_id: ~
```

If required input fields are missing, the processor silently skips the event.

## decode_xml

| Field | Default | Notes |
|---|---|---|
| `field` | `message` | Source. |
| `target_field` | — | Destination; `""` merges decoded keys at root. |
| `overwrite_keys` | `true` | Whether existing keys can be replaced. |
| `document_id` | — | Key from XML to lift into `@metadata._id`. |
| `to_lower` | `true` | Lowercases all decoded keys. |
| `ignore_missing` | `false` | Skip when source absent. |
| `ignore_failure` | `false` | Suppress all errors. |

```yaml
- decode_xml:
    field: message
    target_field: xml
```

## decode_cef

| Field | Default | Notes |
|---|---|---|
| `field` | `message` | Source. |
| `target_field` | `cef` | Destination object. |
| `ecs` | `true` | Emit ECS fields too. |
| `timezone` | `UTC` | IANA name or fixed offset; `Local` uses host zone. |
| `ignore_missing` | `false` | Skip when source absent. |
| `ignore_failure` | `false` | Skip when source isn't CEF. |
| `ignore_empty_values` | `false` | Drop CEF extensions with empty values. |
| `id` | — | Identifier label. |

Decoded CEF includes its own `message` field — rename the original first:

```yaml
- rename:
    fields:
      - {from: message, to: event.original}
- decode_cef:
    field: event.original
```

## decompress_gzip_field

| Field | Default | Notes |
|---|---|---|
| `field.from` / `.to` | required | Source / destination field names. |
| `ignore_missing` | `false` | Skip when source absent. |
| `fail_on_error` | `true` | Rollback vs continue. |

```yaml
- decompress_gzip_field:
    field: {from: gzip_blob, to: message}
```

Cannot overwrite an existing destination — drop or rename first.

## registered_domain

Splits an FQDN into registered domain / eTLD / subdomain (Public Suffix List).

| Field | Required | Notes |
|---|---|---|
| `field` | yes | Source FQDN. |
| `target_field` | yes | Where the registered domain is written (e.g., `google.co.uk`). |
| `target_etld_field` | no | Where the effective TLD goes (e.g., `co.uk`). |
| `target_subdomain_field` | no | Where the subdomain goes (e.g., `www`). |
| `ignore_missing` | no | Default `false`. |
| `ignore_failure` | no | Default `false`. |
| `id` | no | Debug label. |

```yaml
- registered_domain:
    field: dns.question.name
    target_field: dns.question.registered_domain
    target_etld_field: dns.question.top_level_domain
    target_subdomain_field: dns.question.subdomain
```

## syslog (processor)

Parses a syslog string already inside a field (distinct from the syslog **input** in `10-input-syslog.md`).

| Field | Default | Notes |
|---|---|---|
| `field` | `message` | Source. |
| `format` | `auto` | `rfc3164` / `rfc5424` / `auto`. |
| `timezone` | `Local` | IANA name or fixed offset. Applies to timestamps without a zone. |
| `overwrite_keys` | `true` | Whether parsed fields can replace existing keys. |
| `ignore_missing` | `false` | Skip when source absent. |
| `ignore_failure` | `false` | Suppress all errors. |
| `tag` | — | Debug label. |

```yaml
- syslog:
    field: message
    format: rfc5424
    timezone: UTC
```

## append

| Field | Default | Notes |
|---|---|---|
| `target_field` | required | Destination (created if missing). |
| `fields` | — | Source field names whose values are pushed in. Array values are spread element-by-element. |
| `values` | — | Literal values to push. |
| `ignore_missing` | `false` | Skip when a source field is absent. |
| `ignore_empty_values` | `false` | Skip `""` and `nil`. |
| `fail_on_error` | `true` | Rollback vs continue. |
| `allow_duplicate` | `true` | When `false`, existing values aren't re-appended. |

```yaml
- append:
    target_field: tags
    values: [filebeat, prod]
    allow_duplicate: false
```

## move_fields

Re-parents fields under a different prefix.

| Field | Default | Notes |
|---|---|---|
| `from` | event root | Source object/prefix; nested fields included. |
| `fields` | all under `from` | Whitelist of specific fields to move. |
| `exclude` | — | Fields under `from` to leave behind. |
| `to` | required | Destination prefix. |
| `ignore_missing` | `false` | Skip when source absent. |

```yaml
- move_fields:
    from: app
    fields: [method, elapsed_time]
    to: "rpc."
```

Result: `app.method` / `app.elapsed_time` → `app.rpc.method` / `app.rpc.elapsed_time`.

## add_observer_metadata (beta)

For Beats running off-host (collecting from another machine), this attaches **observer.\*** instead of **host.\*** — preferred over `add_host_metadata` in that case.

| Field | Default | Notes |
|---|---|---|
| `netinfo.enabled` | `true` | Adds `observer.ip` / `observer.mac`. |
| `cache.ttl` | `5m` | Negative disables cache. |
| `geo.name` / `location` / `continent_name` / `country_iso_code` / `region_name` / `region_iso_code` / `city_name` | — | Static labels. |

```yaml
- add_observer_metadata:
    geo:
      name: edge-collector-01
      country_iso_code: US
```
