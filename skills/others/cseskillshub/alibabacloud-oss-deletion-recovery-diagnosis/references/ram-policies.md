# Minimal Read-Only RAM Policy

This skill performs strictly read-only deletion-recovery diagnosis. It
requires exactly five RAM actions. No wildcards (`*`) are used in any
action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `oss_deletion_recovery_diagnosis.py`) |
| 2 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fetch the bucket location and storage class (`scripts/oss_deletion_recovery_diagnosis.py`) |
| 3 | `oss:GetBucketVersioning` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Read the versioning status that drives the recoverability decision tree (`scripts/oss_deletion_recovery_diagnosis.py`) |
| 4 | `oss:ListMultipartUploads` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Count leftover unfinished multipart fragments for residue attribution (`scripts/oss_deletion_recovery_diagnosis.py`, residue/all scopes) |
| 5 | `oss:ListBuckets` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fallback bucket-location lookup when GetBucketInfo is denied or the region is unknown (`scripts/oss_deletion_recovery_diagnosis.py`) |

All five are read-only Get/List-class actions. They never modify any
resource, object, version, policy, or configuration.

## Read-Only Guarantee

- The scripts contain NO mutating OSS call: no version restore, no
  delete-marker removal, no multipart abort, no object/bucket deletion, no
  versioning or lifecycle change exists anywhere in this skill. Recovery
  and cleanup are described as manual guidance in words only and are
  **executed by the user**, never by this skill. The declared action set
  above is exactly equal to the action set actually invoked by the scripts.
- `GetBucketInfo` / `GetBucketVersioning` / `ListMultipartUploads` /
  `ListBuckets` return metadata only; object content is never read or
  written by this skill.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-deletion-recovery-diagnosis/{session-id}`).

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
        "oss:GetBucketVersioning",
        "oss:ListMultipartUploads",
        "oss:ListBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the diagnosis must cover any bucket the
  user asks about; read-only effect is guaranteed by the action list itself
  (Get/List-class only). Optionally, the OSS statement can be narrowed to
  the ARN of a specific bucket (no wildcards) when the diagnosis scope is
  known in advance.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — the bucket's region is exactly what the diagnosis discovers, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level metadata of the buckets named by the user; `ListBuckets` enumerates bucket names/locations of the caller's own account only |
| Data exposed | Bucket location, storage class, versioning status, unfinished multipart upload keys — metadata only, never object content |
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

- Grant only the five actions above; do not attach `AliyunOSSFullAccess` or
  any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
