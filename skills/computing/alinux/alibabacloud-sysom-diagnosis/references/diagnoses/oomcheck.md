# oomcheck（OOM 诊断）

> 参数说明依据 `service_scripts/oomcheck_pre.py` 整理。

## 功能概述

在目标实例上执行 SysOM oomcheck，结合 memgraph 输出路径分析 **OOM / oom-killer**。

## 何时选用（Agent）

- 云上 **OOM、oom-killer**、需 **SysOM 远程 OOM 诊断**。
- **勿**与父仓库 **linux-memory-oom / `sysom_cli memory oom`**（本机 dmesg）混淆。

## Agent 操作约定

通用约定（执行目录、Bash 执行、本机/远程区分、凭证安全）见 [agent-conventions.md](../agent-conventions.md)。以下仅列 oomcheck 特有规则。

### 多次 OOM

- 本机 quick 显示多次 OOM 时，可用 `--oom-at` 锚定某次。
- 远程 oomcheck 须用 `--oom-time` 或 `--params` 中的 `time`；**禁止**在用户已指定时刻时仍走无时间限定的默认命令。

### 时间格式

- CLI 支持 ISO、`YYYY-MM-DD HH:MM:SS`、Unix 秒、journal 风格等；发起 Invoke 前会自动转为 Unix 秒。

## `params` 字段

| 字段 | 类型 | 必填 | 含义 | 默认 | 备注 |
|------|------|------|------|------|------|
| `region` | string | 是* | 地域 | — | `--region` |
| `instance` | string | 是* | 实例 ID | — | `--instance` |
| `pod` | string | 否 | Pod 名 | `""` | 非空追加 `-p` |
| `time` | string | 否 | OOM 发生时间或 `开始~结束` | `""` | CLI `--oom-time`；自动转 Unix 秒 |

## 平台约束

| 项 | 值 |
|----|-----|
| support_channel | **all** |
| support_mode | **all** |

## 建议用法

本机（CLI 自动补全 region/instance）：

```bash
./shared/scripts/osops memory oom --deep-diagnosis --channel ecs --timeout 300
```

远程实例：

```bash
./shared/scripts/osops memory oom --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx --timeout 300
```

本机 quick 专用选项：`--oom-at`（锚定时间）、`--max-oom-summaries`（默认 64）、`--max-oom-full-logs`（默认 1）。
远程：`--oom-time` 写入 `params.time`（自动转 Unix 秒）。历史窗口务必 **≤1 小时、7 天内**。
