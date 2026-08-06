# RAM Permissions Required

All SLS (Log Service) APIs and corresponding RAM permissions used by this skill.

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| SLS | `sls:ListLogStores` | `acs:log:*:*:project/<project>` | List LogStores |
| SLS | `sls:CreateOSSExport` | `acs:log:*:*:project/<project>` | Create OSS export task |
| SLS | `sls:ListOSSExports` | `acs:log:*:*:project/<project>` | List export tasks |
| SLS | `sls:GetOSSExport` | `acs:log:*:*:project/<project>` | Get export task details |
| SLS | `sls:UpdateOSSExport` | `acs:log:*:*:project/<project>` | Update export task |
| SLS | `sls:StartOSSExport` | `acs:log:*:*:project/<project>` | Start export task |
| SLS | `sls:StopOSSExport` | `acs:log:*:*:project/<project>` | Stop export task |
| SLS | `sls:DeleteOSSExport` | `acs:log:*:*:project/<project>` | Delete export task |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sls:ListLogStores",
        "sls:CreateOSSExport",
        "sls:ListOSSExports",
        "sls:GetOSSExport",
        "sls:UpdateOSSExport",
        "sls:StartOSSExport",
        "sls:StopOSSExport",
        "sls:DeleteOSSExport"
      ],
      "Resource": "acs:log:*:*:project/*"
    }
  ]
}
```

## Minimum Privilege Policy

If only read/view permissions are needed (no create/modify/delete), use the following minimal policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sls:ListLogStores",
        "sls:ListOSSExports",
        "sls:GetOSSExport"
      ],
      "Resource": "acs:log:*:*:project/*"
    }
  ]
}
```

## RAM Role Requirements

SLS OSS export tasks require two RAM roles (can be the same one):

1. **Read LogStore RAM Role**: Grants the export task permission to read LogStore data
2. **Write OSS RAM Role**: Grants the export task permission to write data to the OSS Bucket

By default, `aliyunlogdefaultrole` (Alibaba Cloud system role) is used. Its ARN format is:
`acs:ram::<account-id>:role/aliyunlogdefaultrole`

When using a custom role, you must separately grant:
- The custom role permission to read LogStore data
- The custom role permission to write to the OSS Bucket

## Error Handling and Human-In-The-Loop (HITL)

When any command or API call fails, identify the error type and follow the corresponding handling process. For ALL error types, you MUST immediately stop further execution, output the exact error message received, and respond with the standardized error message format. Do NOT attempt to retry, rephrase the command, or proceed to the next step. Report the error to the user with remediation guidance — the user will decide next steps.

### Error Type Identification

| Error Type | Error Codes / Keywords | Handling Process |
|------------|----------------------|------------------|
| **Permission** | `401`, `403`, `Forbidden`, `AccessDenied`, `Forbidden.RAM`, `Unauthorized`, `does not belong` | 1. Refer to the permission list above\n2. Use `ram-permission-diagnose` skill to guide the user\n3. Output: "Operation failed — insufficient RAM permissions. Please grant the required permissions and retry."\n4. **Report the error to the user with remediation guidance** |
| **Parameter** | `400`, `InvalidParameter`, `MissingParameter`, `invalid` | 1. List the specific invalid/missing parameters\n2. Output: "Operation failed — parameter error: [details]. Please verify the parameters and retry."\n3. **Report the error to the user with remediation guidance** |
| **Throttling** | `503`, `Throttling`, `flow control`, `rate limit` | 1. Output: "Operation failed — request throttled. Please wait a moment and retry later."\n2. **Report the error to the user with remediation guidance** — do NOT auto-retry |
| **System** | `500`, `InternalError`, `ServiceUnavailable` | 1. Output: "Operation failed — server error. Please retry later or contact Alibaba Cloud support."\n2. **Report the error to the user with remediation guidance** |

### Standardized Error Message Format

```
Operation failed — requires human intervention: [error reason].
Please verify permissions/parameters and retry.
```

Your error report MUST contain the exact phrase `Operation failed — requires human intervention:` — do NOT substitute alternative phrasing such as "I cannot proceed", "Please check", or "Error occurred".

**[MUST] Error Transparency:** When a command or API call fails, capture and print the complete original error — including the HTTP status code, error code (e.g., `Forbidden.RAM`, `InvalidParameter`, `Throttling.User`), and the raw error message from stderr/stdout — BEFORE giving remediation guidance. Example: `Error: HTTP 403 | Code: Forbidden.RAM | Message: User is not authorized to perform sls:CreateOSSExport`. Never swallow, paraphrase-only, or truncate the original error text.

**[CRITICAL] Do NOT refuse to help:** When an error occurs, NEVER use refusal phrases such as "无法帮您", "我无法完成", "无法继续", "帮不了", "I cannot help", or "I am unable to help". Instead, explain the specific error, its cause, and the exact steps the user should take to resolve it, then hand the decision back to the user.

**[CRITICAL] No Auto-Retry:** If a command fails with any error code listed in the table above, you MUST immediately STOP execution. Do NOT retry the same command, do NOT modify parameters and retry, do NOT read reference files to "fix" the error and re-execute, and do NOT proceed to the next workflow step. Output the exact error message and the standardized HITL response. Re-executing a failed command without explicit user approval is a violation.
