# DataHub ConnectionProperties Documentation

## Overview

- **Data Source Type**: `datahub`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where DataHub is located. |
| `endpoint` | String | `http://dh-cn-shanghai.aliyuncs.com` | Yes | DataHub access endpoint. |
| `project` | String | `project-name` | Yes | DataHub project name. |
| `accessId` | String | `xxxxx` | Yes | The accessId used to access the data source in AK mode. Required when using AK mode. |
| `accessKey` | String | `xxxxx` | Yes | The accessKey used to access the data source in AK mode. Required when using AK mode. |
| `envType` | String | `Dev` | Yes | Indicates the data source environment information. Valid values: <br>- `Dev`: Development environment <br>- `Prod`: Production environment |

---

## Configuration Example

### Connection String Mode

```json
{
    "envType": "Prod",
    "endpoint": "http://dh-cn-shanghai.aliyuncs.com",
    "project": "jiangcheng-test1",
    "accessId": "xxx",
    "accessKey": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/datahub*
