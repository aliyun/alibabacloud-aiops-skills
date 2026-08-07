---
name: check-data-source-connectivity
description: |-
  校验数据源连通性（不会实际创建数据源，仅测试连接）。 触发场景：测试数据源连接 / 检查数据源是否可达 / 创建数据源前先验证连通性 / 数据源连接失败排查 / check-data-source-connectivity。 CheckCommand 中 Type 决定 ConfigItemList 内 Key/Value 的组合，与 create-data-source 同构。 触发词：测试数据源连接、检查连通性、数据源连接失败、check-data-source-connectivity、验证数据源。
---
# 校验数据源连通性 skill

## 适用场景

- **建源前预检**：在 `create-data-source` 之前先用本命令验证 Key/Value 是否正确
- **调试连接失败**：已建数据源改密后先本地验证
- **不需要真实创建**的 ad-hoc 连通性排查

## 命令 & 官方文档

- CLI：`aliyun dataphin-public check-data-source-connectivity --help`
- OpenAPI：[CheckDataSourceConnectivity](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CheckDataSourceConnectivity)

## Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile（AK、STS 或 OAuth 身份）。
>
> **如果没有有效 profile，请在此停止。** 先在会话外执行 `aliyun configure` 配置凭证，`aliyun configure list` 确认有效后再继续。

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限（`dataphin:CheckDataSourceConnectivity` / `dataphin:CheckDataSourceConnectivityById`）见 [../../ram-policies.md](../../ram-policies.md)。连通性校验为只读探测，不创建/修改任何资源。

## IMPORTANT: Parameter Confirmation

执行连通性校验命令前必须向用户确认以下参数，禁止静默提交：

| 参数 | 说明 |
|------|------|
| `--tenant-id` | 租户 ID（`--op-tenant-id` 的别名，profile 已配置时可省） |
| `--type` | 数据源类型枚举（大写，如 `MYSQL` / `MAX_COMPUTE`） |
| `--config-item-list` | 连接配置项 JSON 对象列表（含 `jdbc.url` / 账号 / 密码等敏感信息，确认后再执行） |

> 本命令为只读探测，不创建数据源；但 `--config-item-list` 会携带目标库账号密码，务必确认无误、避免误连生产库。

## Observability

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 生成的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun` 命令必须携带：

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id}
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

## 顶层参数骨架

```text
--op-tenant-id, --tenant-id <int>   必填 | 租户 ID（profile 已配置时可省略）
--type <string>                     必填 | 数据源类型枚举（大写，如 MYSQL / MAX_COMPUTE）
--config-item-list <JSON>...        必填 | 连接配置项列表，每个配置项一个 JSON 对象，可重复
```

> ⚠ **致命易错点（作者曾踩坑）**：本命令**没有** `--check-command` 参数。API 请求体里的 `CheckCommand` 对象由 CLI 用 `--type` + `--config-item-list` **自动组装**。若照 `--check-command '{...}'` 写法调用，该参数会被 CLI **静默忽略**、生成空请求体 → 必然失败。可用 `--cli-dry-run` 先确认组装出的 Body 形如 `{"CheckCommand":"{\"ConfigItemList\":[...],\"Type\":\"MYSQL\"}"}`。

## --config-item-list 写法

`--config-item-list` 是**列表参数**：每个配置项写成一个独立 JSON 对象，空格分隔、可重复。CLI 会把它与 `--type` 一起组装成 API 的 `CheckCommand` 体（`{ "Type": ..., "ConfigItemList": [...] }`），**无需手写外层结构**。

```text
--config-item-list '{"Key":"<k1>","Value":"<v1>"}' '{"Key":"<k2>","Value":"<v2>"}' ...
```

单个配置项对象结构（`Key` / `Value` 均必填）：

```jsonc
{ "Key": "<配置 key>", "Value": "<配置值>" }
```

## Type 与 Key 清单

`--type` 的枚举值及每种 Type 对应的 `ConfigItemList` Key 清单，**与同套件子 skill `create-data-source` 完全同构**（服务端复用同一套 Provider）。参见该 skill（经套件入口 alibabacloud-dataphin-skills 路由加载）的 "Type 枚举与 ConfigItemList Key 清单" 章节。

### ✓ MYSQL

```bash
aliyun dataphin-public check-data-source-connectivity \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} \
  --tenant-id <tenant-id> \
  --type MYSQL \
  --config-item-list \
    '{"Key":"jdbc.url","Value":"<jdbc-url>"}' \
    '{"Key":"jdbc.username","Value":"<your-db-username>"}' \
    '{"Key":"jdbc.password","Value":"<your-db-password>"}'
```

### ✓ MAX_COMPUTE

```bash
aliyun dataphin-public check-data-source-connectivity \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} \
  --tenant-id <tenant-id> \
  --type MAX_COMPUTE \
  --config-item-list \
    '{"Key":"maxcompute.access.id","Value":"<ak_id>"}' \
    '{"Key":"maxcompute.access.key","Value":"<ak_secret>"}' \
    '{"Key":"maxcompute.endpoint","Value":"<endpoint>"}' \
    '{"Key":"maxcompute.project","Value":"<odps_project_name>"}'
```

### ⚠ 其他 21 种（unverified）

查阅：[CreateDataSource 官方文档](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CreateDataSource) 末尾的"补充说明"即为各 Type 的 Key 清单（Check 与 Create 共享同一份清单）。

## 返回判读

响应体关键字段（以 OpenAPI 2023-06-30 CheckDataSourceConnectivity 元数据为准）：

| 字段 | 含义 |
|------|------|
| `Success` (boolean) | 请求是否成功（仅表示调用链路正常） |
| `Code` (string) | `OK` 表示请求正常；非 `OK` 通常是参数结构问题（Type 名拼错或 Key 缺失必填） |
| `Message` (string) | 请求错误信息 |
| `Data` (boolean) | **连通性校验结果**：`true` = 连通，`false` = 不连通 |

判读规则：

- `Success: true` + `Data: true` → 连通
- `Success: true` + `Data: false` → 网络可达但认证/配置错（或白名单未放行），根据 `Message` 排查
- `Code` 非 `OK` → 请求参数结构问题（通常是 Type 名拼错或 Key 缺失必填）

> 注：早期文档曾写 `CheckResult: { Connected, Reason }` 字段，实为误写；以上字段以 API 元数据为准。

## 常见坑

1. `Type` **必须大写、使用元数据里列出的枚举**（如 `MYSQL` 不是 `Mysql`）
2. 私有化 MySQL / Oracle 需确保 Dataphin 出口 IP 在目标库白名单内，否则 Connected=false / timeout
3. MaxCompute endpoint 必须带 `https://` 与 `/api` 后缀
4. Check 通过不代表 Create 必过；Create 还会校验 Name 唯一性、权限等

## 相关命令

- `create-data-source` — Check 通过后再 Create（经套件入口 alibabacloud-dataphin-skills 路由加载）
- `aliyun dataphin-public check-data-source-connectivity-by-id --data-source-id <N>` — 对已存在的数据源按 ID 校验
