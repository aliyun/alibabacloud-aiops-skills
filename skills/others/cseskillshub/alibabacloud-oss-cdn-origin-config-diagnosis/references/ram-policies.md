# Minimal Read-Only RAM Policy

This skill performs strictly read-only CDN back-to-origin configuration
diagnosis across CDN and OSS. It requires exactly five RAM actions. No
wildcards (`*`) are used in any action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in the entry script) |
| 2 | `cdn:DescribeUserDomains` | aliyun CLI: `aliyun cdn describe-user-domains` | List the caller's CDN domains (inventory / candidate suggestions when the target domain is not found) |
| 3 | `cdn:DescribeCdnDomainDetail` | aliyun CLI: `aliyun cdn describe-cdn-domain-detail --domain-name <d>` | Domain state, CNAME and origin sources (`scripts/origin_config_diagnosis.py`) |
| 4 | `cdn:DescribeCdnDomainConfigs` | aliyun CLI: `aliyun cdn describe-cdn-domain-configs --domain-name <d> --function-names set_req_host_header` | Read the configured back-to-origin Host header (`scripts/origin_config_diagnosis.py`) |
| 5 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Origin-bucket cross-check: ACL, owner, region, storage class (`scripts/_oss_client.py`) |

All five are read-only Get/Describe-class actions. They never modify any
resource, domain, origin, policy, or configuration.

## Read-Only Guarantee

- The scripts contain NO mutating CDN or OSS call: no domain change, no
  origin change, no bucket configuration change exists anywhere in this
  skill. The declared action set above is exactly equal to the action set
  actually invoked by the scripts.
- `cdn:Describe*` and `oss:GetBucketInfo` return configuration metadata
  only; object content is never read or written by this skill.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-cdn-origin-config-diagnosis/{session-id}`).

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyCdnDomainQuery",
      "Effect": "Allow",
      "Action": [
        "cdn:DescribeUserDomains",
        "cdn:DescribeCdnDomainDetail",
        "cdn:DescribeCdnDomainConfigs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyOssMetadataQuery",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the diagnosis must cover whichever domain
  and bucket the user asks about; read-only effect is guaranteed by the
  action list itself (Get/Describe-class only).
- The evaluation role used by this skill's gated cases was measured to carry
  both the CDN read and the OSS read chains (single-role closed loop).
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — CDN is a global service and the bucket region is what the diagnosis discovers |
| Resources | CDN domain configuration metadata of the caller's account; bucket-level metadata of the origin buckets named by the diagnosis |
| Data exposed | Domain state, origin list, back-to-origin Host, bucket ACL/owner/region — metadata only, never object content |
| Mutations | None possible; only Get/Describe-class actions are granted |

## How to grant

Option A — RAM user (same-account use):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. JSON script mode: paste the policy document above.
3. Grant the policy to the RAM user.
4. Configure the aliyun CLI with that credential (`aliyun configure`) and
   expose the same credential through the environment variables of the
   default credential chain for the oss2 SDK; the scripts never take AK/SK
   arguments.

Option B — RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: pick a RAM role trusted by the
   calling account.
2. Grant the policy above to the role.
3. Assume the role via STS and export the temporary credential through the
   `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` /
   `ALIBABA_CLOUD_SECURITY_TOKEN` environment variables; the CLI and the
   oss2 SDK both resolve it from the default credential chain.

Least-privilege checklist:

- Grant only the five actions above; do not grant any full-access or
  administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
