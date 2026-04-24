# RAM Policies for OSS Scheduled Local Sync

## Overview

This scenario needs least-privilege permissions for four things:
1. account-level bucket discovery
2. target-bucket creation when the bucket is missing
3. target-bucket metadata verification
4. object upload under the confirmed OSS prefix

The default flow still does **not** require broad permissions such as full-bucket administration or account-wide object deletion.

## Required Permission Summary

**Account scope (Resource: `*`)**

- `oss:ListBuckets` — List all buckets under the current account to verify whether the target BucketName already exists

**Target bucket scope (Resource: `acs:oss:*:*:${BucketName}`)**

- `oss:GetBucketInfo` — Query target bucket metadata (e.g., region, storage class) to verify the bucket is in the correct region
- `oss:PutBucket` — Create the bucket (conditional: only required when `BucketAlreadyExists=no` and the user explicitly requests bucket creation)

**Target prefix scope (Resource: `acs:oss:*:*:${BucketName}/${TargetOssPrefix}*`)**

- `oss:PutObject` — Upload new or modified files to the target prefix
- `oss:GetObject` — Read existing object metadata; required by `aliyun ossutil cp -u` incremental upload to compare local files against remote objects
- `oss:ListObjects` — Enumerate existing objects under the target prefix for incremental upload comparison and post-upload verification
- `oss:DeleteObject` — Delete test objects (**optional**: only required when the user explicitly requests automated cleanup of test data)

## Minimal Policy Template

Replace `${BucketName}` and `${TargetOssPrefix}` with confirmed values before creating the policy.

Normalize `TargetOssPrefix` first so it is bucket-relative and does not start with `/`.
If `TargetOssPrefix` is empty, replace the object resource with `acs:oss:*:*:${BucketName}/*`.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:ListBuckets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:${BucketName}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:${BucketName}",
        "acs:oss:*:*:${BucketName}/${TargetOssPrefix}*"
      ]
    }
  ]
}
```

## Optional Cleanup Extension

Only add this if the user explicitly wants the skill to delete test objects after verification:

```json
{
  "Effect": "Allow",
  "Action": [
    "oss:DeleteObject"
  ],
  "Resource": [
    "acs:oss:*:*:${BucketName}/${TargetOssPrefix}*"
  ]
}
```

## Bucket Creation Extension

If the bucket may be missing, include bucket-creation permissions in the reviewed policy scope.

> **Idempotent pattern**: Bucket creation must follow a **check-then-act** pattern — first call `list-buckets` to verify the bucket does not exist, then create it only if confirmed absent. This prevents duplicate creation attempts and ensures idempotency. The `aliyun ossutil cp -u` upload command is inherently idempotent (uploads only when the target object is missing or the source file is newer).

Bucket versioning is only an optional hardening suggestion in this repository. Do not add bucket-versioning permissions by default unless the user explicitly asks to manage versioning through CLI as part of the workflow.

## What Not to Grant by Default

Avoid these broad patterns unless the user explicitly asks for expanded scope:
- `AliyunOSSFullAccess`
- account-wide delete permissions
- bucket policy or ACL mutation permissions
- cross-prefix object administration unrelated to the confirmed upload target
- redefining the default minimum policy around `oss:AbortMultipartUpload` instead of the documented `ListBuckets` + `GetBucketInfo` + `PutObject` + `GetObject` + `ListObjects` set

## Attachment Guidance

Policy creation and attachment are usually handled through the RAM Console or the user's existing IAM workflow.

Label this step clearly as manual or existing-IAM-process work. Do not claim the default scenario is fully automated through `aliyun` CLI in this repository, and do not pad the answer with fake attachment scripts or simulated execution output when IAM prerequisites are still unresolved.

## Verification

After the policy is attached, verify with:

```bash
aliyun configure list
aliyun ossutil api list-buckets --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region "${RegionId}" \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Expected behavior:
- the active profile is valid
- bucket inventory succeeds without `AccessDenied`
- prefix listing succeeds after the first upload test
- the documented minimum action set still matches `oss:ListBuckets`, `oss:GetBucketInfo`, `oss:PutObject`, `oss:GetObject`, and `oss:ListObjects`; if a draft answer swaps in `oss:AbortMultipartUpload` as part of the default minimum set, treat that as drift from this skill
