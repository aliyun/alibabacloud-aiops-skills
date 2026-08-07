---
name: monitor-api-operations
description: |
  数据服务 API 运维监控。查看 API 调用汇总、趋势分析、调用日志明细和异常影响分析，支持日常运维和问题排查。
  触发场景：API 监控 / 调用日志 / 运维分析 / 异常分析 / 调用趋势 / 调用统计。
---

# 数据服务 API 运维监控

## 1. Scenario Description

运维工程师通过阿里云 CLI 查看数据服务 API 的调用统计与日志，用于日常运维和问题排查。

**业务流程：**
```
查看调用汇总 → 分析调用趋势 → 查看调用日志 → 异常分析（可选）
```

**资源拓扑：**
```
数据服务项目
├── API
│   ├── 调用汇总（总次数、成功率、平均耗时）
│   ├── 调用趋势（时间维度调用量、成功/失败走势）
│   ├── 调用日志（单次调用详情：时间、调用者、状态、耗时）
│   └── 异常影响（错误影响范围、受影响调用明细）
```

**前置条件：**
- 数据服务项目已存在，当前用户为项目成员
- 目标 API 已创建（来自 S1 `create-and-publish-api`）

**特别说明：本 Skill 所有操作均为只读，不涉及任何写操作。**

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

```bash
# 检查凭证配置
aliyun configure list

# 检查 CLI 版本
aliyun version
# 要求 >= 3.4.8

# 检查插件可用
aliyun dataphin-public --help
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 涉及的最小 RAM 权限（全部只读）：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:GetDataServiceApiCallSummary",
    "dataphin:GetDataServiceApiCallTrend",
    "dataphin:ListDataServiceApiCalls",
    "dataphin:ListDataServiceApiCallStatistics",
    "dataphin:GetDataServiceApiErrorImpact",
    "dataphin:ListDataServiceApiImpacts"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | CLI 参数名 | 含义 | 获取方式 | 必填 |
|------|-----------|------|---------|------|
| OpTenantId | `--op-tenant-id` | 租户 ID | profile 或询问用户 | 是 |
| ProjectId | `--project-id` | 项目 ID | 用户提供或查询 | 是 |
| StartTime | `--start-time` 或 `--list-query StartTime=` | 查询开始时间，格式：`yyyy-MM-dd HH:mm:ss` | 用户指定 | 是 |
| EndTime | `--end-time` 或 `--list-query EndTime=` | 查询结束时间，格式：`yyyy-MM-dd HH:mm:ss` | 用户指定 | 是 |
| ApiId | `--list-query ApiId=` | 目标 API ID | 用户提供（来自 S1） | `list-data-service-api-impacts` **必填**；`list-data-service-api-calls` 可选（过滤） |
| PageNo | `--list-query PageNo=` | 分页页码（list-* 命令用 PageNo，非 PageNum） | 默认 1 | 否 |
| PageSize | `--list-query PageSize=` | 每页条数 | 默认 20 | 否 |

**参数传入规则：**
- `get-*` 系命令：`--start-time`、`--end-time` 为独立参数（`yyyy-MM-dd HH:mm:ss` 格式）
- `list-*` 系命令：时间、分页、过滤条件均通过 `--list-query` JSON 对象传入，例：
  ```
  --list-query '{"StartTime":"2026-06-01 00:00:00","EndTime":"2026-06-30 23:59:59","PageNo":1,"PageSize":20}'
  ```

**时间参数格式**：`yyyy-MM-dd HH:mm:ss`（例：`2026-06-01 00:00:00`），6 个命令均使用此格式。

**API ID 获取说明：**
> ApiId 可通过 S1 `create-and-publish-api` 创建后获得，或通过 `list-data-service-published-apis` 查询。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 1：查看 API 调用汇总

获取指定项目下 API 的整体调用统计（总调用次数、成功率、平均耗时）。

```bash
aliyun dataphin-public get-data-service-api-call-summary \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --start-time "2026-06-01 00:00:00" \
  --end-time "2026-06-30 23:59:59" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}"
```

**响应处理：**
- 确认 `Code` 为 `OK`、`Success` 为 `true`
- 关注 `Data` 中：`CallCount`（总调用次数）、`ErrorCount`（失败次数）、`ErrorRate`（失败率）

### 步骤 2：分析调用趋势

按时间维度查看 API 的调用量、成功/失败趋势，用于发现异常波动。

```bash
aliyun dataphin-public get-data-service-api-call-trend \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --start-time "2026-06-01 00:00:00" \
  --end-time "2026-06-30 23:59:59" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}"
```

> 注意：`get-data-service-api-call-trend` 无 `--api-id` 参数，返回项目下全量趋势数据。

**响应处理：**
- 确认 `Code` 为 `OK`、`Success` 为 `true`
- 关注 `Data` 中：`CallErrorTrendList`（调用错误趋势）、`CallErrorImpactTrendList`（错误影响趋势）
- 若发现异常波动（如失败率突增），继续步骤 3 和 4 排查

### 步骤 3：查看调用日志明细

获取 API 的单次调用详情，包括调用时间、调用者、状态码、耗时、请求/响应内容。

```bash
aliyun dataphin-public list-data-service-api-calls \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --list-query '{"ApiId":{ApiId},"StartTime":"2026-06-01 00:00:00","EndTime":"2026-06-30 23:59:59","PageNo":1,"PageSize":20}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}"
```

> `list-*` 系命令的时间、分页、过滤条件均通过 `--list-query` JSON 对象传入，而非独立参数。

**响应处理：**
- 确认 `Code` 为 `OK`、`Success` 为 `true`
- 关注 `PageResult.CallLogList`（调用日志列表）和 `PageResult.TotalCount`（总条数）
- 翻页：增大 `PageNo` 获取更多记录

### 步骤 4：异常影响分析（问题排查时使用）

当发现异常调用时，分析错误的影响范围和受影响调用明细。

**4a. 获取异常影响汇总：**

```bash
aliyun dataphin-public get-data-service-api-error-impact \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --start-time "2026-06-01 00:00:00" \
  --end-time "2026-06-30 23:59:59" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}"
```

> 注意：`get-data-service-api-error-impact` 无 `--api-id` 参数，返回项目下所有 API 的异常汇总。

**4b. 获取异常调用明细：**

> **⚠️ 本命令 `ApiId` 必填**（实测不传直接返回 `DPN.Oltp.MgmtSys.ParamError：参数错误：apiId 不能为空`），与步骤 3 的 `list-data-service-api-calls`（ApiId 可选）不同。

```bash
aliyun dataphin-public list-data-service-api-impacts \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --list-query '{"ApiId":{ApiId},"StartTime":"2026-06-01 00:00:00","EndTime":"2026-06-30 23:59:59","PageNo":1,"PageSize":20}' \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/monitor-api-operations/{SESSION_ID}"
```

**响应处理：**
- 先看 4a 汇总中 `Data.ErrorApiList`（受影响 API）和 `Data.ErrorAppList`（受影响应用）
- 再看 4b 明细中 `PageResult.ImpactList`（异常调用明细列表），定位具体异常调用

## 9. Success Verification

采用两步验证法：

1. **返回码检查**：命令返回 `Code` 为成功
2. **数据完整性**：返回数据含预期统计字段（如调用次数 > 0、成功率在合理范围等）

> 注意：调用次数为 0 可能表示时间范围内无调用，不一定是错误。

## 10. Cleanup

纯只读操作，无资源需清理。

## 11. Command Tables

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-data-service-api-call-summary` | 查看 API 调用汇总 | 读 |
| `get-data-service-api-call-trend` | 分析调用趋势 | 读 |
| `list-data-service-api-calls` | 查看调用日志明细 | 读 |
| `list-data-service-api-call-statistics` | 调用统计列表 | 读 |
| `get-data-service-api-error-impact` | 异常影响汇总 | 读 |
| `list-data-service-api-impacts` | 异常调用明细 | 读 |

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **时间范围**：建议不超过 7 天，避免返回数据过多导致分析困难
- **排查顺序**：先看汇总（步骤 1）→ 趋势（步骤 2）→ 日志（步骤 3）→ 异常分析（步骤 4），逐步缩小范围
- **异常分析**：先看 `get-data-service-api-error-impact` 汇总再查看明细，快速定位问题
- **调用日志联动**：可配合 S3 `call-data-service-api` 的 session-id 过滤定位特定请求
- **大整数 ID**：ApiId、ProjectId 等 19 位 snowflake ID 在 `--list-query` JSON 中传整数即可，独立参数也无需引号
- **list-query JSON 格式**：`list-*` 系命令时间含空格，必须用 JSON 字符串传入（`'{"StartTime":"2026-06-01 00:00:00",...}'`），不可用 `key=value` 形式
- **get-* 命令无 ApiId 参数**：`get-data-service-api-call-summary`、`get-data-service-api-call-trend`、`get-data-service-api-error-impact` 均无 `--api-id` 参数，返回项目维度聚合数据
- **无写操作**：本 Skill 不涉及任何写操作，所有步骤均为只读查询
- **空数据正常**：无调用记录时返回空列表（`TotalCount: 0`），不代表命令出错
