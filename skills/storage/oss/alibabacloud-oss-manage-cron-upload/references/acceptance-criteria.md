# Acceptance Criteria: alibabacloud-oss-manage-cron-upload

**Scenario**: `Scheduled incremental sync from a local folder to OSS`
**Purpose**: Verify that the skill stays aliyun-CLI-first, preserves the canonical `aliyun ossutil cp` upload command, and clearly labels manual or OS-local steps.

---

# Correct CLI Command Patterns

## 1. Aliyun plugin-mode command shape

#### ✅ CORRECT
```bash
aliyun oss --help
aliyun ossutil api list-buckets --output-format json --user-agent AlibabaCloud-Agent-Skills
aliyun ossutil stat "oss://example-bucket" --output-format json --user-agent AlibabaCloud-Agent-Skills
```

Why it is correct:
- product and subcommands are lowercase plugin-mode commands
- every live `aliyun` command stays on the `aliyun` CLI surface documented by this skill

#### ❌ INCORRECT
```bash
aliyun OSS Help
aliyun ossutil api ListBuckets
aliyun ossutil stat "oss://example-bucket"
```

Why it is incorrect:
- uses non-plugin command shapes or mixed casing
- drifts away from the documented CLI form

## 2. Credential verification gate

#### ✅ CORRECT
```bash
aliyun configure list
```

Why it is correct:
- verifies profile availability without printing secrets
- matches the skill's safe authentication rule

#### ❌ INCORRECT
```bash
echo "$ALIBABA_CLOUD_ACCESS_KEY_ID"
aliyun configure set --access-key-id YOUR_ID --access-key-secret YOUR_SECRET
```

Why it is incorrect:
- prints or inlines credentials
- bypasses the required credential gate

## 3. Canonical incremental upload command

#### ✅ CORRECT
```bash
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" \
  -r -u \
  --max-age "${MaxAge}" \
  --region "${RegionId}" \
  --read-timeout 300 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills
```

Why it is correct:
- keeps the official `ossutil cp` workflow through `aliyun` CLI
- keeps the canonical incremental flags together
- `-u` means upload only when the target object is missing or the local source file is newer than the existing OSS object
- `-f` is optional and should be added only for explicitly requested non-interactive unattended runs such as cron, Task Scheduler, or CI
- `--region` sets both the endpoint and signing region correctly, which is required when the CLI profile's default region differs from the target bucket's region
- assumes a bucket-relative target prefix rather than an absolute OSS path

Using `--endpoint "oss-${RegionId}.aliyuncs.com"` in addition to `--region` is also acceptable but not required, since `--region` alone is sufficient and handles cross-region signing correctly.

#### ❌ INCORRECT
```bash
ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" -r -u --max-age "${MaxAge}" --endpoint "oss-${RegionId}.aliyuncs.com"
ossutil config
aliyun ossutil sync "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}"
aliyun oss sync "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}"
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" -r -u --endpoint "https://oss-${RegionId}.aliyuncs.com"
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" --recursive --update --meta "Cache-Control:max-age=604800"
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" -r -u
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" -r -u --endpoint "oss-${RegionId}.aliyuncs.com"
cat ~/.aliyun/config.json
```

Why it is incorrect:
- uses bare `ossutil` instead of the integrated `aliyun ossutil` surface required by this skill
- reintroduces `ossutil config`, which this skill must not use as the in-session auth flow
- replaces the documented `cp` workflow with `sync`
- omits `--max-age`
- rewrites the requested incremental window into unrelated object metadata
- uses `https://` prefix in endpoint which is not the documented format
- uses only `--endpoint` without `--region`, which fails with "Invalid signing region" when the CLI profile region differs from the target bucket region (STS token signing mismatch)
- omits both `--max-age` and `--region`
- reads credential files directly, exposing AK/SK values

## 4. Bucket prerequisite and versioning preference

#### ✅ CORRECT
```text
Use the existing bucket-creation flow documented by this skill, then continue with the verified `aliyun ossutil` upload path.
```

Why it is correct:
- if the bucket is missing, it is created before scheduled upload is configured
- if the bucket already exists, the answer may mention that versioning is preferable for backup safety, but does not block the workflow when no versioned bucket is available
- keeps bucket-management guidance on the `aliyun` CLI surface instead of drifting to unrelated tools

#### ❌ INCORRECT
```text
When the bucket is missing, stop permanently and refuse to show any bucket-creation path.
Never mention that bucket versioning can be beneficial for recurring backup scenarios even when the user asks for safer rollback options.
Treat a non-versioned existing bucket as unusable and block the workflow even though the user already confirmed that bucket.
```

Why it is incorrect:
- leaves the workflow incomplete when the missing-bucket step can be handled first
- drops a key backup-safety preference for recurring sync scenarios
- fails to encode the repository's new bucket-selection priority

## 5. Integrated `ossutil` through `aliyun` CLI

#### ✅ CORRECT
```text
Use aliyun CLI for installation checks, credential verification, help discovery, bucket verification, and the `aliyun ossutil cp` scheduled upload command.
```

Why it is correct:
- matches the user's CLI-only requirement for this skill
- keeps the upload flow on the integrated `aliyun ossutil` surface

#### ❌ INCORRECT
```text
Require a separate standalone `ossutil` installation or document bare `ossutil` commands as the primary path for this skill.
Tell the user to run `brew install ossutil` or `ossutil config` for the default workflow.
```

Why it is incorrect:
- drifts away from the required `aliyun` CLI surface
- reintroduces a separate local dependency that this skill should avoid
- swaps the required `aliyun configure list` gate for an unsupported credential flow

## 6. Scheduler labeling

#### ✅ CORRECT
```text
[OS-local] Configure cron with crontab or configure Windows Task Scheduler with schtasks or the Task Scheduler UI.
```

Why it is correct:
- labels the scheduler as host-level configuration
- makes it clear this is outside Alibaba Cloud APIs

#### ❌ INCORRECT
```text
Use aliyun CLI to create the cron job in OSS.
Use launchd as the default macOS answer even though the requested skill flow is documented around cron.
```

Why it is incorrect:
- misclassifies local scheduler setup as a cloud API operation
- drifts away from the skill's documented cron-first macOS path

## 7. Manual and unvalidated steps

#### ✅ CORRECT
```text
If the bucket is missing, create it first through the existing creation flow of this skill. If the bucket already exists, it is fine to mention that a versioning-enabled bucket is preferable for backup safety, but the confirmed existing bucket can still be used directly.
```

Why it is correct:
- avoids inventing unverified commands
- keeps the user informed about capability boundaries

#### ❌ INCORRECT
```text
Claim that bucket creation, RAM policy attachment, and scheduler setup are fully validated in this repository even though aliyun was not installed locally.
Mark the normal `aliyun ossutil cp ... --max-age ...` upload flow itself as unvalidated and replace it with a placeholder-only local filtering script.
Generate fake success artifacts such as sample upload logs, demo test files, or placeholder execution traces when the real prerequisite is still missing.
```

Why it is incorrect:
- overstates what was actually verified
- hides important operational limits
- blurs the line between truly unvalidated steps and the canonical upload pattern already required by the skill
- encourages simulated success instead of accurate boundary reporting

---

# Validation Checklist

The generated skill passes only if all of the following are true:
1. every live `aliyun` command shown by the skill stays on the documented `aliyun` CLI surface
2. the credential gate uses `aliyun configure list` rather than printing or setting secrets inline
3. the scheduled upload step uses `aliyun ossutil cp` with `-r -u --max-age`
4. the answer explains that `-u` uploads only when the target object is missing or the local source file is newer than the existing OSS object
5. if `-f` is mentioned, it is framed only as an optional flag for explicitly requested non-interactive unattended runs
6. the endpoint format is `oss-${RegionId}.aliyuncs.com` without `https://`
7. scheduler setup is labeled OS-local
8. if the bucket is missing, the answer creates it first following the existing creation flow of this skill
9. if the bucket already exists, the answer may mention that a versioned bucket is preferable for backup safety, but does not treat versioning as a hard prerequisite
10. macOS default scheduling guidance stays on `cron` / `crontab` unless the user explicitly asks for `launchd`
11. the answer does not replace the canonical upload command with bare `ossutil`, `ossutil config`, `Cache-Control` metadata mapping, or placeholder-only filtering scripts
