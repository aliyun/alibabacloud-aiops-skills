# Memcache Data Source ConnectionProperties

## Basic Information

- **Data source type**: `memcache`
- **Supported configuration mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| proxy | String | `127.0.0.1` | Yes | Proxy Host. |
| port | String | `22` | Yes | Port number. |
| username | String | `xxxxx` | Yes | Username. |
| password | String | `xxxxx` | Yes | Password. |
| envType | String | `Dev` | Yes | envType indicates data source environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Configuration Examples

### Connection String Mode

```json
{
  "proxy": "127.0.0.1",
  "port": "5432",
  "username": "xxxxx",
  "password": "xxxxx",
  "envType": "Dev"
}
```

---

**Last updated**: 2024-10-15 09:32:01

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/memcache
