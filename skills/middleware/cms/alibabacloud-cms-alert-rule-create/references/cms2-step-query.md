# CMS 2.0：查询告警规则

## 目的

查询已有的 CMS 2.0 告警规则（Prometheus/APM/UModel），支持灵活过滤。

---

## API 请求结构

```
POST /queryAlertRules
API 版本: 2024-03-30
Endpoint:    metrics.{regionId}.aliyuncs.com

顶层参数:
- maxResults (integer, 可选) — 分页大小
- nextToken  (string, 可选)  — 分页令牌
- clientToken (string, 可选) — 幂等令牌
- body (QueryAlertRulesInput, 必填) — 请求体

QueryAlertRulesInput:
- workspace  (string, 必填)        — Workspace，必须向用户询问获取
- filter     (QueryAlertRulesFilter)    — 过滤条件
- pagination (Pagination)              — 分页配置
```

> **workspace 是必传参数**，必须向用户询问获取，不可自行构造（其值不一定以 `default` 开头）。

> **注意**：过滤字段放在 `body.filter` 内部，而非 body 顶层。
> `QueryAlertRulesFilter` 支持的完整字段需参考官方 API 文档。基于响应结构推断的常用过滤模式包括按 `datasourceConfig.type`、`displayName`、`status`、`enabled` 等字段过滤。

---

## CLI 命令

```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-cms-alert-rule-create"

# 基本查询（带分页）
aliyun cms query-alert-rules \
  --max-results 100 \
  --body '{
    "workspace": "{user_provided_workspace}"
  }'

# 带过滤条件的查询
aliyun cms query-alert-rules \
  --max-results 50 \
  --body '{
    "workspace": "{user_provided_workspace}",
    "filter": {
      <filter-fields>
    }
  }'
```

---

## 可用参数

| 参数 | 位置 | 类型 | 是否必填 | 说明 | 示例 |
|-----------|----------|------|----------|-------------|---------|
| `maxResults` | 顶层 | integer | 否 | 分页大小 | `50`、`100` |
| `nextToken` | 顶层 | string | 否 | 上一次响应返回的分页令牌 | `""`（首页） |
| `body.workspace` | body | string | **是** | Workspace，必须向用户询问获取 | （用户提供） |
| `body.filter.datasourceConfig.type` | body.filter | string | 否 | 按告警类型过滤 | `PROMETHEUS`、`APM`、`UMODEL` |
| `body.filter.datasourceConfig.instanceId` | body.filter | string | 否 | 按数据源实例过滤 | Prometheus 实例 ID |
| `body.filter.*` | body.filter | — | 否 | 其他过滤字段参见 API 文档 | 参见 API 文档 |

> **重要**：`filter` 的完整字段定义需参考官方 API 文档（`QueryAlertRulesFilter`），上表仅列出基于响应结构推断的常用字段。

---

## 常用查询示例

### 列出所有规则（全量扫描）

```bash
aliyun cms query-alert-rules \
  --max-results 100 \
  --body '{
    "workspace": "{user_provided_workspace}"
  }'
```

### 列出所有 Prometheus 告警规则

```bash
aliyun cms query-alert-rules \
  --max-results 50 \
  --body '{
    "workspace": "{user_provided_workspace}",
    "filter": {
      "datasourceConfig": {"type": "PROMETHEUS"}
    }
  }'
```

### 列出所有 APM 告警规则

```bash
aliyun cms query-alert-rules \
  --max-results 50 \
  --body '{
    "workspace": "{user_provided_workspace}",
    "filter": {
      "datasourceConfig": {"type": "APM"}
    }
  }'
```

### 列出所有 UModel 规则

```bash
aliyun cms query-alert-rules \
  --max-results 50 \
  --body '{
    "workspace": "{user_provided_workspace}",
    "filter": {
      "datasourceConfig": {"type": "UMODEL"}
    }
  }'
```

### 分页查询（下一页）

```bash
aliyun cms query-alert-rules \
  --max-results 50 \
  --next-token "<token-from-previous-response>" \
  --body '{
    "workspace": "{user_provided_workspace}"
  }'
```

---

## 响应结构

```json
{
  "data": {
    "totalCount": 0,
    "alertRules": [...]
  },
  "code": "",
  "success": true,
  "requestId": "",
  "nextToken": ""
}
```

### 每条 `alertRule` 的关键字段

| 字段 | 说明 |
|-------|-------------|
| `uuid` | 告警规则 UUID |
| `displayName` | 规则显示名称 |
| `status` | 当前状态 |
| `enabled` | 是否启用 |
| `workspace` | 工作空间 |
| `datasourceConfig.type` | 告警类型（`PROMETHEUS` / `APM` / `UMODEL`） |
| `datasourceConfig.instanceId` | 数据源实例 ID |
| `datasourceConfig.regionId` | 地域 |
| `queryConfig.type` | 查询类型 |
| `queryConfig.promQl` | PromQL 表达式（Prometheus） |
| `conditionConfig.severity` | 严重等级（P1-P4） |
| `conditionConfig.operator` | 比较运算符 |
| `conditionConfig.threshold` | 告警阈值 |
| `conditionConfig.durationSecs` | 持续时间（秒） |
| `scheduleConfig.intervalSecs` | 检测间隔（秒） |
| `notifyConfig.channels` | 通知渠道 |
| `notifyConfig.silenceTimeSecs` | 静默时间（秒） |
| `labels` | 标签（键值对） |
| `annotations` | 注解（键值对） |
| `createdAt` | 创建时间 |
| `updatedAt` | 最后更新时间 |

---

## 工作流程

1. 识别用户的查询意图和所需过滤条件
2. 向用户询问获取 workspace 值
3. 使用 `--max-results` 和 `--body '{"workspace": "...", "filter": {...}}'` 构建 query-alert-rules 请求
4. 执行查询 CLI 命令
5. 解析响应：结果在 `data.alertRules` 中，使用 `nextToken` 进行分页
6. 格式化并向用户展示结果
7. 如果用户需要修改/删除，使用 manage-alert-rules 并设置 action=UPDATE/BATCH_DELETE
