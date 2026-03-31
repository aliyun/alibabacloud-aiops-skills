# LogHub Data Source ConnectionProperties

## Property Definition

- **Data source type**: `loghub`
- **Supported configuration mode**: UrlMode (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-sanghai | Yes | Region where LogHub is located. |
| endpoint | String | http://cn-beijing.log.aliyuncs.com | Yes | LogHub access endpoint. |
| project | String | project-name | Yes | LogHub project name. |
| accessId | String | xxxxx | Yes | AccessId used for accessing the data source in AK mode. Required in AK mode. |
| accessKey | String | xxxxx | Yes | AccessKey used for accessing the data source in AK mode. Required in AK mode. |
| envType | String | Dev | Yes | envType indicates data source environment information.<br>- **Dev**: Development environment<br>- **Prod**: Production environment |

---

## Configuration Examples

### Connection String Mode

```json
{
    "envType": "Prod",
    "endpoint": "http://cn-beijing.log.aliyuncs.com",
    "project": "jiangcheng-test1",
    "accessId": "xxx",
    "accessKey": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/loghub*
