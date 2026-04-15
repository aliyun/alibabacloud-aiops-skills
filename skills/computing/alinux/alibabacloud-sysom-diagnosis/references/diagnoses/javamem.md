# javamem（Java 内存诊断）

> 参数说明依据 `service_scripts/javamem_pre.py` 整理。

## 功能概述

对指定 **Java 进程**执行 SysOM javamem，输出 **`javamem.json`**，用于 JVM 内存分析。

## 何时选用（Agent）

- **Java 应用内存高、堆、JNI profiling** 等需云上采集时。

## `params` 字段

| 字段 | 类型 | 必填 | 含义 | 默认 | 备注 |
|------|------|------|------|------|------|
| `region` | string | 是* | 地域 | — | `--region` |
| `instance` | string | 是* | 实例 ID | — | `--instance` |
| `pod` | string | 否 | Pod 名 | — | 与 `Pid`/`pid` 至少其一配合使用 |
| `Pid` 或 `pid` | string/int | **条件** | Java 进程 PID | — | **`pod` 与 `pid` 至少填一个**（否则 INVALID_PARAMS） |
| `duration` | int | 否 | profiling 持续 **分钟数** | `"0"` | `0` 表示不追加 profiling |

### 校验

- 若 **既无 `pod` 也无 `pid`**：服务端返回 **参数无效**。

## 平台约束

| 项 | 值 |
|----|-----|
| support_channel | **all** |
| support_mode | **all** |
| 最低版本 | 常见 **`3.8.0-beta`** |

## 建议用法

**当前目录**：见 [README.md](./README.md)（在 `sysom-diagnosis/` 下使用 `./shared/scripts/osops`）。

```bash
./shared/scripts/osops memory javamem --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx \
  --params '{"pid":12345,"duration":5}'
```

按需把 `pid`/`Pod`/`duration` 放入 `--params-file`。长耗时加大 `--timeout`。
