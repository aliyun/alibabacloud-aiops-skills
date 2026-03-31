# Redshift Datasource Documentation

## Overview

- **Datasource Type:** `redshift`
- **Supported Configuration Mode:** `UrlMode` (Connection String Mode)

---

## ConnectionProperties Parameters (UrlMode)

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only **one set** of host and port is allowed. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Indicates the datasource environment. Valid values: `Dev` (Development environment), `Prod` (Production environment). |

---

## Configuration Example (UrlMode)

```json
{
    "address": [
        {
            "host": "127.0.0.1",
            "port": 5432
        }
    ],
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "xxxxx",
    "password": "xxxxx",
    "envType": "Dev"
}
```

---

## Field Details

### `address`
- **Type:** JSON Array
- **Required:** Yes
- **Notes:** Although formatted as an array, it only accepts a single host/port configuration pair.

### `database`
- **Type:** String
- **Required:** Yes
- **Description:** The name of the database to connect to.

### `username`
- **Type:** String
- **Required:** Yes
- **Description:** Authentication username.

### `password`
- **Type:** String
- **Required:** Yes
- **Description:** Authentication password.

### `properties`
- **Type:** JSON Object
- **Required:** No
- **Description:** Additional JDBC driver properties (e.g., `useSSL`, `connectTimeout`).

### `envType`
- **Type:** String
- **Required:** Yes
- **Valid Values:**
  - `Dev` - Development environment
  - `Prod` - Production environment
