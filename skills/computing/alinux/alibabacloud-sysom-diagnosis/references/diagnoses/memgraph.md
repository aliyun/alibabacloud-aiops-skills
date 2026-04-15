# memgraph（内存大盘 / 内存全景）

> 参数说明依据 SysOM 诊断侧脚本与 OpenAPI 行为整理。

## 功能概述

在目标实例上执行 SysOM memgraph 采集，生成 **`memgraph.json`** 回传，用于 **内存全景 / 内存大盘** 分析。覆盖 **整机/应用维度的内存组成**，部分版本还支持 **TCP 内存 / socket 队列** 等网络侧视角。Agent 结论应结合用户现象与回传 JSON，勿仅凭本机 `/proc` 粗检。

## 何时选用（Agent）

- 需要 **整体内存分布、各类占用**；或怀疑 **TCP / socket 队列** 参与内存压力时。
- 用户主诉延迟/卡顿且 **`ss` 显示 Send-Q/Recv-Q 偏大**：应加做 **`memory memgraph --deep-diagnosis`**。
- OOM 排查链路中需要 memgraph 结果（与 **oomcheck** 数据路径相关）。

## `params` 字段（JSON 对象，经 InvokeDiagnosis 作字符串传入）

| 字段 | 类型 | 必填 | 含义 | 默认 | 备注 |
|------|------|------|------|------|------|
| `region` | string | 是* | 地域 ID | — | CLI `--region` 可合并写入 |
| `instance` | string | 是* | ECS 实例 ID 或目标标识 | — | CLI `--instance` 可合并写入 |
| `pod` | string | 否 | Pod 名（容器场景） | `""` | 非空时命令追加 `-p <pod>` |
| `profiling_on` | bool | 否 | 是否开启 profiling | `false` | 高版本才生效 |
| `pid` | string/int | 否 | 进程 PID | `null` | 与 `profiling_on` 配合 |
| `duration` | int | 否 | profiling 持续 **分钟数** | `0` | `0` 表示不追加 profiling |

\* 在 **sysom-diagnosis（技能根）** 执行、且 **`--region` / `--instance` 由 CLI 从元数据或命令行合并进 `params`** 时，JSON 内可不写二者。

## 平台约束

| 项 | 值 |
|----|-----|
| support_channel | **all** |
| support_mode | **all**（node / pod） |
| 最低版本 | 常见 node **`3.6.0-1`** |

## 建议用法

**当前目录**：须在 **sysom-diagnosis（技能根）**（存在 `shared/scripts/osops`）下执行；若不在该目录，使用 `cd <sysom-diagnosis> && …`（说明见 [README.md](./README.md) 中「运行命令时的当前目录」）。在任意工作目录下直接执行 `./shared/scripts/osops` 会报「未找到」。

```bash
# Agent：直接走内存全景专项（常见「内存高、要大图拆解」主路径）
cd <sysom-diagnosis> && ./shared/scripts/osops memory memgraph --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx --timeout 300
```

不确定归类时用 **`memory classify --deep-diagnosis`**。复杂 profiling 时用 `--params-file` 传 JSON；长耗时加大 `--timeout`。
