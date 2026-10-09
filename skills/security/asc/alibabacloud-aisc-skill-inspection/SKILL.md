---
name: alibabacloud-aisc-skill-inspection
description: "使用阿里云 AISC 做 Skill 安全检查：提交扫描、查询 rootTaskId、解读 check-report.json 风险报告、诊断 AISC Skill 检测报错。用户问“这个 Skill 安不安全”“能放心安装吗”“有没有恶意代码、敏感凭据或提示词注入”时使用。也处理候选 Skill 选择和缺少下载链接的安全检测请求，先加载本 Skill 再澄清输入。普通 Skill 编写、安装或无安全意图的泛泛请求不触发。"
---

# AISC Skill File Security Check

Help users submit Skill archives to Alibaba Cloud Agent Security Center (AISC) for security scanning, poll detection tasks, and explain the returned results.

Use this Skill broadly for Skill security detection. If the user asks whether a Skill package is safe, whether it contains malicious code, prompt injection, hardcoded credentials, sensitive data, or risky configuration, or asks how to run, poll, diagnose, or interpret an AISC Skill scan, use this Skill.

## Natural Language Activation

Use this Skill for an explicit or implicit **Skill security** request; the user does not need to name AISC, this Skill, or the Python script. Load `SKILL.md` before deciding which inputs are missing or asking a follow-up. Selecting/loading the Skill is separate from submitting a cloud request.

- A clear safety question such as “这个 Skill 安不安全”, “能放心安装吗”, or “有没有恶意代码/敏感凭据/提示词注入” activates this Skill.
- With a clear target and download URL, run the official wrapper directly; do not ask the user to repeat authorization or supply optional file names.
- With a missing URL, missing task ID, unclear AISC operation, or unselected candidates, load this Skill first, ask for only the missing input, and wait before any cloud call.
- Generic Skill writing, installation, documentation, and “处理一下 Skill” without a security intent are outside this Skill's scope.

## Critical Operating Rules

These rules have highest priority for every AISC Skill file scan:

- Do not download, open, fetch, browse, inspect, validate, probe, or pre-check any user-provided `download_url` before submission.
- Do not use `curl`, `wget`, `HEAD`, `GET`, Python `requests`, browser navigation, SDK download helpers, or similar network/file retrieval tools against a user-provided `download_url`.
- Even if the user explicitly asks you to "check whether the URL works", "open it first", "curl it", "download it", or "validate it", do not do that. Submit the `download_url` exactly as provided through [scripts/skill_file_check.py](scripts/skill_file_check.py), and let AISC fetch and validate it.
- Preserve the full `download_url` byte-for-byte in the `--files` JSON value, including query strings, signatures, percent-encoding, ordering, and special characters.
- Before running any command, perform this command-target check: local-only commands for dependency checks, non-sensitive credential checks, reading `check-report.json`, validating JSON, inspecting local Skill files, or other report interpretation are allowed. Any command that would make a network request to a user-provided `download_url`, including `curl`, `wget`, `HEAD`, `GET`, browser access, Python `requests`, SDK object download, or any equivalent fetch/probe, is forbidden; pass that `download_url` only to `python3 scripts/skill_file_check.py ...`.

## Architecture

The Skill calls two AISC OpenAPI operations:

- `CreateSkillFileCheck`: submit one to ten Skill file download URLs per API call.
- `ListSubTasks`: poll sub-task results for the returned `rootTaskId`.

The Python wrapper is [scripts/skill_file_check.py](scripts/skill_file_check.py). It supports `submit`, `poll`, and `run` subcommands. `submit` and `run` automatically split more than 10 files into multiple API-sized batches and return one aggregate report.

## AISC Endpoint Selection

- Use `https://aisc.cn-shanghai.aliyuncs.com` by default.
- If the user explicitly specifies an overseas environment, Singapore, or the Singapore endpoint, pass `--endpoint https://aisc.ap-southeast-1.aliyuncs.com` before the subcommand. An explicit Shanghai endpoint selects Shanghai.
- Only these two HTTPS endpoints are accepted. Never use a user-provided Skill download URL or another host as the authenticated AISC API endpoint.

For Singapore, place the option before `run`, `submit`, or `poll`: `python3 scripts/skill_file_check.py --endpoint https://aisc.ap-southeast-1.aliyuncs.com run --files '...'`.

## URL Handling Rules

- Never download Skill files locally.
- Never pre-validate, pre-check, or pre-flight URLs with `HEAD`, `GET`, `curl`, `wget`, `requests`, or similar tools.
- Always pass user-provided `download_url` values to AISC as-is, including signatures, query strings, percent-encoded characters, and other special characters.
- When a URL contains query parameters or a signature, copy the entire URL byte-for-byte into the `download_url` JSON value. Do not decode `%2F`, normalize `=`, drop query keys, sort query parameters, or visit the URL first.
- URLs shown in this document are syntax examples only. Never treat an example URL from `SKILL.md`, references, or code comments as user input for a real scan.
- If AISC cannot fetch a URL, report the API error honestly and remind the user to fix the URL when convenient. Do not force the user to correct it before completing the response.
- `rootTaskId` is useful only when at least one file upload is accepted by AISC.

## Installation

```bash
python3 -m pip install -r scripts/requirements.txt
```

Dependencies are declared in [scripts/requirements.txt](scripts/requirements.txt).

## Authentication

Alibaba Cloud credentials must come from the default credential chain used by `alibabacloud_credentials`.

Security rules:

- Never read, echo, print, or ask the user to paste credential values.
- Never put AccessKey, AccessKeySecret, STS token, or passwords in prompts, logs, command lines, reports, or final answers.
- If credentials are missing, ask the user to configure credentials outside this conversation and rerun the scan after credentials are available.
- Credential secrecy applies to all intermediate tool output as well as final answers. Do not print credential values to stdout/stderr, debug logs, markdown artifacts, JSON reports, or chat.
- Do not write custom credential-inspection scripts. Never print, serialize, inspect, or expose `CredentialClient`, credential objects, config objects, `os.environ`, `env`, `printenv`, `access_key_id`, `access_key_secret`, `security_token`, `AccessKeyId`, `AccessKeySecret`, or `SecurityToken` values. Forbidden examples include `vars(...)`, `.__dict__`, `dir(...)`, `repr(...)`, `to_map()`, `get_credential()`, or any inline Python/shell command whose purpose is to reveal credential fields.
- The only allowed credential check is a non-sensitive presence check that constructs the default credential client and prints a fixed success/failure marker, never the credential object or any of its fields.

Optional non-sensitive credential presence check:

```bash
python3 -c "from alibabacloud_credentials.client import Client as CredentialClient; CredentialClient(); print('Credentials OK')"
```

If that exact style of check fails, report that the default credential chain is unavailable and stop. Do not add extra debugging that displays credential internals.

## RAM Permissions

Required permissions:

- `aisc:CreateSkillFileCheck` for `CreateSkillFileCheck`.
- `aisc:ListSubTasks` for `ListSubTasks`.

When an API call fails with a permission error, tell the user that both permissions are required and refer to [references/ram-policies.md](references/ram-policies.md). Pause the scan until the user confirms the permissions are available.

## Parameter Handling

Required input:

- `Files[].download_url`: public download URL of a real Skill archive: ZIP, TAR, or GZIP-compressed TAR (`.tar.gz`/`.tgz`). Pass it as-is to AISC. A raw `SKILL.md`, HTML page, or JSON download descriptor is not a supported archive. The backend validates content, so changing `file_name` to end in `.zip` does not make an unsupported file valid. An archive may have a signed or extensionless download URL; never fetch or reject it solely by its URL suffix.

Optional input:

- `Files[].file_name`: display file name. If omitted, [scripts/skill_file_check.py](scripts/skill_file_check.py) infers it from the URL path.
- `--interval`: polling interval in seconds. Default is `10`.
- `--timeout`: polling timeout in seconds. Default is `600`.

Input rules:

- Do not ask for redundant confirmation when the user has provided one or more URLs and clearly asks to run the scan.
- Do not ask only for an optional `file_name`; infer it from the URL path when the user omitted it.
- If the user explicitly provides or requests a `file_name`, preserve that `file_name` exactly in the `--files` JSON. Do not replace it with an inferred name.
- Ask a clarification question when the required URL is missing, the intent is too unclear to know whether the user wants Skill security detection, multiple candidate files are mentioned without a clear target, or the user explicitly asks you to confirm parameters before execution.
- If more than 10 files are provided, do not ask the user to split or confirm batching. Pass all URLs to [scripts/skill_file_check.py](scripts/skill_file_check.py); it splits them into batches of at most 10, calls AISC for each batch, and returns one aggregate report.

## Scan Execution Contract

Use these rules for real AISC scans:

- Use the official wrapper exactly as the cloud interaction surface: `python3 scripts/skill_file_check.py ...`. Do not write alternate Python, shell, curl, SDK, credential-debugging, or retry scripts for AISC calls.
- Unless the user explicitly asks for `submit`/`poll` separately, use `run` for end-to-end scans and include `--output ./check-report.json`.
- If the user asks for a local JSON report, `check-report.json`, `poll.status`, task count, artifact verification, or any final answer based on report fields, always include `--output ./check-report.json` in the command and then read that JSON report.
- For separate submission, include `submit --output ./submit-report.json` and read that file before polling. The official `--output` option writes JSON separately from diagnostic stderr. Never use `2>&1 | tee ...json`, edit the official report, or create a replacement report to satisfy an artifact check. Diagnostic logs may be saved separately.
- If the user asks for two steps, first call `submit`, copy the returned `root_task_id` exactly, and call `poll --root-task-id <that exact id>` only when `success_count > 0` and the ID is non-empty. Do not use `run` for an explicit two-step request.
- If the user asks for a short timeout such as 20 seconds, pass `--timeout 20` to `run` or `poll`. On timeout, keep the returned `root_task_id` and tell the user to continue later with `poll --root-task-id <root_task_id>`.
- For one to ten files, submit all files in one `--files` JSON array. For more than ten files, still pass all files to the wrapper and let it batch internally.
- Final answers after scans must summarize `root_task_id` (or `rootTaskId`), `success_count`, `fail_count`, `poll.status`, and `total_tasks` with their real values, preferably in a short table. Include `root_task_ids` and `tasks` when present. Explain the meaning in Chinese; field names identify the source of the values. Read the official output rather than guessing counts from the number of inputs.
- If uploads all fail, report the actual upload counts and `root_task_id: null`; mark `poll.status` and `total_tasks` as unavailable / 未查询. `poll: null` does not prove there are zero backend tasks. A top-level `status: completed` in this branch only means the command stopped; say that the security scan did not complete. Never infer missing counts, task status, or risk conclusions.
- When the official script returns a nonzero exit or an error JSON, do not ask the user whether to retry. Give one final diagnostic answer using the standardized Error Handling mapping below and stop.

## Observability

The Skill version is the top-level non-empty string `version` in [references/manifest.json](references/manifest.json), currently `2026-01-01`. Read it from the manifest for every cloud client; do not hard-code a fallback version or derive it from frontmatter. If the manifest is missing, invalid JSON, or its version is missing, empty, not a string, or invalid for the User-Agent, stop before loading credentials or making the first cloud call and report the manifest error.

Generate one random 32-character lowercase hex session ID when starting work with this Skill. Reuse the same session ID for every `submit`, `poll`, and `run` command in that user request so all AISC API calls from one troubleshooting flow are correlated consistently. Pass it to scripts through `SKILL_SESSION_ID`.

The Python SDK sets user-agent to: **AlibabaCloud-Agent-Skills/alibabacloud-aisc-skill-inspection/{version}/{session-id}**

This is the exact user-agent template:

```text
AlibabaCloud-Agent-Skills/alibabacloud-aisc-skill-inspection/{version}/{session-id}
```

Replace `{version}` with the manifest version and `{session-id}` with the generated 32-character lowercase hex value. Both are required before any cloud call. Do not add extra prefixes, suffixes, timestamps, usernames, credentials, or per-command random values.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py run --files '...' --output ./check-report.json
```

The script automatically adds the session ID to the user-agent and never treats it as a secret.

## Core Workflow

### Step 1: Collect Input

Collect any number of Skill file URLs. Include `file_name` only when the user provides one or when a clearer name helps readability.

Hard stop: if the user did not provide a clear `download_url`, or the user's intent is too vague to know whether they want Skill security detection, do not submit or poll a cloud task. Loading this Skill and reading its instructions are allowed before clarification. Do not use sample URLs from this document or any placeholder as a substitute. Ask one clarification question for the target Skill file, public download URL, or intended AISC operation, then wait.

If the URL is present, continue directly. If the URL is missing, ask the user to provide a public Skill file download URL. If the request is too vague, ask what Skill security check target or operation they want. If multiple candidate Skills are mentioned without a clear target, ask the user which one to scan before executing.

### Step 2: Submit and Poll

For ordinary end-to-end checks, use the one-command flow:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py run \
  --files '[{"download_url":"https://example.org/user-provided-skill-package.zip","file_name":"user-provided-skill-package.zip"}]' \
  --output ./check-report.json
```

If the user provides more than 10 files, still use the one-command flow with all files in `--files`. The script will call `CreateSkillFileCheck` in batches of 10 and then output `total_batches`, `root_task_ids`, per-batch details, and a combined `poll` summary.

For step-by-step operation:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py submit --files '[...]' --output ./submit-report.json
SKILL_SESSION_ID={session-id} python3 scripts/skill_file_check.py poll --root-task-id <rootTaskId> --output ./check-report.json
```

Run `poll` only after `submit.success_count > 0` and a non-empty `root_task_id` exists. The value passed to `--root-task-id` must be copied exactly from submit stdout, without shortening, retyping from memory, or inventing a fallback. For multi-batch submissions, poll each returned `root_task_id`; the `run` subcommand performs this automatically.

Partial success handling:

- If some files succeed and some fail, poll only the successful files. Report failed file `error_msg` values and remind the user to fix those URLs. Do not block successful files.
- If all files fail, the script returns `status: "completed"`, `root_task_id: null`, and `poll: null`. Report the API errors and stop. Do not call `poll`, retry automatically, drop failed files to create a partial-success rerun, or ask the user to re-provide URLs.
- If AISC says a URL is invalid or unreachable, report that result. The Skill must not validate the URL before submission.
- If the file count exceeds 10, the script returns one aggregate report with multiple batches. Summarize total files, total batches, accepted files, failed uploads, `root_task_ids`, and combined poll status.
- If [scripts/skill_file_check.py](scripts/skill_file_check.py) exits nonzero or returns a non-retryable API/SDK error such as missing credentials, expired temporary security token, `permission`, `parameter`, `throttling`, `internal`, HTTP 503, or other service errors, stop the current attempt. Do not write custom retry code, do not switch to another script, do not reimplement AISC calls, and do not ask the user to refresh credentials inside the conversation. Read stdout/stderr or `check-report.json`, map the error using the Error Handling section, report it to the user, and stop.
- Transient network timeout during `ListSubTasks` polling may be retried by [scripts/skill_file_check.py](scripts/skill_file_check.py) within the configured `--timeout` window. Do not add a second custom retry loop outside the wrapper. If the wrapper returns `poll.status: "timeout"`, keep the returned `root_task_id` and tell the user they can continue later with `poll --root-task-id <root_task_id>`.

### Step 3: Interpret Results

Read `check-report.json` after the command finishes.

For each task:

- If a task has `task_status` other than `completed`, report that status before interpreting risks. If `risk_info` is missing because the backend task failed, say that no valid risk report was generated for that task.
- If `risk_info` is empty, say that AISC returned no risk findings for that file. Do not invent risk analysis or claim the file is absolutely safe.
- If risks are present, summarize the returned findings by priority: Virus, Sensitive, Guardrail, then Config.
- Provide remediation only for risks that actually appear in the report.
- For `Sensitive` findings, include practical remediation such as removing the sensitive material, rotating exposed credentials or tokens, and re-scanning after cleanup.
- Include `root_task_id` or `root_task_ids`, `poll.status`, task count, total batch count when applicable, and any failed upload messages when available.
- Copy every `root_task_id`, `rootTaskId`, and `root_task_ids` value exactly from script stdout or `check-report.json`. Do not manually retype, shorten, invent, or repair IDs. If the report value is `null`, say no task ID was created and do not provide a `poll --root-task-id` continuation command.

Use [references/result-interpretation-guide.md](references/result-interpretation-guide.md) for risk category meanings.

## Error Handling

Handle common failures as follows:

- Credentials not configured: classify the script output as `error_type: "credential"` and ask the user to configure credentials through the default credential chain outside this conversation.
- Expired temporary security token (`InvalidSecurityToken.Expired`, `SecurityToken is expired`, expired token): classify it as `error_type: "credential"` for the current attempt. Report the `error_code`, non-sensitive `request_id`, `root_task_id: null`, and that no AISC task was created. Stop without retrying and without asking the user to paste, refresh, or reconfigure credentials in-chat.
- Permission errors (`403`, `AccessDenied`, `NoPermission`, `permission`): say that the current credentials need `aisc:CreateSkillFileCheck` and `aisc:ListSubTasks`, reference [references/ram-policies.md](references/ram-policies.md), and stop until permissions are available.
- Parameter errors (`400`, `InvalidParameter`, `parameter`, missing `download_url`, invalid `--files`): explain that `--files` must be a JSON array of objects and every object must include `download_url`; show the expected shape without printing credentials.
- Throttling errors (`429`, `Throttling`, `TooManyRequests`, `rate limit`): explain that AISC is rate limiting the request and suggest retrying later or increasing `--interval`; do not loop or write custom retry code.
- Internal/system errors (`5xx`, `503`, `InternalError`, `ServiceUnavailable`, `internal`): report that AISC returned a service error, include the non-sensitive `RequestId` or error code if present, and suggest retrying later or contacting Alibaba Cloud support. Stop the current attempt.
- Transient network timeout while polling `ListSubTasks`: allow the official wrapper to retry until `--timeout`. If polling eventually times out, report `poll.status: "timeout"`, preserve `root_task_id`, and give the continuation command. If a timeout occurs while creating credentials or submitting the task and the script returns `error_type: "credential"` or another terminal error, report that terminal error instead of retrying.
- URL unreachable or rejected by AISC: report the API message and remind the user to fix the URL; do not pre-check, retry forever, or force correction.
- Unsupported archive (`文件格式错误，仅支持 ZIP、TAR 或 GZIP 压缩的 TAR`): explain that AISC requires a real archive containing the Skill files. A raw `SKILL.md` or renamed file is insufficient. Stop this attempt and report the actual error; do not change the URL, manufacture a ZIP result, or submit an example package as a replacement.
- All uploads failed: report each upload error and stop without polling.
- File count exceeds 10: submit through [scripts/skill_file_check.py](scripts/skill_file_check.py) and let the script split the files into batches of at most 10; never ask the user to confirm batching.
- Polling timeout: return the `root_task_id` and tell the user they can continue later with the `poll` subcommand.

## Success Verification

After an end-to-end scan:

- Confirm the script executed `run` or both `submit` and `poll`.
- Confirm `submit.success_count > 0` before treating `root_task_id` as usable. If `root_task_id` is `null`, explicitly state that no AISC task was created and stop instead of offering a polling command.
- A successful scan requires `submit.success_count > 0`, a real non-empty task ID, `poll.status` of `completed`, and completed backend tasks. A command exit code of zero, an accepted submission, or an all-upload-failed report does not establish a completed security scan. Report timeout/error and incomplete tasks explicitly.
- For more than 10 files, confirm `total_batches` and `root_task_ids` in the aggregate report instead of asking the user to split the files.
- Confirm `check-report.json` exists and is valid JSON when `--output ./check-report.json` was used.
- In the final response, include the exact strings `poll.status`, `total_tasks`, and `tasks` when the user asked about those report fields, because they are the stable report contract.

Example local verification:

```bash
python3 - <<'PY'
import json
d = json.load(open("check-report.json", encoding="utf-8"))
poll = d.get("poll") or {}
print({"status": poll.get("status"), "tasks": len(poll.get("tasks", []))})
PY
```

## Cleanup

This Skill does not create cloud resources. The local `check-report.json` report can be kept for audit or deleted by the user.

## References

- [references/ram-policies.md](references/ram-policies.md): RAM permission list.
- [references/result-interpretation-guide.md](references/result-interpretation-guide.md): detection result interpretation guide.
- [references/verification-method.md](references/verification-method.md): success verification methods.
- [scripts/skill_file_check.py](scripts/skill_file_check.py): Python SDK detection script.
