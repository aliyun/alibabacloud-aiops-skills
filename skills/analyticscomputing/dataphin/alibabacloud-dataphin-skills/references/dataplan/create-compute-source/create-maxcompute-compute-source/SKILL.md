---
name: create-maxcompute-compute-source
description: |-
  创建 MaxCompute 类型计算源——将 MaxCompute 项目接入 Dataphin 作为数据开发任务的计算底座。
  计算源是项目运行离线任务的引擎，必须先建计算源才能在项目上绑定。

  触发场景：
  - 为 Dataphin 项目准备 MaxCompute 计算资源（dev / prod）
  - 新建 MaxCompute 计算引擎 / 绑定 MaxCompute 项目
  - 创建计算源前先做连通性预检

  触发词：创建计算源、新建计算源、添加计算引擎、MaxCompute 计算源、create-compute-source、ConfigList 怎么填。

  关键限制：Type 固定 MAX_COMPUTE（大写下划线，非驼峰）；同一 MaxCompute project 只能绑定一个计算源且无解绑 API；19 位 ID 字符串传参。
---

# 创建 MaxCompute 计算源

## 1. Scenario Description

将 MaxCompute 项目接入 Dataphin 作为**计算源**，使项目下的离线数据开发任务（`MaxCompute_SQL` 等）可以在该 MaxCompute 引擎上运行。

**Architecture**：`Dataphin Tenant → ComputeSource (MAX_COMPUTE) → MaxCompute Project`

- 计算源是任务的**运行底座**，与数据源（读写数据）职责不同
- DEV-PROD 项目通常需分别创建 dev / prod 两套计算源（各指向不同 MaxCompute project 实现环境隔离）

## 2. Installation

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

（详见 [`references/cli-installation-guide.md`](references/cli-installation-guide.md)）

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values to terminal or logs
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

**Pre-check: Aliyun CLI >= 3.4.8 required**
> Run `aliyun version` to verify >= 3.4.8. If not installed or version too low,
> install/update from https://aliyuncli.alicdn.com (see `references/cli-installation-guide.md` for the OS-specific script).

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`../../../ram-policies.md`](../../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., tenant id, compute source name, MaxCompute
> endpoint / project, access id, etc.) MUST be confirmed with the user. Do NOT assume
> or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `TENANT_ID` | 是 | 租户 ID（19 位 snowflake，**字符串传**；profile 已配置时可省略） | — |
| `CS_NAME` | 是 | 计算源名称（英文、数字、下划线） | — |
| `CS_DESCRIPTION` | 否 | 计算源描述 | 空 |
| `MC_ENDPOINT` | 是 | MaxCompute Endpoint（形如 `http://service.<region>.maxcompute.aliyun.com/api`） | — |
| `MC_PROJECT` | 是 | MaxCompute 项目名称（ODPS project 名，需与 MaxCompute 控制台一致） | — |
| `MC_ACCESS_ID` | 是 | MaxCompute 访问 AccessKey ID | — |
| `MC_ACCESS_KEY` | 是 | MaxCompute 访问 AccessKey Secret | — |

> 💡 **术语**：ODPS（Open Data Processing Service）是 MaxCompute 的旧名，参数/配置中仍可能出现 `odps` 字样，均指 MaxCompute。

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-compute-source/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-compute-sources --op-tenant-id "1234567890123456789" \
  --type MAX_COMPUTE --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/create-maxcompute-compute-source/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<19位租户ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-compute-source/$SESSION_ID"
```

> **CLI 入参结构说明**：`create-compute-source` 使用**扁平 flag**（`--compute-source-name` / `--type` / `--description` / `--config-list`），CLI 会自动序列化为 OpenAPI 的 `CreateCommand` JSON 对象。`--config-list` 是**列表**，每个元素是一个 `{"Key":"...","Value":"..."}` JSON 字符串，多个用空格分隔。

### Step 1：连通性预检（推荐）

创建前先验证 MaxCompute 配置是否连通（`check-compute-source-connectivity` 只测试、不落库）：

```bash
aliyun dataphin-public check-compute-source-connectivity \
  --op-tenant-id "$TENANT_ID" \
  --type MAX_COMPUTE \
  --config-list \
    '{"Key":"maxcompute.endpoint","Value":"<MC_ENDPOINT>"}' \
    '{"Key":"maxcompute.project","Value":"<MC_PROJECT>"}' \
    '{"Key":"maxcompute.access.id","Value":"<MC_ACCESS_ID>"}' \
    '{"Key":"maxcompute.access.key","Value":"<MC_ACCESS_KEY>"}' \
  $UA
```

期望返回 `"Success": true` 且 `CheckResult.Connected: true`。若 `Connected: false`，看 `Reason` 字段（`InvalidAK` / `ProjectNotFound` / `timeout`）排查后重试。

### Step 2：创建计算源

```bash
aliyun dataphin-public create-compute-source \
  --op-tenant-id "$TENANT_ID" \
  --compute-source-name "<CS_NAME>" \
  --type MAX_COMPUTE \
  --description "<CS_DESCRIPTION>" \
  --config-list \
    '{"Key":"maxcompute.endpoint","Value":"<MC_ENDPOINT>"}' \
    '{"Key":"maxcompute.project","Value":"<MC_PROJECT>"}' \
    '{"Key":"maxcompute.access.id","Value":"<MC_ACCESS_ID>"}' \
    '{"Key":"maxcompute.access.key","Value":"<MC_ACCESS_KEY>"}' \
  $UA
```

响应：
```json
{
  "Code": "OK",
  "Success": true,
  "CreateResult": { "Id": 6865280996660864 }
}
```

记录 `CreateResult.Id`（字符串保存）。

> **DEV-PROD 项目**：dev / prod 两套计算源需**分别创建**（各跑一次 Step 2，`--compute-source-name` 与 `maxcompute.project` 不同）。建议先建 prod，再建 dev。

### 执行前确认（写操作必备）

> 本 skill 涉及写操作（`create-compute-source`），执行前必须向用户确认：
> - 即将创建的计算源名称与类型（MAX_COMPUTE）
> - 目标租户 ID
> - MaxCompute 连接配置（endpoint / project / access.id，**不打印 access.key**）
> - 是否可回滚（可通过 `delete-compute-source` 删除；但绑定项目后需先解绑）

仅当用户明确回复"确认 / yes / 执行"后才发起创建命令。

## 9. Success Verification

### Step 1：检查 API 返回

`Code: "OK"`、`Success: true` 且 `CreateResult.Id` 非空。

> **注意**：`Code: OK` 仅代表请求被受理，需进一步反查确认。

### Step 2：列表反查

```bash
aliyun dataphin-public list-compute-sources \
  --op-tenant-id "$TENANT_ID" \
  --type MAX_COMPUTE --keyword "<CS_NAME>" --page-size 20 $UA
```

确认返回 `ComputeSourceList` 中包含刚创建的计算源（按 `Name` 匹配），记录其 `Id`。

### Step 3：连通性校验（按 Id）

```bash
CS_ID="<Step 2 反查到的 Id>"

aliyun dataphin-public check-compute-source-connectivity-by-id \
  --op-tenant-id "$TENANT_ID" \
  --compute-source-id "$CS_ID" $UA
```

期望返回连通状态为通过。

## 10. Cleanup

```bash
aliyun dataphin-public delete-compute-source \
  --op-tenant-id "$TENANT_ID" \
  --compute-source-id "$CS_ID" $UA
```

> **前置条件**：计算源若已 `BindProject: true`（绑定项目），需先在项目上解绑/更换计算源后才能删除。

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. **Type 固定 `MAX_COMPUTE`（大写下划线）**：不是驼峰 `MaxCompute`。传 `MaxCompute` 会报 `No enum constant ...ComputeSourceTypeEnum.MaxCompute`。（注：计算源与数据源侧均用 `MAX_COMPUTE`。）
2. **MaxCompute project 不可重复绑定**：同一 MaxCompute project 只能绑定一个 Dataphin 计算源，且目前**无解绑 API**。若 project 已被占用，只能换 project 或删除旧计算源。
3. **`--config-list` 为列表**：每项是独立的 `{"Key":"...","Value":"..."}` JSON 字符串，用空格分隔；漏项会导致连接配置不完整。
4. 大整数 ID（19 位 snowflake）一律**字符串传参**（引号包住），避免 shell / JSON 序列化精度丢失。
5. 写操作（create / delete）执行前必须 HITL 二次确认。
6. 建议先 `check-compute-source-connectivity` 预检，通过后再 `create-compute-source`。

### ConfigList Key 说明

MaxCompute 计算源 ConfigList 使用与数据源侧一致的连接器 Key：`maxcompute.endpoint` / `maxcompute.project` / `maxcompute.access.id` / `maxcompute.access.key`。若某环境对 Key 命名有微调导致被拒，先 `list-compute-sources` 找一个同类型已存在计算源，或参考已有 MaxCompute **数据源**的连接配置作为模板核对。

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../../ram-policies.md`](../../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
