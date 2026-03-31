# SelectDB Datasource Documentation

## Overview

- **Data Source Type**: `selectdb`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)
- **Last Updated**: 2024-11-06

---

## Connection String Mode Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `address` | Array | Yes | Only a single address is allowed. |
| `loadAddress` | String | Yes | FE Endpoint, multiple addresses can be configured. |
| `database` | String | Yes | Database name. |
| `username` | String | Yes | Username. |
| `password` | String | Yes | Password. |
| `properties` | JSON Object | No | Driver properties. |
| `envType` | String | Yes | Indicates the datasource environment information. Values: `Dev` (Development environment) or `Prod` (Production environment). |

---

## Parameter Examples

### address
```json
[
  {
    "host": "127.0.0.1",
    "port": 3306
  }
]
```

### loadAddress
```json
[
  {
    "host": "127.0.0.1",
    "port": 3306
  }
]
```

### properties
```json
{
    "useSSL": "false"
}
```

---

## Complete Configuration Example

```json
{
    "envType": "Prod",
    "address": [
        {
            "host": "127.0.0.1",
            "port": "3306"
        }
    ],
    "loadAddress": [
        {
            "host": "127.0.0.2",
            "port": "8031"
        }
    ],
    "database": "my_database",
    "username": "my_username",
    "password": "<PASSWORD>",
    "properties": {
        "socketTimeout": "2000"
    }
}
```

---

## API Reference Summary

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `envType` | String | Yes | - | `Dev` or `Prod` |
| `address[].host` | String | Yes | - | Host IP address |
| `address[].port` | String/Number | Yes | - | Port number |
| `loadAddress[].host` | String | Yes | - | FE Endpoint host |
| `loadAddress[].port` | String/Number | Yes | - | FE Endpoint port |
| `database` | String | Yes | - | Target database name |
| `username` | String | Yes | - | Authentication username |
| `password` | String | Yes | - | Authentication password |
| `properties` | Object | No | - | Additional JDBC driver properties |
