# BigQuery Datasource Documentation

## Overview

- **Datasource Type**: `bigquery`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## ConnectionProperties Parameters

### Connection String Mode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `bigQueryProjectId` | String | `bigquery_id` | **Yes** | The ID of the BigQuery Project. |
| `bigQueryAuth` | String | `123` | **Yes** | BigQuery authentication credentials. Enter the file ID. |
| `envType` | String | `Dev` | **Yes** | Indicates the datasource environment information. <br>• `Dev`: Development environment <br>• `Prod`: Production environment |

---

## Configuration Example

### Connection String Mode

```json
{
  "bigQueryProjectId": "bigquery_id",
  "bigQueryAuth": "123",
  "envType": "Dev"
}
```

---

## API Reference Summary

| Property | Value |
|----------|-------|
| Datasource Type (`type`) | `bigquery` |
| ConnectionPropertiesMode | `UrlMode` |
| Required Parameters | `bigQueryProjectId`, `bigQueryAuth`, `envType` |

---

**Source**: [Aliyun DataWorks Developer Reference - BigQuery](https://help.aliyun.com/zh/dataworks/developer-reference/bigquery)  
**Last Updated**: 2024-10-15
