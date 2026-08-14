# Connection & Endpoint APIs

PolarDB-X connection string, VIP, and custom endpoint APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

> **Security:** NEVER expose the instance to the public internet. The public-connection APIs listed at the bottom are FORBIDDEN by default and must not be used unless the user explicitly accepts the risk.

---

## DescribeDBInstanceEndpoint

Query the custom endpoints of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `max-results` | Integer | Page size, max 100 |
| `next-token` | String | Pagination token |

### CLI example

```bash
aliyun polardbx describe-db-instance-endpoint \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceEndpoint`

---

## ModifyDBInstanceConnectionString

Modify an instance's connection string (prefix / port).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `connection-string` | String | The current connection string to modify |
| `new-prefix` | String | New address prefix |
| `new-port` | String | New port |

### CLI example

```bash
aliyun polardbx modify-db-instance-connection-string \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connection-string pxc-********.polarx.rds.aliyuncs.com \
  --new-prefix <new-prefix> \
  --new-port 3306 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDBInstanceConnectionString`

---

## ModifyDBInstanceVip

Modify the VIP (virtual IP) bound to an instance (change internal IP, subnet, or zone).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `vpc-id` | String | VPC ID |
| `vswitch-id` | String | VSwitch ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `instance-cluster-name` | String | CN cluster name, e.g. `default` |

### CLI example

```bash
aliyun polardbx modify-db-instance-vip \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --vpc-id vpc-******** \
  --vswitch-id vsw-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDBInstanceVip`

---

## CreateCustomEndpoint

Create a custom connection endpoint for an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance ID |
| `name` | String | Endpoint name, 2-128 chars |
| `vpc-id` | String | VPC ID |
| `vswitch-id` | String | VSwitch ID |
| `node-ids` | String | Node IDs, comma-separated |
| `node-auto-enter` | Boolean | Whether nodes auto-join the cluster |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `node-role` | String | `READONLY` for read-only nodes |

### CLI example

```bash
aliyun polardbx create-custom-endpoint \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --name <endpoint-name> \
  --vpc-id vpc-******** \
  --vswitch-id vsw-******** \
  --node-ids r-******** \
  --node-auto-enter true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateCustomEndpoint`

---

## DeleteCustomEndpoint

Delete a custom endpoint.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |
| `custom-endpoint-id` | String | Custom endpoint ID |

### CLI example

```bash
aliyun polardbx delete-custom-endpoint \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --custom-endpoint-id <endpoint-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteCustomEndpoint`

---

## ModifyCustomEndpoint

Modify a custom endpoint's configuration.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance ID |
| `custom-endpoint-id` | String | Custom endpoint ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `name` | String | Endpoint name |
| `node-ids` | String | Node IDs |
| `node-auto-enter` | Boolean | Whether nodes auto-join the cluster |
| `node-role` | String | Node role |

### CLI example

```bash
aliyun polardbx modify-custom-endpoint \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --custom-endpoint-id <endpoint-id> \
  --node-ids r-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyCustomEndpoint`

---

## ModifyCustomEndpointNet

Modify a custom endpoint's network configuration (subnet, port).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance ID |
| `custom-endpoint-id` | String | Custom endpoint ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `conn-prefix` | String | Connection prefix |
| `port` | Integer | Port |
| `vpc-id` / `vswitch-id` | String | VPC / VSwitch |

> Do NOT use this to allocate a public-network address.

### CLI example

```bash
aliyun polardbx modify-custom-endpoint-net \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --custom-endpoint-id <endpoint-id> \
  --vswitch-id vsw-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyCustomEndpointNet`

---

## DescribeCustomEndpointList

Query the custom endpoint list.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `custom-endpoint-ids` | String | Filter by custom endpoint IDs |
| `check-delete-cn` | Boolean | Whether to check if the CN is deleted |

### CLI example

```bash
aliyun polardbx describe-custom-endpoint-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeCustomEndpointList`

---

## DescribeDBInstanceViaEndpoint

Get basic instance info via its connection endpoint.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `biz-endpoint` | String | Instance connection endpoint |

### CLI example

```bash
aliyun polardbx describe-db-instance-via-endpoint \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --biz-endpoint pxc-********.polarx.rds.aliyuncs.com \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceViaEndpoint`

---

## CreateSubCNInstance

Create a sub-CN instance (e.g. a columnar read-only endpoint).

> **[MUST] Secondary confirmation required.** Adding CN resources may change billing. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `is-auto-create` | Boolean | Auto-compute resource parameters |
| `read-type` | String | `ReadWrite` (row store) / `ColumnarRead` (columnar read-only) |

### CLI example

```bash
aliyun polardbx create-sub-cn-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --read-type ColumnarRead \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateSubCNInstance`

---

## DeleteSubCNInstance

Delete a sub-CN instance.

> **[MUST] Secondary confirmation required.** Confirm the target cluster with the user before deleting.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `instance-cluster-name` | String | CN cluster name |

### CLI example

```bash
aliyun polardbx delete-sub-cn-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteSubCNInstance`

---

## Public-network connection APIs (FORBIDDEN)

`AllocateInstancePublicConnection` (`allocate-instance-public-connection`) and `ReleaseInstancePublicConnection` (`release-instance-public-connection`) allocate/release a PUBLIC-network connection and are **forbidden** by this skill's security policy. Do NOT generate convenience commands for them. Only proceed if the user explicitly acknowledges the risk of exposing the instance to the public internet.

RAM actions: `polardbx:AllocateInstancePublicConnection`, `polardbx:ReleaseInstancePublicConnection`
