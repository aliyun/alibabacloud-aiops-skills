# RAM Policies for WAF CNAME Config Export

## Required Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `yundun-waf:DescribeInstance` | `acs:waf:*:*:instance/*` | Query WAF instance info |
| `yundun-waf:DescribeDomains` | `acs:waf:*:*:instance/*` | Query domain list |
| `yundun-waf:DescribeDomainDetail` | `acs:waf:*:*:instance/*` | Query domain detailed config |

## Recommended System Policy

Attach system policy: `AliyunYundunWAFReadOnlyAccess`

## Custom Policy (If Needed)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeDomains",
        "yundun-waf:DescribeDomainDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

> **[MUST]** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read this file to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
> 4. Re-run `aliyun configure list` to verify credentials
> 5. Retry the export workflow
