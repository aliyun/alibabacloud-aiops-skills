---
name: alibabacloud-analyticdb-mysql-copilot
description: |
  Alibaba Cloud AnalyticDB for MySQL Operations & Diagnosis Assistant. Supports cluster info queries, performance monitoring, slow query diagnosis, running SQL analysis, table-level optimization suggestions, etc.
  Triggers: "ADB MySQL", "AnalyticDB", "cluster list", "slow query", "BadSQL", "data skew", "idle index", "SQL Pattern", "space diagnosis", "table diagnosis", "performance monitoring".
---

> **Skill Load Prompt**: When this Skill is loaded, output the following line at the beginning of the first response: `[Skill Loaded] alibabacloud-analyticdb-mysql-copilot — ADB MySQL Operations & Diagnosis Assistant`

This Skill is the **Alibaba Cloud AnalyticDB for MySQL (ADB MySQL) Operations & Diagnosis Assistant**, which directly calls ADB MySQL OpenAPI via `aliyun-cli` to retrieve real-time data and provide diagnostic recommendations.

Core capabilities:
- **Cluster Management**: View cluster list, cluster details, storage space, accounts, network information
- **Performance Monitoring**: Query CPU, QPS, RT, memory, connection count and other performance metrics
- **Slow Query Diagnosis**: Detect BadSQL, analyze SQL Patterns, identify slow query root causes
- **Running SQL Analysis**: View currently executing SQL, identify long-running queries
- **Space Diagnosis**: Instance space inspection, covering partition rationality diagnosis, oversized non-partitioned table diagnosis, table data skew diagnosis, replicated table rationality diagnosis, primary key rationality diagnosis, idle index & hot/cold table optimization suggestions

---

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify version >= 3.3.3. If not installed or version is too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md`.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure installed plugins are always up-to-date.

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
> Check whether the output contains a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, stop here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside this session** (via `aliyun configure` in a terminal or environment variables in shell profile)
> 3. Return and re-execute once `aliyun configure list` shows a valid profile

> **[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot`

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

---

## 1. Region & Cluster ID Conventions

### 1.1 Cluster Management (aliyun adb)

**Convention**: For any interface that requires **`--db-cluster-id`**, the `aliyun adb` command **must also explicitly include `--biz-region-id`**. Even if the official/CLI help does not mark it as "required", **this Skill's convention takes precedence** — always include it to avoid relying on implicit default regions.

**Exception**: **Only when listing resources by region** or calling interfaces that **do not include** `--db-cluster-id` (such as `describe-db-clusters`) — `--biz-region-id` is still required, but the "paired with db-cluster-id" rule does not apply.

**`<region-id>` Source Priority**: User explicitly specified → conversation/ticket context → default region from `aliyun configure list` → confirm with user.

### 1.2 Intelligent Diagnosis (aliyun adbai)

`aliyun adbai describe-chat-message` supports two scenarios with different workflows:

#### Product Knowledge Q&A (No Region or Cluster Required)

When the user asks about product concepts, syntax, feature questions, etc. (e.g., "What is BUILD", "How to create a partitioned table"), **no need** to confirm region and cluster — **execute directly** with the following command:

```bash
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-beijing --query "<user question>" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

#### Instance-Level Diagnosis (Requires Region + Cluster)

When diagnosis involves specific instance data or status (e.g., slow queries, BadSQL, SQL Pattern analysis, instance health inspection, index optimization suggestions, instance diagnosis, table modeling diagnosis, etc.), **the following steps must be completed**:

1. **Region Confirmation**: `<region-id>` source priority is: user explicitly specified → conversation/ticket context → default region from `aliyun configure list` → confirm with user. If user confirmation is needed, **must read `references/region-list.md`** and present options as option cards — **forbidden** to require manual region ID input.
2. **Cluster ID Validation**: Before calling `aliyun adbai`, **must first execute** `aliyun adb describe-db-clusters --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id>`, and search for the user's cluster ID in the returned `Items.DBCluster[]`:
   - Match found → validation passed
   - Empty list or no match → **do not proceed**, display actual clusters as option cards for user to select
   - User did not provide cluster ID → display cluster list as option cards (≤10 options) for user to select
3. **Pre-Execution Confirmation**: After parameter validation, present the operation to be executed as option cards (e.g., "Continue" / "Cancel") for user confirmation — **forbidden** to require manual confirmation input.
4. **Mandatory Checklist** (all conditions **must be met** before execution, none can be omitted):
   - [ ] `biz-region-id` confirmed by user
   - [ ] `cluster-id` confirmed by user and exists in `describe-db-clusters` returned list
   - [ ] Pre-execution confirmation obtained from user
5. **Region Routing Rules (P0)**: The `aliyun adbai` service endpoint is not deployed in every region. **For all `aliyun adbai` calls, `--region` and `--endpoint` must be forcibly overridden** according to the following routing table mapping, even if the user has specified a region — do not use the user's specified values:

| biz-region-id | --region | --endpoint |
|-----------|----------|------------|
| cn-hangzhou, cn-shanghai, cn-beijing, cn-shenzhen, cn-hongkong, cn-qingdao, cn-heyuan, cn-chengdu, cn-guangzhou, cn-zhangjiakou, cn-wulanchabu, cn-huhehaote, cn-shanghai-cloudspe, cn-hangzhou-finance, cn-beijing-finance-1, cn-shenzhen-finance-1, cn-shanghai-finance-1 | cn-beijing | adbai.cn-beijing.aliyuncs.com |
| ap-southeast-1, ap-southeast-3, ap-southeast-5, ap-southeast-6, ap-southeast-7, ap-northeast-1, ap-northeast-2, eu-central-1, eu-west-1, me-east-1, me-central-1, na-south-1 | ap-southeast-1 | adbai.ap-southeast-1.aliyuncs.com |
| us-east-1, us-west-1 | us-west-1 | adbai.us-west-1.aliyuncs.com |

**Example**: User's cluster is in `cn-zhangjiakou` → `--biz-region-id cn-zhangjiakou --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com`

All sections below and examples in `references/*.md` that contain `--db-cluster-id` without `--biz-region-id` **are automatically supplemented per this section's convention**; this is not repeated in each reference — **this section takes precedence**.

## 2. Scenario Routing

> **Product Boundary**: This Skill only applies to **AnalyticDB for MySQL (ADB MySQL)**, cluster IDs typically start with `am-xxx` or `amv-xxx`. If the user mentions other Alibaba Cloud products (e.g., Elasticsearch, RDS MySQL, PolarDB, ClickHouse, etc.), clearly inform the user that this Skill does not apply and stop execution.

---

> **🚨🚨🚨 MUST | P0 | NON-NEGOTIABLE — Mandatory Enforcement Rules (Violation = Failure) 🚨🚨🚨**
>
> The following rules have the highest priority and **must be enforced unconditionally** — they **must not be violated** under any circumstances:
>
> ### Rule 1: Mandatory API Invocation
> When a user request matches the following scenarios, **must immediately execute the corresponding API call** — **skipping is prohibited**:
>
> | User Request Keywords | MUST-Call API | Prohibited Behavior |
> |---------------|---------------|----------|
> | "cluster list", "instance list", "all clusters", "list clusters" | `describe-db-clusters` | ❌ Not calling API, giving advice directly |
> | "data skew", "BadSQL", "slow SQL detection", "running SQL", "idle index", "SQL Pattern", "space diagnosis", "health inspection", "instance diagnosis", "slow query", "RT increase", "cluster stall" and other diagnosis keywords | `DescribeChatMessage` | ❌ Not calling API, only giving advice/explaining concepts |
>
> ### Rule 2: Mandatory Command String Output (First Line of Response)
> **MUST**: Every ADB OpenAPI call, **must explicitly output the executed command string at the [first line] or [beginning] of the response**.
>
> **Mandatory Format** (must be strictly followed):
> ```
> Command executed: `aliyun adb <command-name> --api-version 2021-12-01 --biz-region-id <region-id> [--db-cluster-id <cluster-id>] [other parameters]`
> or
> Command executed: `aliyun adbai describe-chat-message --region <mapped-region> --endpoint <mapped-endpoint> --biz-region-id <region-id> --query "<user question>"`
>
> [Then diagnostic results, tables, etc.]
> ```
>
> **Correct Examples**:
> ```
> Command executed: `aliyun adb describe-db-clusters --api-version 2021-12-01 --biz-region-id cn-zhangjiakou --region cn-zhangjiakou`
>
> Query complete! There are 2 ADB MySQL clusters in the Zhangjiakou region...
> ```
>
> ```
> Command executed: `aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou --query "amv-xxx slow query diagnosis for the last 3 hours"`
>
> Diagnosis complete! Found the following issues...
> ```
>
> **Incorrect Examples** (violation = failure):
> ```
> ❌ Query complete! There are 2 clusters in the Zhangjiakou region... (command string not output)
> ❌ I called the API to query the cluster list... (complete command not output)
> ❌ Command executed... (specific command content not output)
> ❌ aliyun adb describe-db-clusters --biz-region-id cn-zhangjiakou --region cn-zhangjiakou (missing --api-version 2021-12-01)
> ```
>
> ### Rule 3: Prohibited Evasion Behaviors
> **NON-NEGOTIABLE**: The following behaviors **are absolutely prohibited**:
> - ❌ Not calling API and directly giving general advice or concept explanations
> - ❌ Calling API but not outputting the complete command string at the beginning of the response
> - ❌ Using vague expressions like "We suggest you...", "You can try..." instead of actual diagnosis
> - ❌ Only outputting documentation content without executing actual operations
> - ❌ Placing the command string in the middle or end of the response
> - ❌ Calling `aliyun adb` commands without `--api-version 2021-12-01` (would default to the old version `2019-03-15`)
>
> **Violating the above rules = task failure, no exceptions**

---

> **🔴 Cluster ID Recognition Rule (Highest Priority)**: If the user-provided cluster ID starts with `am-` or `amv-`, then the cluster **is definitely** an ADB MySQL cluster. **No need** and **must not** verify its ownership through `aliyun rds`, `aliyun polardb`, `aliyun clickhouse`, `aliyun hbase` or other product commands. Violating this rule will result in numerous invalid API calls.

Based on the user's intent, read the corresponding `references/` files for detailed operation guidelines.

| User Intent | Reference File | When to Use | MUST-Call API |
|----------|----------|----------|----------------|
| View instance list, instance details, cluster configuration, storage space | Read `references/cluster-info.md` then execute | When the user wants to know what instances exist, instance specifications, or disk usage | `describe-db-clusters` / `describe-db-cluster-attribute` |
| Slow query diagnosis, BadSQL, running queries, SQL Pattern, instance diagnosis, instance write diagnosis, space diagnosis, table modeling diagnosis, data skew, idle index, product knowledge Q&A, etc. | Read `references/cluster-diagnosis.md` then execute | When the user reports performance anomalies, needs instance diagnosis, table modeling optimization, or product knowledge Q&A | `describe-chat-message` |

**Routing Rules**:
1. Identify the user's intent and find the matching scenario from the table above
2. **🚨 MUST: Immediately execute the corresponding API command** (do not skip, do not only give advice): cluster management uses `aliyun adb`, intelligent diagnosis uses `aliyun adbai describe-chat-message`
3. **🚨 MUST: Output the command string in the response** (e.g., `aliyun adb describe-db-clusters --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id>` or `aliyun adbai describe-chat-message --region <mapped-region> --endpoint <mapped-endpoint> --biz-region-id <region-id> --query "<question>"`)
4. Cluster management scenario: read `references/cluster-info.md`, execute per its steps; diagnosis scenario: read `references/cluster-diagnosis.md`, execute per its steps
5. If the user's intent cannot be matched to a specific scenario in the table, execute the following **default diagnosis workflow**:
   1. Call `describe-db-clusters` to confirm the cluster exists and its status is normal
   2. **Use option cards** to list the 2-3 most likely routing options (refer to the table above) — **forbidden** to require manual diagnosis type input
   3. Based on user selection, route to the corresponding operation and continue execution
6. Multiple scenarios can be combined — e.g., first confirm the target instance via cluster info, then diagnose and locate the issue via `describe-chat-message`

**Cluster ID Validation Rule**: If the user-provided cluster ID does not exist in the API response (error code `InvalidDBClusterId.NotFound`), do not abort the task. Instead, call `describe-db-clusters` to list the actual clusters in that region, guide the user to confirm the correct cluster ID, and continue execution.

## 3. Time Parameter Handling

> **Note**: The `describe-chat-message` interface automatically handles time parameters — no need to manually pass time ranges. The user only needs to describe the time in natural language within `--query` (e.g., "slow queries in the last 3 hours"), and the interface will parse it automatically.
>
> For cluster information query interfaces like `aliyun adb` (e.g., `describe-db-clusters`), no time parameters are needed.

## 4. Command Reference

### 4.1 OpenAPI Commands (aliyun-cli)

This Skill uses two CLI command formats:

#### Cluster Management (aliyun adb)

```bash
aliyun adb <command-name> --api-version 2021-12-01 --biz-region-id <region-id> --region <region-id> [--db-cluster-id <cluster-id>] [other parameters] --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

> **🚨 API Version Mandatory Requirement (P0)**: When calling `aliyun adb`, **must always explicitly include `--api-version 2021-12-01`**.
> ADB MySQL has two API versions (`2019-03-15` and `2021-12-01`), and the CLI may default to the old version `2019-03-15`,
> which lacks the interfaces needed by this Skill. **Commands without `--api-version 2021-12-01` will fail, constituting task failure.**

> **This Skill's Convention**: For any row in the table below that "requires `--db-cluster-id`", the actual command **must also include `--biz-region-id <region-id>`** (see Section 1.1). Only `describe-db-clusters` does not follow the "paired" rule, but still requires `--biz-region-id`.

| CLI Command Name | Description | Requires `--db-cluster-id` |
|----------|------|:---:|
| `describe-db-clusters` | Query ADB MySQL cluster list within a region | No |
| `describe-db-cluster-attribute` | Query cluster detailed attributes | Yes |
| `describe-db-cluster-space-summary` | Query storage space overview | Yes |

#### Intelligent Diagnosis (aliyun adbai)

```bash
aliyun adbai describe-chat-message --region <mapped-region> --endpoint <mapped-endpoint> --biz-region-id <region-id> --query "<user question>" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

`DescribeChatMessage` is the SSE streaming interface of the ADB MySQL intelligent diagnosis assistant, providing product RAG retrieval and instance analysis, kernel diagnosis capabilities. It includes the following diagnosis scenarios:
- **Slow SQL Query Diagnosis**: Performance metric analysis, BadSQL detection, running SQL analysis, SQL Pattern analysis
- **Instance Diagnosis**: Instance health inspection, capacity assessment, scaling recommendations
- **Instance Write Diagnosis**: Write performance analysis, write bottleneck identification
- **Table Modeling Diagnosis**: Oversized non-partitioned tables, partition rationality, primary key rationality, data skew, replicated table rationality, idle indexes, hot/cold table optimization

| Parameter | Description | Required |
|------|------|:---:|
| `--biz-region-id` | User's cluster region ID (product knowledge Q&A uses default value `cn-beijing`, no user confirmation needed) | Conditionally required |
| `--query` | Query content; for instance diagnosis, format is `"<cluster-id> <diagnosis question>"`; for product knowledge questions, ask directly (e.g., `"What is BUILD"`). | Yes |
| `--region` | Service endpoint region (Skill auto-maps based on `--biz-region-id`, no user specification needed) | Auto |
| `--endpoint` | Service endpoint address (Skill auto-maps based on `--biz-region-id`, no user specification needed) | Auto |
| `--session-id` | Session ID for multi-turn conversations (not passed = new session) | No |
| `--timezone` | Timezone, default `Asia/Shanghai` | No |

> **Important**: Instance-level diagnosis (slow queries, table modeling, etc.) `--query` must include the cluster ID; no need to separately pass `--db-cluster-id`; product knowledge questions do not need a cluster ID. Examples: `"amv-xxx slow query diagnosis for the last 3 hours"`, `"What is BUILD"`

**Examples**:

```bash
# Slow query diagnosis
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx slow query diagnosis for the last 3 hours" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Instance health inspection
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx instance health inspection analysis" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Table modeling diagnosis
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx instance space diagnosis and table modeling diagnosis" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Data skew detection
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx detect data skewed tables" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Product knowledge Q&A
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-beijing \
  --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

### 4.2 Common Parameters

**Cluster Management Parameters (aliyun adb)**:

| Parameter | Description | Default Value |
|------|------|--------|
| `--biz-region-id` | Region ID (this Skill requires it when `--db-cluster-id` is present) | — |
| `--region` | Service endpoint region (value matches `--biz-region-id`, required for `aliyun adb` commands) | — |
| `--db-cluster-id` | ADB MySQL cluster ID (e.g., `amv-xxx`) | Required |
| `--db-cluster-version` | Cluster version (`3.0`/`5.0`/`All`) | `All` |
| `--page-number` | Page number | `1` |
| `--page-size` | Items per page | `30` |

**Intelligent Diagnosis Parameters (aliyun adbai)**:

| Parameter | Description | Default Value |
|------|------|--------|
| `--biz-region-id` | User's cluster region ID (product knowledge Q&A uses default value `cn-beijing`, no user confirmation needed) | Conditionally required |
| `--query` | Query content; instance diagnosis format `"<db-cluster-id> <problem description>"`, knowledge Q&A asks directly (supports natural language time descriptions). | Required |
| `--region` | Service endpoint region (Skill auto-maps based on `--biz-region-id`, no user specification needed) | Auto |
| `--endpoint` | Service endpoint address (Skill auto-maps based on `--biz-region-id`, no user specification needed) | Auto |
| `--session-id` | Session ID (passed for multi-turn conversations) | Empty (new session) |
| `--timezone` | Timezone: e.g., `Asia/Shanghai`, etc. | `Asia/Shanghai` |

### 4.3 Credential Configuration

**Alibaba Cloud API credentials** are configured via `aliyun configure` **outside this session**; the CLI reads them automatically.

**Credential Status Check**:

```bash
aliyun configure list
```

If the AccessKeyId column in the output is empty or shows `<empty>`, credentials are not configured. Prompt the user:
1. Run `aliyun configure` in a terminal **outside this session** to configure
2. Or configure environment variables in shell profile
3. Return and continue after configuration is complete

> **🔴 Important Rules**:
> - **Strictly prohibited** from guiding users to input AK/SK credentials in the session
> - **Strictly prohibited** from using `aliyun configure set --access-key-id` and other explicit credential parameters
> - Credential check must be the first step of the task; if it fails, report and terminate directly

Multiple credential types are supported: AK, StsToken, RamRoleArn, EcsRamRole, etc. See [Credential Configuration Documentation](https://help.aliyun.com/zh/cli/configure-credentials).

## 5. RAM Policy

For the complete RAM permission list required by this Skill, see `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors during execution, follow this process:
> 1. Read `references/ram-policies.md` for the complete permission list required by this Skill
> 2. Use `ram-permission-diagnose` skill to guide the user to apply for necessary permissions
> 3. Pause and wait for user confirmation that required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, all user-configurable parameters (such as biz-region-id, db-cluster-id, --query, etc.) **must be confirmed with the user**. **Do not** assume or use default values without the user's explicit approval.
>
> **Interaction Mode Mandatory Rule**: For any step requiring user confirmation or selection (region, cluster, diagnosis scenario, execution confirmation, etc.), **must use option cards** — **forbidden** to require manual input. Specifically:
> - Region confirmation → option cards (read `references/region-list.md` for options, see Section 1.2 region confirmation rules) — **Product knowledge Q&A does not require this step**
> - Cluster ID selection → option cards (generated from `describe-db-clusters` results) — **Product knowledge Q&A does not require this step**
> - Diagnosis scenario selection → option cards (when user intent is unclear, list available diagnosis types)
> - Pre-execution confirmation → option cards (e.g., "Continue" / "Cancel") — **Product knowledge Q&A does not require this step, execute directly**

## 7. Best Practices

1. **CLI-First**: Prioritize using CLI commands for diagnosis; cluster management uses `aliyun adb`, intelligent diagnosis uses `aliyun adbai`
2. **Command Output**: Every API call must output the complete command string at the beginning of the response
3. **Error Handling**: When cluster ID does not exist, guide the user to select the correct cluster instead of failing directly
4. **Product Boundary**: Only handle ADB MySQL clusters (ID prefix `am-` or `amv-`), do not mix other product APIs
5. **Options First**: For any step requiring user confirmation or selection, always use option cards; do not require manual input

## 8. Reference Links

| Reference File | Content |
|----------|------|
| `references/ram-policies.md` | RAM permission list |
| `references/verification-method.md` | Verification methods |
| `references/cli-installation-guide.md` | Aliyun CLI installation guide |
| `references/region-list.md` | Alibaba Cloud region ID list |
| `references/cluster-info.md` | Cluster info query detailed steps |
| `references/cluster-diagnosis.md` | Cluster intelligent diagnosis detailed steps |