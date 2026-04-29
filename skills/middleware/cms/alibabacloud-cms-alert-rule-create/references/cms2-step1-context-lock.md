# CMS 2.0 步骤 1：上下文锁定（datasourceConfig + workspace）

## 目的

构建 CMS 2.0 告警规则的 datasourceConfig 和 workspace。此步骤决定使用哪个监控系统、实例和工作空间。

---

## workspace 参数（必填）

所有 CMS 2.0 API 调用都需要 `workspace` 参数。

| 字段 | 类型 | 是否必填 | 获取方式 |
|-------|------|----------|---------------|
| `workspace` | string | **是** | **必须询问用户获取** |

> workspace 是 CMS 2.0 API 的必传参数，其值不一定以 `default` 开头，格式不固定，**必须向用户询问获取**，不可自行构造。

---

## datasourceConfig 结构

| 字段 | 类型 | 是否必填 | 说明 |
|-------|------|----------|-------------|
| `type` | string | 是 | 数据源类型：`PROMETHEUS`、`APM`、`UMODEL` |
| `instanceId` | string | 按需 | Prometheus 实例 ID（type=PROMETHEUS 时使用）；APM 应用 service_id（type=APM 时使用） |
| `regionId` | string | 否 | 地域 ID（各类型可选，缺省与规则/网关一致） |

---

## 各类型配置说明

### Prometheus

> **⚠️ 必须向用户询问 `cluster_id`（即 Prometheus 实例 ID，对应 `datasourceConfig.instanceId`）和 `workspace`。这两个参数必须由用户提供，不可猜测、不可省略、不可自动构造。**

| 字段 | 获取方式 | 是否必填 |
|-------|---------------|----------|
| `cluster_id` (instanceId) | **🔴 必须询问用户** — 即 Prometheus 实例 ID | **是** |
| `workspace` | **🔴 必须询问用户** — 不可自行构造 | **是** |

```json
{
  "type": "PROMETHEUS",
  "instanceId": "{user_provided_cluster_id}",
  "regionId": "cn-hangzhou"
}
```

- `cluster_id` 就是 Prometheus 实例的 instanceId，用户可在 ARMS 控制台或 Prometheus 实例列表中找到
- 获取 cluster_id 和 workspace 后，再根据用户的监控需求（如 CPU、内存、Pod 重启等）生成对应的 PromQL

### APM

> **⚠️ 必须向用户询问 `service_id`（用于 `datasourceConfig.instanceId`）和 `workspace`。这两个参数必须由用户提供，不可猜测、不可省略、不可自动构造。**

| 字段 | 获取方式 | 是否必填 |
|-------|---------------|----------|
| `service_id` (instanceId) | **🔴 必须询问用户** — APM 应用 ID，传入 datasourceConfig.instanceId | **是** |
| `workspace` | **🔴 必须询问用户** — 不可自行构造 | **是** |

```json
{
  "type": "APM",
  "instanceId": "{user_provided_service_id}",
  "regionId": "cn-hangzhou"
}
```

> **重要**：根据官方 API 文档，当 type=APM 时，instanceId 传入的就是 service_id。service_id 是 APM 应用的唯一标识，用户可在 ARMS 控制台的应用列表中找到。

### UModel

> **⚠️ 必须向用户询问 `workspace`。此参数必须由用户提供，不可猜测、不可省略、不可自动构造。**

| 字段 | 获取方式 | 是否必填 |
|-------|---------------|----------|
| `workspace` | **🔴 必须询问用户** — 不可自行构造 | **是** |

```json
{
  "type": "UMODEL",
  "regionId": "cn-hangzhou"
}
```

UModel 不需要 instanceId — 实体选择在 queryConfig 中完成。

---

## 必填参数检查清单

- [ ] workspace 已从用户处获取 — **🔴 必须询问用户**（必须向用户询问获取，不可自行构造）
- [ ] datasourceConfig.type 已确认（PROMETHEUS / APM / UMODEL）
- [ ] **Prometheus**：`cluster_id` 已从用户处获取 — **🔴 必须询问用户**（即 instanceId，不可猜测）
- [ ] **APM**：`service_id` 已从用户处获取 — **🔴 必须询问用户**（用于 datasourceConfig.instanceId，不可编造）
- [ ] regionId 已确认（或使用默认值，缺省与规则/网关一致）

---

## 下一步
→ `cms2-step2-query-config.md`
