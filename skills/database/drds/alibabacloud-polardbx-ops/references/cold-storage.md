# Cold Storage & Storage Pool APIs

PolarDB-X cold-data volume and storage pool management APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## AllocateColdDataVolume

Allocate a cold-data volume for an instance.

> **[MUST] Secondary confirmation required.** Allocating a cold-data volume may change billing. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx allocate-cold-data-volume \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:AllocateColdDataVolume`

---

## ReleaseColdDataVolume

Release the cold-data volume of an instance.

> **[MUST] Secondary confirmation required.** Releasing a cold-data volume removes cold storage. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx release-cold-data-volume \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ReleaseColdDataVolume`

---

## DescribeColdDataBasicInfo

Query the basic cold-storage information of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-cold-data-basic-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeColdDataBasicInfo`

---

## CreateStoragePool

Create a storage (resource) pool.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `storage-pool-name` | String | Storage pool name |
| `storage-pool-dn-list` | String | DN list of the storage pool |
| `resource-group-id` | String | Resource group ID |

### CLI example

```bash
aliyun polardbx create-storage-pool \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --storage-pool-name <pool-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateStoragePool`

---

## DescribeStoragePoolInfo

Query storage pool details (capacity, usage, status).

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
aliyun polardbx describe-storage-pool-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeStoragePoolInfo`

---

## DescribeShowStorageInfo

Query the instance's storage space usage details (total/used/free).

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
aliyun polardbx describe-show-storage-info \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeShowStorageInfo`
