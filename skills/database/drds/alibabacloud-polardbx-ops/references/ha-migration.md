# High Availability & Migration APIs

PolarDB-X HA info, primary-standby switching, zone migration, and standard-to-enterprise transform APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## DescribeDBInstanceHA

Query the HA (high availability) information of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-db-instance-ha \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceHA`

---

## SwitchDBInstanceHA

Perform a primary-standby (HA) switch.

> **[MUST] Secondary confirmation required.** An HA switch causes a brief interruption and changes the primary role. Confirm the target and timing with the user before executing.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `target-primary-region-id` | String | Target primary region ID |
| `target-primary-azone-id` | String | Target primary zone ID |
| `switch-time-mode` | String | Switch time mode |
| `switch-time` | String | Scheduled switch time |

### CLI example

```bash
aliyun polardbx switch-db-instance-ha \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --target-primary-azone-id cn-hangzhou-i \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:SwitchDBInstanceHA`

---

## MigrateDBInstance

Migrate an instance from one zone (topology) to another.

> **[MUST] Secondary confirmation required.** Zone migration involves a switch and potential interruption. Confirm the target topology/zones and timing with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |
| `topology-type` | String | `3azones` / `1azone` |
| `primary-zone-id` | String | Primary zone ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `secondary-zone-id` | String | Secondary zone ID (must differ from primary) |
| `tertiary-zone-id` | String | Tertiary zone ID |
| `switch-mode` | String | `0` immediate / `1` within maintenance window |
| `vpc-id` / `vswitch-id` | String | VPC / VSwitch |

### CLI example

```bash
aliyun polardbx migrate-db-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --topology-type 3azones \
  --primary-zone-id cn-hangzhou-h \
  --secondary-zone-id cn-hangzhou-i \
  --tertiary-zone-id cn-hangzhou-j \
  --switch-mode 1 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:MigrateDBInstance`

---

## AlignStoragePrimaryAzone

Align the storage node primary zone with the instance primary zone.

> **[MUST] Secondary confirmation required.** Involves a storage switch. Confirm timing with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `storage-instance-name` | String | Target storage node name |
| `switch-time-mode` | String | Switch time mode |
| `switch-time` | String | Scheduled switch time |

### CLI example

```bash
aliyun polardbx align-storage-primary-azone \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:AlignStoragePrimaryAzone`

---

## ConfirmNoConnection

Confirm there are no active connections when rolling back a switch.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `slink-task-id` | String | Task ID to roll back |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx confirm-no-connection \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ConfirmNoConnection`

---

## StartSwitchDatabase

Start the database switch step in a migration/sync task.

> **[MUST] Secondary confirmation required.** The database switch redirects traffic to the target instance. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `slink-task-id` | String | Import/migration task ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name |
| `is-modify-endpoint` | String | Whether to modify source/target endpoint |
| `src-main-connect-string` / `src-main-port` | String | Source main endpoint / port |
| `dst-main-connect-string` / `dst-main-port` | String | Target main endpoint / port |

### CLI example

```bash
aliyun polardbx start-switch-database \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --slink-task-id etx-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:StartSwitchDatabase`

---

## DescribeTransformStatus

Query the status of a standard-to-enterprise upgrade/transform task.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name |
| `query-report` | Boolean | Whether to query the validation report |

### CLI example

```bash
aliyun polardbx describe-transform-status \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeTransformStatus`

---

## CreateTransformOperation

Create a transform operation to change an instance's state/configuration (e.g. finish a standard-to-enterprise transform).

> **[MUST] Secondary confirmation required.** A transform changes the instance edition/state. Confirm with the user.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |
| `operation` | String | Operation type, e.g. `finish` |

### CLI example

```bash
aliyun polardbx create-transform-operation \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --operation finish \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateTransformOperation`
