# RAM Permissions (Minimum Read-Only Policy)

This skill requires **read-only** access to the following APIs. No write permissions are needed — the skill never modifies, disables, or deletes any resource.

## Required Actions

| Product | RAM Action | Purpose |
|---------|-----------|---------|
| STS | `sts:GetCallerIdentity` | Auto-derive account UID when not provided |
| Security Center (SAS) | `yundun-aegis:DescribeAccesskeyLeakList` | Verify AK leak via Security Center alerts |
| Security Center (SAS) | `yundun-aegis:DescribeAccessKeyLeakDetail` | Get leak detail (ban status, risk level) |
| ActionTrail | `actiontrail:LookupEvents` | Audit leaked AK operations across products |
| RAM | `ram:GetAccessKeyLastUsed` | Check when the leaked AK was last used |
| RAM | `ram:ListAccessKeys` | List AccessKeys for a RAM user (chain tracing) |
| RAM | `ram:GetPasswordPolicy` | Assess password policy strength |
| RAM | `ram:GetSecurityPreference` | Check MFA and security settings |
| IMS | `ims:GetAccountSummary` | Account-level summary (resource counts) |
| CloudSSO | `cloudsso:GetServiceStatus` | Check if CloudSSO is enabled |

## Important: RAM Action Prefix for Security Center

The Security Center (SAS) product uses the `yundun-aegis:` RAM action prefix, **NOT** `sas:`. Granting `sas:DescribeAccesskeyLeakList` will result in `Forbidden.NoPermission`. Always use:

```
yundun-aegis:DescribeAccesskeyLeakList
yundun-aegis:DescribeAccessKeyLeakDetail
```

## Example Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "yundun-aegis:DescribeAccesskeyLeakList",
        "yundun-aegis:DescribeAccessKeyLeakDetail",
        "actiontrail:LookupEvents",
        "ram:GetAccessKeyLastUsed",
        "ram:ListAccessKeys",
        "ram:GetPasswordPolicy",
        "ram:GetSecurityPreference",
        "ims:GetAccountSummary",
        "cloudsso:GetServiceStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

## Scope Notes

- All actions are **read-only** queries (Describe/Get/List). No mutating actions required.
- `Resource: "*"` is acceptable for read-only queries. To restrict further, scope to specific resources where the API supports it.
- ActionTrail `LookupEvents` returns events for the entire account — there is no resource-level restriction for this action.
