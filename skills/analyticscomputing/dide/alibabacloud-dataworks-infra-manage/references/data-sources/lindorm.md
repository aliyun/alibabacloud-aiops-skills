# Lindorm Datasource Documentation

**Last Updated:** 2024-10-15 09:31:57

---

## Property Definition

| Property | Value |
|----------|-------|
| **Data Source Type (type)** | `lindorm` |
| **Supported Configuration Mode (ConnectionPropertiesMode)** | `UrlMode` (Connection String Mode) |

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `seedserver` | String | `ld-xxx.lindorm.rds.aliyuncs.com:30020` | Yes | Connection address. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `namespace` | String | `default` | Yes | Namespace. |
| `envType` | String | `Dev` | Yes | envType represents data source environment information. |
| | | | | - **Dev**: Development environment |
| | | | | - **Prod**: Production environment |

---

## Configuration Example

### Connection String Mode

```json
{
  "seedserver": "ld-xxx.lindorm.rds.aliyuncs.com:30020",
  "username": "xxxxx",
  "password": "xxxxx",
  "namespace": "default",
  "envType": "Dev"
}
```

---

## API Reference Summary

- **Source:** DataWorks Developer Reference > Appendix > Data Source Connection Information (ConnectionProperties)
- **Platform:** Alibaba Cloud DataWorks
- **Navigation:** Previous: KingbaseES | Next: LogHub
