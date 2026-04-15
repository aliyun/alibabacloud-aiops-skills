# 内存域：快速排查与 SysOM 专项（Agent 补充）

本页**不重复** [SKILL.md](../SKILL.md) 中的「诊断能力总览」表；仅归纳 **内存相关命令** 与 **下一步读哪**。

## 何时用哪条入口

**原则**：优先匹配用户表述是否已对应某一 **专项**（下表前几行）；**无法匹配或意图明显模糊**时，再用最后一行 **`memory classify`** 综合归类。

| 意图 | 建议 |
|------|------|
| 内存占用高、要看整机/应用内存大图与组成拆解；怀疑 **TCP 内存高 / socket 队列积压**；或**主诉延迟/卡顿**且 **`ss` 显示 Send-Q/Recv-Q 偏大** | `./shared/scripts/osops memory memgraph` |
| 明确怀疑 OOM / 要看内核 oom-killer 线索 | `./shared/scripts/osops memory oom` |
| 明确 Java 内存 / JVM | `./shared/scripts/osops memory javamem` |
| Go 相关弱特征或需语言侧细节（非 Java） | `./shared/scripts/osops memory memgraph`（全景）；已确认 Java 时用 `javamem` |
| 不明确、需综合归类（meminfo + OOM 线索 + RSS 合一） | `./shared/scripts/osops memory classify` |

各命令 stdout 信封中请关注 **`agent.next`**（环境已通过时常仅一条深度命令；否则可含 precheck 步骤）、**`agent.findings`**（关键指标摘要）、**`data.routing`** / **`data.local`**。路由到 **oomcheck** 时另见 [oomcheck.md](./diagnoses/oomcheck.md)「Agent 操作约定」。**`data`** 侧不放 `next_steps`；**`--verbose-envelope`** 只加长 **`agent.summary`**。

## 可选：一步完成专项

在 **`memory memgraph` / `oom` / `javamem` / `classify`** 上加 **`--deep-diagnosis`**（并可传 `--region` / `--instance` / **`--params` / `--params-file`** 等与 [invoke-diagnosis.md](./invoke-diagnosis.md) 专项约定一致的选项），可发起**深度诊断**；**`memory oom`** 还可传 **`--oom-time`** 写入 oomcheck 的 `time`。本地入口加 `--deep-diagnosis` 时以远程专项为主，合并结果见 **`data.remote`**。**本机诊断**的示例命令**勿**写 `--region`/`--instance`；**仅诊断其它 ECS** 且用户已提供时再写入这两项。

远程路径会**内建**与 precheck 相同的环境检查；**可选**单独执行 **`./shared/scripts/osops precheck`** 做自检或排障。

## 专项参数与契约

各 `service_name` 的 **params**、边界：仅读 [diagnoses/](./diagnoses/) 下对应专文；请求体与元数据补全：[invoke-diagnosis.md](./invoke-diagnosis.md)。
