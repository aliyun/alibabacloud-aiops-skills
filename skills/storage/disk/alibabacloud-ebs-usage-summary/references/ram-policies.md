# RAM Policies for EBS Monitoring Skill

This document lists the RAM (Resource Access Management) permissions required for the Alibaba Cloud EBS monitoring skill.

## Required Permissions

This skill is **read-only**. Every action below is a query action; none of them create, modify, or delete a resource.

### EBS and ECS API Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ebs:DescribeMetricData",
        "ebs:GetReport",
        "ebs:ListReports",
        "ecs:DescribeDisks"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

| API Action | CLI Command (plugin mode) | Description | Use Case |
|------------|---------------------------|-------------|----------|
| `ebs:DescribeMetricData` | `aliyun ebs describe-metric-data` | Query disk monitoring metrics (IOPS, BPS, bandwidth utilization) | Scenarios 1-5: Query single/multiple disk metrics, group by category, compare across AZs, multi-dimension filtering |
| `ebs:GetReport` | `aliyun ebs get-report` | Retrieve CloudLens for EBS resource overview reports (latest or historical) | Scenarios 6, 8: Get latest or specific historical resource overview report |
| `ebs:ListReports` | `aliyun ebs list-reports` | List historical CloudLens for EBS resource overview reports | Scenario 7: Browse available historical reports |
| `ecs:DescribeDisks` | `aliyun ecs describe-disks` | Look up disk metadata (disk ID, name, category, attached instance) | Scenario 5 Pre-Step **only**: resolve a user-supplied disk *name* to the disk ID required by `--dimensions`, or list a region's disks when the user supplied no identifier. Never used to fetch metric values |

> The `Action` values in the policy JSON are POP API action identifiers and keep their original casing. The CLI is always invoked in plugin mode (lowercase-hyphenated), as shown in the second column.
>
> **Scope note:** `ecs:DescribeDisks` is required only when a disk reference has to be resolved to a disk ID. If callers always supply disk IDs directly, it can be omitted from the policy — the Scenario 5 Pre-Step is then unavailable and the skill must ask the user for the disk ID instead.

## Applying Permissions

### Option 1: Attach System Policy

If a system policy exists that covers these permissions, attach it directly to the RAM user or role.

### Option 2: Create Custom Policy

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies** > **Create Policy**
3. Select the **JSON** tab
4. Paste the policy JSON above
5. Name the policy (e.g., `EBSMonitoringReadOnly`)
6. Click **Create Policy**
7. Attach the policy to the target RAM user or role

## Troubleshooting Permission Errors

### Common Error Codes

| Error Code | Cause | Solution |
|------------|-------|----------|
| `Forbidden.RAM` | RAM user/role lacks required permissions | Attach the policy above to the user/role |
| `NoPermission` | No permission to call the API | Verify the policy is attached and the user is using the correct identity |
| `403 Forbidden` | Access denied | Check if the account has been suspended or if there are account-level restrictions |

### Verification

After attaching permissions, verify access:

```bash
# Test DescribeMetricData permission
aliyun ebs describe-metric-data \
  --metric-name disk_read_iops \
  --biz-region-id <region-id> \
  --period 60 \
  --start-time <start-time> \
  --end-time <end-time>

# Test GetReport permission
aliyun ebs get-report \
  --biz-region-id <region-id> \
  --report-type present \
  --app-name default

# Test ListReports permission
aliyun ebs list-reports \
  --biz-region-id <region-id> \
  --page-size 10 \
  --page-number 1

# Test DescribeDisks permission (only needed for disk name -> disk ID resolution)
aliyun ecs describe-disks \
  --biz-region-id <region-id> \
  --page-size 10
```

Substitute `<region-id>` with the target region and `<start-time>` / `<end-time>` with an ISO 8601 UTC window (`yyyy-MM-ddTHH:mm:ssZ`) inside the retention period.

If any command returns a permission error, follow the **Permission Failure Handling** flow in the main SKILL.md.

## Additional Notes

- These permissions are **read-only** — they allow querying metrics, reports, and disk metadata but do not permit creating, modifying, or deleting EBS resources.
- For production environments, consider restricting the `Resource` field to specific regions or resource ARNs if needed.
- CloudLens for EBS must be enabled in the target region before using the `get-report` and `list-reports` commands. See the main SKILL.md **Prerequisites** section for details.
