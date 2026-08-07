---
name: create-maxcompute-data-source
description: |-
  创建 MaxCompute 类型数据源并验证连通性——将 MaxCompute 项目接入 Dataphin 作为数据源。
  支持 Basic 和 DEV-PROD 两种项目模式。

  触发场景：
  - 新接入 MaxCompute 数据仓库到 Dataphin
  - 为 Dataphin 项目配置 MaxCompute 数据源
  - 验证 MaxCompute 数据源连通性

  触发词：创建 MaxCompute 数据源、接入 MaxCompute、新建 MC 数据源、MaxCompute datasource、配置 MaxCompute。

  关键限制：Type 固定 MAX_COMPUTE；DEV-PROD 项目需分两步创建（先生产后开发）；19 位 ID 必须字符串传参。
---

# 创建 MaxCompute 数据源并验证连通性

## 1. Scenario Description

将 MaxCompute 项目接入 Dataphin 作为数据源，使下游数据开发任务可以读写该 MaxCompute 项目中的数据。

**Architecture**：`Dataphin Tenant → DataSource (MAX_COMPUTE) → MaxCompute Project`

支持两种项目模式：
- **Basic 项目**：仅创建生产环境数据源
- **DEV-PROD 项目**（开发-生产分离）：先创建生产环境数据源，再创建开发环境数据源并关联

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
> install/update from https://aliyuncli.alicdn.com (see `references/cli-installation-guide.md` for the OS-specific script),
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## 5. RAM Policy

最小权限策略详见 [`../../ram-policies.md`](../../ram-policies.md)。

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必填 | 描述 | 默认值 |
|---|---|---|---|
| `TENANT_ID` | 是 | 租户 ID（19 位 snowflake，**字符串传**） | — |
| `DS_NAME` | 是 | 数据源名称（英文、数字、下划线，不超过 64 字符） | — |
| `DS_DESCRIPTION` | 否 | 数据源描述 | 空 |
| `PROJECT_MODE` | 是 | 项目模式：`BASIC` 或 `DEV_PROD` | — |
| `MC_ENDPOINT` | 是 | MaxCompute Endpoint | — |
| `MC_PROJECT` | 是 | MaxCompute 项目名称（生产环境） | — |
| `MC_PROJECT_DEV` | DEV_PROD 时必填 | MaxCompute 项目名称（开发环境，可与生产相同） | 同 `MC_PROJECT` |
| `MC_ACCESS_ID` | 是 | MaxCompute 访问 AccessKey ID | — |
| `MC_ACCESS_KEY` | 是 | MaxCompute 访问 AccessKey Secret | — |

> **Endpoint 参考**：`http://service.<region>.maxcompute.aliyun.com/api`，常见 region 如 `cn-hangzhou`、`cn-shanghai`、`cn-beijing`。

## 7. Observability (MUST follow for every aliyun command)

**session-id 由父 skill `alibabacloud-dataphin-skills` 在套件入口加载时生成（32-char 小写 hex），本子 skill 加载时直接继承同一 session-id，不再重新生成。**

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-data-source/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun dataphin-public list-data-source-with-config --op-tenant-id "1234567890123456789" \
  --list-query '{"TypeList":["MAX_COMPUTE"],"Page":1,"PageSize":20}' \
  --user-agent AlibabaCloud-Agent-Skills/create-maxcompute-data-source/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 8. Core Workflow

```bash
TENANT_ID="<19位租户ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-data-source/$SESSION_ID"
```

### Step 1：连通性预检（可选但推荐）

创建前先验证 MaxCompute 配置是否连通：

```bash
aliyun dataphin-public check-data-source-connectivity \
  --op-tenant-id "$TENANT_ID" \
  --check-command '{
    "Type": "MAX_COMPUTE",
    "ConfigItemList": [
      {"Key": "maxcompute.endpoint", "Value": "<MC_ENDPOINT>"},
      {"Key": "maxcompute.project", "Value": "<MC_PROJECT>"},
      {"Key": "maxcompute.access.id", "Value": "<MC_ACCESS_ID>"},
      {"Key": "maxcompute.access.key", "Value": "<MC_ACCESS_KEY>"}
    ]
  }' $UA
```

期望返回 `"ConnectStatus": true`。若为 `false`，请检查 endpoint / project / AK 是否正确后重试。

### Step 2：创建数据源

#### 分支 A：Basic 项目（仅生产环境）

```bash
aliyun dataphin-public create-data-source \
  --op-tenant-id "$TENANT_ID" \
  --create-command '{
    "ProdDataSourceCreate": {
      "Name": "<DS_NAME>",
      "Type": "MAX_COMPUTE",
      "Description": "<DS_DESCRIPTION>",
      "CheckActivity": true,
      "ConfigItemList": [
        {"Key": "maxcompute.endpoint", "Value": "<MC_ENDPOINT>"},
        {"Key": "maxcompute.project", "Value": "<MC_PROJECT>"},
        {"Key": "maxcompute.access.id", "Value": "<MC_ACCESS_ID>"},
        {"Key": "maxcompute.access.key", "Value": "<MC_ACCESS_KEY>"}
      ]
    }
  }' $UA
```

响应：
```json
{
  "Code": "OK",
  "CreateResult": { "ProdDataSourceId": 7461272386043530112 }
}
```

记录 `ProdDataSourceId`（字符串保存）。

#### 分支 B：DEV-PROD 项目（生产 + 开发环境）

**Step 2a** — 创建生产环境数据源（同分支 A），记录 `ProdDataSourceId`。

**Step 2b** — 创建开发环境数据源（关联生产侧）：

```bash
PROD_DS_ID="<Step 2a 返回的 ProdDataSourceId>"

aliyun dataphin-public create-data-source \
  --op-tenant-id "$TENANT_ID" \
  --create-command '{
    "DevDataSourceCreate": {
      "ProdDataSourceId": "'"$PROD_DS_ID"'",
      "DataSourceCreate": {
        "Name": "<DS_NAME>",
        "Type": "MAX_COMPUTE",
        "Description": "<DS_DESCRIPTION> (DEV)",
        "CheckActivity": true,
        "ConfigItemList": [
          {"Key": "maxcompute.endpoint", "Value": "<MC_ENDPOINT>"},
          {"Key": "maxcompute.project", "Value": "<MC_PROJECT_DEV>"},
          {"Key": "maxcompute.access.id", "Value": "<MC_ACCESS_ID>"},
          {"Key": "maxcompute.access.key", "Value": "<MC_ACCESS_KEY>"}
        ]
      }
    }
  }' $UA
```

> **提示**：开发环境的 `maxcompute.project` 推荐与生产环境使用不同的 MaxCompute 项目以实现数据隔离。

记录 `DevDataSourceId`。

### 执行前确认（写操作必备）

> 本 skill 涉及写操作（`create-data-source`），执行前必须向用户确认：
> - 即将创建的数据源名称和类型（MAX_COMPUTE）
> - 目标租户 ID
> - 项目模式（Basic / DEV-PROD）
> - MaxCompute 连接配置（endpoint / project / access.id，**不打印 access.key**）
> - 是否可回滚（可通过 `delete-data-source` 删除）

仅当用户明确回复"确认 / yes / 执行"后才发起创建命令。

## 9. Success Verification

### Step 1：检查 API 返回

`Code: "OK"` 且 `CreateResult.ProdDataSourceId` 非空。

> **注意**：`Code: OK` 仅代表请求被受理，不代表数据源连通可用。

### Step 2：列表反查

```bash
aliyun dataphin-public list-data-source-with-config \
  --op-tenant-id "$TENANT_ID" \
  --list-query '{"TypeList":["MAX_COMPUTE"],"Name":"<DS_NAME>","Page":1,"PageSize":20}' $UA
```

确认返回列表中包含刚创建的数据源（按 Name 匹配）。

### Step 3：连通性校验

```bash
aliyun dataphin-public check-data-source-connectivity-by-id \
  --op-tenant-id "$TENANT_ID" \
  --id "$PROD_DS_ID" $UA
```

期望返回 `"ConnectStatus": true`。

## 10. Cleanup

```bash
aliyun dataphin-public delete-data-source \
  --op-tenant-id "$TENANT_ID" \
  --delete-command '{"Mode":"DEV_PROD","ProdDataSourceId":"'"$PROD_DS_ID"'"}' $UA
```

> `Mode` 枚举值：
> - `DEV` — 仅删除开发环境数据源
> - `DEV_PROD` — 同时删除开发和生产环境数据源

## 11. Command Tables

详见 [`references/related-commands.md`](references/related-commands.md)。

## 12. Best Practices + Reference Links

1. 大整数 ID（19 位 snowflake）一律字符串传参（引号包住）
2. 写操作（create/delete）执行前必须 HITL 二次确认
3. DEV-PROD 项目建议开发与生产使用**不同的 MaxCompute 项目**，实现数据隔离
4. `CheckActivity: true` 会在创建时自动验证连通性，建议始终开启

### 常见坑

#### [Agent 自主发现] deploy.type 自动回填
- 现象：MaxCompute 数据源不需要显式传 `deploy.type`，服务端会自动填回 `RDS`
- 结论：可省略 `deploy.type`，但私有化环境建议显式传入以兼容

#### [Agent 自主发现] DEV 环境数据源需关联 PROD
- 现象：DEV-PROD 项目下，开发环境数据源必须通过 `ProdDataSourceId` 关联到已有的生产环境数据源，不能独立创建
- 结论：必须先创建生产环境数据源，获取 ID 后再创建开发环境数据源

#### [L3 实测发现] delete-data-source 的 ProdDataSourceId 必须字符串传参
- 现象：`ProdDataSourceId` 以裸整数传入 JSON 时（如 `7468647409615827520`），CLI 序列化会精度丢失，服务端报“数据源不存在”
- 结论：19 位 snowflake ID 在 `--delete-command` 和 `--create-command` 的 JSON 中**必须加引号传为字符串**（如 `"ProdDataSourceId":"7468647409615827520"`）

### Reference Links

- [`references/cli-installation-guide.md`](references/cli-installation-guide.md)
- [`../../ram-policies.md`](../../ram-policies.md)
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md)
- [`references/related-commands.md`](references/related-commands.md)
