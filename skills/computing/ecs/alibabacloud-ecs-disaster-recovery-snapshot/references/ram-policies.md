# RAM Policies for ECS Snapshot-Based Disaster Recovery

## Required Permissions

The following RAM policy grants the minimum permissions required for this skill to operate.

### Full Policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:CreateSnapshot",
        "ecs:CreateSnapshotGroup",
        "ecs:DescribeSnapshotGroups",
        "ecs:DescribeSnapshots",
        "ecs:CreateImage",
        "ecs:DescribeImages",
        "ecs:DescribeVSwitches",
        "ecs:CreateVSwitch",
        "ecs:DescribeAvailableResource",
        "ecs:RunInstances",
        "ecs:CreateDisk",
        "ecs:AttachDisk"
      ],
      "Resource": "*"
    }
  ]
}
```

### Permission Breakdown by Scenario

#### Scenario A — Full Instance Backup

| Permission                    | Step | Purpose                                         |
| ----------------------------- | ---- | ----------------------------------------------- |
| ecs:DescribeInstances         | 2    | Query source instance spec, VPC, security group |
| ecs:DescribeDisks             | 2, 7 | Query source disks; verify new instance disks   |
| ecs:CreateSnapshot            | 3    | Create individual snapshot (single disk path)   |
| ecs:CreateSnapshotGroup       | 3    | Create snapshot consistency group (multi-disk)  |
| ecs:DescribeSnapshotGroups    | 3    | Poll snapshot group completion status           |
| ecs:DescribeSnapshots         | 3    | Poll individual snapshot completion status      |
| ecs:CreateImage               | 4    | Create system-disk-only custom image            |
| ecs:DescribeImages            | 4    | Poll image creation status                      |
| ecs:DescribeVSwitches         | 5    | Check existing VSwitches in target AZ           |
| ecs:CreateVSwitch             | 5    | Create VSwitch if none exists (with user consent) |
| ecs:DescribeAvailableResource | 5    | Check instance type & disk category stock       |
| ecs:RunInstances              | 6    | Launch DR instance in target AZ                 |
| ecs:CreateDisk                | 7    | Create data disk from snapshot group (multi-disk) |
| ecs:AttachDisk                | 7    | Attach restored data disk to DR instance        |

#### Scenario B — Disk-Level Backup

| Permission                    | Step | Purpose                                    |
| ----------------------------- | ---- | ------------------------------------------ |
| ecs:DescribeInstances         | 2    | Query target instance details (AZ)         |
| ecs:DescribeDisks             | 2, 6 | Query source disks; verify attached disks  |
| ecs:CreateSnapshot            | 3    | Create snapshot of specified disk(s)       |
| ecs:DescribeSnapshots         | 3    | Poll snapshot completion status            |
| ecs:CreateDisk                | 4    | Create new disk from snapshot              |
| ecs:AttachDisk                | 5    | Attach new disk to target instance         |

### Optional Permissions

| Permission                    | When Needed                                  |
| ----------------------------- | -------------------------------------------- |
| ecs:DescribeSecurityGroups    | If security group validation is required     |
| vpc:DescribeVpcs              | If VPC information needs to be queried       |
| ecs:DeleteSnapshot            | If cleanup of temporary snapshots is needed  |
| ecs:DeleteImage               | If cleanup of temporary images is needed     |

## Applying the Policy

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** → **Policies** → **Create Policy**
3. Select **Script** mode and paste the JSON above
4. Name it: `EcsDisasterRecoverySnapshotPolicy`
5. Attach the policy to the RAM user/role used by the CLI

## Least Privilege Recommendations

- Restrict `Resource` to specific instance IDs if the source instances are known
- Use condition keys to limit operations to specific regions:
  ```json
  "Condition": {
    "StringEquals": {
      "acs:RequestedRegion": ["cn-beijing", "cn-hangzhou"]
    }
  }
  ```
- For production environments, consider separate policies for Scenario A and Scenario B
