---
name: update-compute-source
description: |-
  编辑/更新已存在的计算源配置。 触发场景：修改计算源配置 / 更新计算源密码 / 调整计算源参数 / update-compute-source。 UpdateCommand 需要 Id，Type + ConfigList 的 Key 规则与 create-maxcompute-compute-source 完全相同。 触发词：修改计算源、更新计算源、编辑计算源、update-compute-source。
---
# 编辑计算源 skill

## 适用场景

- 修改计算源 Name / Description
- 更新 ConfigList（如轮换 AccessKey、调整 endpoint）
- 迁移 MaxCompute project（需谨慎，此操作可能影响已运行任务）

## 命令 & 官方文档

- CLI：`aliyun dataphin-public update-compute-source --help`
- OpenAPI：[UpdateComputeSource](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/UpdateComputeSource)

## 顶层参数骨架

```text
--tenant-id <int>          必填 | 租户 ID
--update-command <JSON>       必填 | 更新命令体
```

## UpdateCommand JSON 结构

```jsonc
{
  "Id": <int>,                  // 必填，计算源 Id（先调 list-compute-sources 获取）
  "Name": "<string>",           // 必填，即便不改也要传原值
  "Description": "<string>",    // 必填
  "Type": "<枚举值>",            // 必填，值与 create-maxcompute-compute-source 完全一致，原则上不建议改 Type
  "ConfigList": [               // 必填，传完整清单（非增量）
    { "Key": "<k>", "Value": "<v>" }
  ]
}
```

## Type 与 Key 规则

**与 `create-maxcompute-compute-source`（经套件入口路由加载） 完全同构。** 详细枚举与 Key 清单见该 skill。

### ✓ MaxCompute（verified）

```bash
# 轮换 MaxCompute AccessKey 示例
aliyun dataphin-public update-compute-source \
  --tenant-id <tenant-id> \
  --update-command '{
    "Id": <compute-source-id>,
    "Name": "<compute-source-name>",
    "Description": "MaxCompute prod compute source (rotated)",
    "Type": "MaxCompute",
    "ConfigList": [
      { "Key": "maxcompute.endpoint",  "Value": "<maxcompute-endpoint>" },
      { "Key": "maxcompute.project",   "Value": "<project-name>" },
      { "Key": "maxcompute.accessId",  "Value": "<new_ak_id>" },
      { "Key": "maxcompute.accessKey", "Value": "<new_ak_secret>" }
    ]
  }'
```

### ⚠ 其他 Type（unverified）

同 `create-maxcompute-compute-source`（经套件入口路由加载） 中的“其他 Type”表；通过 `get-compute-source --compute-source-id <N>` 读取现有 ConfigList 再做最小修改。

## 常见坑

1. **ConfigList 必须全量传**：update 不是 patch，漏传的 Key 会被清空
2. **改 MaxCompute project 不等于迁移**：只是改了计算源指向的 project；已发布到旧 project 的任务不会自动迁移
3. **Type 原则上不可改**：由 A 类型改成 B 类型通常会报错；如需更换请删后重建
4. **Id 必须是 Long**：注意 shell 里大整数不要被截断（JSON 里写成数字即可，不用加引号）

## 相关命令

- `create-maxcompute-compute-source`（经套件入口路由加载）
- [check-compute-source-connectivity.md](./check-compute-source-connectivity.md) — 改完再校验
- `aliyun dataphin-public get-compute-source --compute-source-id <N>` — 读取当前 ConfigList 作为 update 模板
