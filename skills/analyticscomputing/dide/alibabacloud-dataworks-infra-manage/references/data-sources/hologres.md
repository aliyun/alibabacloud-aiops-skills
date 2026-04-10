# Hologres Datasource Documentation

## Property Definition

- **Datasource Type**: `hologres`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode` (Instance Mode)

---

## Same Account Access Identity Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `regionId` | String | `cn-shanghai` | Yes | The Region where the Hologres instance belongs. |
| `instanceId` | String | `hgpostcn-cn-xxxxx` | Yes | The Hologres instance ID. |
| `database` | String | `holo_db` | Yes | The Hologres database name. |
| `warehouseName` | String | `init_warehouse` | No | Hologres compute group information, e.g., the default `init_warehouse`. Note: If a compute group is configured, the database parameter in downstream `findConnection` will append `@` with compute group info, e.g., `"database": "holo_demo@compute_group_name"`. |
| `authType` | String | `Executor` | Yes | Datasource access identity. Enum values:<br>• `Executor`: Executor (Development environment)<br>• `PrimaryAccount`: Primary account (Production environment)<br>• `SubAccount`: A specified sub-account (Production environment)<br>• `RamRole`: A specified RAM role (Production environment) |
| `authIdentity` | String | `<ACCOUNT_ID>` | No | In the same account scenario, the cloud account ID of the corresponding task submitter. |
| `securityProtocol` | String | `authTypeNone` | No | Whether to enable SSL transmission for datasource access. Enum values:<br>• `authTypeNone`: Do not use SSL authentication<br>• `authTypeSsl`: Use SSL authentication |
| `sslMode` | String | `require` | No | Verification requirement during SSL transmission:<br>• `require`: Indicates verification |
| `envType` | String | `Dev` | Yes | `envType` indicates the datasource environment information.<br>• `Dev`: Development environment<br>• `Prod`: Production environment |

---

## Cross-Account Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `regionId` | String | `cn-shanghai` | Yes | The Region where the Hologres instance belongs. Note: Historical data for non-engine datasources may not have this value. |
| `instanceId` | String | `hgpostcn-cn-xxxxx` | Yes | The Hologres instance ID. |
| `database` | String | `holo_db` | Yes | The Hologres database name. |
| `warehouseName` | String | `init_warehouse` | No | Hologres compute group information, e.g., the default `init_warehouse`. Note: If a compute group is configured, the database parameter in downstream `findConnection` will append `@` with compute group info. |
| `authType` | String | `RamRole` | Yes | Fixed as `RamRole`. |
| `crossAccountOwnerId` | String | `<ACCOUNT_ID>` | Yes | The other party's primary account ID for cross-Alibaba Cloud primary account. Required for cross-account scenarios. |
| `crossAccountRoleName` | String | `holo-accross-role-name` | Yes | The role name under the other party's account in cross-account scenarios. |
| `securityProtocol` | String | `authTypeNone` | No | Whether to enable SSL transmission for datasource access. Enum values:<br>• `authTypeNone`: Do not use SSL authentication<br>• `authTypeSsl`: Use SSL authentication |
| `sslMode` | String | `require` | No | Verification requirement during SSL transmission:<br>• `null`: Indicates no verification<br>• `require`: Indicates verification |
| `envType` | String | `Dev` | Yes | `envType` indicates the datasource environment information.<br>• `Dev`: Development environment<br>• `Prod`: Production environment |

---

## Datasource Configuration Examples

### Executor Access Identity Mode

```json
{
  "database": "database",
  "instanceId": "hgpostcn-cn-xxxxx",
  "securityProtocol": "authTypeNone",
  "regionId": "cn-beijing",
  "envType": "Dev",
  "authType": "Executor"
}
```

### Cross-Account Mode

```json
{
  "crossAccountOwnerId": "<ACCOUNT_ID>",
  "crossAccountRoleName": "holo-accross-role-name",
  "database": "database",
  "instanceId": "hgpostcn-cn-xxxxx",
  "securityProtocol": "authTypeNone",
  "regionId": "cn-beijing",
  "envType": "Dev",
  "authType": "RamRole"
}
```
