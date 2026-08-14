# Parameter Management APIs

PolarDB-X instance configuration and parameter management APIs.

---

## DescribeDBInstanceConfig

Get instance configuration parameters (such as HTAP-related config).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `config-name` | String | Config identifier, default `htap` |

### CLI example

```bash
aliyun polardbx describe-db-instance-config \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --config-name htap \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceConfig`

---

## ModifyDBInstanceConfig

Modify instance configuration items.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `config-name` | String | Config item name, e.g. `ENABLE_CONSISTENT_REPLICA_READ` |
| `config-value` | String | Config item value, e.g. `true` / `false` |

### CLI example

```bash
aliyun polardbx modify-db-instance-config \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --config-name ENABLE_CONSISTENT_REPLICA_READ \
  --config-value true \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDBInstanceConfig`

---

## DescribeParameters

View instance parameters (compute layer / storage layer).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-id` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `param-level` | String | `compute` compute layer / `storage` storage layer |

### CLI example

```bash
aliyun polardbx describe-parameters \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --param-level compute \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeParameters`

---

## ModifyParameter

Modify instance parameters (compute layer and storage layer).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-id` | String | Instance ID |
| `parameters` | String | JSON-format parameter key-value pairs, e.g. `{"CONN_POOL_BLOCK_TIMEOUT":6000}` |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `param-level` | String | `compute` compute layer / `storage` storage layer |
| `client-token` | String | Idempotency token |

### CLI example

```bash
aliyun polardbx modify-parameter \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --param-level compute \
  --parameters '{"CONN_POOL_BLOCK_TIMEOUT":6000}' \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyParameter`

---

## DescribeParameterTemplates

View the instance parameter template list (modifiable parameter whitelist).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-id` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `param-level` | String | `compute` / `storage` |

### CLI example

```bash
aliyun polardbx describe-parameter-templates \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --param-level compute \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeParameterTemplates`
