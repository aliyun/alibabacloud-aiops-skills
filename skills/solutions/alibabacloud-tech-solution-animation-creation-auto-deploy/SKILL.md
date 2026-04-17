---
name: alibabacloud-tech-solution-animation-creation-auto-deploy
description: |
  Alicloud Service Scenario-Based Skill. Use for auto-deploying the "Build AI Animation Story Creation App" solution.
  Automatically creates OSS Bucket, deploys FC application via Devs template, and stops at the experience page.
  Triggers: "AI动画创作", "animation creation", "动画故事部署", "deploy animation story app".
---

# Build AI Animation Story Creation App — Auto Deploy

Automatically deploy the Alibaba Cloud "Build AI Animation Story Creation App" solution. Deployment stops once the application is accessible — the hands-on experience is left to the user.

**Architecture:** `OSS Bucket + DashScope (Bailian API Key) + FC App (ComfyUI + WebUI — two functions deployed via Devs template)`
---

## Installation

> **Prerequisites (scripts/ runtime dependencies):**
>
> | Dependency | Min Version | Check Command | Purpose |
> |-----------|-------------|---------------|---------|
> | `bash` | 4.0+ | `bash --version` | Script runtime |
> | `aliyun` CLI | >= 3.3.7 | `aliyun version` | Alibaba Cloud resource operations (3.3.7+ required for `ai-mode` subcommand) |
> | `python3` | 3.6+ | `python3 --version` | JSON parsing |
> | `curl` | any | `curl --version` | HTTP API calls |
>
> If Aliyun CLI is not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

---

## CLI Initialization (MUST run before Core Workflow)

Enable AI-Mode, set the dedicated User-Agent, and update plugins so all subsequent CLI calls are tagged correctly and run on the latest plugin versions:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy"
aliyun plugin update
```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
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
> 2. Configure credentials **outside of this session**
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

See `references/ram-policies.md` for full permission list.

**Required system policies:** `AliyunFCFullAccess`, `AliyunOSSFullAccess`

**Additional permissions:** Devs-related permissions (`devs:CreateProject`, `devs:RenderServicesByTemplate`, `devs:UpdateEnvironment`, `devs:DeployEnvironment`, `devs:ListEnvironments`, `devs:GetEnvironment`)

**Before the Core Workflow, automatically check and attach required policies:**

```bash
bash scripts/attach-policies.sh
```

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> all parameters are either fixed values or auto-generated/created — no manual user input required.

| Parameter | Required | Description | Value |
|-----------|----------|-------------|-------|
| `RegionId` | Yes | Deployment region (FC and OSS in the same region) | **Fixed `cn-hangzhou`** |
| `BUCKET_NAME` | Yes | OSS Bucket name | Auto-generated `animation-story-<6 random lowercase letters>` |
| `API_KEY` | Yes | Bailian (DashScope) API Key | Auto-created via `aliyun modelstudio create-api-key` |
| `PROJECT_NAME` | Yes | Devs project name | Auto-generated `animation-creation-<6 random lowercase letters>` |

**Before starting the Core Workflow, set the following variables in the shell (all subsequent commands reference them directly):**

```bash
# Generate random names
BUCKET_NAME="animation-story-$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z' | head -c 6)"
PROJECT_NAME="animation-creation-$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z' | head -c 6)"
echo "BUCKET_NAME=$BUCKET_NAME, PROJECT_NAME=$PROJECT_NAME"
```

---

## Core Workflow

### Step 1: Create Bailian API Key (CLI)

Automatically obtain the workspace and create an API Key via `aliyun modelstudio` CLI:

```bash
source scripts/create-api-key.sh
```

> **Note:** Use `source` to ensure the `API_KEY` variable is exported to the current shell. The script automatically fetches the default workspace (or creates one if none exists), creates an API Key, and prints the full value.

### Step 2: Enable OSS Service and Create Bucket (CLI)

> **Note:** The OSS CLI plugin uses the `--ua` flag (not `--user-agent`) to set the User-Agent.

First enable OSS service (returns `ORDER.OPEND` if already enabled — can be ignored):

```bash
aliyun ossadmin open-oss-service --endpoint oss-admin.aliyuncs.com --force --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy 2>&1 || true
```

Create Bucket:

```bash
aliyun oss mb "oss://$BUCKET_NAME" --region cn-hangzhou --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

Verify:

```bash
aliyun oss stat "oss://$BUCKET_NAME" --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

### Step 3: Create Devs Project (CLI)

Use the `CreateProject` API to create a project. Specify the template name and parameters via `templateConfig` — Devs will automatically create a `production` environment.

> **Note:** CreateProject only creates the project and an empty environment — it does NOT trigger deployment automatically. You must follow up with RenderServicesByTemplate + UpdateEnvironment + DeployEnvironment to complete deployment.

```bash
aliyun devs create-project --body "{
  \"name\": \"$PROJECT_NAME\",
  \"spec\": {
    \"templateConfig\": {
      \"templateName\": \"animation-creation\",
      \"parameters\": {
        \"region\": \"cn-hangzhou\",
        \"bailian_api_key\": \"$API_KEY\",
        \"ossBucket\": \"$BUCKET_NAME\"
      }
    }
  }
}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

> **Template parameter notes (confirmed — do not modify):**
> - `region`: Fixed `cn-hangzhou`
> - `bailian_api_key`: Bailian API Key auto-created in Step 1
> - `ossBucket`: OSS Bucket name created in Step 2 (without `oss://` prefix)
> - All parameters are passed via `parameters`, **not** `variableValues`

### Step 4: Render Template and Configure Environment (CLI)

> **All commands in this step use shell variables `MY_UID`, `PROJECT_NAME`, `BUCKET_NAME`, `API_KEY` — make sure Step 1 and Parameter Confirmation have been executed.**

First obtain the current user UID and check the role trust policy:

```bash
source scripts/setup-role.sh
```

> **Note:** Use `source` to ensure the `MY_UID` variable is exported to the current shell. The script automatically checks whether the role exists and creates it if not. This role is the standard Devs role, typically auto-created when using the FC console's application feature for the first time.

#### 4a. Render Template → Build JSON → Update Environment (all-in-one script)

> **The following script automatically: renders the template → filters out custom-domain → adds roleArn → calls UpdateEnvironment.** The agent does not need to handle JSON manually.

```bash
bash scripts/render-and-update.sh
```

> **Key notes (built into the script — no manual handling needed):**
> - `custom-domain` service is automatically filtered out (causes "Unknown service type" error)
> - `roleArn` is automatically added
> - Uses `--body` to pass data (`--spec` cannot correctly pass deeply nested JSON)

#### 4b. Trigger Deployment

> **Built-in rate-limit protection:** The script retries up to 3 times with 60-second intervals, and stops immediately on 404. **Run the script directly — do not call `deploy-environment` manually.**

```bash
bash scripts/deploy-environment.sh
```

### Step 5: Poll Deployment Status

Deployment is asynchronous — poll until complete (typically takes 5–15 minutes). **Run the following script directly:**

```bash
bash scripts/poll-deploy-status.sh
```

### Step 6: Create Custom Domain

> **Why is a custom domain needed?** FC trigger URLs (`*.fcapp.run`) force a `Content-Disposition: attachment` response header, causing the browser to download the HTML instead of rendering it. A custom domain (`*.devsapp.net`) is required for the application to work properly.

> **Must use FC 2.0 API (`aliyun fc-open`)** to create the helper function: FC 3.0 does not support `$` in function names. The `fc-open` plugin will be auto-installed via the `--auto-plugin-install true` configuration.

**Run the following complete script directly (only `MY_UID` and `PROJECT_NAME` variables need to be set):**

```bash
bash scripts/create-custom-domain.sh
```

### Step 7: Get Access URL (stop here)

The access URL is automatically printed at the end of the Step 6 script. Format:

```text
http://${PROJECT_NAME}-web.fcv3.${MY_UID}.cn-hangzhou.fc.devsapp.net/
```

**Stop here. Provide the access URL from Step 6 output to the user and let them experience the app on their own. Do not operate the application on behalf of the user.**

> **⚠️ 安全提醒 — 展示访问 URL 时必须告知用户：**
> 该 URL 可通过公网直接访问，请勿随意分享给不信任的人。未经授权的访问可能导致：
> - **云资源被消耗：** 每次访问都会消耗函数计算资源和百炼 API 调用额度，可能产生额外费用。
> - **隐私信息泄露：** 生成的动画故事、上传的图片等内容可能包含个人或敏感信息。

---

## Cleanup

To clean up deployed resources, delete in the following order (requires `PROJECT_NAME`, `MY_UID`, `BUCKET_NAME`, `API_KEY_ID` variables):

```bash
# 1. Delete FC custom domain
aliyun fc delete-custom-domain --domain-name "${PROJECT_NAME}-web.fcv3.${MY_UID}.cn-hangzhou.fc.devsapp.net" --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 2. Delete Devs project (also deletes associated FC functions; --force true skips environment resource check)
aliyun devs delete-project --name "$PROJECT_NAME" --force true --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 3. Delete OSS Bucket (recursively delete all objects first, then delete the Bucket)
aliyun oss rm "oss://$BUCKET_NAME" -r -f --region cn-hangzhou --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
aliyun oss rm "oss://$BUCKET_NAME" -b -f --region cn-hangzhou --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# 4. Delete Bailian API Key (API_KEY_ID is output during create-api-key.sh execution)
aliyun modelstudio delete-api-key --api-key-id "$API_KEY_ID" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

---

## Workflow Teardown

After the workflow completes (or after Cleanup), disable AI-Mode:

```bash
aliyun configure ai-mode disable
```

---

## Cannot-via-CLI/SDK Summary

See `references/related-commands.md` for full CLI command reference.

> **Key limitation:** First-time activation of FC has no CLI/API support — users must activate it manually in the console.
>
> **Auto-activated:** OSS service via `aliyun ossadmin open-oss-service` (built into Step 2). Bailian workspace via `aliyun modelstudio create-workspace` (built into Step 1).

---

## Best Practices

1. Region is fixed to `cn-hangzhou` (FC and OSS in the same region)
2. DashScope API Key is passed via Devs template parameters — not hardcoded
3. OSS Bucket names include a random suffix to avoid conflicts
4. Record the access URL and created resources after deployment completes

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/related-commands.md](references/related-commands.md) | CLI/SDK command reference |
| [references/verification-method.md](references/verification-method.md) | Deployment verification steps |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
