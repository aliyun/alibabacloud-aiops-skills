# Graph Database Connection Properties Documentation

## Overview

- **Data Source Type**: `graph_database`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `host` | String | `10.0.0.1` | Yes | Graph instance domain name. |
| `port` | String | `22` | Yes | Graph instance port number. |
| `username` | String | `xxxxx` | No | Graph instance account. |
| `password` | String | `xxxxx` | No | Graph instance password. |
| `envType` | String | `Dev` | Yes | Indicates the data source environment information. Possible values: <br>- `Dev`: Development environment <br>- `Prod`: Production environment |

---

## Configuration Example

### Connection String Mode

```json
{
  "host": "127.0.0.1",
  "port": "5432",
  "username": "xxxxx",
  "password": "xxxxx",
  "envType": "Dev"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/graph-database*

*Last Updated: 2024-10-15 09:31:48*
