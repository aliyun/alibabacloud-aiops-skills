# CLI 输出信封格式（sysom-diagnosis）

本文件从 SKILL.md 迁出，描述 `osops` CLI stdout JSON 信封的字段结构与读取约定。

## 信封版本

- **`format`**: `sysom_agent`
- **`version`**: `3.4`（字段契约版本；删改已承诺的 data/agent 键时递增）

## 顶层结构

| 字段 | 说明 |
|------|------|
| `ok` | 布尔，成功/失败 |
| `action` | 命令动作标识（`memory_classify`、`memory_memgraph_hint` 等） |
| `error` | 失败时含 `code`/`message`/`request_id`（若有） |
| `agent` | 供模型读取的摘要与引导（见下） |
| `data` | 业务载荷（见下） |
| `execution` | 执行元信息（`subsystem`、`phase`、`mode`） |

## `agent` 块

| 字段 | 说明 |
|------|------|
| `summary` | 一段话摘要；**`--verbose-envelope`** 展开完整版 |
| `findings` | 发现列表，每条含 `kind` 与关键指标 |
| `next` | 结构化下一步（`action_kind`/`command`/`purpose_zh`）；成功深度诊断后为空 |

## `data` 块（memory quick 路径）

| 字段 | 说明 |
|------|------|
| `data.routing` | 路由结果：`recommended_service_name`/`confidence`/`categories`/`oom_signal` 等 |
| `data.local` | 本机快照：`facts`/`oom_local`/`meminfo_facts`/`rss_top_sample` |
| `data.remote` | 仅 `--deep-diagnosis` 时出现：`ok`/`task_id`/`result`/`error` |

## CLI 可调项

- **通用选项**：`--channel`、`--region`、`--instance`、`--timeout`、`--poll-interval`、`--verbose-envelope`
- **专项参数**：通过 **`--params`（JSON 字符串）或 `--params-file`（JSON 文件）** 传入 OpenAPI `params`，字段见 [diagnoses/](./diagnoses/) 对应专文
- **本机 memory quick**（未加 `--deep-diagnosis`）：默认策略固定，可调项走远程专项 + `--params`
