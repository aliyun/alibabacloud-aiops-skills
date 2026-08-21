# RAM Policies (Read-Only, Least Privilege)

This skill is **strictly read-only**. It requires no write/mutating permissions
and never performs containment, quarantine, process termination, or any
handling action.

## Required Permissions

### Security Center (SAS) — Core Data Source

SAS APIs accept **both** RAM action prefixes (they are equivalent aliases):

- `yundun-aegis:` — classic SAS prefix (legacy)
- `yundun-sas:` — newer SAS prefix

Both prefixes grant the same authorization. The role policy MUST include both
to ensure compatibility across different RAM evaluation paths.

| Action (both prefixes) | Step | Purpose |
|--------|------|---------|
| `DescribeSuspEvents` | 1 | Mining alert detection |
| `DescribeAlarmEventDetail` | 2 | Alert detail + IOC extraction |
| `DescribeSuspEventDetail` | 2 | Suspicious event detail |
| `DescribeSecurityStatInfo` | 3 | Account security overview |
| `DescribeFieldStatistics` | 3 | Asset/field statistics |
| `DescribeExposedInstanceList` | 4 | Exposed assets |
| `DescribeVulList` | 4 | Unpatched vulnerabilities |
| `DescribeCheckWarningSummary` | 4a | Baseline weak-config risks |
| `DescribeGroupedVul` | 4a | Grouped vulnerability stats |
| `DescribeExposedStatistics` | 4a | Exposure statistics |

### STS — Account ID Resolution

| Action | Step | Purpose |
|--------|------|---------|
| `sts:GetCallerIdentity` | Init | Auto-derive account UID when `--account` omitted |

### Optional Corroboration (only with `--corroborate`)

| Action | Step | Purpose |
|--------|------|---------|
| `cms:QueryMetricList` | 4b | CloudMonitor CPU utilization (sustained-high-CPU signal) |
| `actiontrail:LookupEvents` | 4b | High-risk operation trace (miner delivery/spread) |

## Minimal Read-Only Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-aegis:DescribeSuspEvents",
        "yundun-aegis:DescribeAlarmEventDetail",
        "yundun-aegis:DescribeSuspEventDetail",
        "yundun-aegis:DescribeSecurityStatInfo",
        "yundun-aegis:DescribeFieldStatistics",
        "yundun-aegis:DescribeExposedInstanceList",
        "yundun-aegis:DescribeVulList",
        "yundun-aegis:DescribeCheckWarningSummary",
        "yundun-aegis:DescribeGroupedVul",
        "yundun-aegis:DescribeExposedStatistics",
        "yundun-sas:DescribeSuspEvents",
        "yundun-sas:DescribeAlarmEventDetail",
        "yundun-sas:DescribeSuspEventDetail",
        "yundun-sas:DescribeSecurityStatInfo",
        "yundun-sas:DescribeFieldStatistics",
        "yundun-sas:DescribeExposedInstanceList",
        "yundun-sas:DescribeVulList",
        "yundun-sas:DescribeCheckWarningSummary",
        "yundun-sas:DescribeGroupedVul",
        "yundun-sas:DescribeExposedStatistics",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricList",
        "actiontrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Prohibited Actions

Under no circumstances should this skill call any mutating API. All actions
matching the following patterns are strictly forbidden:
`Update*`, `Delete*`, `Disable*`, `Modify*`, `Create*`,
`Rotate*`, `Set*`, `Operate*`.
