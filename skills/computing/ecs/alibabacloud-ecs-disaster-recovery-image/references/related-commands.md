# Related CLI Commands -- alibabacloud-ecs-disaster-recovery-image

This Skill is implemented entirely with Aliyun CLI in plugin mode. The list below covers each step's commands and key parameters.

> **Every command MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}`** to ensure observability and auditability. The flag is omitted from the table for brevity, but it is [MUST] add it at execution time.

## Command Summary

| Step | Product | CLI Command | Description |
|------|---------|-------------|-------------|
| 1 | ECS | `aliyun ecs describe-instances` | Query basic info (type, network, billing) of the source instance |
| 1 | ECS | `aliyun ecs describe-disks` | Query Category, Size, PerformanceLevel, and Device for all disks (system + data) |
| 2 | ECS | `aliyun ecs create-image` | Create a whole-instance image from the source instance (with all data disk mappings) |
| 3 | ECS | `aliyun ecs describe-images` | Poll image creation progress until status is Available |
| 4 | ECS | `aliyun ecs describe-available-resource` | Query stock for a given instance type / disk category in the target zone |
| 4 | ECS | `aliyun ecs describe-vswitches` | List VSwitches in the source VPC for the target zone |
| 4 | VPC | `aliyun vpc create-vswitch` | Create a new VSwitch when the target zone has none |
| 5 | ECS | `aliyun ecs run-instances` | Create the new instance from the image in the target zone (restores all disks in one call) |
| 6 | ECS | `aliyun ecs describe-instances` | Verify Running status, zone, type, and private IP of the new instance |
| 6 | ECS | `aliyun ecs describe-disks` | Verify the new instance's disk Category/PerformanceLevel match the source |

## General Command Conventions

| Rule | Correct example | Incorrect example |
|------|-----------------|-------------------|
| Command name format | `describe-instances` (hyphenated) | `DescribeInstances` (PascalCase) |
| Region parameter | `--biz-region-id cn-beijing` | `--region-id`, `--RegionId` |
| Cross-region endpoint | `--endpoint ecs.cn-beijing.aliyuncs.com` | Endpoint omitted on cross-default-region calls |
| User-Agent | Every API call carries `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}` | Missing user-agent |

## Key Parameter Quick Reference

### `aliyun ecs describe-instances`
- `--biz-region-id` -- Required, the region of the source instance
- `--instance-ids` -- JSON array string, e.g., `'["i-xxx"]'`
- `--endpoint` -- Required when calling outside the default region, e.g., `ecs.cn-beijing.aliyuncs.com`

### `aliyun ecs describe-disks`
- `--biz-region-id` -- Required
- `--instance-id` -- A single instance ID (do NOT use a JSON array form)

### `aliyun ecs create-image`
- `--biz-region-id` -- Required
- `--instance-id` -- Required, source instance ID (the whole-instance image will automatically include the system disk + data disks)
- `--image-name` -- Required, recommended format `Create_from_<instance-id>`
- `--description` -- Optional, image description

### `aliyun ecs describe-images`
- `--biz-region-id` -- Required
- `--image-id` -- Required, a single image ID
- `--status` -- Recommended `"Creating,Available,UnAvailable"` to monitor abnormal states

### `aliyun ecs describe-available-resource`
- `--biz-region-id` -- Required
- `--destination-resource` -- Enum: `InstanceType` / `SystemDisk` / `DataDisk` / `Network` / `IoOptimized` / `Zone`, etc.
- `--instance-type` -- Required, target instance type
- `--instance-charge-type` -- Required, `PostPaid` or `PrePaid`
- `--zone-id` -- Use when checking a specific zone

### `aliyun ecs describe-vswitches`
- `--biz-region-id` -- Required
- `--vpc-id` -- Required, the VPC of the source instance

### `aliyun vpc create-vswitch`
- `--biz-region-id` -- Required
- `--vpc-id` -- Required
- `--zone-id` -- Required, target zone
- `--cidr-block` -- Required, VSwitch CIDR (must not conflict with existing VSwitches)
- `--endpoint` -- Required when calling outside the default region: `vpc.<region>.aliyuncs.com`

### `aliyun ecs run-instances`
- `--biz-region-id` -- Required
- `--zone-id` -- Required, target zone
- `--image-id` -- Required, the image created in Step 2
- `--instance-type` -- Required, instance type
- `--vswitch-id` -- Required, VSwitch in the target zone
- `--security-group-id` -- Required, recommended to reuse the source security group
- `--instance-name` -- Optional, new instance name (suggested `recovery-<original-name>`)
- `--instance-charge-type` -- Reuse source instance value
- `--internet-charge-type` -- Reuse source instance value
- `--internet-max-bandwidth-out` -- Reuse source instance value
- `--system-disk-category` -- Reuse source system disk Category
- `--system-disk-size` -- Reuse source system disk size (GB)
- `--system-disk-performance-level` -- **Must be explicit** (PL0/PL1/PL2/PL3, only for the cloud_essd family)
- `--data-disk` -- Used to override data-disk parameters from the image: `Device=/dev/xvdb Category=cloud_essd Size=120 PerformanceLevel=PL0`
- `--amount` -- Number of instances to create; fixed at `1` for this scenario

> **CRITICAL: `--data-disk` MUST use `Device=` rather than `SnapshotId=`.**
> `Device=` **overrides** parameters of disks already auto-restored by the image; `SnapshotId=` creates an **additional** disk, causing duplicates.

> **CRITICAL: Do not use the `--data-disk-N-*` form (e.g., `--data-disk-1-category`)**; that form does not support `PerformanceLevel` and causes PL downgrades.
