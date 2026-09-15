---
name: alibabacloud-flink-python-job-submission
description: Submit and operate PyFlink jobs on Alibaba Cloud Realtime Compute for Apache Flink. Use for storage-routed artifact upload, Python deployment creation or configuration updates, cross-session deployment recovery, state-aware start or stop, and JM/TM logs or metrics. Route deletion-only and SQL requests elsewhere.
---

# Flink Python Job Submission

## 1. Scope

Create a Python deployment from ready PyFlink code: upload its artifacts, fill
its deployment configuration, and verify the saved result.

For SQL or existing deployment operations (start, stop, update, status, logs,
metrics, or deletion), use **alibabacloud-flink-workspace-ops**. If available,
load that skill; otherwise point the user to installing it. Code development
belongs to **alibabacloud-flink-python-coding**.

## 2. Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for full installation instructions.

Before the first non-version `aliyun` command, apply the conversation-scoped
CLI initialization in section 7.

**Python SDK dependencies:**
```bash
pip3 install alibabacloud_tea_openapi alibabacloud_credentials \
  alibabacloud_tea_util alibabacloud_openapi_util \
  'alibabacloud_foasconsole20211028==2.2.1'
```

## 3. Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Yes (if not using CLI config) | Access Key ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Yes (if not using CLI config) | Access Key Secret |

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
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

## 5. RAM Policy

Creation permissions are listed below; the reference also includes workspace operations. See `references/ram-policies.md` for full list.

| Product | RAM Action | Purpose |
|---------|-----------|---------|
| RealtimeCompute | `stream:DescribeVvpInstances` | Detect workspace storage mode and retrieve its VVP console URL |
| RealtimeCompute | `stream:CreateDeployment` | Create Python deployment |
| RealtimeCompute | `stream:GetDeployment` | Verify newly created deployment |
| RealtimeCompute | `stream:ListEngineVersionMetadata` | List workspace-supported VVR engine versions |
| OSS (user-managed storage only) | `oss:PutObject` / `oss:GetObject` / `oss:ListObjects` | Upload, replace, and verify artifacts |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Create a Deployment

1. Resolve the exact region, workspace, and namespace from the user or explicit
   project configuration. If any is missing, ask for it and pause until the user
   supplies all three. This gate applies to every cloud discovery call, including
   workspace listing and engine queries; a partially known location stays pending.
2. Follow [storage routing](references/storage-routing.md) to discover the bound
   storage and console URL, upload the main artifact and dependencies, and verify
   each filename and size. Resolve exact-name conflicts with the user.
3. Use `scripts/flink_python_submit.py create-deployment --help` for the argument
   schema and [deployment configuration](references/create-deployment.md) for
   Python-specific choices. Present the resolved creation parameters together,
   including defaults that will be sent, and obtain approval before creation.
4. Create the deployment and read it back with `get-deployment`. Compare its
   Python artifact, dependencies, engine, queue, resources, and `flinkConf` with
   the approved values, allowing equivalent server normalization. Return the
   deployment ID, location, and a clickable VVP configuration link:

   ```text
   <consoleUrl>/web/<workspace>/zh/#/workspaces/<workspace>/namespaces/<namespace>/operations/stream/<deployment-id>/configuration
   ```

Use the exact `consoleUrl` from storage discovery. Creation is complete when
the saved configuration matches; runtime state is outside this workflow.

## 7. CLI Initialization and Observability

For each skill invocation, generate a fresh random 32-character lowercase hex
session ID and reuse it throughout that invocation. Before the first cloud API
call, read [manifest.json](references/manifest.json) and validate its `version`
as a non-empty string without whitespace. If the file is missing, unreadable,
invalid JSON, or has an invalid version, stop and report the error; do not guess
a version or make a cloud call.

Reuse successful CLI initialization already visible in the conversation. Before
the first non-version `aliyun` command, run each pending command once:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

Retry only a failed initialization command. Keep this state in the conversation.
For cloud OpenAPI CLI commands, include:

```text
--user-agent 'AlibabaCloud-Agent-Skills/alibabacloud-flink-python-job-submission/{session-id} skill-version/{version}'
```

Omit that flag for `ossutil` and local commands (`configure`, `plugin`, `version`).
For SDK script calls, supply the same session ID through the environment:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/flink_python_submit.py create-deployment ...
```

The SDK script validates the manifest before constructing either cloud client
and derives the same versioned user-agent from it.
