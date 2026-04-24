---
name: alibabacloud-oss-manage-network-probe
description: |
  Alicloud Service Scenario-Based Skill. Use for diagnosing local-to-OSS network state,
  upload/download bandwidth, download time, and local symlink issues with `aliyun ossutil probe`.
  Triggers: "aliyun ossutil probe", "OSS 网络探测", "OSS 带宽探测", "OSS 下载时间探测", "OSS 软链接探测".
---

# Detailed description of the scenario's application and purpose.

Diagnose network connectivity, upload/download bandwidth, download time, and local symlink anomalies between the local workstation and OSS using `ossutil 2.0` integrated with the Alibaba Cloud CLI.

**Architecture**: Local Workstation + Alibaba Cloud CLI 3.3.3+ + `aliyun ossutil` + OSS Bucket + Optional target object or presigned URL + Optional probe domain

| Scenario | Recommended Command | Output |
| --- | --- | --- |
| Upload connectivity probe | `aliyun ... ossutil probe --upload` | Upload duration, object name, log file |
| Download connectivity probe | `aliyun ... ossutil probe --download` | Download duration, local file path, log file |
| Upload bandwidth suggestion | `aliyun ... ossutil probe --probe-item upload-speed` | Suggested concurrency value |
| Download bandwidth suggestion | `aliyun ... ossutil probe --probe-item download-speed` | Suggested concurrency value |
| Download time measurement | `aliyun ... ossutil probe --probe-item download-time` | Concurrency/part-size/duration statistics |
| Symlink anomaly check | `aliyun ... ossutil probe --probe-item cycle-symlink` | Whether abnormal symlinks exist |

> **Important implementation boundary**
> - `probe` is a composite client-side diagnostic command provided by `aliyun ossutil`; there is no equivalent `aliyun oss api probe`.
> - `cycle-symlink` can only detect abnormal symlinks — it cannot safely auto-fix target paths.
> - Probe output can locate symptoms and suggest concurrency, but cannot guarantee an automatic precise root cause for all network anomalies.
> - `download-speed` requires a real existing object, and the official recommendation is objects larger than 5 MiB. If no suitable object exists, the user must first confirm an existing object path, or confirm a local file to upload via `aliyun ossutil cp` before probing.

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then run the credential gate `aliyun configure list`.
> **Only after `configure list` shows a valid profile**, run `aliyun configure set --auto-plugin-install true` and `aliyun ossutil version`.

Run the version and credential gate first:
```bash
aliyun version
aliyun configure list
```

Only after `configure list` confirms a valid profile, proceed:
```bash
aliyun configure set --auto-plugin-install true
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe"
aliyun ossutil version
aliyun plugin update
```

> **AI safety mode**: `configure ai-mode enable` activates the CLI's built-in safety guard, which blocks dangerous operations (e.g. deleting critical resources) at the CLI level. This must be enabled before executing any ossutil commands.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe`

## Environment Variables

| Environment Variable | Required/Optional | Description | Default Value |
| --- | --- | --- | --- |
| `ALIBABA_CLOUD_PROFILE` | Optional | Specify which CLI profile to use | Current default profile |
| `HTTP_PROXY` | Optional | HTTP proxy address in proxied environments | None |
| `HTTPS_PROXY` | Optional | HTTPS proxy address in proxied environments | None |
| `NO_PROXY` | Optional | Proxy bypass list | None |

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
| --- | --- | --- | --- |
| `profile` | Optional | CLI profile to use | Current default profile |
| `region_id` | Optional | Region where the bucket is located; use when auto-detection is unreliable or explicit specification is needed | None |
| `bucket_name` | Required for bucket-based probes | Target bucket name | None |
| `object_name` | Required for `download-speed` and `download-time`; optional for other bucket-based probes | Full object path, e.g. `dir/example.txt`; for `download-speed`, objects larger than 5 MiB are recommended for stable results | None |
| `local_path` | Optional | Local upload file path, symlink scan directory, or download save path | None |
| `download_url` | Required for URL-based download probe | Public-read URL or signed private URL | None |
| `endpoint` | Optional | Use only when the user explicitly provides it or the error message clearly points to a specific endpoint | None |
| `addr` | Optional | Domain for `--addr` network connectivity check | `www.aliyun.com` only if user explicitly accepts |
| `upmode` | Optional | Upload probe mode | `normal` |
| `runtime` | Optional | Max runtime in seconds for `upload-speed` / `download-speed` | CLI default |
| `parallel` | Optional | Single-file concurrency for `download-time` | `1` |
| `part_size` | Optional | Part size in bytes for `download-time` | CLI auto/default |

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** read credential files such as `~/.aliyun/config.json`, or dump environment variables to inspect credentials
> - **NEVER** write a full presigned URL with query-string signature parameters into logs or final output; if you must mention it, redact everything after `?`
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

If multiple profiles exist, explicitly add `--profile <profile>` in subsequent commands, placed after `aliyun` and before `ossutil`, e.g. `aliyun --profile <profile> ossutil version`.

## RAM Policy

The minimum OSS permissions required by this skill depend on the probe mode. Refer to `references/ram-polices.md` for per-scenario permission tables and policy examples.

- Upload probes, upload bandwidth probes, temporary object probes: require at least `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject`
- Download probes, download bandwidth probes, download time probes: require at least `oss:GetObject`
- If using `aliyun ossutil cp` to pre-upload a test object: requires `oss:PutObject`
- If using `aliyun ossutil rm` to clean up an explicitly specified test object: requires `oss:DeleteObject`

## Core Workflow

### 1. Validate the CLI environment

Execute in the following order — do not skip steps:

1. Check CLI version first:
```bash
aliyun version
```
2. Then check credentials/profile:
```bash
aliyun configure list
```
3. **If `configure list` does not show a valid profile, or reports a missing config file, STOP immediately.**
   - Do NOT proceed with `configure set --auto-plugin-install true`
   - Do NOT proceed with `ossutil version`
   - Do NOT fabricate bucket, object, profile, region, or probe success results
4. Only after the profile is valid, proceed to prepare the plugin, enable AI safety mode, and verify `ossutil`:
```bash
aliyun configure set --auto-plugin-install true
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe"
aliyun ossutil version
```

### 1.1 Log file naming and command substitution

- When saving execution logs, use static strings for filenames (e.g. `probe_download_time.log`). **Do not use `$(date ...)`, `$(...)`, or backtick shell command substitutions in filenames**, because different execution environments have inconsistent shell interpolation support, which can easily cause syntax errors.
- Some execution environments block `$()` command substitution entirely. When you need to capture command output into a variable (e.g. for presigned URLs), **use the file+script pattern**: redirect output to a temporary file, then create a shell script that reads the file and uses the value. See §B for a concrete example.

### 2. Choose the probe mode

#### A. Upload connectivity probe

- If the user only wants network/upload connectivity diagnostics without keeping the object, omit `local_path` and `object_name` and let `probe` use a temporary file that is auto-cleaned after completion.
- If the user wants to verify a specific real file's upload path, confirm `local_path`.
- If the upload probe returns `AccessDenied`, quote the error as-is and explain that at least `oss:GetObject`, `oss:PutObject`, `oss:DeleteObject` are required; do not enumerate buckets, regions, or fall back to legacy command forms.

```bash
aliyun ossutil probe \
  --upload "<LOCAL_PATH_IF_ANY>" \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME_IF_USER_WANTS_TO_KEEP_IT>" \
  --addr "<ADDR_IF_CONFIRMED>" \
  --upmode "<UPMODE_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

When `LOCAL_PATH_IF_ANY` is not provided, remove that positional parameter entirely — do not pass an empty string.

#### B. Download probe via URL

- Public-read objects: have the user confirm a directly accessible URL.
- Private objects: generate a presigned URL first, then run `probe --download --url`.

Generate a presigned URL, save it to a temporary file, then run the probe via a shell script. This two-step approach avoids exposing the full URL in command history and works in environments where `$()` command substitution is blocked.

**Step 1** — Generate the presigned URL and redirect output to a temporary file:
```bash
aliyun ossutil presign \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --expires-duration 1h \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe > /tmp/_presign_url.txt
```

**Step 2** — Create a probe script that reads the URL from the file and runs the download probe:
```bash
cat > /tmp/_run_presign_probe.sh << 'PROBE_SCRIPT'
#!/bin/bash
PRESIGN_URL=$(cat /tmp/_presign_url.txt)
aliyun ossutil probe \
  --download \
  --url "$PRESIGN_URL" \
  "<LOCAL_PATH_IF_USER_WANTS_TO_RENAME>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
PROBE_SCRIPT
bash /tmp/_run_presign_probe.sh
```

> **Important — you MUST use `probe --download --url` with the presigned URL**:
> - **Never** copy-paste the full presigned URL directly into the `--url` parameter — use the file+script pattern above so the URL is never exposed in command history or execution logs.
> - If `/tmp/` is not writable, use the current workspace directory for the temporary file and script instead.

`--url` only accepts HTTP/HTTPS URLs — it cannot take `oss://bucket/object`.

- A successful `ossutil presign` only means the signed URL was generated; it does not guarantee the bucket or object exists, nor that the subsequent download will succeed.
- If you need to log the execution, do not persist the full presigned URL; at most keep the object address without the query string, or redact all signature parameters after `?`.
- If `probe --download --url` returns 404/403, quote the raw HTTP error first; if the bucket/object was already confirmed input, you may do one `ossutil stat` validation with the same `bucket + object + region`. Do not try to "guess" the root cause by listing buckets, trying random regions, or reading local credential files.

#### C. Download probe via Bucket/Object

- If the user confirmed `object_name`, the command will download that object directly.
- If the user does not provide `object_name`, `probe` will create a temporary object, download it, and delete the temporary object after completion.

```bash
aliyun ossutil probe \
  --download \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME_IF_ANY>" \
  --addr "<ADDR_IF_CONFIRMED>" \
  "<LOCAL_PATH_IF_USER_WANTS_TO_RENAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

- If the command reports `NoSuchBucket`, `NoSuchKey`, or other object-level errors, prefer running `ossutil stat "oss://<BUCKET_NAME>/<OBJECT_NAME>" --region "<REGION_ID_IF_NEEDED>"` for same-target validation.
- Do not list all buckets, try unconfirmed regions, or switch to `aliyun oss api` / `GetBucketLocation` or other commands outside this skill's scope to confirm whether the object exists.

#### D. Local symlink anomaly probe

This mode only checks local directory/file paths — it does not access OSS.

```bash
aliyun ossutil probe \
  --probe-item cycle-symlink \
  "<LOCAL_DIRECTORY_OR_FILE>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

- If the command returns `stat <path>: no such file or directory`, explicitly state that the local path does not exist in the current execution environment; this is still a local-only flow with no OSS access.
- **When the local path does not exist, you must NEVER**:
  - Interpret it as "this is a containerized/sandbox environment limitation"
  - Automatically rewrite it as "the user should run on another machine/production environment"
  - Generate a script file saying "run this command in the correct environment"
  - Check the parent directory with `ls` and then give up

  **Correct approach**: Quote the raw error `stat <path>: no such file or directory`, explicitly tell the user the path does not exist in the current environment, and ask whether they provided the correct path. Unless the user proactively states the current session is not on the target machine, do not make that judgment for them.

When reporting results of this probe, include at minimum:
- This is a local-only flow — no OSS access occurred
- Which symlinks are abnormal and which link chains were **directly verified**; if only partial chains can be verified, clearly distinguish "confirmed chain segments" from "anomaly points proven by probe errors", e.g. `loop-b -> loop-a`, and resolving `loop-a` reports `too many levels of symbolic links`
- If the probe output contains raw errors, quote at least one key error, e.g. `too many levels of symbolic links`
- Minimum fix prerequisites, e.g. break one of the cyclic links or re-point the abnormal link to a real target before retrying

If you need to clarify the abnormal link chain, you may perform read-only local forensics on the same path (e.g. `readlink`, `stat -f "%N -> %Y"`). Only write precise chains when these supplementary results are actually readable; if the supplementary forensics itself fails, report only verified segments — do not fabricate a complete cycle.

If the output lists abnormal symlinks, the user or a local script must fix them according to business semantics; this skill does not auto-rewrite symlink targets.

#### E. Upload bandwidth probe with suggested concurrency

Basic command:
```bash
aliyun ossutil probe \
  --probe-item upload-speed \
  --bucket "<BUCKET_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

To limit runtime, add:
```bash
aliyun ossutil probe \
  --probe-item upload-speed \
  --bucket "<BUCKET_NAME>" \
  --runtime "<RUNTIME_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

Successful output will contain `suggest parallel is <N>`.

#### F. Download bandwidth probe with suggested concurrency

- `object_name` is required.
- Official recommendation: target object should be larger than 5 MiB.
- If the user has no suitable object, first confirm a local file path, then upload a cleanable test object via `aliyun ossutil cp`.

Optional preparation step:
```bash
aliyun ossutil cp \
  "<LOCAL_FILE_TO_UPLOAD>" \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

Run download bandwidth probe:
```bash
aliyun ossutil probe \
  --probe-item download-speed \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --runtime "<RUNTIME_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

#### G. Download time probe

Basic command:
```bash
aliyun ossutil probe \
  --probe-item download-time \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

To explicitly control concurrency and part size, add:
```bash
aliyun ossutil probe \
  --probe-item download-time \
  --bucket "<BUCKET_NAME>" \
  --object "<OBJECT_NAME>" \
  --parallel "<PARALLEL_IF_CONFIRMED>" \
  --part-size "<PART_SIZE_IF_CONFIRMED>" \
  --region "<REGION_ID_IF_NEEDED>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

`--parallel` and `--part-size` are only meaningful in the `download-time` scenario; do not misuse them with `upload-speed`.

### 3. Interpret the output

- When upload/download probes succeed, the output will contain `upload file:success` or `download file:success`
- When bandwidth probes succeed, the output will contain multiple `parallel:<N>` statistics and `suggest parallel is <N>`
- When download time probes succeed, the output will contain `total bytes`, `cost`, `avg speed`
- All probe modes typically generate a `logOssProbe*.log` local log file; **after probe execution, you must check whether `logOssProbe*.log` was generated in the current directory** and report the log path in the final answer
- If a real command returns an error or has no success marker, the final conclusion must **explicitly state failure/blocked and quote the raw error message** — do not write "task completed successfully" or describe a failure as successful verification
- When a command fails, the final answer must explicitly state the **termination reason** (e.g. "stopped due to AccessDenied", "stopped due to path not found") — do not end silently
- For errors like `The bucket you are attempting to access must be addressed using the specified endpoint`, this only means the current access endpoint does not match the bucket's requirements; **stop immediately**, ask the user to confirm the correct region/endpoint — do not infer or try other region/endpoints on your own

See `references/verification-method.md` for more detailed verification steps.

## Success Verification Method

Follow the steps in `references/verification-method.md` to confirm each item:

1. CLI version and profile are valid
2. Probe output contains success markers or suggested concurrency
3. **You must run `ls logOssProbe*.log` to check whether log files were generated locally**, and report the log path in the final answer; if no log files were generated, it means the probe may not have reached the actual probing stage
4. If an explicit test object was used, confirm whether it should be retained or enter the cleanup step
5. If any of the above steps fail, the final answer must explicitly state **failure** and quote the raw error with termination reason

## Cleanup

- Upload/download connectivity probes without an explicit `--object` will auto-clean temporary objects
- If you explicitly uploaded a test object in the `download-speed` preparation step, decide whether to delete it based on user confirmation after probing

Delete an OSS test object:
```bash
aliyun ossutil rm \
  "oss://<BUCKET_NAME>/<OBJECT_NAME>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-network-probe
```

If a temporary test file was downloaded locally, it should also be deleted or retained based on user confirmation.

After all probe and cleanup steps are finished, disable AI safety mode:
```bash
aliyun configure ai-mode disable
```

## API and Command Tables

For all commands, underlying OSS capability mappings, and which steps are local client-side logic only, see `references/related-apis.md`.

## Best Practices

1. Always use `aliyun ossutil probe` — do not fabricate non-existent commands like `aliyun oss api probe`
2. Confirm all user-variable parameters before execution, especially `bucket_name`, `object_name`, `download_url`, `local_path`
3. Only retain probe objects when the user explicitly confirms; otherwise prefer temporary objects or explicit cleanup
4. For `download-speed`, choose a real object larger than 5 MiB for more stable results
5. In proxy, dedicated line, or custom domain scenarios, explicitly confirm `--addr`, `--region`, `--endpoint`
6. Use `suggest parallel is <N>` as an empirical baseline, then do small-scale validation combined with actual business concurrency
7. For `cycle-symlink`, only diagnose — do not auto-fix
8. After command failure, prefer same-target validation (e.g. `ossutil stat`) — do not expand into listing buckets, guessing regions, trying unsupported flags, or reading local credential files
9. Do not expose AK/SK, STS tokens, or full presigned URL query strings in logs or final results
10. A successful presign, resolvable DNS, or reachable ping/traceroute does not guarantee the object exists or that the probe will succeed; conclusions must be based on actual probe/validation results

## Reference Links

| Reference | Purpose |
| --- | --- |
| `references/cli-installation-guide.md` | Installing and upgrading Aliyun CLI |
| `references/verification-method.md` | Checking success by probe mode |
| `references/related-apis.md` | Command to underlying OSS capability/permission mapping |
| `references/ram-polices.md` | RAM permission checklist and policy examples |
| `references/acceptance-criteria.md` | Skill acceptance criteria and counter-examples |
| `references/implementation-boundaries.md` | Boundaries that cannot be fully automated via CLI or code |
