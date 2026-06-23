# Related CLI Commands — ECS Snapshot-Based Disaster Recovery

All commands use plugin mode (kebab-case). Every API command requires `--user-agent`.

## Instance & Disk Queries

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs describe-instances` | Query instance details | `--biz-region-id`, `--instance-ids '["id"]'` |
| `aliyun ecs describe-disks` | Query disk info for an instance | `--biz-region-id`, `--instance-id` |
| `aliyun ecs describe-available-resource` | Check resource availability in AZ | `--zone-id`, `--destination-resource`, `--instance-type` |

## Snapshot Operations

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs create-snapshot-group` | Create snapshot consistency group for all disks | `--instance-id`, `--name` |
| `aliyun ecs describe-snapshot-groups` | Query snapshot group status | `--snapshot-group-id` |
| `aliyun ecs create-snapshot` | Create snapshot from a single disk | `--endpoint`, `--disk-id`, `--snapshot-name` |
| `aliyun ecs describe-snapshots` | Query snapshot status | `--snapshot-ids '["id1" "id2"]'` |

## Image Operations

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs create-image` | Create custom image | `--image-name`, `--disk-device-mapping DiskType=system SnapshotId=... Size=...` |
| `aliyun ecs describe-images` | Query image status | `--image-id`, `--status "Creating,Available,UnAvailable"` |

## Network Operations

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs describe-vswitches` | Check VSwitches in a VPC/AZ | `--vpc-id`, `--zone-id` |
| `aliyun ecs create-vswitch` | Create VSwitch in target AZ | `--vpc-id`, `--zone-id`, `--cidr-block` |

## Instance Creation

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs run-instances` | Launch new instance | `--zone-id`, `--image-id`, `--instance-type`, `--security-group-id`, `--vswitch-id`, `--system-disk-category`, `--system-disk-size`, `--instance-charge-type`, `--internet-charge-type`, `--internet-max-bandwidth-out`, `--data-disk SnapshotId=... Category=... Size=... PerformanceLevel=...` |

## Disk Operations (Scenario B)

| Command | Description | Key Parameters |
| --- | --- | --- |
| `aliyun ecs create-disk` | Create disk from snapshot | `--biz-region-id`, `--zone-id`, `--snapshot-id`, `--disk-category`, `--size`, `--performance-level` |
| `aliyun ecs attach-disk` | Attach disk to instance | `--endpoint`, `--disk-id`, `--instance-id` |

## Common Flags for All Commands

| Flag | Description | Required |
| --- | --- | --- |
| `--biz-region-id <region>` | Target region (e.g., cn-beijing) | Yes |
| `--endpoint ecs.<region>.aliyuncs.com` | Explicit endpoint | Yes (when CLI default differs) |
| `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot/{session-id}` | Observability UA | Yes (all API commands) |

## Parameter Format Notes

### List parameters
```bash
# Space-separated values (NOT numbered params)
--snapshot-ids '["s-xxx" "s-yyy"]'
--instance-ids '["i-xxx"]'
```

### Structured parameters (Key=Value)
```bash
# disk-device-mapping for create-image
--disk-device-mapping DiskType=system SnapshotId=s-xxx Size=40

# data-disk for run-instances (multiple disks = multiple flags)
--data-disk SnapshotId=s-aaa Category=cloud_essd Size=100 PerformanceLevel=PL1 \
--data-disk SnapshotId=s-bbb Category=cloud_essd Size=200 PerformanceLevel=PL0
```

### Enum values requiring PascalCase
```bash
--destination-resource InstanceType    # NOT "instancetype"
--destination-resource SystemDisk      # NOT "systemdisk"
```
