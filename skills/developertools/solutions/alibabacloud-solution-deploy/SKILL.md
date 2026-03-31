---
name: alibabacloud-solution-deploy
description: >
  Deploy Alibaba Cloud official tech solutions. Trigger when the user mentions
  an Alibaba Cloud solution, pastes a solution URL (aliyun.com/solution/tech-solution/...),
  or wants to deploy an official solution template. Covers both Terraform module
  deployment and CLI step-by-step execution paths.
---

# Alibaba Cloud Solution Deploy

Match the user's scenario to the best execution path (Terraform or CLI), then complete the task end-to-end.

## Core Principles

### Maximum Automation
If 10 steps are needed and 9 can be automated, automate all 9. Only pause for the 1 that genuinely requires human action. Every cloud operation that has a CLI path should use it — the user came to you precisely so they don't have to click through consoles.

### CLI-First, Console-Last
Express every cloud action as a runnable `aliyun` CLI command. Only fall back to console when no CLI exists — and when you do, give a **direct deep-linked URL** (not a product homepage). The difference between `https://vision.aliyun.com/facebody` and `https://console.aliyun.com/` is the difference between being helpful and being useless.

### Never Guess — Verify First
- **CLI syntax**: Run `aliyun <product> <command> --help` before constructing commands. Parameter naming is inconsistent across products — `--RegionId` vs `--region-id` vs `--region` all exist.
- **Errors**: Run `diagnose_cli_command.py` immediately on failure. Error messages from the Alibaba Cloud API are often cryptic — the diagnosis script calls a specialized endpoint that maps error codes to fixes.

---

## Workflow

### Step 0: Verify Environment

Run this first in any new session:

> **Pre-check: Aliyun CLI >= 3.3.1 required**
>
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low, see [installation guide](references/aliyun-cli-installation-guide.md) for instructions.
>
> Then run the following command to enable automatic plugin installation and set the agent user-agent:
> ```bash
> aliyun configure set --auto-plugin-install true --user-agent AlibabaCloud-Agent-Skills
> ```
> This ensures product-specific CLI plugins are downloaded on first use (no manual install needed), and identifies requests as coming from this skill.

Then run the full environment check:

```bash
bash {{SKILL_PATH}}/scripts/verify_env.sh
```

This checks: CLI version, valid credentials, auto-plugin-install, Python3 + SDK. If any check fails, tell the user what to fix and stop — a broken environment means every subsequent command will fail.

#### RAM Permission Pre-check

Before executing any commands, verify the current user has the required permissions:

1. Compare the user's permissions against [references/ram-policies.md](references/ram-policies.md)
2. If any permission is missing, abort and prompt the user to attach the required policy

Minimum required permissions are listed in [references/ram-policies.md](references/ram-policies.md).

### Step 1: Understand the Scenario

Extract from the user's request:
- **What** they want to build or configure
- **Which Alibaba Cloud products** are involved (or can be inferred)
- **Key requirements**: region, instance specs, budget, HA needs, environment (dev/staging/prod)

Distill into search keywords (Chinese + English) for Step 2. For example, "我要搭个RAG知识库" → keywords: `RAG`, `知识库`, `AnalyticDB`, `百炼`.

### Step 2: Route to the Right Path

Check `references/alicloud-tech-solutions-all.md` — the master catalog of 187 Alibaba Cloud tech solutions. Search by keyword match against the solution names and descriptions.

Each row has a `Terraform Module 名称` column:

- **Column has a value** (e.g., `analyticdb-rag`, `deepseek-personal-website`) → **Path A: Terraform**
- **Column is empty or no matching solution found** → **Path B: CLI-First**

Also use [intent-mapping.md](references/intent-mapping.md) for fuzzy keyword → solution matching (e.g., "小程序" → `develop-your-wechat-mini-program-in-10-minutes`).

Tell the user which path you're taking and why before proceeding.

---

## Path A: Terraform Solution

When a Terraform module matches, deploy through the IaCService remote runtime — no local `terraform` binary needed.

### A.1: Locate the Module

Look up the Module 名称 and Module 地址 in `references/tf-plan/tf-solutions.md`. Match by:
1. Exact module name from the master catalog
2. Keyword match against the 描述 column
3. [Intent mapping](references/intent-mapping.md)

### A.2: Fetch Example Parameters

Every module has a GitHub repo with tested examples. Derive the URLs:

```
Module 地址: https://registry.terraform.io/modules/alibabacloud-automation/<name>/alicloud/latest
GitHub repo: https://github.com/alibabacloud-automation/terraform-alicloud-<name>
Example:     https://raw.githubusercontent.com/alibabacloud-automation/terraform-alicloud-<name>/main/examples/complete/main.tf
```

Fetch the example `main.tf` via WebFetch. These values come from real tested deployments — they're far more reliable than generic defaults.

**Parameter priority:**
1. User explicitly specified → always use
2. Example `main.tf` from `examples/complete/` → use as default
3. Fallback defaults (only if fetch fails): see [terraform-defaults.md](references/terraform-defaults.md)

### A.3: Confirm with User

Show the parameters and ask for confirmation. Never silently apply them — cloud resources cost real money.

```
以下是基于官方示例的部署参数，请确认或修改：
• Region: cn-hangzhou
• Instance type: ecs.c7.large
• VPC CIDR: 172.16.0.0/12
• Password: (请提供)
```

Sensitive values like passwords and API keys: never generate them yourself. The user provides these.

### A.4: Write main.tf and Deploy

```hcl
# Based on: https://github.com/alibabacloud-automation/terraform-alicloud-<name>/blob/main/examples/complete/main.tf
module "<module_name>" {
  source  = "alibabacloud-automation/<module_name>/alicloud"
  version = "~> 1.0"
  # Parameters adjusted per user confirmation
}
```

Deploy using the remote runtime — see [terraform-online-runtime.md](references/terraform-online-runtime.md) for full usage:

```bash
SKILL_DIR="{{SKILL_PATH}}"
TF="${SKILL_DIR}/scripts/terraform_runtime_online.sh"
STATE_ID=$($TF apply main.tf | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
```

The STATE_ID is required for any future update or destroy. Losing it means you lose control over the resources.

### A.5: Verify and Report

Confirm resources exist. Provide the destroy command for cleanup.

---

## Path B: CLI-First Execution

This path handles everything without a Terraform template. The approach: understand the architecture → decompose into steps → find the CLI command for each step → execute.

### B.1: Understand the Architecture

Before writing any commands, understand what you're building:

- If the master catalog had a matching solution (just without TF Module), it still has **tutorial links** (部署教程 column). Fetch that page to understand the target architecture, required products, and deployment sequence. This gives you the blueprint — you'll then translate each step into CLI commands.
- If no solution matched at all, reason from the user's description: what products are needed, what depends on what, what's the end state.

### B.2: Decompose into Steps

Break the goal into atomic steps ordered by dependency. Think through:

- **Resource creation order**: VPC → VSwitch → Security Group → ECS is almost always the foundation
- **ID chaining**: which step outputs IDs that later steps need (VpcId → CreateVSwitch, VSwitchId → RunInstances)
- **Async operations**: some create calls return immediately but the resource takes time — you'll need to poll
- **What might not have a CLI**: some product activations, some console-only features

### B.3: Research CLI Commands

For each step, use the scripts to find the correct API name and parameters. This is critical — don't rely on memory. Alibaba Cloud has thousands of APIs, and parameter names are inconsistent across products.

```bash
python3 {{SKILL_PATH}}/scripts/lsit_products.py '<keyword>'        # Find product code + API version
python3 {{SKILL_PATH}}/scripts/search_apis.py '<what you want to do>'  # Natural language → API
python3 {{SKILL_PATH}}/scripts/search_documents.py '<topic>'       # Parameter details, valid values, constraints
python3 {{SKILL_PATH}}/scripts/lsit_api_overview.py <Product> <version>  # Full API list for a product
```

Run scripts in parallel when researching multiple products — don't serialize what can be parallelized.

**Common CLI shortcuts that avoid console entirely:**

| Scenario | CLI Command | Notes |
|----------|------------|-------|
| Get Bailian (百炼) API Key | `aliyun maas list-workspaces` → `aliyun maas create-api-key --WorkspaceId <id>` | Avoids console entirely. Almost every AI solution needs this. |
| Run commands on ECS | `aliyun ecs RunCommand --Type RunShellScript --CommandContent '<script>' --InstanceId.1 <id>` | Use Cloud Assistant instead of asking the user to SSH in. |
| OSS operations | `aliyun ossutil cp/ls/mb ...` | Use `ossutil` subcommand, not `oss`. |

The Bailian API Key pattern is especially important — nearly every AI-related solution needs a DashScope/Bailian SK, and users often don't know it can be obtained programmatically. Whenever a plan involves 百炼/Bailian/DashScope, proactively use the `maas` commands to get the key.

### B.4: Present Plan and Confirm

Before running any write operations, show the complete execution plan. The plan MUST include a **RAM permissions section** listing all permissions the current account needs — this lets the user verify access before execution starts, avoiding mid-deploy `Forbidden.RAM` errors.

Derive the required permissions from the planned CLI commands: each `aliyun <product> <API>` call maps to a RAM action in the form `<product>:<API>` (e.g., `aliyun vpc CreateVpc` → `vpc:CreateVpc`).

```
所需 RAM 权限:

| 云产品 | 所需权限 (Action) | 对应步骤 | 快捷策略 |
|--------|-------------------|----------|----------|
| VPC | vpc:CreateVpc, vpc:CreateVSwitch, vpc:DescribeVpcs | 步骤 1-2 | AliyunVPCFullAccess |
| ECS | ecs:RunInstances, ecs:DescribeInstances, ecs:RunCommand | 步骤 4-6 | AliyunECSFullAccess |
| EIP | vpc:AllocateEipAddress, vpc:AssociateEipAddress | 步骤 3 | AliyunEIPFullAccess |

提示: 可使用快捷策略快速授权，或按 Action 列配置最小权限自定义策略。

---

执行计划 (共 N 步, M 步 CLI 自动化, K 步需控制台):

步骤 1 — 创建 VPC
  aliyun vpc CreateVpc --RegionId cn-hangzhou --CidrBlock 172.16.0.0/12 --VpcName demo-vpc

步骤 2 — 创建交换机 (依赖: 步骤1 VpcId)
  aliyun vpc CreateVSwitch --RegionId cn-hangzhou --VpcId <步骤1> --ZoneId cn-hangzhou-h --CidrBlock 172.16.0.0/24

步骤 3 — [控制台] 开通视觉智能 API (无 CLI)
  打开: https://vision.aliyun.com/facebody → 点击 "立即开通"
```

Wait for user approval. Cloud resources cost money, and some operations (like deleting RDS instances) are irreversible.

### B.5: Execute

For each step:
1. **Verify syntax first**: `aliyun <product> <api> --help` — catch parameter errors before they hit the API
2. **Run the command**
3. **Verify result**: poll async operations; describe the resource to confirm it exists
4. **Capture output**: save IDs, endpoints, connection strings for subsequent steps and final report

### B.6: Handle Errors

When a command fails:

```bash
python3 {{SKILL_PATH}}/scripts/diagnose_cli_command.py '<the full command>' '<the error message>'
```

The diagnosis script calls a specialized API that maps error codes to actionable fixes. Apply the fix and retry. If the same error persists after the fix, report to the user with the diagnosis — don't keep retrying blindly.

Resume from the failed step. Never re-run steps that already succeeded — those resources already exist and re-running would either fail (duplicate) or create unwanted duplicates.

### B.7: Report

Summarize:
- Resources created (with IDs)
- Access endpoints / connection strings
- How to use what was built
- Cleanup commands (delete in reverse dependency order: ECS → Security Group → VSwitch → VPC)

---

## Script Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `verify_env.sh` | Environment check | `bash {{SKILL_PATH}}/scripts/verify_env.sh` |
| `lsit_products.py` | Find product code + version | `python3 {{SKILL_PATH}}/scripts/lsit_products.py 'ECS'` |
| `search_apis.py` | Natural language → API | `python3 {{SKILL_PATH}}/scripts/search_apis.py '创建ECS实例'` |
| `search_documents.py` | Doc search for details | `python3 {{SKILL_PATH}}/scripts/search_documents.py 'ECS实例规格'` |
| `lsit_api_overview.py` | Full API list for a product | `python3 {{SKILL_PATH}}/scripts/lsit_api_overview.py Ecs 2014-05-26` |
| `diagnose_cli_command.py` | Diagnose CLI errors | `python3 {{SKILL_PATH}}/scripts/diagnose_cli_command.py '<cmd>' '<err>'` |
| `terraform_runtime_online.sh` | Remote TF execution | See [terraform-online-runtime.md](references/terraform-online-runtime.md) |

## References

- [Intent Mapping](references/intent-mapping.md) — keyword → solution mapping
- [Terraform Defaults](references/terraform-defaults.md) — default parameter values
- [Terraform Online Runtime](references/terraform-online-runtime.md) — IaCService script usage
- [All Tech Solutions Catalog](references/alicloud-tech-solutions-all.md) — 187 solutions with TF Module availability
- [TF Solutions Detail](references/tf-plan/tf-solutions.md) — 48 Terraform modules with Registry addresses
