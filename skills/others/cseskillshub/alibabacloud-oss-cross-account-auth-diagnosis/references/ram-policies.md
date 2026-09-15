# Minimal Read-Only RAM Policy

This skill performs strictly read-only cross-account authorization
diagnosis. It requires exactly four CORE RAM actions, plus one OPTIONAL
action that only enhances the 403 diagnostic decode (the skill degrades
gracefully without it). No wildcards (`*`) are used in any action name.

## Required actions (core)

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `oss_cross_account_auth_diagnosis.py`) |
| 2 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fetch the bucket owner UID and location - the ownership comparison that decides same-account vs cross-account (`scripts/oss_cross_account_auth_diagnosis.py`) |
| 3 | `oss:GetBucketPolicy` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Bucket-Policy existence + content check (404 NoSuchBucketPolicy is the measured "not configured" fact, handled as a normal result) (`scripts/oss_cross_account_auth_diagnosis.py`) |
| 4 | `oss:ListBuckets` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fallback bucket-location lookup when GetBucketInfo is denied or the region is unknown (`scripts/oss_cross_account_auth_diagnosis.py`) |

All four core actions are read-only Get/List-class actions. They never
modify any resource, object, policy, role, trust policy, or replication
rule.

## Optional action (403 diagnostic decode enhancement)

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 5 (optional) | `ram:DecodeDiagnosticMessage` | aliyun CLI: `aliyun ram decode-diagnostic-message` (plugin mode, lowercase-hyphenated) | Decode the `EncodedDiagnosticMessage` carried by a 403 `AccessDeniedDetail` into the exact `AuthAction` / `AuthResource` / `AuthPrincipal` / `AuthConditions` / `MatchedPolicies` (the official 403 localization main path, `scripts/_oss_client.py decode_diagnostic_message`; Ram/2015-05-01, read/write = read) |

`ram:DecodeDiagnosticMessage` is a READ-only action (the API is classified
`read`; it decodes a diagnostic token and changes nothing). It is OPTIONAL:
when the credential lacks it, RAM answers `403 NoPermission` and the skill
DEGRADES to the official manual path (`[WARN]` +
`ram_403_diagnosis.manual_decode_guidance`: paste the message into the RAM
permission-diagnosis page, or hand it to an account administrator who holds
the permission). The plain `AccessDeniedDetail` fields (Step A) are
interpreted without it. MEASURED (2026-09-07, account 1552974654746705):
the evaluation role `skillsclienttest` does NOT hold this action, so the
decode runs the degradation path there.

## Read-Only Guarantee

- The scripts contain NO mutating call: no bucket-policy writing or
  modification, no RAM policy creation/attachment, no role trust-policy
  edit, no replication-rule change, no assume for mutation exists
  anywhere in this skill. Authorization fixes are emitted as JSON
  TEMPLATES in the report and are **applied by the user**, never by this
  skill. The declared
  action set above is exactly equal to the action set actually invoked by
  the scripts (the four core actions unconditionally; the optional
  `ram:DecodeDiagnosticMessage` only when a 403 carries an
  `EncodedDiagnosticMessage` -- and it is a read-class decode, never a
  write).
- `GetBucketInfo` / `GetBucketPolicy` / `ListBuckets` return metadata only;
  object content is never read or written by this skill.
- `DecodeDiagnosticMessage` only decodes an opaque diagnostic token into
  the deny attribution; it reads no resource and writes nothing.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-cross-account-auth-diagnosis/{session-id}`).

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
        "oss:GetBucketPolicy",
        "oss:ListBuckets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DecodeAccessDeniedDiagnostic",
      "Effect": "Allow",
      "Action": [
        "ram:DecodeDiagnosticMessage"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- The `DecodeAccessDeniedDiagnostic` statement is OPTIONAL: omit it and the
  skill still diagnoses the 403 from the plain `AccessDeniedDetail` fields
  and degrades the decode to the RAM permission-diagnosis page /
  administrator handoff. Include it only when the diagnosing credential
  should decode the `EncodedDiagnosticMessage` itself.

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the diagnosis must cover any bucket the
  user asks about; read-only effect is guaranteed by the action list itself
  (Get/List-class only). Optionally, the OSS statement can be narrowed to
  the ARN of a specific bucket (no wildcards) when the diagnosis scope is
  known in advance.
- No `Deny` statements are required; anything not listed above is denied by
  default.
- When the diagnosed bucket belongs to ANOTHER account, these grants only
  help on the owning-account side; a non-owner caller legitimately gets
  NoSuchBucket/AccessDenied and the report says so honestly.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions - the bucket's region is exactly what the diagnosis discovers, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level metadata of the buckets named by the user; `ListBuckets` enumerates bucket names/locations of the caller's own account only |
| Data exposed | Bucket owner UID, location, storage class, Bucket Policy document - metadata and policy text only, never object content |
| Mutations | None possible; only Get/List-class actions are granted |

## How to grant

Option A - RAM user (same-account use):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. JSON script mode: paste the policy document above.
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that credential (`aliyun configure`) and
   expose the same credential through the environment variables of the
   default credential chain for the oss2 SDK; the scripts never take AK/SK
   arguments.

Option B - RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: pick a RAM role trusted by the
   calling account.
2. Attach the policy above to the role.
3. Assume the role (`aliyun sts assume-role`) and export the temporary
   credential via the `ALIBABA_CLOUD_ACCESS_KEY_ID` /
   `ALIBABA_CLOUD_ACCESS_KEY_SECRET` / `ALIBABA_CLOUD_SECURITY_TOKEN`
   environment variables; the CLI and the oss2 SDK both resolve it from the
   default credential chain.

Least-privilege checklist:

- Grant only the four core actions above (plus, optionally,
  `ram:DecodeDiagnosticMessage` for the 403 decode); do not attach
  `AliyunOSSFullAccess` or any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
