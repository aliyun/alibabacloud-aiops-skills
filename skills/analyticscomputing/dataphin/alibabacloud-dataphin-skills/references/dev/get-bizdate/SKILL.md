---
name: get-bizdate
description: |-
  获取真实系统日期 / 业务日期（bizdate）。 触发场景：任何需要“今天/昨天/当前日期”的场景，包括补数据填 start-biz-date / 即席查询传日期参数 / 任务参数模板 $bizdate / 授权 effective-end。 核心规则：bizdate = T-1（昨天）；禁止使用会话上下文中的 system time（是快照不可信）；必须用 date 命令实时获取。 平台差异：macOS 用 date -v-1d，Linux 用 date -d "-1 day"。 触发词：今天日期、昨天日期、当前日期、bizdate、业务日期、T-1、补数据日期、system time。
---
# 获取当前日期 / 业务日期 skill

## 背景知识（必读）

- **会话上下文中的 system time 不可信**：Qoder 等 IDE 在系统提示里给的 "current system time" 是**会话创建时刻**的快照，与"现在"可能差几小时甚至几天，在跨日 / 跨小时取数场景下产生错位。
- **Dataphin bizdate 默认 = T-1**：Dataphin 调度日 `cyctime` 凌晨执行，产出**业务归属日期 = 调度日 - 1** 的数据。命令 / API 中所有 `bizdate` 入参都按此惯例，除非业务明确"业务日 = 调度日"。
- **bizdate 是无时区日期串**：调度系统按各租户配置时区计算"昨天"，编排时使用 `yyyymmdd`（无分隔符）或 `yyyy-MM-dd`（API 文档示例）。

## 适用场景

- 补数据：`ops create-node-supplement --start-biz-date / --end-biz-date`
- 即席查询 / 手动触发：填 bizdate 入参
- 任务参数模板替换：`${bizdate}` / `${yyyymmdd}` / `${yyyy-MM-dd}`
- 任何需要"今天 / 昨天 / N 天前"的脚本逻辑

## 标准取值命令

```bash
# 今天（YYYYMMDD）
TODAY=$(date "+%Y%m%d")

# 业务日期 bizdate（T-1）
# macOS / BSD:
BIZDATE=$(date -v-1d "+%Y%m%d")
# Linux / GNU:
BIZDATE=$(date -d "-1 day" "+%Y%m%d")

echo "今天=$TODAY 业务日期(T-1)=$BIZDATE"
# => 今天=20260520 业务日期(T-1)=20260519
```

## 跨平台兼容写法（推荐）

```bash
# 自动适配 macOS / Linux
if date -v-1d "+%Y%m%d" >/dev/null 2>&1; then
  BIZDATE=$(date -v-1d "+%Y%m%d")          # macOS
else
  BIZDATE=$(date -d "-1 day" "+%Y%m%d")    # Linux
fi
```

## 常见格式速查

| 用途 | 命令 | 示例输出 |
|---|---|---|
| `yyyymmdd`（CLI bizdate） | `date "+%Y%m%d"` | `20260520` |
| `yyyy-MM-dd`（API 文档示例） | `date "+%Y-%m-%d"` | `2026-05-20` |
| `yyyy-MM-dd HH:mm:ss`（如 `effective-end`） | `date "+%Y-%m-%d %H:%M:%S"` | `2026-05-20 16:43:19` |
| 完整 ISO + 时区（落地排查） | `date "+%Y-%m-%d %H:%M:%S %Z"` | `2026-05-20 16:43:19 CST` |
| 毫秒时间戳 | macOS: `echo $(($(date +%s) * 1000))`；Linux: `date "+%s%3N"` | `1747728199000` |
| 任意 N 天前 | macOS: `date -v-Nd "+%Y%m%d"`；Linux: `date -d "-N day" "+%Y%m%d"` | — |

## ✗ 禁止做法

| 反模式 | 为什么不行 |
|---|---|
| 直接用上下文中的 `current system time: 2026-05-20 ...` 当成"现在" | 那是会话创建时刻；如已聊了几小时跨午夜，bizdate 会早 1 天 |
| Agent 凭"训练知识"猜今天日期 | 训练截止 ≠ 当前；时间观念严重失真 |
| 用 `git log -1 --format=%cd` 取最新提交时间 | 与"现在"无关，且依赖仓库状态 |

## 与上下游 skill 衔接

- 补数据前必跑：见 [create-node-supplement.md](./create-node-supplement.md) 章节"完整命令链"步骤 1
- 授权时填长期有效：`--effective-end "3025-12-31 23:59:59"`，见 [grant-data-source-permission.md](./grant-data-source-permission.md)
- 即席查询用 bizdate 过滤：见 [execute-ad-hoc-task.md](./execute-ad-hoc-task.md)

## 相关命令

- `date`（系统命令） — 真实日期 / 时间唯一可靠来源
- 内置 skill `get-current-date` — Qoder 提供的同等能力（IDE 内调用）
