# GDN (Global Database Network) APIs

PolarDB-X GDN (Global Database Network) instance and member APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; primary instance flag is `--db-instance-name`; GDN instance flag is `--gdn-instance-name`.

---

## CreateGdnInstance

Create a GDN instance from an existing primary instance.

> **[MUST] Secondary confirmation required.** Creating a GDN may change billing and topology. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Primary instance name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | String | Description |
| `gdn-mode` | String | GDN mode |
| `rpl-conflict-strategy` | String | Replication conflict strategy |
| `rpl-dml-strategy` | String | DML replication strategy |
| `rpl-sync-ddl` | Boolean | Whether to sync DDL |

### CLI example

```bash
aliyun polardbx create-gdn-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateGdnInstance`

---

## DeleteGdnInstance

Delete a GDN instance.

> **[MUST] Secondary confirmation required.** Deleting a GDN dismantles the global network. Confirm the GDN name with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `gdn-instance-name` | String | GDN instance name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |

### CLI example

```bash
aliyun polardbx delete-gdn-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --gdn-instance-name gdn-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteGdnInstance`

---

## DescribeGdnInstances

Query the GDN instance list.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `gdn-id` | String | GDN ID |
| `filter-type` | String | Filter type |
| `filter-value` | String | Filter value |
| `page-num` / `page-size` | String | Pagination |

### CLI example

```bash
aliyun polardbx describe-gdn-instances \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-num 1 --page-size 30 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeGdnInstances`

---

## CreateGdnStandbyMember

Add a standby member (clone from a source instance) to a GDN.

> **[MUST] Secondary confirmation required.** This creates a new billable standby instance. Present the full spec, `PayType`, and billing note to the user and obtain explicit confirmation.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region for the standby member |
| `clone-instance-name` | String | Source instance name |
| `source-instance-region` | String | Source instance region |
| `engine-version` | String | MySQL engine version `5.7` or `8.0` |
| `pay-type` | String | `PREPAY` / `POSTPAY` |
| `topology-type` | String | `3azones` / `1azone` |

### Common optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `series` | String | `enterprise` / `standard` |
| `cn-class` / `dn-class` | String | Enterprise CN / DN class (enterprise only) |
| `cn-node-count` / `dn-node-count` | String | Enterprise CN / DN node count |
| `vpc-id` / `vswitch-id` | String | VPC / VSwitch |
| `primary-zone` / `secondary-zone` / `tertiary-zone` | String | Zones |
| `storage-type` | String | Storage type |
| `period` / `used-time` / `auto-renew` | - | Billing options |
| `description` | String | Description |
| `client-token` | String | Idempotency token |

### CLI example

```bash
aliyun polardbx create-gdn-standby-member \
  --biz-region-id cn-shanghai \
  --region cn-shanghai \
  --clone-instance-name pxc-primary \
  --source-instance-region cn-hangzhou \
  --engine-version 8.0 \
  --pay-type POSTPAY \
  --topology-type 1azone \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateGdnStandbyMember`

---

## SwitchGdnMemberRole

Switch the primary-standby role within a GDN.

> **[MUST] Secondary confirmation required.** A GDN role switch changes the primary member and may interrupt writes. Confirm the target and timing with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Primary instance ID |
| `switch-mode` | String | Switch mode |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task-timeout` | Integer | Switch task timeout (seconds) |
| `is-modify-endpoint` | String | Whether to modify endpoints |
| `src-main-connect-string` / `src-main-port` | String | Source main endpoint / port |
| `dst-main-connect-string` / `dst-main-port` | String | Target main endpoint / port |

### CLI example

```bash
aliyun polardbx switch-gdn-member-role \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --switch-mode <mode> \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:SwitchGdnMemberRole`
