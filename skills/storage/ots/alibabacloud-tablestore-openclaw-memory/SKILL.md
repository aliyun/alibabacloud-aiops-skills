---
name: alibabacloud-tablestore-openclaw-memory
description: |
  This skill installs and configures the **Tablestore Mem0** plugin for OpenClaw.
  Tablestore Mem0 uses Alibaba Cloud Tablestore as the vector store backend for mem0, providing persistent long-term memory for AI agents.
  Use this skill when the user wants OpenClaw to persist or manage long-term memory using Alibaba Cloud Tablestore as the backend.
  Triggers: "set up tablestore memory", "install tablestore mem0 plugin", "configure long-term memory with tablestore", "remember this".
---

## Prerequisites

The user must have:

1. An **Alibaba Cloud account**
2. **Credentials** — **AccessKey ID + Secret** (with `AliyunOTSFullAccess` permission) or **ECS RAM Role** (recommended on ECS)
3. An **阿里云百炼 API Key** (for Qwen LLM and embedding)
4. Optional: existing Tablestore instance endpoint + instance name (otherwise auto-created)
5. Optional: **region ID** for auto-provisioning (defaults to `cn-hangzhou`)

> 📋 **RAM Permissions:** See [references/ram-policies.md](references/ram-policies.md) for the complete list of required API permissions.

---

## Definition of Done

This task is NOT complete until all of the following are true:

1. User has provided credentials
2. Plugin is installed (version 0.8.2)
3. `openclaw.json` is configured correctly
4. OpenClaw is restarted
5. Setup is verified (plugin loads without errors)

---

## Onboarding

### Step 0 — Collect credentials

`[AGENT]` Ask the user:

> To set up Tablestore Mem0, I need:
>
> **Required:**
> 1. Alibaba Cloud **AccessKey ID**
> 2. Alibaba Cloud **AccessKey Secret**
> 3. **阿里云百炼 API Key**
>
> **Optional (if you have an existing Tablestore instance):**
> 4. Tablestore **endpoint** (e.g. `https://my-instance.cn-hangzhou.ots.aliyuncs.com`)
> 5. Tablestore **instance name**
>
> If you don't provide an endpoint and instance name, I'll automatically create a new Tablestore instance. In that case, I need:
> 6. **Region ID** (e.g. `cn-hangzhou`, `cn-shanghai`)

Ask the user:

> **Question 1 — Authentication:** How would you like to authenticate?
> - **Option A: ECS RAM Role** (recommended on ECS) — Provide the **role name**.
> - **Option B: AccessKey** — Provide AccessKey ID and Secret.
>
> **Question 2 — Tablestore instance:** Do you already have a Tablestore instance?
> - **Yes** → Provide endpoint and instance name.
> - **No** → Provide region ID for auto-provisioning.

⚠️ **HIGH-RISK OPERATION — Pre-flight Confirmation:**

If the user answers **No**, the agent MUST:

1. **Explicit Confirmation:**
   > ⚠️ This setup will **create a new Tablestore instance** in your Alibaba Cloud account.
   > - Instance type: VCU (pay-as-you-go, typically under ¥1/month)
   > - Region: as specified
   > **Do you confirm?** (yes/no)

2. **Double-check:**
   > Please verify in Tablestore Console (`https://ots.console.aliyun.com/`) that you don't have existing instances.

Do **NOT** proceed until the user explicitly confirms.

**If the user is missing credentials, point them to:**
- Alibaba Cloud sign-up: `https://account.alibabacloud.com/register/intl_register.htm`
- AccessKey creation: `https://ram.console.aliyun.com/manage/ak`
- 阿里云百炼 API Key: `https://dashscope.console.aliyun.com/apiKey`

#### Setting up ECS RAM Role (if the user chose Option A)

1. **Attach a RAM role to the ECS instance** — [Documentation](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance)
2. **Grant the role `AliyunOTSFullAccess`** — [Reference](https://help.aliyun.com/zh/tablestore/developer-reference/access-tablestore-by-ram-user)

### Step 1 — Install plugin

**Plugin version: `0.8.2`**

⚠️ **External Package Installation Notice:**

> This skill will install `@tablestore/openclaw-mem0@0.8.2` from npm registry. By proceeding, you acknowledge installing an external package.
> **Do you consent?** (yes/no)

Wait for user confirmation, then:

```bash
NPMJS_TIME="$(curl -o /dev/null -sS --connect-timeout 2 --max-time 6 -w '%{time_total}' https://registry.npmjs.org/@tablestore%2fopenclaw-mem0 || echo timeout)"
MIRROR_TIME="$(curl -o /dev/null -sS --connect-timeout 2 --max-time 6 -w '%{time_total}' https://registry.npmmirror.com/@tablestore%2fopenclaw-mem0 || echo timeout)"

if [ "$MIRROR_TIME" != "timeout" ] && { [ "$NPMJS_TIME" = "timeout" ] || awk "BEGIN { exit !($NPMJS_TIME > 2 && $MIRROR_TIME < $NPMJS_TIME) }"; }; then
  echo "Using China npm mirror"
  NPM_CONFIG_REGISTRY=https://registry.npmmirror.com openclaw plugins install @tablestore/openclaw-mem0@0.8.2
else
  openclaw plugins install @tablestore/openclaw-mem0@0.8.2
fi
```

If `extract tar timed out`, fallback to manual install:
```bash
cd /tmp && npm pack @tablestore/openclaw-mem0@0.8.2
mkdir -p /tmp/openclaw-mem0-install
tar xzf /tmp/tablestore-openclaw-mem0-*.tgz -C /tmp/openclaw-mem0-install --strip-components=1
openclaw plugins install /tmp/openclaw-mem0-install
```

### Step 2 — Detect OpenClaw version

```bash
openclaw --version
```

- Version `>= 2.2.0` → use **Step 3A**
- Version `< 2.2.0` → use **Step 3B** (remove `.plugins.allow` line)

### Step 3 — Configure openclaw.json

Detect config file path:
```bash
OPENCLAW_CONFIG="$(openclaw config file 2>/dev/null | head -1)"
OPENCLAW_CONFIG="${OPENCLAW_CONFIG/#\~/$HOME}"
echo "Config file: $OPENCLAW_CONFIG"
```

⚠️ **Credential Security (REQUIRED):**

**ALWAYS prefer environment variables:**
```bash
export TABLESTORE_ACCESS_KEY_ID="<your-access-key-id>"
export TABLESTORE_ACCESS_KEY_SECRET="<your-access-key-secret>"
export DASHSCOPE_API_KEY="<your-dashscope-api-key>"
```

⚠️ **Input Validation (REQUIRED):**

| Input | Validation Rule |
|-------|-----------------|
| AccessKey ID | Regex: `^LTAI[Nt][A-Za-z0-9]{12,20}$` |
| AccessKey Secret | Alphanumeric, ~30 chars |
| Region ID | Regex: `^cn-[a-z]+(-[0-9]+)?$` or `^[a-z]+-[a-z]+-[0-9]+$` |
| Endpoint | Regex: `^https://[a-z0-9-]+\.[a-z0-9-]+\.ots\.aliyuncs\.com$` |
| Instance Name | Regex: `^[a-z][a-z0-9-]{0,19}$` |

⚠️ **Embedder/LLM provider MUST be `"openai"` with baseURL `"https://dashscope.aliyuncs.com/compatible-mode/v1"`, NOT `"dashscope"`.**

#### Step 3A — OpenClaw ≥2.2.0

| Auth method | Has existing instance? | `vectorStore.config` fields |
|-------------|----------------------|----------------------------|
| AccessKey | No | `accessKeyId`, `accessKeySecret`, `regionId` |
| AccessKey | Yes | `accessKeyId`, `accessKeySecret`, `endpoint`, `instanceName` |
| ECS RAM Role | No | `roleName`, `regionId` |
| ECS RAM Role | Yes | `roleName`, `endpoint`, `instanceName` |

Template (AccessKey auth + auto-create):
```bash
jq '
  .plugins.slots.memory = "openclaw-mem0" |
  .plugins.entries["openclaw-mem0"] = {
    enabled: true,
    config: {
      mode: "open-source",
      oss: {
        vectorStore: {
          provider: "tablestore",
          config: {
            accessKeyId: "${TABLESTORE_ACCESS_KEY_ID}",
            accessKeySecret: "${TABLESTORE_ACCESS_KEY_SECRET}",
            regionId: "cn-hangzhou"
          }
        },
        embedder: {
          provider: "openai",
          config: {
            apiKey: "${DASHSCOPE_API_KEY}",
            model: "text-embedding-v3",
            baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1"
          }
        },
        llm: {
          provider: "openai",
          config: {
            apiKey: "${DASHSCOPE_API_KEY}",
            model: "qwen-plus",
            baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1"
          }
        }
      }
    }
  } |
  .plugins.allow = ((.plugins.allow // []) + ["openclaw-mem0"] | unique)
' "$OPENCLAW_CONFIG" > /tmp/openclaw-tmp.json && mv /tmp/openclaw-tmp.json "$OPENCLAW_CONFIG"
```

For **existing instance**: replace `regionId` with `endpoint` and `instanceName`.
For **ECS RAM Role**: replace `accessKeyId`/`accessKeySecret` with `roleName`.

#### Step 3B — OpenClaw <2.2.0

Same as Step 3A but remove the `.plugins.allow` line.

### Step 4 — Restart OpenClaw

```bash
openclaw gateway restart
```

Wait ~1 minute for the gateway to restart.

### Step 5 — Verify setup

```bash
openclaw mem0 stats
```

Success criteria: plugin loads without errors, shows mode and memory count.

### Step 6 — Handoff

```
✅ Tablestore Mem0 is ready.

Your memory is now backed by Alibaba Cloud Tablestore.
The plugin will automatically recall relevant memories before each conversation
and capture key facts after each conversation.

Manual commands: "remember this" / "what do you know about me?" / "forget that"

Configuration: Tablestore vector store + 阿里云百炼 text-embedding-v3 + Qwen-Plus
Instance: <auto-created or user-provided>

Security: Prefer ECS RAM Role on ECS. Never commit credentials to version control.
```

---

## Configuration Reference

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `accessKeyId` | No* | — | AccessKey ID (or env `TABLESTORE_ACCESS_KEY_ID`) |
| `accessKeySecret` | No* | — | AccessKey Secret (or env `TABLESTORE_ACCESS_KEY_SECRET`) |
| `roleName` | No* | — | ECS RAM Role name (or env `TABLESTORE_ROLE_NAME`) |
| `endpoint` | No | Auto-created | Tablestore instance endpoint |
| `instanceName` | No | Auto-created | Tablestore instance name |
| `regionId` | No | `cn-hangzhou` | Region for auto-provisioning |
| `tableName` | No | `mem0_vectors` | Data table name |
| `dimension` | No | `1024` | Vector dimension |

*Required unless `roleName` is set.

### Auto-provisioning

When `endpoint`/`instanceName` not provided, creates VCU instance with:
- VCU=0 (pay-as-you-go)
- Auto-enables public internet access if VPC unreachable

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Plugin not loading | Check `slots.memory = "openclaw-mem0"` and `enabled = true` |
| `AccessKeyId is invalid` | Verify AccessKey is correct and account is active |
| Auto-provisioning fails | Ensure AccessKey has `AliyunOTSFullAccess` |
| Embedding errors | Verify `DASHSCOPE_API_KEY` is set |
| VPC endpoint unreachable | Plugin auto-enables public access; verify `AliyunOTSFullAccess` |
| `extract tar timed out` | Use manual fallback: `npm pack` + system `tar` |
| Provider shows `dashscope` | Change provider to `"openai"` with correct baseURL |

---

## Update

Do not set up automatic updates. Only update when explicitly requested.
