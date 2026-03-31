# Doris Datasource Documentation

## Overview

- **Datasource Type**: `doris`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection Properties (UrlMode)

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `address` | Array | Yes | Query address. **Only a single address is allowed.** |
| `loadAddress` | String | Yes | FE Endpoint. **Multiple addresses are allowed.** |
| `database` | String | Yes | Database name. |
| `username` | String | Yes | Username for authentication. |
| `password` | String | Yes | Password for authentication. |
| `properties` | JSON Object | No | Driver properties. |
| `envType` | String | Yes | Datasource environment information. Values: `Dev` (Development environment) or `Prod` (Production environment). |

---

## Field Details

### address
- **Type**: Array
- **Required**: Yes
- **Example**:
  ```json
  [
    {
      "host": "127.0.0.1",
      "port": 3306
    }
  ]
  ```
- **Note**: Only a single address is allowed.

### loadAddress
- **Type**: String
- **Required**: Yes
- **Example**:
  ```json
  [
    {
      "host": "127.0.0.1",
      "port": 3306
    }
  ]
  ```
- **Note**: FE Endpoint; multiple addresses are allowed.

### database
- **Type**: String
- **Required**: Yes
- **Example**: `dbName`
- **Description**: The database name to connect to.

### username
- **Type**: String
- **Required**: Yes
- **Example**: `xxxxx`
- **Description**: Username for authentication.

### password
- **Type**: String
- **Required**: Yes
- **Example**: `xxxxx`
- **Description**: Password for authentication.

### properties
- **Type**: JSON Object
- **Required**: No
- **Example**:
  ```json
  {
    "useSSL": "false"
  }
  ```
- **Description**: Additional driver properties.

### envType
- **Type**: String
- **Required**: Yes
- **Example**: `Dev`
- **Description**: Represents the datasource environment information.
  - `Dev`: Development environment
  - `Prod`: Production environment

---

## Configuration Example (UrlMode)

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

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `address` | Array | Yes | Query endpoint (single address only) |
| `loadAddress` | String | Yes | FE endpoint (multiple addresses allowed) |
| `database` | String | Yes | Target database name |
| `username` | String | Yes | Authentication username |
| `password` | String | Yes | Authentication password |
| `properties` | JSON Object | No | Optional driver properties (e.g., `useSSL`, `socketTimeout`) |
| `envType` | String | Yes | Environment type: `Dev` or `Prod` |

---

**Source**: [Aliyun DataWorks Developer Reference - Doris](https://help.aliyun.com/zh/dataworks/developer-reference/doris)  
**Last Updated**: 2024-10-15
