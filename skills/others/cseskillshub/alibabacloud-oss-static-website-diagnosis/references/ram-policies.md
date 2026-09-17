# Minimal Read-Only RAM Policy

This skill performs strictly read-only static website hosting diagnosis. It
requires exactly four RAM actions. No wildcards (`*`) are used in any
action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `static_website_diagnosis.py`) |
| 2 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fetch the bucket location, ACL, and extranet endpoint (`scripts/static_website_diagnosis.py`) |
| 3 | `oss:GetBucketWebsite` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read the hosting configuration: IndexDocument / ErrorDocument / routing rules (`scripts/static_website_diagnosis.py`) |
| 4 | `oss:ListBucketCname` | Python oss2 SDK (OSS control-plane, not the POP gateway) | List custom domains bound to the bucket (`scripts/static_website_diagnosis.py`) |

All four are read-only Get/List-class actions. They never modify any
resource, object, policy, or configuration. The anonymous default-domain
probe uses NO credential at all, so it requires no RAM action.

## Read-Only Guarantee

- The scripts contain NO mutating OSS call: no hosting-configuration
  change, no ACL or policy mutation, no domain binding, no object write
  exists anywhere in this skill. The declared action set above
  is exactly equal to the action set actually invoked by the scripts.
- `GetBucketWebsite` / `GetBucketInfo` / `ListBucketCname` return metadata
  only; object content is never read or written by this skill (the anonymous
  probe reads only the HTTP status/headers of the bucket root).
- Any authenticated request the scripts issue carries a traceable
  User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-static-website-diagnosis/{session-id}`).

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
      "Sid": "ReadOnlyOssWebsiteMetadataQuery",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo",
        "oss:GetBucketWebsite",
        "oss:ListBucketCname"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are prohibited for this skill.
- `Resource: "*"` is used because the three OSS queries must cover any
  bucket the user asks about; read-only effect is guaranteed by the action
  list itself (Get/List-class only). Optionally, the OSS statement can be
  narrowed to the ARN of a specific bucket (no wildcards) when the
  diagnosis scope is known in advance.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — the bucket's region is exactly what the diagnosis discovers, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level metadata of the buckets named by the user |
| Data exposed | Hosting rules (index/error document names, routing-rule prefixes), bucket location, ACL label, bound custom-domain names, anonymous probe status — metadata only, never object content |
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
   credential via the standard `ALIBABA_CLOUD_*` access key and security
   token environment variables; the CLI and the oss2 SDK both resolve it
   from the default credential chain.

Least-privilege checklist:

- Grant only the four actions above; do not attach `AliyunOSSFullAccess` or
  any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
