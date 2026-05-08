# DataX Content Format (content)

## content

```json
{
  "type": "job",
  "version": "2.0",
  "steps": [
    {
      "stepType": "<source datasource type>",
      "parameter": {
        "column": [],
        "datasource": "<source datasource name>"
      },
      "name": "Reader",
      "category": "reader"
    },
    {
      "stepType": "<destination datasource type>",
      "parameter": {
        "column": [],
        "datasource": "<destination datasource name>"
      },
      "name": "Writer",
      "category": "writer"
    }
  ],
  "setting": {
    "errorLimit": {
      "record": "0"
    },
    "speed": {
      "throttle": false,
      "concurrent": 3
    }
  },
  "extend": {
    "mode": "code",
    "__new__": true,
    "formatType": "datax",
    "resourceGroup": "<resource group identifier>",
    "cu": "0.5"
  }
}
```

## extend

```json
{
  "extend": {
    "mode": "code",
    "__new__": true,
    "formatType": "datax",
    "resourceGroup": "<resource group identifier>",
    "cu": "<CU configuration value>"
  }
}
```

| Field | Description                                                                 | Required |
|-------|-----------------------------------------------------------------------------|----------|
| mode | Edit mode: `wizard` (wizard mode) or `code` (script mode) ，default `code` | Y |
| `__new__` | Whether to support the new interaction, default `true`                      | Y |
| formatType | Format type: `datax` (standard DataX)                                       | Y |
| resourceGroup | Resource group identifier (use identifier, not name)                        | Y |
| cu | CU configuration value                                                      | Y |

## Key Fields

| Field | Description |
|-------|-------------|
| `steps[].stepType` | Datasource type, e.g. `mysql`, `odps`, `holo`, etc. See each datasource reference document for details |
| `steps[].parameter.column` | Sync columns, must be explicitly specified; format varies by datasource type |
| `steps[].parameter.datasource` | Datasource name (must match the name registered in DataWorks datasource management) |
| `setting.errorLimit.record` | Error tolerance record count; `"0"` means no tolerance |
| `setting.speed.concurrent` | Maximum concurrency, range 1-32 |
| `setting.speed.throttle` | Whether to throttle; `false` means no throttle |
