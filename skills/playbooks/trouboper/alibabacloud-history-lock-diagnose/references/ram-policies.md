# RAM Permission Policy List

## Required RAM Permissions

### DAS Permissions

| Permission | Action | Access Level | Description |
|-----------|--------|-------------|-------------|
| Get SQL Audit Hot Data | hdm:GetDasSQLLogHotData | Read | Query SQL audit logs (primary data source) |
| Get Deadlock History | hdm:GetDeadLockHistory | Read | Query historical deadlock analysis task list |
| Get Deadlock Detail | hdm:GetDeadLockDetail | Read | Get detailed deadlock event analysis |
| Create Latest Deadlock Analysis | hdm:CreateLatestDeadLockAnalysis | Write | Trigger latest InnoDB deadlock analysis |
| Query SQL Insight Config | hdm:DescribeSqlLogConfig | Read | Query SQL Insight feature status |
| Get MySQL Sessions | hdm:GetMySQLAllSessionAsync | Read | Get instance current session information |

## Minimum Privilege Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hdm:GetDasSQLLogHotData",
        "hdm:GetDeadLockHistory",
        "hdm:GetDeadLockDetail",
        "hdm:CreateLatestDeadLockAnalysis",
        "hdm:DescribeSqlLogConfig",
        "hdm:GetMySQLAllSessionAsync"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Check the RAM permissions listed above in this file
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
