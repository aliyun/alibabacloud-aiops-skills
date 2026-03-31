# Compute Resource ConnectionProperties Reference

## Workspace Mode and Compute Resource Configuration

> **Important**: Workspace mode (Simple Mode / Standard Mode) affects the quantity and authType configuration of compute resources.

### Query Workspace Mode

```bash
aliyun dataworks-public GetProject --user-agent AlibabaCloud-Agent-Skills --Id <PROJECT_ID> 2>/dev/null | jq '.Project | {Id, Name, DevEnvironmentEnabled}'
```

- `DevEnvironmentEnabled: false` → Simple Mode
- `DevEnvironmentEnabled: true` → Standard Mode

### Simple Mode vs Standard Mode

| Dimension | Simple Mode | Standard Mode |
|------|---------|---------|
| Number of environments | 1 (Production environment) | 2 (Development + Production) |
| Number of compute resources | 1 | 2 |
| envType | `Prod` only | `Dev` + `Prod` |

### Compute Resource Creation Strategy

#### Simple Mode Workspace

Create **1 compute resource** with `envType: Prod`:

```json
{
  "envType": "Prod",
  "authType": "PrimaryAccount",
  ...
}
```

#### Standard Mode Workspace

Create **2 compute resources**. Different environments use different authType:

**Production environment**:
```json
{
  "envType": "Prod",
  "authType": "PrimaryAccount",
  ...
}
```

**Development environment**:
```json
{
  "envType": "Dev",
  "authType": "Executor",
  ...
}
```

---

## authType Rules (by environment)

- **Dev environment** (`envType: "Dev"`): `authType` is fixed as **`Executor`**
- **Prod environment** (`envType: "Prod"`): `authType` supports the following values:

| AuthType | Description |
|----------|------|
| PrimaryAccount | Access using primary account identity (**Recommended**) |
| TaskOwner | Access using task owner identity |
| SubAccount | Access using specified sub-account identity |
| RamRole | Access using specified RAM role identity |

---

## Hologres (InstanceMode only)

**Prod environment example:**
```json
{
  "envType": "Prod",
  "regionId": "cn-hangzhou",
  "instanceId": "hgprecn-cn-xxxxx",
  "database": "mydb",
  "securityProtocol": "authTypeNone",
  "authType": "PrimaryAccount"
}
```

**Dev environment example:**
```json
{
  "envType": "Dev",
  "regionId": "cn-hangzhou",
  "instanceId": "hgprecn-cn-xxxxx",
  "database": "mydb",
  "securityProtocol": "authTypeNone",
  "authType": "Executor"
}
```

## MaxCompute (UrlMode only)

**Prod environment example:**
```json
{
  "envType": "Prod",
  "regionId": "cn-hangzhou",
  "project": "my_maxcompute_project",
  "authType": "PrimaryAccount",
  "endpointMode": "SelfAdaption"
}
```

**Dev environment example:**
```json
{
  "envType": "Dev",
  "regionId": "cn-hangzhou",
  "project": "my_maxcompute_project_dev",
  "authType": "Executor",
  "endpointMode": "SelfAdaption"
}
```

## Flink (InstanceMode)

```json
{
  "envType": "Prod",
  "regionId": "cn-hangzhou",
  "instanceId": "flink-xxxxx",
  "workspaceName": "my_flink_workspace",
  "authType": "PrimaryAccount"
}
```

## Spark (InstanceMode)

```json
{
  "envType": "Prod",
  "regionId": "cn-hangzhou",
  "clusterId": "spark-xxxxx",
  "authType": "PrimaryAccount"
}
```

---

## Important Notes

- All compute resource types use **camelCase** for ConnectionProperties fields
- Dev environment authType is fixed as `Executor`; Prod environment supports `PrimaryAccount`/`TaskOwner`/`SubAccount`/`RamRole`
- Hologres compute resources support InstanceMode only
- MaxCompute compute resources support UrlMode only
