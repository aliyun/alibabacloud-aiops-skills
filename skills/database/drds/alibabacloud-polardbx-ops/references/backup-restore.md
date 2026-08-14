# Backup & Restore APIs

PolarDB-X backup policy, backup set, and instance restore APIs. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`; instance identifier flag is `--db-instance-name` (format `pxc-********`).

---

## CreateBackup

Trigger an on-demand backup.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region, e.g. `cn-hangzhou` |
| `db-instance-name` | String | Instance name/ID |

> **[MUST] `--backup-type` is required in practice even though the OpenAPI doc lists it as optional.** Omitting it makes the server return HTTP 400 `InvalidParameter.BackupType` (`Message: BackupType is illegal`). The error is printed by the CLI as non-JSON `SDKError:` text, so piping straight to `jq` fails with `parse error: Invalid numeric literal ...` and hides the error code. Always pass `--backup-type 0` (fast backup) and `--client-token`.

> **[MUST] On any create-backup failure, first print the raw output without piping to `jq`**, read the `Code` (e.g. `InvalidParameter.BackupType`, `InvalidDBInstance.NotFound`, `Throttling`, `InternalError`), then handle it per SKILL.md Error & Timeout Handling and retry with the **same** `--client-token`. Do not silently fall back to other APIs.

> Note: a successful response returns `Data.BackupSetId` (often `0`), which is **not** a usable backup ID. Verify the result by polling `DescribeBackupSetList` with a time window anchored at the create-backup call (see below), never by trusting the response body alone.

### CLI example

```bash
aliyun polardbx create-backup \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --backup-type 0 \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CreateBackup`

---

## DescribeBackupPolicy

Query the backup policy of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### CLI example

```bash
aliyun polardbx describe-backup-policy \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeBackupPolicy`

---

## UpdateBackupPolicy

Modify the backup policy of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `db-instance-name` | String | Instance name/ID |
| `backup-type` | String | Backup type; currently only `0`. **Required in practice** — omitting it raises `InvalidParameter.BackupType` |
| `backup-way` | String | `P` physical / `L` logical. **Required in practice** — omitting it raises `InvalidParameter.BackupWay` |

> **[MUST] Read-then-full-write to avoid `Internal Server Error` (`Message: null`).** The backend throws a null-pointer error (surfaced as `Internal Server Error` / `null`) when the cross-region backup fields are not supplied. This happens even when you replay the instance's current values. To modify a backup policy safely:
>
> 1. First call `DescribeBackupPolicy` to read the full current policy.
> 2. Re-send **all** fields on `UpdateBackupPolicy` (not just the ones you want to change), and in particular ALWAYS include the four cross-region fields: `is-cross-region-data-backup-enabled`, `is-cross-region-log-backup-enabled`, `cross-region-data-backup-retention`, `cross-region-log-backup-retention` (use `false` / `0` when cross-region backup is off).
>
> Also note: a freshly created instance may reject policy edits until its backup subsystem is initialized; `create-backup` may succeed earlier than `update-backup-policy`.

### Common optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `backup-period` | String | Backup weekdays, 7-digit mask (Mon..Sun), `1`=on `0`=off, at least 2 days; all 7 days (`1111111`) = daily |
| `backup-plan-begin` | String | Daily backup start time (UTC), e.g. `03:00Z` |
| `backup-set-retention` | Integer | Backup set retention in days |
| `is-enabled` | Integer | Enable backup, fixed `1` |
| `local-log-retention` | Integer | Local log retention hours (0..168) |
| `local-log-retention-number` | Integer | Local binlog count (6..100, default 60) |
| `remove-log-retention` | Integer | Remote log retention days (7..730) |
| `log-local-retention-space` | Integer | Local log max space usage (0..50, default 30) |
| `cold-data-backup-interval` | Integer | Cold data backup interval days (1..59) |
| `cold-data-backup-retention` | Integer | Cold data backup retention days (30..730) |
| `force-clean-on-high-space-usage` | Integer | Force-clean binlog on high space usage |
| `is-cross-region-data-backup-enabled` | Boolean | Enable cross-region data backup |
| `is-cross-region-log-backup-enabled` | Boolean | Enable cross-region log backup |
| `dest-cross-region` | String | Cross-region backup destination region |
| `cross-region-data-backup-retention` | Integer | Cross-region data backup retention days |
| `cross-region-log-backup-retention` | Integer | Cross-region log backup retention days |

### CLI example

Complete, working example (daily backup, start `03:00Z`, 30-day retention). Note that `backup-type`, `backup-way`, and the four cross-region fields are all supplied to avoid the backend NPE described above:

```bash
aliyun polardbx update-backup-policy \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --is-enabled 1 \
  --backup-type 0 \
  --backup-way P \
  --backup-period 1111111 \
  --backup-plan-begin 03:00Z \
  --backup-set-retention 30 \
  --local-log-retention 7 \
  --local-log-retention-number 60 \
  --log-local-retention-space 30 \
  --remove-log-retention 30 \
  --cold-data-backup-interval 30 \
  --cold-data-backup-retention 120 \
  --force-clean-on-high-space-usage 1 \
  --is-cross-region-data-backup-enabled false \
  --is-cross-region-log-backup-enabled false \
  --cross-region-data-backup-retention 0 \
  --cross-region-log-backup-retention 0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

> Fill `local-*`, `remove-log-retention`, and `cold-data-*` values from the `DescribeBackupPolicy` output so you preserve the instance's current settings while changing only what the user asked for.

### RAM action

`polardbx:UpdateBackupPolicy`

---

## DescribeBackupSet

Query the details of a specific backup set.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name/ID |
| `backup-set-id` | String | Backup set ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `dest-cross-region` | String | Cross-region backup destination region |

### CLI example

```bash
aliyun polardbx describe-backup-set \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --backup-set-id 111 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeBackupSet`

---

## DescribeBackupSetList

Query the backup set list of an instance.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start-time` | Integer | Start timestamp in milliseconds |
| `end-time` | Integer | End timestamp in milliseconds |
| `page-number` | Integer | Page number, starting from 1 |
| `page-size` | Integer | Page size |
| `dest-cross-region` | String | Return backup sets in a specific region |

> **[MUST] When polling for the backup just triggered by `create-backup`, filter by `start-time` / `end-time`** (millisecond timestamps) anchored at the create-backup call time (e.g. now-5min → now+30min). The list is time-ordered and the newest entry may be an older backup set; treating it as this run's result produces a false "backup completed" verdict. Only a backup set whose `BeginTime` falls inside the window belongs to the current call. Numeric `Status`: `2` with a non-zero `EndTime` means completed.

### CLI example

```bash
aliyun polardbx describe-backup-set-list \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --start-time <ms> \
  --end-time <ms> \
  --page-number 1 --page-size 30 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeBackupSetList`

---

## DescribeOpenBackupSet

Open a commercial backup set's topology info and download links (for offline restore).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `db-instance-name` | String | Instance name/ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `restore-time` | String | Restore point, format `yyyy-MM-ddTHH:mm:ssZ` (UTC) |

### CLI example

```bash
aliyun polardbx describe-open-backup-set \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --db-instance-name pxc-******** \
  --restore-time 2024-10-14T00:00:00Z \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeOpenBackupSet`

---

## RestoreDBInstance

Clone / restore a PolarDB-X instance from a backup set or point in time.

> **[MUST] Secondary confirmation required.** This creates a new billable instance. Present the full spec, `PayType`, and billing note to the user and obtain explicit confirmation. See the **Mandatory Secondary Confirmation** section in `SKILL.md`.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region for the new instance |
| `pay-type` | String | `PREPAY` / `POSTPAY` |
| `engine-version` | String | MySQL engine version `5.7` or `8.0` |
| `topology-type` | String | `3azones` / `1azone` |
| `clone-instance-name` | String | Source instance name |
| `recovery-type-code` | String | Recovery type, e.g. `Clone` |
| `backup-set-region` | String | Region of the backup set |
| `source-instance-region` | String | Region of the source instance |

### Common optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `series` | String | `enterprise` / `standard` |
| `cn-class` / `dn-class` | String | Enterprise CN / DN node class |
| `cn-node-count` / `dn-node-count` | String | Enterprise CN / DN node count |
| `db-node-class` / `db-node-count` | String/Int | Standard edition node class / count (min 2) |
| `backup-set-id` | String | Backup set ID (for backup-set restore) |
| `restore-time` | String | Restore point `yyyy-MM-ddTHH:mm:ssZ` (UTC) |
| `vpc-id` / `vswitch-id` | String | VPC / VSwitch |
| `primary-zone` / `secondary-zone` / `tertiary-zone` / `zone-id` | String | Zones |
| `storage-type` | String | `custom_local_ssd` / `cloud_auto` |
| `pay-type` related: `period`, `used-time`, `auto-renew` | - | Billing options |
| `gdn-role` | String | GDN role, e.g. `standby` |
| `client-token` | String | Idempotency token |

### CLI example

```bash
aliyun polardbx restore-db-instance \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --pay-type POSTPAY \
  --engine-version 8.0 \
  --topology-type 1azone \
  --clone-instance-name pxc-source \
  --recovery-type-code Clone \
  --backup-set-id 111 \
  --backup-set-region cn-hangzhou \
  --source-instance-region cn-hangzhou \
  --client-token $(uuidgen) \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:RestoreDBInstance`
