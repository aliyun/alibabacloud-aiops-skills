---
name: alibabacloud-oss-manage-cron-upload
description: |
  Alibaba Cloud OSS scheduled local-folder sync skill using aliyun CLI, including integrated ossutil commands for incremental upload.
  Use when the user wants to schedule recurring local-to-OSS uploads, validate OSS backup prerequisites,
  set up cron or Task Scheduler for OSS sync, or clearly separate what stays on aliyun CLI
  from what remains OS-local or manual.
  Conditional write operations: creates the target bucket (PutBucket) only when the user confirms the bucket does not exist yet;
  optionally deletes test objects (DeleteObject) only when the user explicitly requests cleanup after verification.
  Triggers: "OSS scheduled sync", "定时同步到OSS", "aliyun ossutil cp --max-age", "aliyun ossutil cp -u",
  "cron upload to OSS", "Task Scheduler OSS upload", "aliyun CLI OSS sync", "本地目录增量上传 OSS".
---

# OSS Scheduled Local Sync

Plan and validate scheduled local-folder-to-OSS uploads with an aliyun-CLI-first workflow.

## Scenario Description

This skill covers the case where a local folder changes over time and must be uploaded to OSS on a recurring schedule.

**Architecture**: `Local folder + aliyun CLI (integrated ossutil) + cron/Task Scheduler + OSS Bucket`

**Capability split**:
- `[aliyun CLI]` installation checks, profile verification, command discovery, OSS-side verification, and integrated `aliyun ossutil` upload/list commands.
- `[OS-local]` cron or Windows Task Scheduler configuration.
- `[Manual/Console]` RAM policy attachment and optional visual verification in the OSS Console.

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify `>= 3.3.3`. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then run `aliyun configure set --auto-plugin-install true`.
> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload"
> ```
> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

> **[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload`

Required local tools:

| Tool | Required | Purpose | Verify |
| --- | --- | --- | --- |
| `aliyun` CLI | Yes | Credential gate, command discovery, and integrated `ossutil` upload/list surface | `aliyun version` and `aliyun ossutil --help` |
| `cron` or `schtasks` | Yes | Local recurring execution | `crontab -l` or `schtasks /Query /TN "OSS Scheduled Sync"` |

Use `references/cli-installation-guide.md` only for CLI installation and plugin setup. For this skill, use the integrated `aliyun ossutil` command surface — do **not** require standalone `ossutil` installation or bare `ossutil` commands.

## Environment Variables

No extra cloud-specific environment variables are required beyond an already configured Alibaba Cloud profile.

Optional local variables used in examples:

| Variable | Required/Optional | Description | Default Value |
| --- | --- | --- | --- |
| `ALIBABA_CLOUD_PROFILE` | Optional | Select a preconfigured Alibaba Cloud CLI profile | CLI current profile |
| `ALIYUN_BIN` | Optional | Absolute path to `aliyun` if it is not already in `PATH` | `aliyun` |
| `OSS_SYNC_LOG` | Optional | Log file path for scheduled execution | OS-specific local path |

## Parameter Confirmation

> **Parameter Extraction** — Extract all user-customizable parameters directly from the user's request.
> When the user's message already specifies values (such as region, bucket name, paths, schedule, or MaxAge),
> use those values directly without asking for re-confirmation.
> Only ask the user for clarification when a **required** parameter is genuinely missing from their request
> and cannot be reasonably inferred from context.

| Parameter Name | Required/Optional | Description | Validation Pattern | Default Value |
| --- | --- | --- | --- | --- |
| `RegionId` | Required | OSS region such as `cn-hangzhou` | `^[a-z]{2}-[a-z]+(|-[0-9]+)$` | None |
| `BucketName` | Required | Target OSS bucket name | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` | None |
| `TargetOssPrefix` | Required | Bucket-relative target OSS prefix such as `backup/photos/` (confirm without a leading `/`) | `^[A-Za-z0-9/_.-]*$` (no leading `/`) | None |
| `LocalSourcePath` | Required | Local folder to upload | Absolute path, no `~`, `$`, backtick, or `;` | None |
| `Schedule` | Required | Cron expression or Windows schedule time/frequency | Standard 5-field cron or `schtasks` time | None |
| `MaxAge` | Required | `aliyun ossutil --max-age` window such as `7d` or `24h` | `^[0-9]+[dhm]$` | None |
| `OperatingSystem` | Required | `linux`, `macos`, or `windows` | `^(linux|macos|windows)$` | None |
| `BucketAlreadyExists` | Required | Whether the target bucket already exists | `^(yes|no)$` | None |
| `AliyunBinaryPath` | Optional | Absolute path to `aliyun` for scheduler use | Absolute path, no `$`, backtick, or `;` | `aliyun` |
| `LogPath` | Optional | Local log path for the scheduled job | Absolute path, no `$`, backtick, or `;` | OS-specific local path |

> **Input Validation — All parameters must be validated before use.**
> Treat all inputs (including values extracted from user messages) as untrusted. Before substituting any parameter into a shell command:
> 1. Validate the value against the **Validation Pattern** column above. Reject values that do not match.
> 2. `BucketName` must contain only lowercase letters, digits, and hyphens (`[a-z0-9-]`), be 3–63 characters, and must not start or end with a hyphen.
> 3. `RegionId` must match the Alibaba Cloud region format (e.g., `cn-hangzhou`, `us-west-1`, `ap-southeast-5`).
> 4. `MaxAge` must be a positive integer followed by `d` (days), `h` (hours), or `m` (minutes).
> 5. `LocalSourcePath`, `AliyunBinaryPath`, and `LogPath` must be absolute paths and must **not** contain shell metacharacters (`$`, `` ` ``, `$(`, `;`, `|`, `&`, `>`, `<`, `\n`).
> 6. `TargetOssPrefix` must contain only alphanumeric characters, `/`, `_`, `.`, and `-`, and must not start with `/`.
> 7. If any parameter fails validation, **stop and report the error** to the user. Do not attempt to sanitize or escape invalid values — reject them outright.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** read or `cat` credential files such as `~/.aliyun/config.json`, `~/.ossutil/config`, or any file that may contain secrets
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

Reuse the active CLI profile for all `aliyun ossutil` commands. Do not print or hardcode secrets. Do not replace this gate with `ossutil config` or any other secret-entry flow.

## RAM Policy

The default workflow needs least-privilege access for bucket discovery, bucket metadata verification, and object upload under the confirmed prefix.

| Scope | Required Actions |
| --- | --- |
| Account-level verification | `oss:ListBuckets` |
| Target bucket verification | `oss:GetBucketInfo` |
| Incremental upload to target prefix | `oss:PutObject`, `oss:GetObject`, `oss:ListObjects` |
| Optional test cleanup | `oss:DeleteObject` |

Use `references/ram-policies.md` for the policy JSON and the prefix-scoped resource examples.

Do **not** redefine the default minimum set around `oss:AbortMultipartUpload`. In this skill, the default least-privilege path stays anchored on bucket discovery, bucket metadata verification, and prefix-scoped upload/list/read actions. Multipart-cleanup permissions are follow-up work only when the user explicitly asks for them.

## Core Workflow

> **Execute, don't just document.** Run each step's commands directly in the environment. Do not only write solution documents or scripts — actually execute `aliyun version`, `aliyun configure list`, `aliyun ossutil cp`, etc. against the live environment.
>
> Extract `RegionId`, `BucketName`, `TargetOssPrefix`, `LocalSourcePath`, `Schedule`, `MaxAge`, `OperatingSystem`, and `BucketAlreadyExists` from the user's request. Only ask the user if a required parameter is genuinely missing.

### Step 1: Verify CLI and credentials `[aliyun CLI]`

```bash
aliyun version
aliyun configure list
aliyun configure ai-mode enable
```

Verify that:
- `aliyun` version is `>= 3.3.3`
- at least one valid profile is present
- AI safety mode is enabled (dangerous operations will be blocked)

If the version is too low or `aliyun` is missing, see `references/cli-installation-guide.md`. Do not work around a missing CLI by switching to standalone `ossutil` or `aliyun ossutil sync`.

### Step 2: Verify or create the bucket prerequisite `[aliyun CLI]`

Always start by checking the candidate bucket inventory:

```bash
aliyun ossutil api list-buckets --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

If `BucketAlreadyExists=yes`, verify the selected bucket explicitly:

```bash
aliyun ossutil stat "oss://${BucketName}" --region "${RegionId}" --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

> **Cross-region note**: When the active CLI profile's region (shown by `aliyun configure list`) differs from the target bucket's `RegionId`, you **must** add `--region "${RegionId}"` to `stat`, `ls`, and `cp` commands. Using `--endpoint` alone is insufficient because the request signing region must also match. The `--region` flag overrides both the endpoint and the signing region in a single step.

What to confirm:
- the bucket name is present in the account inventory
- the bucket region matches `RegionId`
- the bucket is reachable with the active profile
- if multiple existing buckets can satisfy the same backup target, you can remind the user that a bucket with versioning enabled is preferable for backup safety, but this is only a recommendation and does not block using the confirmed existing bucket

If `BucketAlreadyExists=no`, use the **check-then-act** idempotent pattern:
1. First run `list-buckets` (above) to confirm the bucket truly does not exist in the account — if it already exists, skip creation and go directly to `stat` verification.
2. Only if the bucket is confirmed absent, create it by following the existing creation flow of this skill.
3. After creation, immediately re-run `stat` to verify:

```bash
aliyun ossutil stat "oss://${BucketName}" --region "${RegionId}" --output-format json \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Optional recommendation for recurring backup scenarios:
- if multiple candidate buckets exist and one already has versioning enabled, mention that it is preferable for backup rollback safety
- if the confirmed existing bucket does not have versioning enabled, it can still be used for this workflow; enabling versioning is only an optional hardening suggestion, not a prerequisite

Keep `aliyun ossutil` as the canonical surface for upload and verification commands such as `cp`, `ls`, and `stat`. For bucket creation, follow the existing creation flow already documented by this skill instead of inventing a new command family here. Do **not** fabricate success, extra deployment files, or fake local artifacts just to cover a missing prerequisite.

### Step 3: Run the canonical incremental upload test `[aliyun CLI / integrated ossutil]`

Use the official data-plane command family for the actual scheduled upload job through `aliyun ossutil`:

```bash
aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" \
  -r -u \
  --max-age "${MaxAge}" \
  --region "${RegionId}" \
  --read-timeout 300 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Key rules for this command:
- `-u` is mandatory: uploads only when the target object is missing or the source file is newer than the existing OSS object
- `-r -u --max-age` must stay together as the canonical flag set
- `--region "${RegionId}"` ensures both endpoint and signing region are correct
- `--read-timeout 300 --connect-timeout 30` prevents the command from hanging indefinitely; adjust `--read-timeout` upward for very large files if needed
- Add `-f` only for unattended runs (cron, Task Scheduler, CI)
- Use absolute paths for `LocalSourcePath` (never `~`)
- Normalize `TargetOssPrefix` without a leading `/`
- Do **not** substitute with bare `ossutil`, `aliyun ossutil sync`, or `Cache-Control` metadata rewrites

If `TargetOssPrefix` is empty, use `oss://${BucketName}/` (with trailing slash). Otherwise use `oss://${BucketName}/${TargetOssPrefix}` after prefix normalization.

> **If `LocalSourcePath` does not exist** in the current environment (e.g., container or CI runner), create it under the current working directory with a small test file, then run the upload command against it and verify with `aliyun ossutil ls`. This proves the upload path works end-to-end. Do **not** skip the upload test just because the directory is absent — create it and validate connectivity, permissions, and command correctness:
> ```bash
> mkdir -p "${LocalSourcePath}" && echo "test" > "${LocalSourcePath}/test.txt"
> aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" \
>   -r -u --max-age "${MaxAge}" --region "${RegionId}" \
>   --read-timeout 300 --connect-timeout 30 \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
> aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region "${RegionId}" \
>   --read-timeout 60 --connect-timeout 30 \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
> ```

### Step 4: Wrap the upload in a local script `[aliyun CLI + OS-local]`

Minimal script template:

```bash
#!/usr/bin/env bash
set -euo pipefail

ALIYUN_BIN="${ALIYUN_BIN:-aliyun}"
LOCAL_SOURCE_PATH="${LocalSourcePath}"   # MUST be an absolute path, never use ~
BUCKET_NAME="${BucketName}"
TARGET_OSS_PREFIX="${TargetOssPrefix#/}"
MAX_AGE="${MaxAge}"
REGION_ID="${RegionId}"
LOG_FILE="${OSS_SYNC_LOG:-$HOME/oss-sync.log}"
READ_TIMEOUT="${READ_TIMEOUT:-600}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-30}"

# --- Input validation ---
[[ "${BUCKET_NAME}" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] || { echo "ERROR: Invalid BucketName: ${BUCKET_NAME}" >&2; exit 1; }
[[ "${REGION_ID}" =~ ^[a-z]{2}-[a-z]+(|-[0-9]+)$ ]]          || { echo "ERROR: Invalid RegionId: ${REGION_ID}" >&2; exit 1; }
[[ "${MAX_AGE}" =~ ^[0-9]+[dhm]$ ]]                           || { echo "ERROR: Invalid MaxAge: ${MAX_AGE}" >&2; exit 1; }
[[ "${TARGET_OSS_PREFIX}" =~ ^[A-Za-z0-9/_.-]*$ ]]            || { echo "ERROR: Invalid TargetOssPrefix: ${TARGET_OSS_PREFIX}" >&2; exit 1; }
[[ "${LOCAL_SOURCE_PATH}" == /* ]]                             || { echo "ERROR: LocalSourcePath must be absolute: ${LOCAL_SOURCE_PATH}" >&2; exit 1; }

TARGET_URI="oss://${BUCKET_NAME}/"

if [ -n "${TARGET_OSS_PREFIX}" ]; then
  TARGET_URI="oss://${BUCKET_NAME}/${TARGET_OSS_PREFIX}"
fi

"${ALIYUN_BIN}" ossutil cp "${LOCAL_SOURCE_PATH}" "${TARGET_URI}" \
  -r -u -f \
  --max-age "${MAX_AGE}" \
  --region "${REGION_ID}" \
  --read-timeout "${READ_TIMEOUT}" --connect-timeout "${CONNECT_TIMEOUT}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload >> "${LOG_FILE}" 2>&1
```

> **Note**: The `-f` flag is included in the script template because the script is intended for unattended cron/Task Scheduler execution where interactive prompts must not block the job. The `--region` flag is preferred over `--endpoint` because it sets both the endpoint and signing region correctly, which is required when the CLI profile's default region differs from the target bucket's region.

### Step 5: Configure the scheduler `[OS-local]`

**Linux/macOS cron**:

For the default Linux/macOS path in this skill, keep `cron` / `crontab` as the documented scheduler surface. Do **not** silently swap the answer to `launchd` unless the user explicitly asks for a launchd-specific variant.

> **If `crontab` is not found**: In container or minimal environments, `crontab` may not be pre-installed. Install the `cronie` package first:
> - CentOS/Alibaba Cloud Linux/RHEL: `yum install -y cronie`
> - Debian/Ubuntu: `apt-get install -y cron`
>
> If `systemctl start crond` fails (e.g., no systemd in containers), you can still add cron entries via `crontab` — the cron daemon is not strictly required for entry registration, only for actual execution. In such cases, document the cron entry for the user to deploy on their production host, and do **not** let the missing daemon block the rest of the workflow.

```bash
crontab -e
```

Example entry (use `echo ... | crontab -` for non-interactive installation):

```cron
0 3 * * * /usr/local/bin/oss-sync-upload.sh >> /var/log/oss-sync-cron.log 2>&1
```

**Windows Task Scheduler** via local CLI:

```bat
schtasks /Create /SC DAILY /ST 03:00 /TN "OSS Scheduled Sync" /TR "C:\tools\oss-sync-upload.bat"
```

Label this step clearly as OS-local. It is not an Alibaba Cloud API action. Keep the scheduler output minimal and directly actionable; do not explode this step into extra README files, XML exports, PowerShell wrappers, demo payloads, or other auxiliary artifacts unless the user explicitly asks for them.

### Step 6: Verify the upload target `[aliyun CLI / integrated ossutil]`

Always run this verification after any upload (including test uploads from Step 3):

```bash
aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region "${RegionId}" \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Confirm that the expected objects appear under the target prefix. Do **not** skip this step — it proves end-to-end connectivity and permissions.

If the user wants a manual visual check, label it clearly as `[Manual/Console]` and confirm the target prefix in the OSS Console.

### Step 7: State the capability boundary clearly

Always state these limitations when relevant:
- **The actual incremental sync step runs through `aliyun ossutil`.** This skill stays on the `aliyun` CLI surface and does not require a separate standalone `ossutil` installation.
- **Scheduler setup is OS-local.** Cron and Task Scheduler are configured on the host OS, not through Alibaba Cloud APIs.
- **RAM policy attachment is typically manual or follows the user's existing IAM workflow.**
- **Bucket creation should happen before scheduled upload when the target bucket is missing.** Follow the existing creation flow of this skill for that prerequisite.
- **If multiple equivalent existing buckets are available, it is fine to remind the user that a versioning-enabled bucket is preferable for backup safety.** If no versioned bucket is available, continue with the confirmed existing bucket instead of blocking the workflow.
- **Optional OSS Console checks are manual.**
- **Do not simulate success.** When a prerequisite is missing, say so plainly instead of creating fake local test data, pretend execution logs, or extra packaging artifacts.

## Success Verification Method

Use `references/verification-method.md` as the authoritative checklist.

Minimum pass conditions:
1. `aliyun configure list` shows a valid profile.
2. `aliyun ossutil cp --help` succeeds.
3. the canonical `aliyun ossutil cp ... -r -u --max-age ... --region ...` command completes without permission or endpoint errors.
4. `aliyun ossutil ls ... --region ...` shows the expected uploaded objects under the confirmed prefix.
5. the upload command keeps `-u`, meaning it uploads only when the target object is missing or the local source file is newer than the existing OSS object.
6. the local scheduler entry is visible through `crontab -l` or Task Scheduler history/query, or is documented for the user when crontab is not available in the current environment.

## Cleanup

Cleanup is optional because this skill is intended for recurring sync, but test artifacts and scheduler entries can be removed safely.

**Linux/macOS cron** `[OS-local]`:
- remove the cron line with `crontab -e`
- delete the local script and log file only if the user explicitly wants rollback

**Windows Task Scheduler** `[OS-local]`:

```bat
schtasks /Delete /TN "OSS Scheduled Sync" /F
```

**Optional OSS test cleanup** `[aliyun CLI / integrated ossutil]`:

```bash
aliyun ossutil rm "oss://${BucketName}/${TargetOssPrefix}test-object.txt" --region "${RegionId}" \
  --read-timeout 60 --connect-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-cron-upload
```

Do not delete the bucket or production objects unless the user explicitly asks for that cleanup scope.

**Disable AI safety mode** `[aliyun CLI]`:

After all tasks are completed, disable AI safety mode to restore normal CLI behavior:

```bash
aliyun configure ai-mode disable
```

## API and Command Tables

See `references/related-apis.md` for the command inventory, OSS capability notes, and validation notes. That file is reference metadata only.

## Best Practices

1. Keep `aliyun` for pre-checks, command discovery, bucket verification, and integrated `aliyun ossutil cp` for the actual scheduled upload.
2. Use `--region "${RegionId}"` on all `aliyun ossutil` commands (`stat`, `cp`, `ls`, `rm`) to ensure both endpoint and signing region are correct. This is especially important when the CLI profile's default region differs from the target bucket's region. Do **not** rely on `--endpoint` alone, as it does not override the signing region and will fail with "Invalid signing region in Authorization header" errors when using STS tokens across regions.
3. Keep scheduler steps labeled as OS-local so the user understands they are outside Alibaba Cloud APIs.
4. Use the narrowest RAM policy possible: bucket inventory at account scope, bucket info on the target bucket, and object upload only on the confirmed prefix.
5. Run `aliyun version` and `aliyun configure list` on the target machine before live execution.
6. Never print AK/SK values, never hardcode them in scripts, never read credential files like `~/.aliyun/config.json`, and never replace the credential gate with inline secret handling.
7. If the bucket does not exist, create it first before configuring scheduled upload. If multiple existing buckets can satisfy the same backup target, you may remind the user that a versioning-enabled bucket is preferable for backup safety, but if no such bucket exists, continue with the confirmed existing bucket.
8. Always use absolute paths for `LocalSourcePath` in commands and scripts. Do not use `~` (tilde) because it may not expand inside quoted strings, causing "not a directory" errors.
9. In generated scripts intended for cron or Task Scheduler, include the `-f` flag to prevent interactive confirmation prompts from blocking unattended execution.

## Reference Links

| Reference | Description |
| --- | --- |
| `references/cli-installation-guide.md` | Required CLI installation guide copied from the creator skill asset |
| `references/verification-method.md` | Pre-check, upload, scheduler, and manual verification checklist |
| `references/related-apis.md` | `aliyun` and integrated `ossutil` command inventory with OSS API mapping |
| `references/ram-policies.md` | Least-privilege RAM policy guidance for verification and upload |
| `references/acceptance-criteria.md` | Correct and incorrect command patterns for this scenario |
