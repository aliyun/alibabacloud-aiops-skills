# Minimal Read-Only RAM Policy

This skill performs strictly read-only traffic-abuse forensics. It
requires exactly nine RAM actions. No wildcards (`*`) are used in any
action name.

## Required actions

| # | RAM Action | Invocation channel | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | aliyun CLI: `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | Verify the caller identity and derive the account UID (`scripts/sts_token.py`, unconditional in `oss_traffic_forensics.py`) |
| 2 | `oss:GetBucketInfo` | Python oss2 SDK (OSS control-plane, not the POP gateway) | Fetch the bucket location, region, storage class, ACL (`scripts/oss_traffic_forensics.py`) |
| 3 | `oss:GetBucketPolicy` | Python oss2 SDK (OSS control-plane) | Detect anonymous (Principal `*`) Allow statements in the bucket policy |
| 4 | `oss:GetBucketPublicAccessBlock` | Python oss2 SDK (OSS control-plane) | Read the bucket-level Block Public Access state |
| 5 | `oss:GetBucketReferer` | Python oss2 SDK (OSS control-plane) | Read the anti-hotlink (Referer) whitelist configuration |
| 6 | `oss:GetBucketRequestPayment` | Python oss2 SDK (OSS control-plane) | Read the Requester Pays payer (exposure neutralizer: a public bucket with RequesterPays is not anonymously readable) |
| 7 | `oss:ListBuckets` | Python oss2 SDK (OSS control-plane) | Fallback bucket-location lookup when GetBucketInfo is denied or the region is unknown |
| 8 | `log:GetHistograms` | aliyun CLI (plugin mode): `aliyun sls get-histograms` (product name `sls`; RAM action prefix is `log:` — they differ by design, mirroring the built-in `AliyunLogReadOnlyAccess` policy) | Volume pre-count over the customer's own OSS real-time-log project before running the query sequence (`scripts/_sls_query.py`) |
| 9 | `log:GetLogs` | aliyun CLI (plugin mode): `aliyun sls get-logs` (product name `sls`; RAM action prefix `log:`) | Execute the 13-statement read-only traffic-source query sequence against `oss-log-<owner-uid>-<regionId>` / `oss-log-store` (`scripts/_sls_query.py`). Forward-compatibility: official metadata marks GetLogs as NOT deprecated while its description recommends GetLogsV2 — if GetLogs is ever removed, switch to GetLogsV2 (same semantics). |

All nine are read-only Get/List/Query-class actions. They never modify any
resource, object, policy, logstore, or configuration.

## Read-Only Guarantee

- The scripts contain NO mutating OSS or SLS call: no object write, no
  bucket or logstore configuration change, no ACL, policy, or index
  mutation exists anywhere in this skill. The declared action set above is
  exactly equal to the action set actually invoked by the scripts.
- The OSS actions return configuration metadata only; the SLS actions
  (`log:GetHistograms` / `log:GetLogs`) query log rows the service already
  ingested and never alter indexing, retention, or shipping.
- The skill does NOT call ActionTrail APIs: ActionTrail data events are
  referenced as manual guidance only. When the caller lacks SLS read
  permission or the bucket's real-time log is not enabled, the log leg
  degrades to emitting the query statements for the user's own SLS console
  and the exposure audit still completes.
- Any request the scripts issue carries a traceable User-Agent
  (`AlibabaCloud-Agent-Skills/alibabacloud-oss-security-incident-forensics/{session-id}`).

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
      "Sid": "ReadOnlyOssExposureQuery",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo",
        "oss:GetBucketPolicy",
        "oss:GetBucketPublicAccessBlock",
        "oss:GetBucketReferer",
        "oss:GetBucketRequestPayment",
        "oss:ListBuckets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlySlsLogQuery",
      "Effect": "Allow",
      "Action": [
        "log:GetHistograms",
        "log:GetLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is used because the forensics must cover any bucket the
  user names and the log project derived from its owner UID; read-only
  effect is guaranteed by the action list itself (Get/List/Query-class
  only). Optionally, the OSS statement can be narrowed to the ARN of a
  specific bucket (no wildcards) when the scope is known in advance.
- No `Deny` statements are required; anything not listed above is denied
  by default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | All regions — the bucket's region is exactly what the forensics discovers, so the policy cannot be pre-narrowed to one region by default |
| Resources | Bucket-level metadata/configuration of the buckets named by the user; `ListBuckets` enumerates bucket names/locations of the caller's own account only; the SLS queries read the OSS real-time-log project derived from the bucket OWNER UID (`oss-log-<owner-uid>-<regionId>`) |
| Data exposed | Bucket location, ACL label, bucket policy text, Block Public Access flag, Referer whitelist, Requester Pays payer — configuration metadata only, never object content; plus already-ingested OSS access-log rows (request metadata, no object content) |
| Mutations | None possible; only Get/List/Query-class actions are granted |

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
3. Assume the role (`aliyun sts assume-role`) and export the temporary
   credential via the `ALIBABA_CLOUD_ACCESS_KEY_ID` /
   `ALIBABA_CLOUD_ACCESS_KEY_SECRET` / `ALIBABA_CLOUD_SECURITY_TOKEN`
   environment variables; the CLI and the oss2 SDK both resolve it from
   the default credential chain.

Least-privilege checklist:

- Grant only the nine actions above; do not attach `AliyunOSSFullAccess`,
  `AliyunLogFullAccess`, or any administrator policy. `AliyunLogReadOnlyAccess`
  (action pattern `log:Get*` / `log:List*` / `log:Query*`) also covers the two
  SLS actions but is broader than the explicit pair; the explicit list is
  preferred for this skill.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them
  in the skill directory.
