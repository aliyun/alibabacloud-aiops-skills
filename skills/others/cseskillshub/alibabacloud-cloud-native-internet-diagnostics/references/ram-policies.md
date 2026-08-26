# RAM Policies (Minimum Read-Only)

Minimum privilege declaration: this skill is **read-only**. The policy below lists every action the scripts actually invoke, one by one. No wildcards, no write actions.

## Required Actions (per action)

| Service | Action | Used by | Purpose |
|---------|--------|---------|---------|
| sts | `sts:GetCallerIdentity` | sts_token.py | Caller identity verification and UID derivation |
| mse | `mse:GetGateway` | cloud_native_internet_diag.py | Resolve MSE gateway VPC/vSwitch |
| apig | `apig:GetGateway` | cloud_native_internet_diag.py | Resolve API/AI gateway VPC/vSwitch |
| sae | `sae:DescribeApplicationConfig` | cloud_native_internet_diag.py | Resolve SAE application VPC/vSwitch |
| fc | `fc:GetFunction` | cloud_native_internet_diag.py | Resolve FC function vpcConfig/internetAccess |
| vpc | `vpc:DescribeVSwitchAttributes` | cloud_native_internet_diag.py | Resolve vSwitch VPC binding |
| vpc | `vpc:DescribeNatGateways` | cloud_native_internet_diag.py | Find NAT gateways in the VPC |
| vpc | `vpc:DescribeSnatTableEntries` | cloud_native_internet_diag.py | Verify SNAT entries covering the vSwitch |

## Minimum Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "mse:GetGateway"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apig:GetGateway"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sae:DescribeApplicationConfig"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "fc:GetFunction"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVSwitchAttributes",
        "vpc:DescribeNatGateways",
        "vpc:DescribeSnatTableEntries"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Read-only actions do not support resource-level restriction on these products, so `Resource: "*"` is scoped by the action list only — no action wildcards are used.
- If a query is rejected with HTTP `403` and an authorization error code (for example `NoPermission`), attach the missing action above; the script records such errors as `[WARN]` degradation traces and points to this file.
- This skill contains **no write or delete operations**; any non-read-only API call observed in traces should be reported as an anomaly.

## Credential Handling Rules

- Credentials come only from the aliyun CLI default credential chain (environment / ~/.aliyun/config.json / platform-injected session). Scripts never accept AK/SK/token parameters.
- AK/SK must never appear in plaintext in scripts, logs, or tickets.
- The identity cache `.sts_cache.json` stores only public identity facts (AccountId / Arn / IdentityType) and is written with permission 0600; it never stores credentials.
