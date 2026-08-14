# Database Management APIs

PolarDB-X database and table management APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## CreateDB

Create a database within an instance and authorize an account on it.

> **[MUST] Secondary confirmation required.** Confirm database name, mode, and authorized account with the user before executing.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region, e.g. `cn-hangzhou` |
| `db-instance-name` | String | Instance name/ID |
| `db-name` | String | Database name to create |
| `account-name` | String | Account to authorize on the new database |
| `account-privilege` | String | `ReadWrite` / `ReadOnly` / `DMLOnly` / `DDLOnly` |
| `charset` | String | Character set: `utf8` / `gbk` / `latin1` / `utf8mb4` |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-description` | String | Database description |
| `biz-mode` | String | Database mode: `auto` (auto partitioning) / `drds` |
| `storage-pool-name` | String | Storage pool name |
| `security-account-name` | String | Security admin account (required if rights separation enabled) |
| `security-account-password` | String | Security admin password (required if rights separation enabled) |

### CLI example

```bash
aliyun polardbx create-db \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --db-name <database> \
  --account-name <account> \
  --account-privilege ReadWrite \
  --charset utf8mb4 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateDB`

---

## DeleteDB

Delete a database.

> **[MUST] Secondary confirmation required.** Deleting a database permanently removes its data. Warn the user and obtain explicit confirmation before executing.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `db-name` | String | Database name to delete |

### CLI example

```bash
aliyun polardbx delete-db \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --db-name <database> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DeleteDB`

---

## DescribeDbList

Query the database list of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-name` | String | Filter by database name |

### CLI example

```bash
aliyun polardbx describe-db-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDbList`

---

## DescribeDistributeTableList

Query the table list of a database (distribution info).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `db-name` | String | Database name |

### CLI example

```bash
aliyun polardbx describe-distribute-table-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --db-name <database> \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeDistributeTableList`

---

## DescribeArchiveTableList

Query the cold-storage (archive) table list.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |
| `page-index` | Integer | Page index, starting from 1 |
| `page-size` | Integer | Page size |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `schema-name` | String | Filter by schema name |
| `table-name` | String | Filter by table name |
| `status` | String | Filter by status |

### CLI example

```bash
aliyun polardbx describe-archive-table-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --page-index 1 \
  --page-size 30 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeArchiveTableList`

---

## ModifyDatabaseDescription

Modify a database's description/remark.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance ID |
| `db-name` | String | Database name |
| `db-description` | String | New database description |

### CLI example

```bash
aliyun polardbx modify-database-description \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --db-name <database> \
  --db-description "order service database" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyDatabaseDescription`
