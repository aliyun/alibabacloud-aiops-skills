# Columnar (Column Store) APIs

PolarDB-X columnar (column-store read-only) instance APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`. Some columnar APIs accept `--db-instance-name` and/or `--instance-name`.

---

## AttachColumnarInstance

Attach a columnar instance to a primary database instance.

> **[MUST] Secondary confirmation required.** Attaching a columnar instance may change billing. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx attach-columnar-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:AttachColumnarInstance`

---

## DescribeColumnarInfo

Query the columnar information of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |

### CLI example

```bash
aliyun polardbx describe-columnar-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeColumnarInfo`

---

## DescribeColumnarClassList

Query the available columnar node spec list.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx describe-columnar-class-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeColumnarClassList`

---

## DescribeColumnarVersionList

Query the columnar version list.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx describe-columnar-version-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeColumnarVersionList`

---

## ModifyColumnarClass

Modify the columnar node spec/count.

> **[MUST] Secondary confirmation required.** Changing columnar spec/count may change billing. Confirm target spec/count with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `instance-name` | String | Instance name |
| `columnar-class` | String | Target columnar spec |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `columnar-node-count` | String | Columnar node count |
| `switch-mode` | String | Switch mode |

### CLI example

```bash
aliyun polardbx modify-columnar-class \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --instance-name pxc-******** \
  --columnar-class <columnar-class> \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyColumnarClass`

---

## UpgradeColumnarVersion

Upgrade the columnar version.

> **[MUST] Secondary confirmation required.** A columnar upgrade may cause a brief switch. Confirm with the user.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |
| `instance-name` | String | Instance name |
| `columnar-version` | String | Target columnar version |
| `switch-mode` | String | Switch mode |

### CLI example

```bash
aliyun polardbx upgrade-columnar-version \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpgradeColumnarVersion`
