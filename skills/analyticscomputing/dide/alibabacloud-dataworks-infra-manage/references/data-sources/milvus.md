# Milvus Data Source ConnectionProperties

**Data source type**: `milvus`

**Supported configuration modes**:
- InstanceMode (Instance Mode)
- UrlMode (Connection String Mode)

---

## Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-shanghai | Yes | Region where the instance is located. |
| ConnectionPropertiesMode | String | InstanceMode | Yes | Configuration mode |
| database | String | xxxxx | No | Database name |
| instanceId | String | c-dd8f**** | Yes | Instance ID |
| username | String | xxxxx | Yes | Username |
| password | String | xxxxx | Yes | Password |
| envType | String | Dev | Yes | envType indicates data source environment information.<br>- Dev: Development environment.<br>- Prod: Production environment. |

### Instance Mode Configuration Example

```json
{
    "envType": "Prod",
    "regionId": "cn-beijing",
    "instanceId": "c-dd8f71372xxxx",
    "database": "default",
    "username": "root",
    "password": "xxxxxxx"
}
```

---

## Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| endpoint | String | http://cmilvusxxxx.com:19530 | Yes | Connection endpoint |
| ConnectionPropertiesMode | String | UrlMode | Yes | Configuration mode |
| database | String | xxxxx | No | Database name |
| username | String | xxxxx | Yes | Username |
| password | String | xxxxx | Yes | Password |
| authType | String | USERNAME_PASSWORD | Yes | Authentication method |
| envType | String | Dev | Yes | envType indicates data source environment information.<br>- Dev: Development environment.<br>- Prod: Production environment. |

### Connection String Mode Configuration Example

```json
{
    "envType": "Prod",
    "endpoint": "http://c-dd8xxxxx.milvus.aliyuncs.com:19530",
    "database": "default",
    "username": "root",
    "password": "xxxx",
    "authType": "USERNAME_PASSWORD"
}
```

---

**Last updated**: 2025-03-27 14:05:17

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/milvus
