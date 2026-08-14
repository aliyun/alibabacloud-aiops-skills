# Instance Lifecycle APIs

PolarDB-X instance lifecycle management APIs. All CLI examples use the `aliyun polardbx` subcommand.

> Note: Some APIs use `DBInstanceName` (instance name/ID, format `pxc-********`) as the instance identifier, while others use `DBInstanceId`.

---

## CreateDBInstance

Create a PolarDB-X instance.

> **[MUST] Secondary confirmation required.** Creating an instance incurs billing. Before running this command, present the full spec, `PayType`, and billing note to the user and obtain explicit confirmation. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides, e.g. `cn-hangzhou` |
| `pay-type` | String | `PREPAY` subscription / `POSTPAY` pay-as-you-go |
| `engine-version` | String | MySQL engine version: `5.7` or `8.0` |
| `topology-type` | String | `3azones` three AZs / `1azone` single AZ |
| `vpc-id` | String | VPC ID (**required**; missing raises `MissingParameter.VpcId`) |
| `vswitch-id` | String | VSwitch ID (**required**; must match the selected zone, otherwise `InvalidParameter.VpcId.VSwitchId`) |

> **3azones topology must specify three zone IDs**: `primary-zone`, `secondary-zone`, and `tertiary-zone` are all required, otherwise `MissingParameter`. `1azone` topology only needs `zone-id`.

> **[MUST] No custom instance name at creation.** `CreateDBInstance` has **no** `db-instance-name` parameter — the instance name is system-assigned (format `pxc-********`) and returned as `DBInstanceName` in the response. When the user asks to create an instance with a specific name (e.g. `pxc-eval-backup-xxx`), you CANNOT set it as the name; put that requested name into the `description` field instead, and tell the user the real instance name is the system-assigned `pxc-********` from the response.

### Common optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-node-count` | Integer | Number of instance nodes; standard edition is 1, enterprise edition >= 2 |
| `db-node-class` | String | Standard edition node class, e.g. `polarx.x4.2xlarge.2d` |
| `series` | String | `enterprise` enterprise edition / `standard` standard edition |
| `cn-class` | String | Enterprise edition compute node class. Local SSD e.g. `polarx.x4.medium.2e`; cloud disk suffix is `.c2e`, e.g. `polarx.x4.medium.c2e` |
| `dn-class` | String | Enterprise edition storage node class. Local SSD e.g. `mysql.n4.medium.25`; cloud disk needs `polarx.` prefix and `.c25` suffix, e.g. `polarx.mysql.n4.medium.c25` |
| `cn-node-count` | Integer | Number of compute nodes |
| `dn-node-count` | Integer | Number of storage nodes |
| `network-type` | String | Only `vpc` is supported |
| `zone-id` | String | Zone ID (used with `1azone`) |
| `primary-zone` / `secondary-zone` / `tertiary-zone` | String | Primary/secondary/tertiary zones (required for `3azones`) |
| `used-time` | Integer | Prepaid duration |
| `period` | String | Billing period: `Year` / `Month` |
| `auto-renew` | Boolean | Whether to auto-renew |
| `dn-storage-space` | String | Storage node disk size |
| `storage-type` | String | `custom_local_ssd` local SSD / `cloud_auto` cloud disk. **Compatibility restriction**: `cloud_auto` only supports `1azone`; `3azones` only supports `custom_local_ssd`. Incompatible combinations fail at order creation with `Buy.CreateOrderError` (`Message: null`), which is hard to diagnose from the error text |
| `client-token` | String | Idempotency token |
| `description` | String | Instance description. Also the **only** place to record a user-requested human-readable name, since the instance name itself is system-assigned (see the note above) |

### Spec query

Query all available specs (local SSD + cloud disk):

```bash
aliyun polardbx create-db-instance --help
```

The help output lists all available values for `cn-class` and `dn-class`. PolarDB-X has **no** `DescribeClassInfo` API. To resolve a spec code to its cores/memory (or find a spec code for a target size), run `scripts/spec_lookup.sh` (e.g. `./scripts/spec_lookup.sh --code polarx.x4.large.2e` or `--cores 4 --memory 16 --category cn`; `--list` to enumerate all specs).

### CN spec naming rules

PolarDB-X CN node specs follow the pattern `polarx.xN.<size>.<suffix>`, where `<size>` determines the core multiplier:

| Suffix | Cores | Memory | Example (N=4) |
|--------|-------|--------|---------------|
| `large` | N (1x) | 4N GB | `polarx.x4.large.2e` = 4C16G |
| `xlarge` | 2N (2x) | 8N GB | `polarx.x4.xlarge.2e` = 8C32G |
| `2xlarge` | 4N (4x) | 16N GB | `polarx.x4.2xlarge.2d` = 16C64G |

> **Common pitfall**: `large` is NOT "small"; it is the **base** multiplier (1x); `xlarge` doubles cores and memory. When the user says "4-core 16G", choose `large`, not `xlarge`.

Cloud disk specs replace the `.2e` suffix with `.c2e`, following the same rule. Use `scripts/spec_lookup.sh` for spec-code <-> cores/memory conversion (including DN and standard edition); run `scripts/spec_lookup.sh --list` to enumerate all specs.

### Zone query

PolarDB-X has **no** `DescribeZones` API. Query available zones by falling back to the ECS API:

```bash
aliyun ecs describe-zones --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

Pick three zones from the result and fill them into `primary-zone`, `secondary-zone`, `tertiary-zone` (`3azones`) or `zone-id` (`1azone`).

### CLI example

```bash
aliyun polardbx create-db-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --pay-type POSTPAY \
  --engine-version 8.0 \
  --topology-type 3azones \
  --series enterprise \
  --cn-class polarx.x4.medium.2e \
  --dn-class mysql.n4.medium.25 \
  --cn-node-count 2 \
  --dn-node-count 2 \
  --vpc-id vpc-xxx \
  --vswitch-id vsw-xxx \
  --primary-zone cn-hangzhou-h \
  --secondary-zone cn-hangzhou-i \
  --tertiary-zone cn-hangzhou-j \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

> Cloud disk example (`1azone` + `cloud_auto`):
>
> ```bash
> aliyun polardbx create-db-instance \
>   --biz-region-id cn-hangzhou \
>   --region cn-hangzhou \
>   --pay-type POSTPAY \
>   --engine-version 8.0 \
>   --topology-type 1azone \
>   --series enterprise \
>   --cn-class polarx.x4.medium.c2e \
>   --dn-class polarx.mysql.n4.medium.c25 \
>   --cn-node-count 2 \
>   --dn-node-count 2 \
>   --vpc-id vpc-xxx \
>   --vswitch-id vsw-xxx \
>   --zone-id cn-hangzhou-h \
>   --storage-type cloud_auto \
>   --client-token $(uuidgen) \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
> ```

### RAM action

`polardbx:CreateDBInstance`

---

## DeleteDBInstance

Delete a PolarDB-X instance.

> **[MUST] Secondary confirmation required.** Deletion permanently removes the instance and its data and cannot be undone. Before running this command, warn the user and obtain explicit confirmation. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID, e.g. `pxc-********` |

### CLI example

```bash
aliyun polardbx delete-db-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteDBInstance`

---

## RestartDBInstance

Restart a PolarDB-X instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx restart-db-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:RestartDBInstance`

---

## DescribeDBInstanceAttribute

Query instance attribute details.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `resource-group-id` | String | Resource group ID |

### CLI example

```bash
aliyun polardbx describe-db-instance-attribute \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceAttribute`

---

## DescribeDBInstances

Query the instance list.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `instance-id` | String | Filter by instance ID |
| `series` | String | `enterprise` / `standard` |
| `page-number` | Integer | Page number, default 1 |
| `page-size` | Integer | Page size, range 5~100 |
| `resource-group-id` | String | Resource group ID |
| `tags` | String | Tag filter, JSON string |
| `must-has-cdc` | Boolean | Whether the instance must have a log engine |

### CLI example

```bash
aliyun polardbx describe-db-instances \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-number 1 \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstances`

---

## DescribeDBInstanceTopology

Query instance topology information.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start-time` | String | Historical topology start time, format `yyyy-MM-dd HH:mm:ss` |
| `end-time` | String | Historical topology end time |
| `minute-simple` | Boolean | Whether to query historical topology |

### CLI example

```bash
aliyun polardbx describe-db-instance-topology \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDBInstanceTopology`

---

## DescribeTasks

Get the instance task list, used to poll asynchronous task status for create/delete/restart/class-change operations.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-id` | String | Instance ID |
| `start-time` | String | Task start time, e.g. `2021-11-01` |
| `end-time` | String | Task end time |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page-number` | Integer | Page number |
| `page-size` | Integer | Page size, range 5~100 |

### CLI example

```bash
aliyun polardbx describe-tasks \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-id pxc-******** \
  --start-time 2024-01-01 \
  --end-time 2024-01-02 \
  --page-number 1 \
  --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeTasks`

---

## ModifyDBInstanceDescription

Modify instance description/remark.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `db-instance-description` | String | New instance description |

### CLI example

```bash
aliyun polardbx modify-db-instance-description \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --db-instance-description "test instance" \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDBInstanceDescription`

---

## ModifyDBInstanceMaintainTime

Modify instance maintenance window time.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `maintain-time` | String | Maintainable time, UTC, e.g. `19:00Z-20:00Z` |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `client-token` | String | Idempotency token |

### CLI example

```bash
aliyun polardbx modify-db-instance-maintain-time \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --maintain-time 19:00Z-20:00Z \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDBInstanceMaintainTime`

---

## UpgradeDBInstanceKernelVersion

Update instance kernel version.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `switch-mode` | String | `0` switch immediately / `1` switch during maintenance window |
| `minor-version` | String | Target kernel version number |

### CLI example

```bash
aliyun polardbx upgrade-db-instance-kernel-version \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --switch-mode 0 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpgradeDBInstanceKernelVersion`

---

## Asynchronous task polling

For write operations such as `CreateDBInstance`, `DeleteDBInstance`, `RestartDBInstance`, `UpgradeDBInstanceKernelVersion`, `ModifyDBInstanceClass`, and `UpdatePolarDBXInstanceNode`, the response may contain a `TaskId` or order ID. Poll task status via `DescribeTasks` to confirm completion.
