# HttpFile Datasource Documentation

## Property Definition

- **Datasource Type**: `httpfile`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `urlPrefix` | String | `http://127.0.0.1` | Yes | URL domain/prefix. |
| `defaultHeaders` | String | `{}` | Yes | HTTP request headers as JSON string. Each key is header name, value is header value. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### Basic Configuration

```json
{
  "envType": "Prod",
  "urlPrefix": "http://example.com",
  "defaultHeaders": "{}"
}
```

### With Custom Headers

```json
{
  "envType": "Prod",
  "urlPrefix": "http://example.com",
  "defaultHeaders": "{\"Authorization\": \"Bearer <TOKEN>\", \"Content-Type\": \"application/json\"}"
}
```
