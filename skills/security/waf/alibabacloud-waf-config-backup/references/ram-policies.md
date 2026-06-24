# RAM Policies for WAF Config Backup

The RAM user associated with the AccessKey must have the following read-only permissions:

## Required Permissions

### Core (always required)

| Action | Description |
|--------|-------------|
| `yundun-waf:DescribeInstance` | Query WAF instance info |
| `yundun-waf:DescribeDomains` | Query CNAME domain list |
| `yundun-waf:DescribeDomainDetail` | Query CNAME domain detailed config |
| `yundun-waf:DescribeCloudResources` | Query cloud-product onboarding resources |
| `yundun-waf:DescribeHybridCloudResources` | Query hybrid-cloud onboarding resources |
| `yundun-waf:DescribeDefenseTemplates` | Query defense template list |
| `yundun-waf:DescribeDefenseRules` | Query defense rule list |
| `yundun-waf:DescribeDefenseResources` | Query protected-object inventory and template-to-resource bindings |
| `yundun-waf:DescribeDefenseResourceGroups` | Query protected-object groups |

### Account topology (for multi-account scenario detection and owner attribution)

| Action | Description |
|--------|-------------|
| `sts:GetCallerIdentity` | Resolve the caller's AliUid (used as filename prefix and Summary attribution) |
| `yundun-waf:DescribeAccountDelegatedStatus` | Detect whether the executing account is the WAF delegated administrator |
| `yundun-waf:DescribeMemberAccounts` | Enumerate member accounts under the delegated administrator |
| `yundun-waf:DescribeDefenseResourceOwnerUid` | Resolve `ResourceName → OwnerUid` for per-row account attribution under the delegated-administrator scenario |

> `sts:GetCallerIdentity` is callable by any RAM identity by default in most accounts; it is listed explicitly here for completeness.
>
> The three `yundun-waf` multi-account APIs are only invoked when needed: `DescribeAccountDelegatedStatus` runs once on the first discovered instance; the remaining two are skipped entirely under the single-UID scenario. Permission failures on these endpoints degrade gracefully (the script falls back to caller UID), but listing them avoids surprise warnings in audit logs.

## Recommended System Policy

Attach the system policy **`AliyunYundunWAFReadOnlyAccess`**, which covers all `yundun-waf:*` actions above (verify in the RAM console for accounts with strict policy version pinning). `sts:GetCallerIdentity` is implicitly available and does not require additional attachment.

## Custom Policy (Minimum Required)

If a custom policy is preferred, use the following:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeDomains",
        "yundun-waf:DescribeDomainDetail",
        "yundun-waf:DescribeCloudResources",
        "yundun-waf:DescribeHybridCloudResources",
        "yundun-waf:DescribeDefenseTemplates",
        "yundun-waf:DescribeDefenseRules",
        "yundun-waf:DescribeDefenseResources",
        "yundun-waf:DescribeDefenseResourceGroups",
        "yundun-waf:DescribeAccountDelegatedStatus",
        "yundun-waf:DescribeMemberAccounts",
        "yundun-waf:DescribeDefenseResourceOwnerUid",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- This skill is **read-only** — no write/modify/delete permissions are required.
- The same permissions apply to both Chinese mainland (`cn-hangzhou`) and International (`ap-southeast-1`) regions.
- If using separate profiles for mainland and international accounts, each profile's RAM user needs these permissions independently.
- Under the delegated-administrator scenario, `DescribeMemberAccounts` and `DescribeDefenseResourceOwnerUid` are invoked on the **administrator account itself**; member accounts do not need to grant any additional permission to the administrator beyond the standard delegation enrollment.
