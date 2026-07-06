# Filebeat processors — per-processor options

> Sources: per-processor pages under https://www.elastic.co/docs/reference/beats/filebeat/
>
> Companion to `06-processors.md` (overview / ordering / `when`). This file holds the full option list for the processors most often combined with file/Kafka/syslog log inputs heading to Elasticsearch.

Reading rules:

- Every processor accepts a `when:` (or `if:` / `then:` / `else:`) block on top of its own fields. Condition syntax is in `11-conditions.md`.
- Most field-modification processors share `ignore_missing` (skip when source absent) and `fail_on_error` (rollback vs. continue) — both default semantics noted per processor.

## add_host_metadata

| Field | Type | Default | Notes |
|---|---|---|---|
| `netinfo.enabled` | bool | `true` | Adds `host.ip` / `host.mac`. |
| `cache.ttl` | duration | `5m` | Negative disables cache. |
| `replace_fields` | bool | `true` | When `false`, keep pre-existing `host.*`. |
| `geo.name` | string | — | Free label for a DC/rack. |
| `geo.location` | string | — | `lat, lon`. |
| `geo.continent_name` / `country_name` / `country_iso_code` / `region_name` / `region_iso_code` / `city_name` | string | — | Static values; nothing is geocoded. |

```yaml
- add_host_metadata:
    cache.ttl: 5m
    geo:
      name: nyc-dc1-rack1
      location: 40.7128, -74.0060
      country_iso_code: US
```

For Beats running off-host (collecting from another machine) prefer `add_observer_metadata`.

## add_cloud_metadata

| Field | Type | Default | Notes |
|---|---|---|---|
| `timeout` | duration | `3s` | If exceeded, no metadata is added. |
| `providers` | []string | enabled providers below | Whitelist; `BEATS_ADD_CLOUD_METADATA_PROVIDERS` env var (comma-separated) overrides. |
| `overwrite` | bool | `false` | Replace existing `cloud.*`. |
| `ssl` | object | — | TLS for HTTP client (see `07-ssl.md`). |

Providers (default-on unless noted): `aws`/`ec2`, `azure`, `gcp`, `digitalocean`, `openstack`/`nova`/`huawei`, `openstack-ssl`/`nova-ssl`, `hetzner`. Off by default (need remote endpoint): `alibaba`/`ecs`, `tencent`/`qcloud`. AKS-managed Azure clusters fill `orchestrator.cluster.{name,id}` using `TENANT_ID`/`CLIENT_ID`/`CLIENT_SECRET` env vars (DefaultAzureCredential fallback).

```yaml
- add_cloud_metadata: ~
```

## add_kubernetes_metadata

| Field | Type | Default | Notes |
|---|---|---|---|
| `node` | string | — | Set when host network mode breaks auto-detection. |
| `scope` | enum | `node` | Or `cluster`. |
| `namespace` | string | — | Restrict watch to one namespace. |
| `kube_config` | path | `$KUBECONFIG` then in-cluster | Kubeconfig path. |
| `use_kubeadm` | bool | `true` | Read `kubeadm-config` ConfigMap for cluster name. |
| `kube_client_options.qps` / `.burst` | number | — | Tune client throughput. |
| `cleanup_timeout` | duration | `60s` | Stop a container's running config after inactivity. |
| `sync_period` | duration | — | Resource list timeout. |
| `add_resource_metadata.{node,namespace,deployment,cronjob}` | object | — | `enabled`, `include_labels`, `exclude_labels`, `include_annotations`. |
| `default_indexers.enabled` | bool | `true` | Toggle built-in indexers. |
| `default_matchers.enabled` | bool | `true` | Toggle built-in matchers. |
| `labels.dedot` | bool | `true` | `.` → `_` in labels. |
| `annotations.dedot` | bool | `true` | Same for annotations. |

Indexers: `container`, `ip_port`, `pod_name`, `pod_uid`. Matchers: `field_format` (build key from `format` string), `fields` (`lookup_fields` first-present-wins, optional `regex_pattern` with named capture `key`), `logs_path` (parse identifiers from `log.file.path`; `resource_type: container|pod`).

Filebeat default = `container` indexer + `logs_path` matcher.

```yaml
- add_kubernetes_metadata:
    # in-cluster + default indexer/matcher works out of the box for Filebeat
```

Custom example (off-host or non-default lookup):

```yaml
- add_kubernetes_metadata:
    node: ${NODE_NAME}
    kube_config: ~/.kube/config
    default_indexers.enabled: false
    default_matchers.enabled: false
    indexers:
      - ip_port:
    matchers:
      - fields:
          lookup_fields: ["metricset.host"]
```

RBAC: a ServiceAccount needs `get/list/watch` on `pods`, `namespaces`, `nodes`. With `use_kubeadm: true`, also `get` on the `kubeadm-config` ConfigMap in `kube-system`. Apply via a `ClusterRole` + `ClusterRoleBinding` (or `Role` if `scope: node` and you can scope down).

## add_docker_metadata

| Field | Type | Default | Notes |
|---|---|---|---|
| `host` | string | `unix:///var/run/docker.sock` | Daemon socket. |
| `ssl` | object | — | TLS to a TCP socket. |
| `match_fields` | []string | — | Field names checked for a container ID. |
| `match_pids` | []string | `["process.pid","process.parent.pid"]` | Used when the producer runs in Docker. |
| `match_source` | bool | `true` | Pull container ID from `log.file.path`. |
| `match_short_id` | bool | `false` | Match 12-char short IDs in paths. |
| `cleanup_timeout` | duration | `60s` | Drop cached metadata after inactivity. |
| `labels.dedot` | bool | `true` | `.` → `_` in labels. |

Mount `/var/run/docker.sock` and run as root when Filebeat itself runs in a container.

## decode_json_fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `fields` | []string | required | Source fields containing JSON strings. |
| `process_array` | bool | `false` | Recurse into arrays. |
| `max_depth` | int | `1` | Decoding depth. |
| `target` | string | replace source | `""` merges into root. `null` = unset. |
| `overwrite_keys` | bool | `false` | Allow decoded keys to replace existing. |
| `expand_keys` | bool | `false` | `{"a.b.c":1}` → `{"a":{"b":{"c":1}}}`. |
| `add_error_key` | bool | `false` | Record decode errors in `error.*`. |
| `document_id` | string | — | Move named JSON key into `@metadata._id`. |

```yaml
- decode_json_fields:
    fields: [message]
    target: ""
    max_depth: 2
    add_error_key: true
```

## dissect

| Field | Type | Default | Notes |
|---|---|---|---|
| `tokenizer` | string | required | Pattern with `%{…}` placeholders. |
| `field` | string | `message` | Source field. |
| `target_prefix` | string | `dissect` | `""` → keys at root. |
| `ignore_failure` | bool | `false` | Silently keep original event on no-match. |
| `overwrite_keys` | bool | `false` | Allow replacing existing fields. |
| `trim_values` | enum | `none` | `none` / `left` / `right` / `all`. |
| `trim_chars` | string | `" "` | Chars to trim; combine in one string. |

Tokenizer modifiers:

- `%{key}` — capture into `key`. Append `|type` for conversion: `integer`, `long`, `float`, `double`, `boolean`, `ip`. Example: `%{port|integer}`.
- `%{key->}` — collapse repeated trailing delimiters (multiple spaces).
- `%{?skipme}` — match-and-discard.
- `%{+key}` — append capture to a previously-named `key`.

Reserved modifier chars (cannot appear in key names): `/ & + # ?`. Match must succeed for **every** placeholder or the event is left untouched (or dropped, depending on `ignore_failure`).

```yaml
- dissect:
    tokenizer: '%{client.ip} - %{user.name} [%{@timestamp}] "%{http.request.method} %{url.original} %{http.version}"'
    field: message
    target_prefix: ""
```

## timestamp

| Field | Required | Default | Notes |
|---|---|---|---|
| `field` | yes | — | Source string field. |
| `target_field` | no | `@timestamp` | UTC always. |
| `layouts` | yes | — | Go reference layouts; `UNIX` and `UNIX_MS` accepted. |
| `timezone` | no | `UTC` | IANA name, fixed offset (`+0200`), or `Local`. |
| `ignore_missing` | no | `false` | Skip when source absent. |
| `ignore_failure` | no | `false` | Suppress all errors. |
| `test` | no | — | Sample timestamps validated at startup. |

Reference moment: `Mon Jan 2 15:04:05 MST 2006`.

| Format | Layout |
|---|---|
| ISO8601 UTC | `2006-01-02T15:04:05Z` |
| ISO8601 + ms | `2006-01-02T15:04:05.999Z` |
| ISO8601 + offset | `2006-01-02T15:04:05.999-07:00` |
| RFC3339 | `2006-01-02T15:04:05Z07:00` |
| Apache | `02/Jan/2006:15:04:05 -0700` |
| Date only | `2006-01-02` |
| Epoch s | `UNIX` |
| Epoch ms | `UNIX_MS` |

Layouts without a year reuse the current year in the configured `timezone`. (Beta — formats differ from Logstash/ES Ingest date processors.)

## fingerprint

| Field | Type | Default | Notes |
|---|---|---|---|
| `fields` | []string | required | Sorted alphabetically before hashing. Dotted nested paths supported. |
| `target_field` | string | `fingerprint` | Output field. |
| `method` | enum | `sha256` | `md5`, `sha1`, `sha256`, `sha384`, `sha512`, `xxhash`. |
| `encoding` | enum | `hex` | `hex`, `base32`, `base64`. |
| `ignore_missing` | bool | `false` | Skip when any listed field is absent. |

Hash input is `|field1|value1|field2|value2|` after sort.

## script

| Field | Notes |
|---|---|
| `lang` | Required; must be `javascript`. |
| `tag` | Identifier for log lines + enables exception/exec-time metrics. |
| `source` | Inline JS. |
| `file` | Single file path; relative to `path.config`; globs allowed. |
| `files` | List of files; concatenated. |
| `params` | Dict passed to a `register(scriptParams)` function. |
| `tag_on_exception` | Default `_js_exception`. |
| `timeout` | `process(event)` execution cap (no default). |
| `max_cached_sessions` | Default `4`. |

```yaml
- script:
    lang: javascript
    tag: redact_email
    source: |
      function process(evt) {
        var msg = evt.Get("message");
        if (msg) evt.Put("message", msg.replace(/[\w.+-]+@[\w.-]+/g, "[redacted]"));
      }
```

## drop_event

Required `when:` (or `if:`/`then:`); without one **all events drop**. No other fields.

```yaml
- drop_event:
    when:
      regexp:
        message: '^DBG:'
```

## Field-modification family

These share semantics: fields list with `from`/`to`, plus `ignore_missing` (default `false`) and `fail_on_error` (default `true`). All accept the `@metadata.` prefix on field paths to reach event metadata.

### add_fields

| Field | Notes |
|---|---|
| `target` | Sub-dictionary; default `fields`; `''` puts keys at root; `@metadata` writes to event metadata. |
| `fields` | Map of values (scalars/arrays/dicts). |

```yaml
- add_fields:
    target: project
    fields:
      name: myproject
      env: prod
```

### drop_fields

| Field | Notes |
|---|---|
| `fields` | Names to remove. Use `/regex/` (slashes) for pattern-match. |
| `ignore_missing` | Default `false`. |

`@timestamp` and `type` are protected and cannot be dropped.

```yaml
- drop_fields:
    fields: [agent.ephemeral_id, "/^debug_/"]
    ignore_missing: true
```

### rename

| Field | Notes |
|---|---|
| `fields[].from` / `.to` | Required pair. |
| `ignore_missing` | Default `false`. |
| `fail_on_error` | Default `true`. |

Cannot overwrite an existing destination — drop or rename it first.

```yaml
- rename:
    fields:
      - {from: "message", to: "event.original"}
```

### copy_fields

| Field | Notes |
|---|---|
| `fields[].from` / `.to` | Required pair. |
| `ignore_missing` | Default `false`. |
| `fail_on_error` | Default `true`. |

Cannot overwrite — drop the destination first.

### convert

| Field | Notes |
|---|---|
| `fields[].from` | Required. |
| `fields[].to` | Optional; without it the source is updated in place. |
| `fields[].type` | One of `integer`, `long`, `float`, `double`, `string`, `boolean`, `ip`. Omit to copy/rename without conversion. |
| `mode` | `copy` (default) or `rename` when both `from`+`to` set. |
| `tag` | Debug identifier. |
| `ignore_missing` | Default `false`. |
| `fail_on_error` | Default `true`. |

```yaml
- convert:
    fields:
      - {from: "src_ip",   to: "source.ip",   type: ip}
      - {from: "src_port", to: "source.port", type: integer}
    fail_on_error: false
```

### truncate_fields

| Field | Notes |
|---|---|
| `fields` | Names. |
| `max_bytes` | Mutually exclusive with `max_characters`. |
| `max_characters` | Mutually exclusive with `max_bytes`. |
| `fail_on_error` | Default `true`. |
| `ignore_missing` | Default `false`. |

### urldecode

| Field | Notes |
|---|---|
| `fields[].from` | Required. |
| `fields[].to` | Defaults to `from` (decode in place). |
| `ignore_missing` | Default `false`. |
| `fail_on_error` | Default `true`. |

### replace

| Field | Notes |
|---|---|
| `fields[].field` | Existing field to modify. |
| `fields[].pattern` | Regex matched against current value. |
| `fields[].replacement` | Replacement string. |
| `ignore_missing` | Default `false`. |
| `fail_on_error` | Default `true`. |

Cannot create new values — only mutate. Useful for masking or path rewriting.

### extract_array (technical preview)

| Field | Notes |
|---|---|
| `field` | Source array. |
| `mappings` | `target_field: index` map (0-based; same index reusable). |
| `ignore_missing` | Default `false`. |
| `overwrite_keys` | Default `false`. |
| `fail_on_error` | Default `true`. |

```yaml
- extract_array:
    field: parts
    mappings:
      source.ip: 0
      destination.ip: 1
      network.transport: 2
```

## Choosing between layers

| Need | Use |
|---|---|
| Drop a noisy line by content | `include_lines` / `exclude_lines` on input (cheaper) |
| Drop after parsing | `drop_event` with a `when:` condition |
| Add static labels to every event | `add_fields` (or top-level `fields:` — see `14-filebeat-general-settings.md`) |
| Mask PII | `replace` (regex), `script` (custom), or `truncate_fields` |
| Promote nested JSON | `decode_json_fields` (with `target: ""`) |
| Tokenize unstructured lines | `dissect` (cheap) > `script` (flexible) |
| Hash for dedup keys | `fingerprint` |
| Enrich from runtime | `add_host_metadata`, `add_cloud_metadata`, `add_kubernetes_metadata`, `add_docker_metadata` |
