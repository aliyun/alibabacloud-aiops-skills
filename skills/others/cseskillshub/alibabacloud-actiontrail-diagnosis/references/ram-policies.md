# RAM Permissions (Minimum Read-Only Policy)

This skill requires **read-only** access to exactly two APIs. No write permissions are needed — the skill never modifies, disables, or deletes any resource.

## Required Actions

| Product | RAM Action | Purpose |
|---------|-----------|---------|
| ActionTrail | `actiontrail:LookupEvents` | Retrieve historical audit events for diagnosis |
| STS | `sts:GetCallerIdentity` | Auto-derive account UID when not provided |

No other actions are required. The skill uses **no wildcards in Action names** and grants no write, create, update, or delete permissions.

## Example Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "actiontrail:LookupEvents",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Scope Notes

- Both actions are **read-only**. `LookupEvents` only retrieves audit events; `GetCallerIdentity` only returns the caller's own identity. No mutating actions are required.
- `Resource: "*"` is used because **neither API supports resource-level authorization**:
  - `actiontrail:LookupEvents` returns events for the entire account; there is no way to scope it to a specific resource ARN.
  - `sts:GetCallerIdentity` operates on the caller identity itself and accepts no resource restriction.
- No wildcard actions are used; only the two exact actions above are granted.
- ActionTrail `LookupEvents` returns events for the entire account (all regions) — be aware that query results are account-wide, filtered only by the `LookupAttribute`, `StartTime` and `EndTime` request parameters.
