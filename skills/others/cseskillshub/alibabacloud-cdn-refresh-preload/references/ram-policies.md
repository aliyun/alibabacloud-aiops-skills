# RAM Policies Required

This skill is **strictly read-only**. No write, modify, or delete permissions are needed.

## Required Permissions

Actions below are listed in aliyun CLI plugin mode (lowercase-hyphenated) per platform static-check requirements; they correspond to the official STS/CDN RAM actions for role assumption and refresh-task queries.

| Action | Service | Purpose |
|--------|---------|---------|
| `sts assume-role` | STS | Obtain temporary STS credentials for target account |
| `cdn describe-refresh-tasks` | CDN | Query refresh/preload task records |

## Read-Only Guarantee

All API calls are `Describe*` / `Get*` queries only. The skill never submits refresh/preload operations (`RefreshObjectCaches` / `PushObjectCache`), modifies CDN configuration, or alters any account resource.

## Authorization Setup

The target account must create a RAM role trusted by the investigation account and attach a policy with the above permissions. Example policy (Action values use the official RAM action names — RAM only accepts these PascalCase forms; the aliyun CLI plugin-mode equivalents are `aliyun cdn describe-refresh-tasks` and `aliyun sts assume-role`):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cdn:DescribeRefreshTasks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "acs:ram::<TARGET_ACCOUNT_UID>:role/cseesadiagnosticrole"
    }
  ]
}
```

Notes on Resource scope (least privilege):

- `sts:AssumeRole` MUST point to the specific diagnosis role ARN, not a wildcard. Replace `<TARGET_ACCOUNT_UID>` with the actual account UID, and replace `cseesadiagnosticrole` with your actual diagnosis role name if different. Never grant `acs:ram::*:role/*`, which would allow assuming any role in any account.
- The read-only query action `cdn:DescribeRefreshTasks` keeps `Resource: "*"` — this is the common practice for read-only `Describe*` queries, as CDN query APIs do not support resource-level authorization and no write access is granted.
