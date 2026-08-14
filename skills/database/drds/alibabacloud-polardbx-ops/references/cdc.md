# CDC (Log Engine) APIs

PolarDB-X CDC / binlog log-engine APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`. Some CDC APIs accept `--db-instance-name` and/or `--instance-name`.

---

## DescribeCdcInfo

Query the CDC (log engine) information of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-cdc-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeCdcInfo`

---

## DescribeCdcClassList

Query the available CDC node spec list.

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
aliyun polardbx describe-cdc-class-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeCdcClassList`

---

## DescribeCdcVersionList

Query the CDC version list.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name |
| `instance-name` | String | Instance name |

### CLI example

```bash
aliyun polardbx describe-cdc-version-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeCdcVersionList`

---

## ModifyCdcClass

Modify the CDC node spec/count.

> **[MUST] Secondary confirmation required.** Changing CDC spec/count may change billing. Confirm target spec/count with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `instance-name` | String | Instance name |
| `cdc-class` | String | Target CDC spec |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `cdc-node-count` | String | CDC node count |
| `switch-mode` | String | Switch mode |

### CLI example

```bash
aliyun polardbx modify-cdc-class \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --instance-name pxc-******** \
  --cdc-class <cdc-class> \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyCdcClass`

---

## UpgradeCDCVersion

Upgrade the CDC node version.

> **[MUST] Secondary confirmation required.** A CDC upgrade may cause a brief switch. Confirm with the user.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance ID |
| `instance-name` | String | Instance name |
| `cdc-db-version` | String | Target database version |
| `cdc-minor-version` | String | Target minor version |
| `switch-mode` | String | Switch mode |

### CLI example

```bash
aliyun polardbx upgrade-cdc-version \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:UpgradeCDCVersion`
