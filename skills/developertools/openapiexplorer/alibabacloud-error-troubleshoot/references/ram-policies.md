# RAM Policies — OpenAPI Troubleshoot

## Required Permissions

The following RAM permissions are required for the troubleshoot APIs used by this skill:

| API | CLI Command | API Action | Description |
|-----|-------------|------------|-------------|
| GetOwnRequestLog | `get-own-request-log` | `openapiexplorer:GetOwnRequestLog` | Query request logs for the current account's API calls |
| GetRequestLog | `get-request-log` | `openapiexplorer:GetRequestLog` | Query request logs under the same parent account — main account and sub-accounts |
| GetErrorCodeSolutions | `get-error-code-solutions` | `openapiexplorer:GetErrorCodeSolutions` | Fetch diagnostic solutions for error codes |

Resource scope for OpenAPI Explorer troubleshoot APIs is typically account-level (`*`).

## Minimum RAM Policy (Own Account Troubleshooting)

Use when the user only needs to troubleshoot their own API calls and look up error solutions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "openapiexplorer:GetOwnRequestLog",
        "openapiexplorer:GetErrorCodeSolutions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Complete RAM Policy (Same Parent Account Organization)

Use when the user also needs to query Request IDs from the main account or sibling sub-accounts under the same parent account:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "openapiexplorer:GetOwnRequestLog",
        "openapiexplorer:GetRequestLog",
        "openapiexplorer:GetErrorCodeSolutions"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

| Error | Likely cause | Action |
|-------|--------------|--------|
| `Unauthorized` / `AccessDenied` on `get-own-request-log` | Missing `GetOwnRequestLog` permission | Attach minimum policy above |
| `Unauthorized` / `AccessDenied` on `get-request-log` | Missing `GetRequestLog` permission | Attach complete policy above |
| `NotFound.RequestLog` (404) on `get-request-log` | Request ID from an unrelated account, log expired, or invalid ID | Not fixable by RAM — scope is limited to the same parent account |
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | Credential misconfiguration | Fix CLI credentials; see [cli-installation-guide.md](cli-installation-guide.md) |

When surfacing permission errors to the user, provide the relevant policy JSON above and explain which action is missing.
