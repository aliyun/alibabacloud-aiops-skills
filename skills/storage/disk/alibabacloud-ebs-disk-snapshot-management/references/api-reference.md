# ECS Snapshot API Reference

Quick reference for the most common ECS snapshot APIs. Always consult the latest [Alibaba Cloud ECS OpenAPI documentation](https://www.alibabacloud.com/help/zh/ecs/developer-reference/api-ecs-2014-05-26-createsnapshot) for updates.

## create-snapshot

Create a snapshot for a single disk.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `DiskId` | string | Yes | Target disk ID. |
| `SnapshotName` | string | No | 2–128 characters, start with letter or Chinese character, cannot start with `auto`. |
| `Description` | string | No | 2–256 characters. |
| `RetentionDays` | integer | No | 1–65535 days; empty means permanent. |
| `ClientToken` | string | No | Idempotency token, up to 64 ASCII characters. |
| `ResourceGroupId` | string | No | Enterprise resource group ID. |
| `Tag.N.Key` / `Tag.N.Value` | string | No | Up to 20 tags. |

### Response parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `SnapshotId` | string | Created snapshot ID. |
| `RequestId` | string | Request ID for troubleshooting. |

### Example request (Alibaba Cloud CLI)

```bash
aliyun ecs create-snapshot \
  --DiskId d-bp1s5fnvk4gn2tws0**** \
  --SnapshotName pre-upgrade-backup \
  --RetentionDays 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{session-id}
```

## describe-snapshots

Query snapshot list and details.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `RegionId` | string | Yes | Region ID. |
| `InstanceId` | string | No | Filter by instance. |
| `DiskId` | string | No | Filter by disk. |
| `SnapshotIds` | string | No | JSON array of up to 100 snapshot IDs. |
| `Status` | string | No | `progressing`, `accomplished`, `failed`, `all` (default). |
| `SnapshotType` | string | No | `auto`, `user`, `all` (default). |
| `Category` | string | No | `standard`, `archive`, `flash`. |
| `NextToken` | string | No | Pagination token. |
| `MaxResults` | integer | No | Page size, max 100, default 10. |
| `Filter.1.Key` / `Filter.1.Value` | string | No | `CreationStartTime` / `CreationEndTime`, UTC+0 format. |
| `Tag.N.Key` / `Tag.N.Value` | string | No | Filter by tags. |

### Key response fields

| Field | Description |
|-------|-------------|
| `Status` | `progressing`, `accomplished`, `failed`. |
| `Progress` | Creation progress percentage. |
| `Available` | Whether the snapshot can be used for rollback or creating disks. |
| `Usage` | `none`, `image`, `disk`, `image_disk`. |
| `Category` | `standard`, `archive`, `flash`. |
| `SourceDiskId` | Source disk ID. |
| `SourceDiskSize` | Source disk size in GiB. |
| `RetentionDays` | Auto-deletion retention days. |
| `Encrypted` | Whether the snapshot is encrypted. |

## delete-snapshot

Delete a specified snapshot.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `SnapshotId` | string | Yes | Snapshot ID to delete. |
| `Force` | boolean | No | Force deletion if the snapshot was used to create a disk. Default `false`. |

### Common blocking conditions

- Snapshot used by a custom image → delete image first.
- Snapshot used by a disk → set `Force=true` after user confirmation.
- Shared snapshot → revoke sharing first.

## reset-disk

Roll back a single disk to a historical snapshot.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `DiskId` | string | Yes | Disk to roll back. |
| `SnapshotId` | string | Yes | Historical snapshot from the same disk. |
| `DryRun` | boolean | No | `true` to pre-check only. |

### Preconditions

- Instance must be `Stopped`.
- Snapshot must belong to the target disk.
- Encryption type must match between disk and snapshot.

## reset-disks

Roll back multiple disks using a snapshot consistency group.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `InstanceId` | string | Yes | Target instance ID. |
| `SnapshotGroupId` | string | Yes | Consistency group ID. |
| `DiskIds` | array | Yes | Disks in the group to roll back. |
| `AutoStartInstance` | boolean | No | Whether to start the instance after rollback. |

## create-snapshot-group

Create a crash-consistent snapshot group for multiple disks.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `RegionId` | string | Yes | Region ID. |
| `InstanceId` | string | No | Instance ID; if set, `DiskId.N` must be disks on this instance. |
| `DiskId.N` | string | No | Cross-instance disk IDs in the same AZ. Max 16 disks / 32 TiB total. |
| `ExcludeDiskId.N` | string | No | Disks to exclude (cannot use with `DiskId.N`). |
| `Name` | string | No | Group name. |
| `Description` | string | No | Group description. |
| `Tag.N.Key` / `Tag.N.Value` | string | No | Tags. |

### Constraints

- ESSD series only.
- Same availability zone.
- No multi-attach disks.
- Max 16 disks per group.

## describe-snapshot-groups

Query snapshot consistency groups.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `RegionId` | string | Yes | Region ID. |
| `SnapshotGroupId` | string | No | Group ID. |
| `Name` | string | No | Group name. |
| `Status` | string | No | `progressing`, `accomplished`, `failed`. |
| `NextToken` | string | No | Pagination token. |
| `MaxResults` | integer | No | Page size, max 100. |

## create-auto-snapshot-policy

Create an automatic snapshot policy.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regionId` | string | Yes | Region ID. |
| `repeatWeekdays` | string | Yes | JSON array of `1`–`7` (Mon–Sun). |
| `timePoints` | string | Yes | JSON array of `0`–`23` (UTC+8 hour). |
| `retentionDays` | integer | Yes | `-1` for permanent, or `1`–`65535`. |
| `autoSnapshotPolicyName` | string | No | Policy name. |
| `Tag.N.Key` / `Tag.N.Value` | string | No | Tags. |

### Example

```bash
aliyun ecs create-auto-snapshot-policy \
  --regionId cn-hangzhou \
  --repeatWeekdays '["2","4","6"]' \
  --timePoints '["2","14"]' \
  --retentionDays 7 \
  --autoSnapshotPolicyName weekly-backup \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{session-id}
```

## apply-auto-snapshot-policy

Apply a policy to one or more disks.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regionId` | string | Yes | Region ID. |
| `autoSnapshotPolicyId` | string | Yes | Policy ID. |
| `diskIds` | string | Yes | JSON array of disk IDs. |

### Limits

- Up to 10 policies per disk.
- New applications add to existing policies rather than replacing them.

## describe-auto-snapshot-policy-ex

Query automatic snapshot policies.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `RegionId` | string | Yes | Region ID. |
| `AutoSnapshotPolicyId` | string | No | Policy ID. |
| `AutoSnapshotPolicyName` | string | No | Policy name. |
| `PageNumber` | integer | No | Page number (deprecated; prefer none). |
| `PageSize` | integer | No | Page size, max 100. |

### Key response fields

| Field | Description |
|-------|-------------|
| `RepeatWeekdays` | Backup weekdays. |
| `TimePoints` | Backup hours. |
| `RetentionDays` | Retention days. |
| `DiskNums` | Number of disks using this policy. |
| `Status` | `Normal` or `Expire`. |

## delete-auto-snapshot-policy

Delete an automatic snapshot policy.

### Request parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regionId` | string | Yes | Region ID. |
| `autoSnapshotPolicyId` | string | Yes | Policy ID. |

Disks previously attached to this policy will no longer receive automatic snapshots from it.
