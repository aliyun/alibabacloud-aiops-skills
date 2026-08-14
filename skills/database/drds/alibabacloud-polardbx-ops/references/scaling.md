# Scaling APIs

PolarDB-X instance scaling, class change, and expansion/shrinkage APIs.

---

## UpdatePolarDBXInstanceNode

Change the number of instance nodes, including scale-out and scale-in. This request creates a trade order.

> **[MUST] Secondary confirmation required.** This operation creates a trade order and changes billing. Before running this command, present the node count change (before → after) and billing note to the user and obtain explicit confirmation. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID, e.g. `pxc-********` |
| `client-token` | String | Client idempotency token |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-node-count` | String | Target total number of instance nodes, range 0-99 |
| `cn-node-count` | String | Number of compute nodes |
| `dn-node-count` | String | Number of storage nodes |

### CLI example

```bash
aliyun polardbx update-polardbx-instance-node \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --cn-node-count 4 \
  --dn-node-count 4 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpdatePolarDBXInstanceNode`

---

## ModifyDBInstanceClass

Modify instance class (upgrade/downgrade). Creates a trade order.

> **[MUST] Secondary confirmation required.** This operation creates a trade order and changes billing. Before running this command, present the class change (before → after) and billing note to the user and obtain explicit confirmation. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `target-db-instance-class` | String | Target class for standard edition, e.g. `mysql.n4.medium.25` |
| `client-token` | String | Client idempotency token |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `cn-class` | String | Target compute node class for enterprise edition, e.g. `polarx.x4.large.2e`. Use `scripts/spec_lookup.sh` to map a spec code to cores/memory or vice versa |
| `dn-class` | String | Target storage node class for enterprise edition, e.g. `mysql.n4.medium.25`. Use `scripts/spec_lookup.sh` to map a spec code to cores/memory or vice versa |
| `specified-dn-scale` | Boolean | Whether this is a DN multi-spec class change |
| `specified-dn-spec-map-json` | String | JSON of target specs for each DN when doing DN multi-spec class change |
| `switch-time-mode` | String | `0` execute immediately / `1` execute during maintenance window |
| `switch-time` | String | Switch start time (UTC), not yet open |
| `dn-storage-space` | String | Target disk size |

### CLI example

```bash
# Upgrade to 8C32G (xlarge = 2x base cores)
aliyun polardbx modify-db-instance-class \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --cn-class polarx.x4.xlarge.2e \
  --dn-class mysql.n4.large.25 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

> **Note**: When choosing `cn-class`, be sure to confirm the core count. `large` = base cores (e.g. 4C16G), `xlarge` = double cores (e.g. 8C32G). Verify with `scripts/spec_lookup.sh --code <spec>` (or `--cores <N> --memory <G> --category cn`); run `scripts/spec_lookup.sh --list` to enumerate all specs.

### RAM action

`polardbx:ModifyDBInstanceClass`

---

## DescribeScaleOutMigrateTaskList

Show ScaleOut migration task progress.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-scale-out-migrate-task-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeScaleOutMigrateTaskList`
