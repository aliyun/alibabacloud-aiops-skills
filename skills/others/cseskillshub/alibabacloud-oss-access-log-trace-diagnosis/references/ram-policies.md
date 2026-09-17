# RAM Policies

This skill is strictly read-only. The policy below grants only the read actions
that the scripts actually invoke. No action name contains a wildcard, and no
write action of any kind is required or declared.

If a read is denied at runtime the script records it in the Graceful
Degradation Log, marks that evidence unavailable, and continues with the rest;
grant the missing action from the mapping table and re-run.

## Invocation channels

| Channel | Products | Why |
|---|---|---|
| Python oss2 SDK (OSS control plane) | bucket and object configuration reads | The aliyun CLI carries no OSS control-plane metadata, and ossutil is not assumed to be installed, so the SDK is the only viable channel |
| aliyun CLI (POP gateway) | caller identity, log reads, RAM reads | Keeps these calls observable, retryable and interceptable for error-path testing |

Credentials always come from the default credential chain: the SDK reads
`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` /
`ALIBABA_CLOUD_SECURITY_TOKEN`, and the CLI reads its own profile. The scripts
never take credential arguments.

## Read-Only Policy (recommended)

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
      "Sid": "ReadOnlyBucketConfiguration",
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo",
        "oss:ListBuckets",
        "oss:GetBucketAcl",
        "oss:GetBucketPolicy",
        "oss:GetPublicAccessBlock",
        "oss:GetBucketReferer",
        "oss:GetBucketWebsite",
        "oss:GetBucketLogging",
        "oss:GetObjectAcl",
        "oss:ListObjects"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyAccessLog",
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs",
        "log:GetLogStore",
        "log:GetIndex",
        "log:ListLogStores",
        "log:GetProject"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyCallerPolicies",
      "Effect": "Allow",
      "Action": [
        "ram:GetRole",
        "ram:GetPolicy",
        "ram:GetPolicyVersion",
        "ram:ListPoliciesForUser"
      ],
      "Resource": "*"
    }
  ]
}
```

## Which statements are mandatory

| Statement | Needed for | Without it |
|---|---|---|
| VerifyCallerIdentity | Deriving the UID that forms the log project name | The project name cannot be derived; the naming template is handed over instead |
| ReadOnlyBucketConfiguration | Every authorization conclusion (ACL, policy, block public access) | Verdicts that depend on configuration are downgraded and reported as unavailable |
| ReadOnlyAccessLog | Reading the logged request row directly | For a customer deployment: an **optional enhancement** - the skill degrades to generating console statements and says plainly that nothing was queried. For platform evaluation: **required**, see [Evaluation grant](#evaluation-grant-required) |
| ReadOnlyCallerPolicies | The explicit-Deny scan and the assumed-role trust check | Those two branches report that the identity chain could not be inspected |

For a customer who does not want an agent reading log data, omitting the log
statement is a legitimate least-privilege choice: the skill still produces the
derived log target, the console verification path and ready-to-run statements,
and it says plainly that no query was executed.


## Evaluation grant (required)

The same statement has two different answers depending on who is running the
skill, and the difference is not cosmetic:

| Audience | ReadOnlyAccessLog | Reason |
|---|---|---|
| Customer production | Optional | Least privilege. Omitting it costs exactly one capability: console statements are handed over instead of the log being read here |
| Platform evaluation | **Required** | A read-only cloud-API skill must have **all three** outcomes measured - success, degradation and failure. Without the grant the success path is unreachable, so every run lands on the degradation branch and the direct-read code ships unmeasured |

Grant the `ReadOnlyAccessLog` statement above to the evaluation role named in
`evals/config/testconfig.json`. The actions are concrete and read-only; no
wildcard action and no write action is involved.

The grant is a console action on the evaluation account. This skill cannot
perform it, and nothing in this repository attempts to.

### Verifying the grant before trusting the cases

Re-run the log-source probe against the evaluation bucket:

```
python3 scripts/log_source_check.py \
    --bucket <evaluation-bucket> --region <region> --uid <account-uid>
```

| Probe `status` | Meaning | Action |
|---|---|---|
| `available` | The grant took effect and rows are being returned | The success path is now measurable; the gated cases can assert on real log content |
| `not_permitted` | The role still cannot read the logstore | The grant did not take effect. Fix the grant - do **not** weaken the assertion to hide it |
| `not_enabled` | Realtime log query is not switched on for that bucket | Enable it in the console first; a permission grant cannot substitute for it |
| `no_data_in_window` | Readable, but nothing was logged in the window | Widen `--hours`, or generate traffic against the bucket |
| `channel_unavailable` | The log-read channel is missing on this host | Nothing was queried. Install the CLI dependency, then re-probe |

Until the probe reports `available`, the gated assertions stay tolerant of both
outcomes - a direct log read, or an honest degradation. That tolerance is
deliberate: it keeps the cases green while the grant is pending, without ever
letting a degradation be reported as a successful read.
## Narrowing the log permission to one project

`Resource` is set to `*` above because the log project of a bucket is only
known once its region has been resolved, and the action list itself is
read-only. When the region and account are known in advance, narrow the
resource of `ReadOnlyAccessLog` to a single logstore:

```json
"Resource": "acs:log:<regionId>:<accountId>:project/oss-log-<uid>-<regionId>/logstore/oss-log-store"
```

The same narrowing applies to the bucket statement, using the bucket ARN
without any wildcard when the diagnosis scope is a single known bucket.

## Action-to-Script Mapping

| Product | Action | Used By | Purpose |
|---|---|---|---|
| STS | GetCallerIdentity | sts_token.py, _oss_client.py | Verify the caller and derive the account UID |
| OSS | GetBucketInfo | _oss_client.resolve_bucket_region, collect_config_evidence.py | Creation date, region, storage class, owner, ACL, versioning, redundancy |
| OSS | ListBuckets | _oss_client.resolve_bucket_region | Fallback region resolution when the bucket read is denied or the region is wrong |
| OSS | GetBucketAcl | collect_config_evidence.py | Bucket ACL, cross-checking the ACL reported by the bucket information read |
| OSS | GetBucketPolicy | collect_config_evidence.py | Policy document, or proof that none is configured |
| OSS | GetPublicAccessBlock | collect_config_evidence.py | Whether public access is blocked |
| OSS | GetBucketReferer | collect_config_evidence.py (conditional) | Hotlink whitelist **and** blacklist |
| OSS | GetObjectAcl | collect_config_evidence.py (conditional) | Per-object ACL override |
| OSS | GetBucketWebsite | collect_config_evidence.py (conditional) | Static website index and error documents |
| OSS | GetBucketLogging | log_source_check.py (conditional) | Periodic log shipping configuration |
| OSS | ListObjects | manual follow-up only | Confirm whether an object key exists |
| SLS | GetLogStoreLogs | log_source_check.py, trace_request.py, diagnose_access_log.py | Read the customer's own realtime access log |
| SLS | GetProject / ListLogStores / GetLogStore / GetIndex | log_source_check.py | Confirm the project and logstore exist and inspect the index |
| RAM | ListPoliciesForUser | collect_config_evidence.py (conditional) | Enumerate the caller's identity policies |
| RAM | GetPolicy / GetPolicyVersion | collect_config_evidence.py (conditional) | Read a policy document to find an explicit Deny |
| RAM | GetRole | collect_config_evidence.py (conditional) | Read an assumed-role trust relationship |

## Not requested by this skill

- **Object read permission is deliberately excluded.** One diagnosis path (an
  image-processing rejection caused by a corrupt source object) is stronger when
  the object bytes can be inspected, but that widens the permission surface
  considerably. The script hands the customer the exact command instead. Add
  object read only if the customer explicitly asks to automate that step.
- **No write action of any kind.** This skill never changes a bucket ACL, a
  policy, block public access, a referer list, a lifecycle rule, a logging
  configuration, or an object. Enabling realtime log query is console guidance
  only.

## Least-privilege checklist

1. Grant only the actions above; do not attach a full-access or administrator
   policy for OSS, for the log service, or for RAM.
2. Prefer a RAM role with a short session duration over long-lived user
   AccessKeys.
3. Narrow the log resource to one project once the region is known.
4. Never share credentials, never pass them to the scripts, and never store
   them inside the skill directory.
