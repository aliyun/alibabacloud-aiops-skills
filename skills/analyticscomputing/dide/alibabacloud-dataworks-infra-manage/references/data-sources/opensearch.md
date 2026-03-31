# OpenSearch ConnectionProperties Documentation

## Overview

**Data Source Type**: `opensearch`

**Supported Configuration Mode (ConnectionPropertiesMode)**:
- `InstanceMode` (Instance Mode)

---

## Instance Mode Parameters

| Name | Type | Example Value | Required | Description & Notes |
|------|------|---------------|----------|---------------------|
| `instanceType` | String | `vectorSearchVersion` | Yes | OpenSearch engine type. Options: <br>- `vectorSearchVersion` (Vector Search Version) <br>- `recallEnginVersion` (Recall Engine Version) |
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance is located. |
| `ConnectionPropertiesMode` | String | `InstanceMode` | Yes | Configuration mode. |
| `instanceId` | String | `ha-cn-kve****` | Yes | Instance ID. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |

### Important Notes

For **Vector Search Version** and **Recall Engine Version**, both username/password and AccessKey are required:

- **AccessKey**: Used by plugins to retrieve table schema and pull table structure information in wizard mode.
- **Username/Password**: Used for actual runtime data writing.

---

## Configuration Example

### Instance Mode

```json
{
    "envType": "Prod",
    "regionId": "cn-beijing",
    "instanceType": "vectorSearchVersion",
    "instanceId": "ha-xxxx",
    "username": "admin",
    "password": "xxxx"
}
```

---

## Document Information

- **Last Updated**: 2024-12-30 18:28:58
- **Source**: https://help.aliyun.com/zh/dataworks/developer-reference/opensearch
