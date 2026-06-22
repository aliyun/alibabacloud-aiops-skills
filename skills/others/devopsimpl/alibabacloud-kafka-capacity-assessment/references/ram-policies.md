# RAM Policies — Kafka Capacity Assessment Skill

This skill invokes the following APIs and requires the corresponding RAM permissions:

## Required Permissions

| API | Action | Resource Scope | Description |
|:---|:---|:---|:---|
| `GetInstanceList` | `alikafka:GetInstanceList` | `*` | Retrieve the Kafka instance list and instance metadata for the specified region |
| `DescribeMetricList` | `cms:DescribeMetricList` | `*` | Query CloudMonitor metric data |

## Minimum Permission Policy

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "alikafka:GetInstanceList",
        "cms:DescribeMetricList"
      ],
      "Resource": "*"
    }
  ],
  "Version": "1"
}
```

## Permission Notes

- This skill performs read-only query operations exclusively; no write-operation permissions are required
- `alikafka:GetInstanceList`: Used to retrieve instance metadata (series, specification family, throughput limits, etc.); this is the foundation of the capacity assessment
- `cms:DescribeMetricList`: Used to query CloudMonitor metric data (throughput ratios, disk utilization, connection counts, throttle durations, etc.)

## Common Permission Errors

| Error Code | Cause | Resolution |
|:---|:---|:---|
| `Forbidden.RAM` | RAM user lacks the required permission | Contact the primary account administrator to attach the minimum permission policy above |
| `InvalidAccessKeyId.NotFound` | AccessKey does not exist | Verify the credential configuration |
| `Forbidden.AccessKeyDisabled` | AccessKey has been disabled | Re-enable the AccessKey in the RAM console |
