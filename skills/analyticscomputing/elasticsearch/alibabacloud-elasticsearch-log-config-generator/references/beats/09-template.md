# Filebeat Index Template (setup.template)

> Source: https://www.elastic.co/docs/reference/beats/filebeat/configuration-template

Controls the Elasticsearch index template used for field mappings.

## Settings

| Setting | Default | Description |
|---|---|---|
| `setup.template.enabled` | `true` | Toggles template loading. |
| `setup.template.name` | `filebeat` | Template name (version appended). |
| `setup.template.pattern` | `filebeat` | Index pattern (version appended). |
| `setup.template.fields` | `fields.yml` | Path to fields definition. |
| `setup.template.overwrite` | `false` | Overwrite existing template. |
| `setup.template.settings` | — | Map under `settings.index` (shards/replicas/etc.). |
| `setup.template.append_fields` | — | Append fields without modifying existing. |
| `setup.template.json.*` | — | Use custom JSON template file. |

## Default

```yaml
setup.template.name: "filebeat"
setup.template.pattern: "filebeat"
```

## Custom template with index settings

```yaml
setup.template.name: "myapp"
setup.template.pattern: "myapp-*"
setup.template.fields: "fields.yml"
setup.template.overwrite: false
setup.template.settings:
  index.number_of_shards: 1
  index.number_of_replicas: 1
```

## JSON template

```yaml
setup.template.json.enabled: true
setup.template.json.path: "template.json"
setup.template.json.name: "template-name"
setup.template.json.data_stream: true
```
