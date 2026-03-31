# KingbaseES Datasource ConnectionProperties Documentation

## Overview

- **Datasource Type**: `kingbasees`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `address` | JSON Array | Yes | An array format, but only allows configuration of 1 set of host and port. |
| `database` | String | Yes | Database name. |
| `username` | String | Yes | Username. |
| `password` | String | Yes | Password. |
| `properties` | JSON Object | No | Driver properties. |
| `envType` | String | Yes | Indicates the datasource environment information. Options: `Dev` (Development environment) or `Prod` (Production environment). |

---

## Parameter Details

### address

**Type**: JSON Array

**Example**:
```json
[
    {
        "host": "127.0.0.1",
        "port": 3306
    }
]
```

**Note**: Although it's an array format, only one set of host and port is allowed.

---

### database

**Type**: String

**Example**: `mysql_database`

**Description**: The name of the database.

---

### username

**Type**: String

**Example**: `xxxxx`

**Description**: The username for authentication.

---

### password

**Type**: String

**Example**: `xxxxx`

**Description**: The password for authentication.

---

### properties

**Type**: JSON Object

**Example**:
```json
{
    "useSSL": "false"
}
```

**Description**: Driver properties (optional).

---

### envType

**Type**: String

**Example**: `Dev`

**Description**: Indicates the datasource environment information.

**Valid Values**:
- `Dev`: Development environment
- `Prod`: Production environment

---

## Configuration Example

### Connection String Mode

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

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/kingbasees
