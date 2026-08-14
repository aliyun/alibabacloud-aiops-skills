# Metadata & Query APIs

PolarDB-X read-only metadata queries: regions, cross-region availability, VPC/VSwitch, character sets, data nodes, and parameter groups. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## DescribeRegions

Query the list of available regions and zones.

### Parameters

No business parameters required (global flags only).

### CLI example

```bash
aliyun polardbx describe-regions \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeRegions`

---

## DescribeAvailableCrossRegions

Query regions available for cross-region operations (backup/replication).

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx describe-available-cross-regions \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeAvailableCrossRegions`

---

## DescribeEnabledCrossRegions

Query the currently enabled cross-regions.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx describe-enabled-cross-regions \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeEnabledCrossRegions`

---

## DescribeRdsVpcs

Query the VPC list available to PolarDB-X.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `zone-id` | String | Zone ID |

### CLI example

```bash
aliyun polardbx describe-rds-vpcs \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --zone-id cn-hangzhou-h \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeRdsVpcs`

---

## DescribeRdsVswitches

Query the VSwitch list available to PolarDB-X.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `vpc-id` | String | VPC ID |
| `zone-id` | String | Zone ID |

### CLI example

```bash
aliyun polardbx describe-rds-vswitches \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --vpc-id vpc-******** \
  --zone-id cn-hangzhou-h \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeRdsVswitches`

---

## DescribeCharacterSet

Query supported character sets for databases under an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |

### CLI example

```bash
aliyun polardbx describe-character-set \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeCharacterSet`

---

## DescribePolarxDataNodes

Query all data nodes (DN) of an instance, including status and storage usage.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `node-type` | String | Node type filter |
| `search-key` | String | Keyword |
| `page-number` / `page-size` | Integer | Pagination |

### CLI example

```bash
aliyun polardbx describe-polarx-data-nodes \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-number 1 --page-size 100 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribePolarxDataNodes`

---

## DescribeParameterGroups

Query the list of parameter groups (user-created or system-supported).

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |

### CLI example

```bash
aliyun polardbx describe-parameter-groups \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeParameterGroups`
