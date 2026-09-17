# Minimal Read-Only RAM Policy

This skill performs strictly read-only cross-region replication configuration
checks. It requires exactly six RAM actions. No wildcards (`*`) are used in
any action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `crr_config_check.py`) |
| 2 | `oss:GetBucketReplication` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read the bucket's replication rule(s): role, scope, delete-sync, historical-data switch, transfer type, status (`scripts/crr_config_check.py`) |
| 3 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fetch the bucket location and storage class (cold-archive limit) (`scripts/crr_config_check.py`) |
| 4 | `oss:ListBuckets` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fallback bucket-location lookup when GetBucketInfo is denied or the region is unknown (`scripts/crr_config_check.py`) |
| 5 | `oss:GetBucketReplicationProgress` | Python oss2 SDK (OSS control-plane, not the POP gateway) | CONDITIONAL — only when a replication rule exists: read the historical-backlog percentage and the new-object watermark (`_oss_client.get_bucket_replication_progress`, post-replication verification) |
| 6 | `oss:ListObjects` | Python oss2 SDK (`ListObjectsV2`, OSS data-plane listing, not the POP gateway) | CONDITIONAL — only under the opt-in `--verify-target` flag: bounded read-only object count + ETag/Size sample on the source (and the target when listable) for post-replication data verification (`_oss_client.count_bucket_objects`) |

All six are read-only Get/List-class actions. They never modify any
resource, object, policy, replication rule, or configuration; `ListObjects`
only enumerates object metadata (key/ETag/size) and never reads object
content. Actions 5 and 6 are conditional (a rule must exist / `--verify-target`
must be passed), but they are declared because the scripts can invoke them.
The declared action set is exactly equal to the action set actually invoked
by the scripts.

## Read-Only Guarantee

- The scripts contain NO mutating OSS call: no replication-rule creation or
  removal, object write, ACL change, or policy mutation exists anywhere in
  this skill.
- `GetBucketReplication` / `GetBucketInfo` / `ListBuckets` /
  `GetBucketReplicationProgress` / `ListObjects` return metadata
  only; object content is never read or written by this skill.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-crr-config-check/{session-id}`).

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
      "Sid": "ReadOnlyOssReplicationMetadata",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketReplication",
        "oss:GetBucketInfo",
        "oss:ListBuckets",
        "oss:GetBucketReplicationProgress",
        "oss:ListObjects"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the replication/bucket metadata queries must
  cover any bucket the user asks about; read-only effect is guaranteed by the
  action list itself (Get/List-class only). Optionally, the OSS statement can
  be narrowed to the ARN of a specific bucket when the check scope is known.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — the bucket's region is exactly what the check discovers, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level replication/metadata of the buckets named by the user; `ListBuckets` enumerates bucket names/locations of the caller's own account only |
| Data exposed | Replication rule fields, bucket location, storage class, ACL label, creation date — metadata only, never object content |
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
   environment variables; the CLI and the oss2 SDK both resolve it from the
   default credential chain.

Least-privilege checklist:

- Grant only the six actions above; do not attach `AliyunOSSFullAccess` or
  any administrator policy.
- Do not grant any replication write/mutating action to this skill's
  credential — mutation is the user's own operation.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
