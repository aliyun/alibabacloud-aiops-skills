---
name: check-compute-source-connectivity
description: |-
  校验计算源连通性（不会实际创建，仅测试连接）。 触发场景：测试计算源连接 / 检查计算源是否可达 / 创建计算源前先验证 / check-compute-source-connectivity。 CheckCommand.Type 决定 ConfigList 内 Key/Value 的组合，与 create-maxcompute-compute-source 同构。 触发词：测试计算源连接、检查计算源连通性、check-compute-source-connectivity、验证计算源。
---
# 校验计算源连通性 skill

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

参照 `create-maxcompute-compute-source`（经套件入口路由加载） 的“其他 Type”表；先用 `get-compute-source --compute-source-id <N>` 读出现有 ConfigList，再做 Check。

## 返回判读

- `Success: true` + `CheckResult.Connected: true` → 配置可用
- `Connected: false` → 看 `Reason` 字段：
  - `InvalidAK` → ak/sk 错
  - `ProjectNotFound` → endpoint / project 不匹配
  - `timeout` → 网络不通，检查 Dataphin 到 endpoint 的网络路由

## 常见坑

1. **Type 与数据源不同**：计算源用驼峰 `MaxCompute`，数据源用大写下划线 `MAX_COMPUTE`
2. **endpoint 必须带 https + /api**：例如 `https://service.cn-shanghai.maxcompute.aliyun.com/api`
3. **Check 通过 ≠ Create 通过**：Create 还会校验 project 不被其他计算源占用

## 相关命令

- `create-maxcompute-compute-source`（经套件入口路由加载）
- [update-compute-source.md](./update-compute-source.md)
- `aliyun dataphin-public check-compute-source-connectivity-by-id --compute-source-id <N>` — 按已存在计算源 Id 校验
