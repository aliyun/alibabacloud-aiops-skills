# RESTAPI ConnectionProperties Documentation

## Property Definition

- **Data Source Type**: `restapi`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `url` | String | `http://test-ots-sh-shanghai.ots.aliyuncs.com` | Yes | URL. |
| `defaultHeader` | String | `{}` | No | Default request headers. |
| `securityProtocol` | String | `authTypeNone` | No | Authentication method. Supported values:<br>- `authTypeNone`<br>- `basic`<br>- `token`<br>Default value: `authTypeNone`. |
| `username` | String | `my-username` | No | Username. Required when `securityProtocol` is `basic`. |
| `password` | String | `<PASSWORD>` | No | Password. Required when `securityProtocol` is `basic`. |
| `authToken` | String | `my-token` | No | Token authentication. Required when `securityProtocol` is `token`. |
| `envType` | String | `Dev` | Yes | `envType` indicates the data source environment information.<br>- `Dev`: Development environment.<br>- `Prod`: Production environment. |

---

## Data Source Configuration Example

### Connection String Mode

```json
{
    "envType": "Prod",
    "url": "http://127.0.0.1/get",
    "securityProtocol": "basic",
    "username": "xxx",
    "password": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/restapi*
