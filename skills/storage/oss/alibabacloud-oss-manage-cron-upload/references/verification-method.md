# Verification Method for OSS Scheduled Local Sync

## Scope

This checklist verifies the CLI prerequisites, the OSS upload path, and the local scheduler.

## Pre-Execution Verification

Run the canonical preflight block from `SKILL.md` Step 1 and Step 2 before live execution.

Minimum checks:

```bash
aliyun version
aliyun configure list
aliyun configure ai-mode enable
```

Success criteria:
- `aliyun` version is `>= 3.3.3`.
- At least one valid profile is present.
- AI safety mode is enabled (dangerous operations will be blocked).
- No credentials are echoed manually.
- No separate standalone `ossutil` installation is required for this skill.
- The workflow does not drift into `ossutil config`, `brew install ossutil`, `aliyun ossutil sync`, or simulated local test-data creation.

## Bucket Prerequisite Verification

If the bucket is expected to exist already:

```bash
aliyun ossutil api list-buckets --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
aliyun ossutil stat "oss://${BucketName}" --region "${RegionId}" --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Verify that:
- `BucketName` appears in the bucket inventory.
- the returned region matches `RegionId`.
- the active profile can read bucket metadata.
- `--region "${RegionId}"` is included when the CLI profile's default region differs from the target bucket's region.

If the bucket does not exist:
- create the bucket first before configuring scheduled upload
- follow the existing bucket-creation flow documented by this skill
- re-run `aliyun ossutil stat "oss://${BucketName}" --region "${RegionId}" --output-format json --read-timeout 60 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload` to confirm the bucket now exists
- do not generate fake upload logs, demo local payloads, placeholder batch/shell wrappers, or pretend success outputs to make the answer look complete

If the bucket already exists:
- continue with the confirmed existing bucket after `aliyun ossutil stat` succeeds
- optionally remind the user that a versioning-enabled bucket can be better for backup rollback safety when such a choice already exists
- do not block the workflow just because the confirmed existing bucket is not versioned

## Upload Verification

### 1. Run the canonical incremental upload once

```bash
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" \
  -r -u \
  --max-age "${MaxAge}" \
  --region "${RegionId}" \
  --read-timeout 300 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Verify that:
- the command uses `cp`, not `sync`
- the canonical flags `-r -u --max-age` are present together
- `-u` is explained correctly: upload only when the target object is missing or the local source file is newer than the existing OSS object
- if `-f` is mentioned, it is framed only as an optional flag for explicitly requested non-interactive unattended runs such as cron, Task Scheduler, or CI
- `--region "${RegionId}"` is used to set both the endpoint and signing region correctly (using `--endpoint` alone without `--region` will fail with "Invalid signing region" when the CLI profile region differs from the target bucket region)
- `TargetOssPrefix` is normalized as a bucket-relative path without a leading `/` before the command is run
- the answer does not silently replace this command with a separate standalone `ossutil` install, `ossutil config` credential setup, `aliyun ossutil sync`, `Cache-Control:max-age=...` metadata mapping, or placeholder-only local filtering scripts

### 1.1 Verify the `-u` incremental behavior

After the first successful upload, verify the incremental semantics explicitly:
- re-run the same `aliyun ossutil cp ... -r -u --max-age ... --region ...` command without modifying local files and confirm unchanged files are not uploaded again
- update the last-modified time of one local source file, then re-run the same command and confirm only that newer file is uploaded

### 2. Verify uploaded objects

```bash
aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region "${RegionId}" \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Verify that:
- expected objects appear under the confirmed prefix
- the object path is correct and not duplicated accidentally
- the prefix does not begin with `/`
- the command succeeds without `AccessDenied`, endpoint-format, or signing-region errors

## Scheduler Verification

### Linux/macOS cron

```bash
crontab -l
```

Verify that:
- the expected cron line is present
- the script path matches the deployed script
- the schedule matches the confirmed `Schedule` value
- the answer did not silently switch the documented macOS path to `launchd` when the skill flow or user request called for `cron`

### Windows Task Scheduler

Verify one of the following:
- `schtasks /Query /TN "OSS Scheduled Sync" /V /FO LIST`
- Task Scheduler UI shows the task and last-run status
- Task Scheduler History records successful launches after the task is enabled

## Manual OSS Console Verification

Use this only when the user wants a visual check.

Manual steps:
1. Open the OSS Console.
2. Open `BucketName`.
3. Browse to `TargetOssPrefix`.
4. Confirm that the expected objects and timestamps are visible.

Label this verification clearly as manual.

## Failure Verification

The workflow should stop clearly in these cases:
1. `aliyun` is not installed.
2. the `aliyun ossutil` command surface is unavailable.
3. `aliyun configure list` does not show a valid profile.
4. bucket creation fails or the active identity lacks bucket-creation permissions.
5. `AccessDenied` indicates missing bucket-list, bucket-management, or upload permissions.
6. the endpoint was built incorrectly (for example by adding `https://`), or `--endpoint` was used without `--region` causing a signing-region mismatch.
7. the scheduler entry is missing after configuration.
8. the answer falls back to standalone `ossutil`, `ossutil config`, `aliyun ossutil sync`, or fake local test-data creation instead of reporting the real blocker.

## Validation Status for This Repository

This repository was generated in an environment where `aliyun` was not installed, so local `aliyun ... --help` and `aliyun ossutil ...` validation could not be completed here. The real upload and listing commands also were not executed against a live bucket in this repository.

What was validated locally in this repository:
- the documentation consistently keeps the upload and listing flow on `aliyun ossutil`
- the canonical flag combination (`-r -u --max-age --region`) remains consistent across the skill files
- `crontab -l` behavior when no user crontab exists

Re-run all `aliyun` verification commands on the target machine before live execution, and run the real `aliyun ossutil cp` and `aliyun ossutil ls` commands against the target bucket before treating the workflow as production-ready.
