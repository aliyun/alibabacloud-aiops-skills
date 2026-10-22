# RAM Policies

## Required Permissions

Select permissions for the requested items before querying. Missing BSS permission
blocks bill details only; missing WAF permission blocks WAF statistics only.
Never grant policies automatically or require all three services for a score query.

| Requested scope | Required permission | Managed-policy option |
|---|---|---|
| SAS score, assets, governance, service dates, billing configuration | Relevant `yundun-sas` read actions below | `AliyunYundunSASReadOnlyAccess` |
| WAF blocked-request statistics | `yundun-waf:DescribeInstance`, `yundun-waf:DescribeFlowChart` | `AliyunWAFReadOnlyAccess` |
| Monthly bill details (including full overview) | `bss:QueryBill` | `AliyunBSSReadOnlyAccess` |

Run `python3 scripts/query_permissions.py score hosts` from the skill directory to
list the exact actions for those items; use `--help` for supported items and `all`
only for an explicitly requested full overview. This is an offline planning aid;
it does not inspect or change RAM authorization. Actual API access determines
whether the selected principal has permission.

On denial, report the item, endpoint region, action, error code and RequestId when
provided; do not infer a missing policy from an unrelated timeout. Continue
independent requested items, mark the failed item unavailable, and label any
summary partial. Do not treat denied billing as zero spend.

The policies below cover the full workflow; select the relevant actions for a
custom policy, or ask the account administrator for the corresponding read-only
managed policy.

### SAS (Security Center)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-sas:DescribeVulFixStatistics",
        "yundun-sas:GetDefenceCount",
        "yundun-sas:GetCheckRiskStatistics",
        "yundun-sas:DescribeVersionConfig",
        "yundun-sas:ListUninstallAegisMachines",
        "yundun-sas:DescribeSecureSuggestion",
        "yundun-sas:DescribeCloudCenterInstances",
        "yundun-sas:DescribeFieldStatistics",
        "yundun-sas:DescribeContainerFieldStatistics",
        "yundun-sas:GetCloudAssetSummary",
        "yundun-sas:DescribeChartData"
      ],
      "Resource": "*"
    }
  ]
}
```

### WAF (Web Application Firewall)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeFlowChart"
      ],
      "Resource": "*"
    }
  ]
}
```

### BssOpenApi (Billing)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:QueryBill"
      ],
      "Resource": "*"
    }
  ]
}
```

## Recommended System Policy

For selected scopes, the administrator can use these managed policies:

| Policy Name | Scope |
|-------------|-------|
| `AliyunYundunSASReadOnlyAccess` | SAS read-only |
| `AliyunWAFReadOnlyAccess` | WAF read-only |
| `AliyunBSSReadOnlyAccess` | Billing read-only |
