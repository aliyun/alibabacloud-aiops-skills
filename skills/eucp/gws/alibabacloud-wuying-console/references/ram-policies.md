# RAM and Least-Privilege Access

This skill uses the credential profile already configured for the official Aliyun CLI. It does not create credentials, attach RAM policies, or bypass the permissions of the current Alibaba Cloud account.

## Authorization rules

- Prefer a human OAuth profile for interactive local use.
- Reuse the user's existing account and profile only after the account context is clear.
- Grant only the OpenAPI Actions needed for the requested WUYING operation.
- Derive the RAM service name and Action from the official OpenAPI documentation for the exact product, API version, and command. Do not infer a permission string from a console label or CLI command name.
- Scope resources and conditions as narrowly as the product supports. If an Action supports only `"Resource": "*"`, restrict the policy with documented account, region, or tag conditions where possible.
- Separate read-only access from mutation and destructive access. Do not request a broad administrative policy merely because the generated command catalog contains every command exposed by an installed plugin.
- Credential and policy changes require explicit user authorization. Never print AccessKey secrets, OAuth tokens, or credential files.

## Concrete WUYING Action examples

WUYING product codes do not always map one-to-one to RAM prefixes. For example,
documented `ecd`, `eds-user`, and `wss` OpenAPIs can use the `ecd` RAM prefix.
Always read the authorization information for the exact OpenAPI version instead
of deriving an Action by transforming a CLI command name.

Representative read-only Actions include:

| Product/API family | RAM Action | Purpose |
|---|---|---|
| `ecd/2020-09-30` | `ecd:DescribeRegions` | List supported regions |
| `ecd/2020-09-30` | `ecd:DescribeDesktops` | Query cloud computers |
| `ecd/2020-09-30` | `ecd:DescribeBundles` | Query desktop templates |
| `ecd/2020-09-30` | `ecd:DescribeDesktopSessions` | Query desktop sessions |
| `eds-user/2021-03-08` | `ecd:DescribeUsersInGroup` | Query users in a user group |
| `wss/2021-12-21` | `ecd:DescribeCreditUsageInfo` | Query credit usage information |

Representative mutation and destructive Actions include:

| Product/API family | RAM Action | Risk |
|---|---|---|
| `ecd/2020-09-30` | `ecd:StartDesktops` | mutation |
| `ecd/2020-09-30` | `ecd:ModifyDesktopGroup` | mutation |
| `eds-user/2021-03-08` | `ecd:ModifyUser` | mutation |
| `eds-user/2021-03-08` | `ecd:ResetUserPassword` | mutation |
| `ecd/2020-09-30` | `ecd:DeletePolicyGroups` | destructive |
| `eds-user/2021-03-08` | `ecd:RemoveUsers` | destructive |

Example of a narrow read-only starting policy for common cloud-computer
discovery. Add only the Actions required by the selected command:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecd:DescribeRegions",
        "ecd:DescribeDesktops",
        "ecd:DescribeBundles",
        "ecd:DescribeDesktopSessions"
      ],
      "Resource": "*"
    }
  ]
}
```

Some WUYING API versions expose service-level rather than per-API authorization,
and their authorization tables can contain no individual Action entries. In
that case, use the documented product system policy or service-level permission
for that API family; do not invent `appstreaming:*`, `wyota:*`, or another
wildcard solely from the CLI product code.

## Permission failures

When an API returns an authorization error:

1. Preserve the error code and `RequestId`.
2. Identify the exact product, API version, and OpenAPI Action that was attempted.
3. Consult the official OpenAPI authorization information for that Action.
4. Ask the account administrator to grant only the missing permission.
5. Retry a read after authorization is updated. For mutations, re-resolve the target and obtain confirmation again before retrying.

The generated command catalog is a discovery index, not a recommended RAM policy. Never convert the entire catalog into one blanket authorization policy.
