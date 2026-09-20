# 数据校验 Python SDK Troubleshooting 排错指引

当通过 Python SDK 调用接口遇到异常时，按以下症状定位和处理。

---

## 1. 通用错误

| 症状 | 诊断 | 处理 |
|------|------|------|
| `resp.body.success == False` | 接口调用失败 | 读取 `resp.body.err_message` 原文反馈给用户，不自行猜测原因 |
| `AliyunCliError`（code=CLI_NOT_FOUND） | aliyun CLI 未安装 | 安装 aliyun CLI（>= 3.3.8）：https://help.aliyun.com/cli/ |
| `AliyunCliError`（code=CLI_TIMEOUT） | CLI 调用超时 | 检查网络连通性；重试即可 |
| `ModuleNotFoundError: lhm_models` | request 模型层未加载 | request 模型由本地 `scripts/lhm_models.py` 提供；`common.py` 会自动把自身所在目录插入 `sys.path`，若从其他目录直接运行脚本，需保证 `scripts/` 可被 import |
| 插件报 command not found | aliyun-cli-lhm 插件未安装或版本过旧 | `aliyun plugin install --names lhm --source-base https://cli.aliyun-inc.com/registry_id/2/env/pre/plugins` |
| `E500R103: ...cannot contain special characters...` | task_name 含非法字符 | task_name 只允许英文字母、中文字符和数字；方括号 `[]`、冒号 `:`、连字符 `-`、空格等**均不可用** |
| `RemoteDisconnected` / `ConnectionResetError` / `ConnectionError` during polling | 服务端超时或网络抖动断开连接 | `poll_exec_status` 已内置重试机制（最多 3 次，指数退避）。若仍失败，检查网络连通性或增大 `timeout_sec` |

---

## 2. 任务执行相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| `exec_status=3`（运行失败） | 任务执行异常 | 查 `list_data_check_report_step(job_id=xxx)` 的 `err_message` 字段定位原因 |
| `ODPS-0130071: ...full scan with all partitions...` | MaxCompute 分区表使用了全表扫描模式 | 在 `exec_data_check_save_task` 中设置 `source_global_params='odps.sql.allow.fullscan=true'`（源端）和/或 `target_global_params='odps.sql.allow.fullscan=true'`（目标端）；或在 `add_data_check_config` 中设置 `is_full_table_count=0` 并指定 `source_partition`/`target_partition` |
| MaxCompute 分区表批量校验报 full scan 或结果不一致 | 批量模式下仅设置全局参数不够，还必须在匹配规则中显式指定源端和目标端的分区条件 | 在 `task_config_match_rule` 中同时写明双边分区条件，如 `dt='2026-01-01';dt='2026-01-01'`；并确保源端和目标端均设置 `odps.sql.allow.fullscan=true`。规则示例见 `references/batch_match_rules.md` 第 2.6 节 |
| 校验结果全为 0（无记录） | 任务未正确触发 | 确认 batch_id 和 task_id 是否匹配；确认是否调用了 run 或 start_immediately=1 |
| 任务一直 `exec_status=1`（运行中）不结束 | 可能卡在某个表或分区 | 查 `list_data_check_report` 看哪些表还在 RUNNING；必要时 stop 终止 |
| 批量模式部分表不通过但 sourceCount 和 targetCount 都是 0 | 分区表在聚合层面 count 为 0，但分区维度存在差异（源端有某些分区值目标端没有） | 查 `list_data_check_report_step_by_job_id` 的 Step SQL，看 GROUP BY 的分区字段；对比源端目标端的分区列表 |
| `Task is running, do not repeat` | 重复触发了正在运行的批次 | 等待当前执行完成，或 stop 后再 run |

---

## 3. 终止相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| stop 调用返回错误 | 当前 exec_status 不是 1 | 仅 `exec_status=1`（运行中）可终止，已完成/已终止/已失败的批次不可再终止 |
| 终止后想重跑 | 正常流程 | 用 `rerun`（全量重跑）或 `run_failed`（run_fail_type=2 重跑被终止的表） |

---

## 4. 报告相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| 报告数据为空 | report_status 不是 2 | 先查 `get_data_check_report_status`，若为 0 需调 `generate_report`；若为 1 需等待 |
| `report_status=3`（生成失败） | 报告生成异常 | 重新调用 `generate_report` 触发生成 |
| download 返回空链接 | 报告未生成完成 | 按 SOP：确认 exec_status=4 → generate_report → 轮询 get_report_status=2 → download |
| overview 的通过率和 report/page 对不上 | 报告仍在生成中 | 确认 `report_status=2` 后数据才完整 |

---

## 5. 任务管理相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| `Running validation tasks cannot be deleted` | 运行中的任务不可删除 | 先调 `stop` 终止，再调 `delete` |
| update 修改 check_type 无效 | 不支持修改校验类型 | 已创建任务的 check_type 和 task_mode 不可变更，需新建任务 |
| `Task does not exist` | task_id 不存在 | 确认 task_id 是否正确，可通过 `get_data_check_task_list` 按名搜索 |
| `No corresponding batch information` | batch_id 不存在 | 先通过 `list_data_check_task_history(task_id=xxx)` 获取正确的 batch_id |

---

## 6. 配置相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| `No corresponding task configuration` | 任务下没有表配置 | 需先通过 `add_data_check_config`（逐表）或 `save` + `task_config_match_rule`（批量）添加配置 |
| SQL 预览缺少 WHERE 条件 | scopeFilter 不在预览范围 | sql/preview 仅支持逐表维度，批次级 scopeFilter 在运行时才解析 |
| 表名格式错误 | 未使用 schema.table 格式 | source_table/target_table 必须为 `schema.table` 格式（如 `lhm.orders`） |

---

## 7. 指标校验相关

| 症状 | 诊断 | 处理 |
|------|------|------|
| 指标校验结果全部不一致 | 模板或字段映射问题 | 检查 `list_data_check_column_results` 的 src_column_name/dst_column_name 是否对应；确认源端目标端数据类型兼容 |
| 自定义字段别名不匹配 | AS 别名不一致 | 源端目标端的 AS 别名必须完全一致（如都用 `AS max_id`） |
| XXHASH64 模板不可用 | 已废弃 | 改用 MIX 模板（check_template_id='1001'） |
| `E002R901 Agent is not active` | 指定 `source_columns`/`target_columns` 自定义聚合字段时，系统需通过服务代理拉取客户侧表元数据，若服务代理未安装或不在线则报此错误 | 前往控制台「迁移准备 → 资源组与服务代理 → 服务代理」页面安装服务代理，安装后重试；若不指定自定义字段则使用模板默认聚合，无需服务代理 |
| 数值字段呈现 min=0 / max 偏高 ~4x / sum 偏高 ~20% 的系统性差异 | 目标端表含有零值行或极大值行，属于数据差异而非模板或配置问题 | 按字段分组分析 min/max/sum/avg 模式；用 SQL `SELECT * FROM target WHERE col_int = 0` 或 `WHERE col_int > max_src` 定位具体差异行 |

---

## 8. Python SDK 特有注意事项

```python
# 1. 响应字段使用 snake_case（非 camelCase）
task_id = resp.body.data          # ✅ 正确
taskId = resp.body.data           # ❌ Python SDK 用 snake_case

# 2. 请求参数也用 snake_case
request = lhm_models.AddDataCheckTaskRequest(
    task_name='xxx',              # ✅ 正确
    taskName='xxx',               # ❌ Python SDK 用 snake_case
)

# 3. 检查响应状态
if not resp.body.success:
    print(f'Error: {resp.body.err_message}')  # err_message 非 errMessage
```

---

## 9. 排查决策树

```
接口调用失败？
  │
  ├── AliyunCliError / CLI 层异常 → 检查 aliyun CLI 与 aliyun-cli-lhm 插件是否安装、AK/SK、endpoint、网络
  │
  ├── resp.body.success=False → 读 err_message 原文反馈
  │
  └── resp.body.success=True 但结果不符合预期
        │
        ├── exec_status=3 → step/page 查 err_message
        │
        ├── 报告为空 → get_report_status 确认是否生成
        │     ├── 0(无记录) → generate_report
        │     ├── 1(生成中) → 等待
        │     └── 3(失败) → 重新 generate_report
        │
        ├── 校验结果全为 0 → 确认任务是否触发（batch_id 是否正确）
        │
        ├── 字段级不一致 → column/page 定位具体字段和指标
        │
        └── 大量 job FAILED/STOPPED 含 connection refused/timeout/rejected
              → 见第 10 节「并发问题应对」，引导客户用 check_global_params
```

---

## 10. 并发问题应对

> **触发条件（仅在以下两种情况激活，不要在任务创建前主动询问）**：
> 1. 任务执行后大量 job 失败，错误特征指向并发过高
> 2. 客户主动询问"并发太高""数据源被打挂"类问题

### 10.1 如何判断是并发过高导致的失败

满足任一即可判定：

- 大量 job 状态为 FAILED / STOPPED，错误信息含：
  - `connection refused` / `too many connections`
  - `timeout` / `query timeout`
  - `rejected` / `RejectedExecutionException`
- 客户反馈源端/目标端业务侧出现数据库变慢、连接池耗尽
- 元数据服务（HMS / Meta API 等）在规划阶段报错或大量超时
- 任务规模较大且失败比例 > 30%

### 10.2 通过 `check_global_params` 调节

数据校验任务支持在创建时通过 `extra.check_global_params` 字段（**文本格式**，不是 JSON）传入运行时参数。

| 参数 | 默认 | 含义 | 调节方向 |
|---|---|---|---|
| `query.submit.max-pool-size` | 100 | 单作业内 SQL 提交并发 | 源端/目标端 SQL 并发受限时调小（如 20/30） |
| `worker.batch.size` | 100 | 单作业处理的校验项数 | 想缩小单作业处理量时调小 |
| `planner.batch.size` | 100 | 单规划作业处理的任务数 | 规划阶段批量过大时调小 |
| `plan.thread.max-pool-size` | 100 | 规划阶段元数据连接并发 | 元数据服务承压时调小（如 20/30） |

### 10.3 注入方式

`check_global_params` 是**文本框格式**：
- 单参数：`key=value`
- 多参数：用 `\n`（换行）分隔

同样的格式适用于 `source_global_params` / `target_global_params`（源端/目标端运行时参数）。

```python
import lhm_models

# 单参数
check_global_params = "query.submit.max-pool-size=20"

# 多参数（用 \n 分隔）
check_global_params = "\n".join([
    "query.submit.max-pool-size=20",
    "plan.thread.max-pool-size=30",
    "worker.batch.size=50",
])

# extra 用普通 dict 传入即可：本地 lhm_models 对 dict 值原样序列化（键用后端约定的 camelCase）
extra = {"checkGlobalParams": check_global_params}
# 把 extra 传入 ExecDataCheckSaveTask 请求的 extra 字段
```

### 10.4 调参指引

**第一步：定位承压点**

| 现象 | 承压点 |
|---|---|
| 校验执行阶段大量 SQL 超时/被拒 | 源端或目标端**数据源**承压 |
| 规划阶段卡住、HMS / Meta API 报错 | **元数据服务**承压 |
| 单 job 内部排队溢出（RejectedExecutionException） | **单作业内并发**过高 |

**第二步：根据承压点选择参数**

- 数据源 SQL 并发受限 → `query.submit.max-pool-size = int(L × 0.7)`（默认 100，L 为数据源能承受的并发上限）
- 元数据服务承压 → `plan.thread.max-pool-size` 调小（默认 100，可降到 20-30）
- 单作业内并发过高 → `worker.batch.size` 调小（默认 100）
- 其他参数保持默认即可

**第三步：先用一个小批量任务验证参数效果，再应用到大批量任务**

### 10.5 数据源并发上限确认线索

| 数据源 | 客户可确认的指标 |
|---|---|
| Hive | HiveServer2 async 线程数；YARN 队列资源 |
| MaxCompute | 项目级 quota；并发作业数 |
| MySQL/PostgreSQL | `max_connections` 减去业务占用 |
| StarRocks/Doris | FE 队列深度；查询并发限制 |
| Hudi/Iceberg | metastore QPS 容量 |
| Spark/EMR | executor 数；队列资源 |

### 10.6 故障特征 → 推荐参数对照

| 失败特征 | 主要原因 | 优先调节 |
|---|---|---|
| `connection refused` 高频 | 数据源连接池打满 | `query.submit.max-pool-size` 调小 |
| `query timeout` | 数据源处理不过来 | `query.submit.max-pool-size` 调小 |
| 规划阶段卡住、元数据服务报错 | 元数据连接打满 | `plan.thread.max-pool-size` 调小 |
| 大量 RejectedExecutionException | 单作业内部排队溢出 | `worker.batch.size` 调小 |

### 10.7 重试建议

- 在创建新任务时通过 `check_global_params` 注入更保守的参数
- 把失败的表抽出来重新创建任务（不要复用原失败任务的配置，因为不带参数）
- 观察新任务的失败率，逐步调整参数到平衡点

### 10.8 AI 行为约束

- **NEVER** 在任务创建前主动询问"并发上限是多少"
- **NEVER** 客户端拆分大任务为多个小任务
- **ALWAYS** 在判定为并发问题后，引导客户使用 `check_global_params` 解决
- **ALWAYS** 把参数含义和默认值告诉客户，让客户根据自己环境决定具体值
