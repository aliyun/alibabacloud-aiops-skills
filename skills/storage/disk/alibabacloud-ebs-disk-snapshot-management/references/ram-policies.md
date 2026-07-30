# RAM Permission Policies for Snapshot Management

## Least-privilege snapshot operator policy

Use this policy for operators who need to create, delete, query, and roll back snapshots, plus manage auto snapshot policies.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateSnapshot",
        "ecs:DeleteSnapshot",
        "ecs:DescribeSnapshots",
        "ecs:ResetDisk",
        "ecs:ResetDisks",
        "ecs:CreateSnapshotGroup",
        "ecs:DescribeSnapshotGroups",
        "ecs:DeleteSnapshotGroup",
        "ecs:CreateAutoSnapshotPolicy",
        "ecs:ApplyAutoSnapshotPolicy",
        "ecs:CancelAutoSnapshotPolicy",
        "ecs:DescribeAutoSnapshotPolicyEx",
        "ecs:DeleteAutoSnapshotPolicy",
        "ecs:DescribeAutoSnapshotPolicyAssociations",
        "ecs:DescribeDisks",
        "ecs:DescribeInstances",
        "ecs:DescribeRegions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-only snapshot auditor policy

Use this policy for users who only need to inspect snapshots and policies.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeSnapshots",
        "ecs:DescribeSnapshotGroups",
        "ecs:DescribeSnapshotLinks",
        "ecs:DescribeAutoSnapshotPolicyEx",
        "ecs:DescribeAutoSnapshotPolicyAssociations",
        "ecs:DescribeDisks",
        "ecs:DescribeInstances",
        "ecs:DescribeRegions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Resource-level authorization example

Restrict snapshot deletion to specific snapshots and disks.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DeleteSnapshot"
      ],
      "Resource": [
        "acs:ecs:cn-hangzhou:*:snapshot/*"
      ],
      "Condition": {
        "StringEquals": {
          "ecs:tag/Environment": "development"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeSnapshots"
      ],
      "Resource": "*"
    }
  ]
}
```

## Mandatory auto snapshot policy on new instances

Use this policy to enforce that newly created instances must attach an auto snapshot policy to system and data disks.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Action": [
        "ecs:RunInstances",
        "ecs:CreateInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ecs:IsDiskAutoSnapshotPolicyEnabled": "*false*"
        }
      },
      "Effect": "Deny"
    },
    {
      "Action": [
        "ecs:RunInstances",
        "ecs:CreateInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ecs:IsSystemDiskAutoSnapshotPolicyEnabled": "false"
        }
      },
      "Effect": "Deny"
    }
  ]
}
```

## Notes

- Replace `*` with specific region IDs, account IDs, or resource IDs for tighter control.
- Some actions, such as `DeleteSnapshot` on a snapshot used by a custom image, may also require `ecs:DeleteImage` permission.
- Always test policies in a non-production environment before broad deployment.
