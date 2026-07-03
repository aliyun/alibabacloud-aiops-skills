# RAM Policies

This skill requires **read-only** access to four Alibaba Cloud security products.
The collection scripts only invoke `Describe*` APIs and never modify any configuration.

## Required Policies

| Product | RAM Policy | Scope |
|---------|-----------|-------|
| WAF 3.0 | `AliyunYundunWAFReadOnlyAccess` | Instance / Defense resources / Rules |
| SAS (Security Center) | `AliyunYundunSASReadOnlyAccess` | Assets / Vulnerabilities / Baselines / Clusters |
| Cloud Firewall (CFW) | `AliyunYundunCloudFirewallReadOnlyAccess` | Assets / Policies / VPC firewalls / Threat intel |
| DDoS Protection (DDoSCoo) | `AliyunYundunDDoSCooReadOnlyAccess` | Instances / Domains / Rules / Blackhole status |

## Credential Chain

Scripts rely on the Alibaba Cloud CLI default credential chain:

1. Environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`)
2. CLI profile (`~/.aliyun/config.json`)
3. ECS instance RAM role (when running on ECS)
4. Credentials file (`~/.alibabacloud/credentials`)

**No credential is read, printed, or transmitted by any script in this repository.**

Verify credentials are configured (without exposing secrets):

```bash
aliyun configure list
```

## Recommended Setup

Create a dedicated RAM sub-account with only the four policies above.
Revoke the account immediately after collection is complete.
