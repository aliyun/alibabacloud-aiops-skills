# Salesforce Datasource Documentation

## Property Definition

- **Datasource Type**: `salesforce`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `type` | String | `rest` | Yes | API type. Currently only supports `rest`. |
| `instanceUrl` | String | `https://xxxxx.my.salesforce.com` | Yes | Salesforce instance URL. |
| `refreshToken` | String | `xxx` | Yes | Refresh token for long-term authentication. |
| `apiVersion` | String | `v58.0` | Yes | API version. Default: `v58.0`. Available versions: `v31.0`~`v58.0`. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Example

```json
{
  "envType": "Prod",
  "type": "rest",
  "instanceUrl": "https://xxxxx.my.salesforce.com",
  "refreshToken": "<REFRESH_TOKEN>",
  "apiVersion": "v58.0"
}
```

---

## Notes

> Salesforce data source uses OAuth authentication. You need to complete the authorization process through the console to obtain the refreshToken. The refreshToken is long-lived and used to automatically refresh access tokens.
