# Filebeat ILM (setup.ilm)

> Source: https://www.elastic.co/docs/reference/beats/filebeat/ilm

Index Lifecycle Management — when enabled, Filebeat creates a managed data stream and uses an ILM policy to roll over and retire indices.

## Options

| Setting | Default | Description |
|---|---|---|
| `setup.ilm.enabled` | `auto` (typically true) | Enable/disable ILM. |
| `setup.ilm.policy_name` | `filebeat` | Lifecycle policy name. |
| `setup.ilm.policy_file` | — | Path to JSON policy file. |
| `setup.ilm.check_exists` | `true` | If `false`, skip policy existence check (no install even with `overwrite`). |
| `setup.ilm.overwrite` | `false` | If `true`, replace existing policy at startup. |

## Interaction with `output.elasticsearch.index`

When ILM is enabled (the default), `setup.template.name` and `setup.template.pattern` are ignored. The custom `index` field on the output is also typically ignored — to use a fully custom index, set `setup.ilm.enabled: false`.

## Minimum sample (default policy)

```yaml
setup.ilm.enabled: true
```

## Custom policy

```yaml
setup.ilm.enabled: true
setup.ilm.policy_name: "my-app-logs"
setup.ilm.policy_file: "/etc/filebeat/policies/my-policy.json"
setup.ilm.overwrite: false
```

## Disable ILM and use a static daily index

```yaml
setup.ilm.enabled: false
setup.template.name: "myapp-logs"
setup.template.pattern: "myapp-logs-*"
output.elasticsearch:
  hosts: ["https://es:9200"]
  index: "myapp-logs-%{+yyyy.MM.dd}"
```
