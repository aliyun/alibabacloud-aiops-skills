# Elasticsearch Datasource Documentation

## Property Definition

- **Datasource Type**: `elasticsearch`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode`, `UrlMode`

---

## InstanceMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | Instance region. |
| `instanceId` | String | `es-xxxxx` | Yes | Elasticsearch instance ID. |
| `instanceType` | String | `cloudNative` | Yes | Instance type. Values:<br>• `cloudNative`: Cloud-native<br>• `serverless`: Serverless |
| `username` | String | `elastic` | Yes | Username. |
| `password` | String | `xxx` | Yes | Password. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `endpoint` | String | `http://esxxx.elasticsearch.aliyuncs.com:9200` | Yes | Elasticsearch connection endpoint. |
| `authEnable` | String | `enable` | Yes | Enable authentication. Values: `enable`, `disable`. Default: `enable`. |
| `username` | String | `elastic` | Conditional | Username. Required when `authEnable=enable`. |
| `password` | String | `xxx` | Conditional | Password. Required when `authEnable=enable`. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### InstanceMode

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "instanceId": "es-xxxxx",
  "instanceType": "cloudNative",
  "username": "elastic",
  "password": "<PASSWORD>"
}
```

### UrlMode (With Authentication)

```json
{
  "envType": "Prod",
  "endpoint": "http://esxxx.elasticsearch.aliyuncs.com:9200",
  "authEnable": "enable",
  "username": "elastic",
  "password": "<PASSWORD>"
}
```

### UrlMode (Anonymous)

```json
{
  "envType": "Prod",
  "endpoint": "http://192.168.1.100:9200",
  "authEnable": "disable"
}
```
