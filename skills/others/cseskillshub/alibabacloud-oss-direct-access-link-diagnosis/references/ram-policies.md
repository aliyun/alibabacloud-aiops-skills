# Minimal Read-Only RAM Policy

This skill performs strictly read-only direct-access-link diagnosis. It
requires exactly seven RAM actions. No wildcards (`*`) are used in any
action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `oss_direct_access_diagnosis.py`) |
| 2 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Confirm the bucket exists; fetch location, endpoints, ACL (`scripts/oss_direct_access_diagnosis.py`) |
| 3 | `oss:GetBucketReferer` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read the hotlink-protection referer whitelist (`scripts/oss_direct_access_diagnosis.py`) |
| 4 | `oss:GetBucketWebsite` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read static website hosting state as context / boundary marker (`scripts/oss_direct_access_diagnosis.py`) |
| 5 | `oss:ListBucketCname` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read the bound custom-domain (cname) list (`scripts/oss_direct_access_diagnosis.py`) |
| 6 | `oss:ListBuckets` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fallback bucket-location lookup when GetBucketInfo is denied or the region is unknown (`scripts/oss_direct_access_diagnosis.py`) |
| 7 | `oss:GetObjectAcl` | Python oss2 SDK (OSS control-plane, not the POP gateway) | EC 0003-00000005 cause-1 verification: read the probed object's own ACL when an anonymous 403 hits a non-private bucket (`scripts/oss_direct_access_diagnosis.py`, conditional on `--object` probe evidence) |

All seven are read-only Get/List-class actions. They never modify any
resource, object, policy, or configuration. In particular the mutation
operations (applying referer rules, website hosting configuration, or
binding/unbinding custom domains) are NOT granted and never called: this
skill only outputs configuration templates as text; applying them is the
user's own manual operation.

The anonymous default-domain probe (`--object`) is an unauthenticated
data-plane HEAD request that carries no credentials and requires no RAM
action.

## Read-Only Guarantee

- The scripts contain NO mutating OSS call: no object write, no referer
  configuration change, no website configuration change, no domain
  binding call, no ACL or policy mutation exists anywhere in this skill.
  The declared action set above is exactly equal to the action set
  actually invoked by the scripts.
- `oss:GetBucketInfo`, `oss:GetBucketReferer`, `oss:GetBucketWebsite`,
  `oss:ListBucketCname`, `oss:ListBuckets` and `oss:GetObjectAcl`
  return metadata/configuration only (GetObjectAcl returns the probed
  object's ACL label, not its content); object content is never read or
  written by this skill.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-direct-access-link-diagnosis/{session-id}`).

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
      "Sid": "ReadOnlyOssMetadataQuery",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo",
        "oss:GetBucketReferer",
        "oss:GetBucketWebsite",
        "oss:ListBucketCname",
        "oss:ListBuckets",
        "oss:GetObjectAcl"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the Get/List queries must cover any
  bucket the user asks about; read-only effect is guaranteed by the action
  list itself (Get/List-class only). Optionally, the OSS statement can be
  narrowed to the ARN of a specific bucket (no wildcards) when the
  diagnosis scope is known in advance.
- No `Deny` statements are required; anything not listed above is denied
  by default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — the bucket's region is exactly what the diagnosis may discover, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level metadata/configuration of the buckets named by the user; `ListBuckets` enumerates bucket names/locations of the caller's own account only |
| Data exposed | Bucket location, endpoints, ACL label, referer whitelist AND blacklist, website hosting state, bound cname list, probed object's ACL label — metadata/configuration only, never object content |
| Mutations | None possible; only Get/List-class actions are granted |

## How to grant

Option A — RAM user (same-account use):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. JSON script mode: paste the policy document above.
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that credential (`aliyun configure`) and
   expose the same credential through the environment variables of the
   default credential chain for the oss2 SDK; the scripts never take AK/SK
   arguments.

Option B — RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: pick a RAM role trusted by the
   calling account.
2. Attach the policy above to the role.
3. Assume the role (`STS AssumeRole`) and export the temporary
   credential via the `ALIBABA_CLOUD_ACCESS_KEY_ID` /
   `ALIBABA_CLOUD_ACCESS_KEY_SECRET` / `ALIBABA_CLOUD_SECURITY_TOKEN`
   environment variables; the CLI and the oss2 SDK both resolve it from
   the default credential chain.

Least-privilege checklist:

- Grant only the seven actions above; do not attach `AliyunOSSFullAccess`
  or any administrator policy.
- Never grant any referer/website/domain mutation permission to the
  diagnosis credential — configuration changes stay manual user
  operations.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them
  in the skill directory.
