---
name: check-compute-source-connectivity
description: |-
  校验计算源连通性（不会实际创建，仅测试连接）。 触发场景：测试计算源连接 / 检查计算源是否可达 / 创建计算源前先验证 / check-compute-source-connectivity。 CheckCommand.Type 决定 ConfigList 内 Key/Value 的组合，与 create-maxcompute-compute-source 同构。 触发词：测试计算源连接、检查计算源连通性、check-compute-source-connectivity、验证计算源。
---
# 校验计算源连通性 skill

调用 CLI / SDK 前，继承[父技能 §7](../../../SKILL.md#7-observability) 初始化的 session-id 与套件 `references/manifest.json` 中的 `version`；直接加载时先完成父层初始化。API 命令统一附带 `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"`，使用父技能名称与同一会话、版本。

## 适用场景

- 建计算源前先验证 ak/sk + endpoint + project 是否正确
- 轮换 AccessKey 之后做预检
- 排查任务启动失败是否因为计算源不通

## 命令 & 官方文档

- CLI：`aliyun dataphin-public check-compute-source-connectivity --help`
- OpenAPI：[CheckComputeSourceConnectivity](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CheckComputeSourceConnectivity)

## 顶层参数骨架

```text
--tenant-id <int>       必填 | 租户 ID
--check-command <JSON>     必填 | 连通性校验体
```

## CheckCommand JSON 结构

```jsonc
{
  "Type": "<枚举值>",         // 必填，同 create-maxcompute-compute-source
  "ConfigList": [             // 必填
    { "Key": "<k>", "Value": "<v>" }
  ]
}
```

## Type 与 Key 规则

**与 `create-maxcompute-compute-source`（经套件入口路由加载） 完全同构。** 详细枚举与 Key 清单见该 skill。

### ✓ MaxCompute（verified）

```bash
aliyun dataphin-public check-compute-source-connectivity \
  --tenant-id <tenant-id> \
  --check-command '{
    "Type": "MaxCompute",
    "ConfigList": [
      { "Key": "maxcompute.endpoint",  "Value": "<maxcompute-endpoint>" },
      { "Key": "maxcompute.project",   "Value": "<project-name>" },
      { "Key": "maxcompute.accessId",  "Value": "<ak_id>" },
      { "Key": "maxcompute.accessKey", "Value": "<ak_secret>" }
    ]
  }'
```

### ⚠ 其他 Type（unverified）

参照 `create-maxcompute-compute-source`（经套件入口路由加载） 的“其他 Type”表。

> **不要指望用 `get-compute-source` 读出 ConfigList**（[实测确认]）：该命令只返回元信息（`Id`/`Name`/`DisplayName`/`Description`/`Type`/`Owner*`/`Creator*`/`GmtCreate`/`GmtModified`/`BindProject*`），**响应中没有 `ConfigList` 字段**，且它仅接受 `--compute-source-id` 与 `--tenant-id` 两个参数，没有任何开关能带出配置。因此对已存在的非 MaxCompute 计算源，**只能用 `check-compute-source-connectivity-by-id`**（无需自己拼 ConfigList）；配置式 `check-compute-source-connectivity` 仅适用于“建之前先验证一组手头上的配置”。

## 返回判读

> **以下为真机实测结果（独立部署 6.3）。连通标志在**顶层 `Data`（布尔）**，不存在 `CheckResult` 对象，也不存在 `Reason` 字段。**

`check-compute-source-connectivity-by-id` 成功响应：

```json
{ "Code": "OK", "Data": true, "HttpStatusCode": 200, "Success": true }
```

判读规则：

- `Code == "OK"` 且 `Data == true` → 计算源可达
- 失败信息**全部在顶层 `Code` + `Message`**，需按错误码分流（实测）：

| Code | HTTP | 含义 | 处理 |
|---|---|---|---|
| `DPN.ComputeEngine.ComputeEngineNotFound` | 400 | 计算源 Id 不存在（或不属于该租户） | 核对 `compute-source-id` 与 `tenant-id` |
| `Dataphin.OpenAPI.BadGateway` | 502 | 计算源存在，但服务端去连集群时失败 | 排查 Dataphin 服务端 ↔ 集群的网络 / Kerberos / 引擎插件状态 |
| `DPN.Filter.NoPermission` | 400 | 当前账号无权限 | 按 §RAM 申请权限或加入项目成员 |
| `DPN.Commons.InternalError` | 400 | 配置式调用传入非法 ConfigList | 不要拿它当“AK 无效”的信号，它对非法配置的错误归类很粗 |

> **区分“计算源不存在”与“集群不通”的关键**：前者固定返 `ComputeEngineNotFound`，后者返 502。实测对比：同一命令对健康 MaxCompute 计算源返 `Data: true`，对不通的 CDP 集群稳定返 502——因此 **502 不是接口坏了，而是目标集群不可达**。

## 常见坑

1. **Type 与数据源不同**：计算源用驼峰 `MaxCompute`，数据源用大写下划线 `MAX_COMPUTE`
2. **endpoint 必须带 https + /api**：例如 `https://service.cn-shanghai.maxcompute.aliyun.com/api`
3. **Check 通过 ≠ Create 通过**：Create 还会校验 project 不被其他计算源占用
4. **不要取 `CheckResult.Connected`**（[实测确认]）：响应里没有这个对象，取到的是 null，会把“已连通”误判为“不连通”。用 `--cli-query 'Data'`
5. **不要依赖 `Reason` 做分类**（[实测确认]）：`InvalidAK` / `ProjectNotFound` / `timeout` 这组分类在实际响应中不存在，按上表顶层 `Code` 分流
6. **Check 通过也不保证 HDFS 可写**：对 Hadoop 计算源，本命令具体探测哪些组件（NameNode / Hive Metastore / YARN）未确认；实测出现过“连通性 `Data: true` 但 `create-resource` 仍因 HDFS 写入报错”的情况，因此它只能当**预警信号**，不能当成功保证

## 相关命令

- `create-maxcompute-compute-source`（经套件入口路由加载）
- [update-compute-source.md](./update-compute-source.md)
- `aliyun dataphin-public check-compute-source-connectivity-by-id --compute-source-id <N>` — 按已存在计算源 Id 校验
