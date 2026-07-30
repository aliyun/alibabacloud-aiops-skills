# Snapshot Error Code Handbook

Common ECS snapshot errors, their meanings, and recommended actions.

## General errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `Throttling` | Too many requests. | Exponential backoff: 1s, 2s, 4s, 8s, 16s; retry up to 5 times. |
| `InternalError` | Server-side internal error. | Retry up to 3 times; preserve `RequestId`; open a ticket if persistent. |
| `InvalidAccountStatus.NotEnoughBalance` | Account in arrears. | Pause operations; recharge the account. |
| `InvalidAccountStatus.SnapshotServiceUnavailable` | Snapshot service not opened. | Open the snapshot service in the ECS console. |
| `InvalidRegionId.MalFormed` / `InvalidRegionId.NotFound` | Bad region ID. | Verify the region ID against `DescribeRegions`. |

## Snapshot creation errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `IncorrectDiskStatus.CreatingSnapshot` | A snapshot is already being created on this disk. | Wait for the existing snapshot to finish. |
| `IncorrectDiskStatus.NeverAttached` | Disk was never attached to an instance. | Attach the disk to an instance first. |
| `QuotaExceed.Snapshot` / `QuotaExceed.SnapshotQuota` | Snapshot quota exceeded. | Delete old or unnecessary snapshots. |
| `QuotaExceed.ConcurrentSnapshotQuota` | Concurrent snapshot tasks exceed limit. | Wait for current tasks to complete. |
| `DiskCategory.OperationNotSupported` | Disk type does not support snapshots. | Check disk category; ESSD PL-X, local disks, and elastic ephemeral disks are unsupported. |
| `IncorrectInstanceStatus` | Attached instance state does not allow snapshot creation. | Ensure the instance is `Running` or `Stopped`. |
| `InstanceLockedForSecurity` | Instance is locked. | Resolve the security lock before proceeding. |

## Snapshot query errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `InvalidSnapshotIds.Malformed` | SnapshotIds format invalid. | Use a JSON array with valid snapshot IDs. |
| `InvalidFilterKey.NotFound` | Filter key not supported. | Use only `CreationStartTime` or `CreationEndTime`. |
| `InvalidFilterValue` | Filter value invalid or too long. | Use ISO 8601 UTC+0 format. |
| `InvalidTag.Mismatch` | Tag key/value mismatch. | Ensure every `Tag.N.Key` has a corresponding `Tag.N.Value`. |

## Snapshot deletion errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `SnapshotCreatedImage` | Snapshot used by a custom image. | Delete the custom image first via `DeleteImage`. |
| `SnapshotCreatedDisk` | Snapshot used to create a disk. | Set `Force=true` only after explicit user confirmation. |
| `InvalidOperation.DeleteSharedSnapshotUnsupported` | Snapshot is shared. | Revoke sharing via Resource Management first. |
| `InvalidOperation.SnapshotIsLocked` | Snapshot is locked. | Wait for the lock to expire or unlock it. |
| `InvalidSnapshotId.NotFound` | Snapshot does not exist. | Verify the snapshot ID. |

## Disk rollback errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `IncorrectDiskStatus` | Disk state not suitable for rollback. | Ensure disk is `In_use` or `Available`. |
| `IncorrectInstanceStatus` | Instance not `Stopped`. | Stop the instance before rollback. |
| `InstanceLockedForSecurity` | Instance locked. | Resolve the security lock. |
| `InvalidParameter.Mismatch` | Snapshot and disk encryption mismatch. | Use a snapshot whose encryption state matches the disk. |
| `InvalidSnapshot.TooOld` | Snapshot created before 2013-07-15. | Use a newer snapshot. |
| `InvalidSnapshotId.NotReady` | Snapshot still in `progressing` state. | Wait for snapshot completion. |
| `InvalidOperation.DiskResetInProgress` | Another reset is running. | Wait for the current reset to finish. |
| `DryRunOperation` | Dry-run validation passed. | Proceed with the actual call. |

## Auto snapshot policy errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `InvalidAutoSnapshotPolicyId.NotFound` | Policy ID does not exist. | Verify the policy ID or create a new policy. |
| `QuotaExceed.AppliedAutoSnapshotPolicyQuota` | Disk already has 10 policies. | Remove unused policies before adding more. |
| `InvalidOperation.AutoSnapshotPolicyConflict` | Cannot mix promotional policies with regular policies. | Choose compatible policies. |
| `InvalidDiskId.NotFound` | Disk not found in the region. | Verify disk ID and region. |

## Snapshot consistency group errors

| Error code | Meaning | Action |
|------------|---------|--------|
| `InvalidDiskIds.NotInSameZone` | Disks are not in the same AZ. | Select disks within one availability zone. |
| `InvalidOperation.MultiAttachDisk` | Multi-attach disk cannot be included. | Exclude multi-attach disks via `ExcludeDiskId.N`. |
| `NumberExceed.TooManyDisks` | More than 16 disks in request. | Reduce group size to 16 disks or less. |
| `CapacityExceed.TooManyDisks` | Total capacity exceeds 32 TiB. | Reduce total disk capacity in the group. |
| `InvalidDisk.ShareVolume` | Shared volume unsupported. | Use instance-local disks instead. |
| `InvalidRegion.NotSupport` | Region does not support snapshot groups. | Use a supported region. |

## Retry guidelines

- **Client errors (4xx)**: Do not retry blindly. Inspect the error, fix the input, and ask the user when confirmation is needed.
- **Server errors (5xx)**: Retry up to 3 times with 2-second intervals; preserve `RequestId`.
- **Throttling (403)**: Back off exponentially, max 5 attempts.
- **Side-effect operations**: Always ask for explicit user confirmation before retrying `DeleteSnapshot` with `Force=true`, `ResetDisk`, or `ResetDisks`.
