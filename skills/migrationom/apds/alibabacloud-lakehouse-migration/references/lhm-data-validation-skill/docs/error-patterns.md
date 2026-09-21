# 故障排查指南

## 排查决策树

```
接口调用失败？
  │
  ├── CLI 层异常（AliyunCliError）→ 检查 aliyun CLI 与 aliyun-cli-lhm 插件是否安装、AK/SK、endpoint、网络
  │
  ├── resp.body.success=False → 读 err_message 原文反馈，不自行猜测原因
  │
  └── resp.body.success=True 但结果不符合预期
        │
        ├── exec_status=3（运行失败）→ step/page 查 err_message
        │
        ├── 报告为空 → get_report_status 确认
        │     ├── 0(无记录) → generate_report
        │     ├── 1(生成中) → 等待
        │     └── 3(失败) → 重新 generate_report
        │
        ├── 校验结果全为 0 → 确认任务是否触发（batch_id 是否正确）
        │
        ├── 字段级不一致 → column/page 定位具体字段和指标
        │
        └── 大量 job FAILED/STOPPED 含 connection refused/timeout/rejected
              → 见下方「并发问题应对」
```

## 通用错误

| 错误 | 原因 | 处理 |
|------|------|------|
| InvalidAccessKeyId | AK 无效 | 检查环境变量或 local_config.yaml |
| SignatureDoesNotMatch | SK 不匹配 | 检查 access_key_secret 是否正确 |
| Forbidden | 无权限 | 确认 RAM 用户有 LHM 服务权限 |
| Throttling | API 限流 | 等待后重试 |
| E500R103: special characters | task_name 含非法字符 | task_name 只允许英文字母、中文字符和数字 |
| ModuleNotFoundError | 依赖缺失 | 确认 pyyaml 已安装；request 模型由本地 `scripts/lhm_models.py` 提供，无需另装 SDK |
| CLI_NOT_FOUND | aliyun CLI 未安装 | 安装 aliyun CLI（>= 3.3.8）：https://help.aliyun.com/cli/ |
| CLI_TIMEOUT | CLI 调用超时 | 检查网络/endpoint；重试即可 |
| aliyun-cli-lhm 插件未安装 | 插件缺失 | `aliyun plugin install --names lhm --source-base https://cli.aliyun-inc.com/registry_id/2/env/pre/plugins` |
| RemoteDisconnected | 网络抖动 | poll_exec_status 已内置重试（最多 3 次） |

## 任务执行错误

| 错误 | 原因 | 处理 |
|------|------|------|
| exec_status=3 | 任务执行异常 | 查 step 的 err_message 定位原因 |
| ODPS-0130071 | MaxCompute 全表扫描限制 | 配置 `source_global_params='odps.sql.allow.fullscan=true'` |
| MaxCompute 分区表批量校验结果不一致或报 full scan | 批量模式下仅配全局参数不够，还必须显式指定源端和目标端分区条件 | 在 `task_config_match_rule` 中写明双边分区条件，如 `dt='2026-01-01';dt='2026-01-01'`；同时两端都设置 `odps.sql.allow.fullscan=true` |
| 校验结果全为 0 | 任务未正确触发 | 确认 batch_id 正确，确认调用了 run 或 start_immediately=1 |
| 任务一直 RUNNING | 卡在某个表或分区 | 查 report 看哪些表还在 RUNNING；必要时 stop 终止 |
| Task is running, do not repeat | 重复触发 | 等待完成，或 stop 后再 run |
| Running tasks cannot be deleted | 运行中不可删除 | 先 stop 终止，再 delete |
| check_type 不可变更 | 已创建任务的类型不可改 | 需新建任务 |

## 报告相关

| 错误 | 原因 | 处理 |
|------|------|------|
| 报告数据为空 | report_status 不是 2 | 先查 report_status，0 需 generate，1 需等待 |
| report_status=3 | 生成失败 | 重新调用 generate_report |
| download 返回空链接 | 报告未生成完成 | 确认 report_status=2 后再 download |

## 指标校验相关

| 错误 | 原因 | 处理 |
|------|------|------|
| 结果全部不一致 | 模板或字段映射问题 | 检查 column_results 的 src/dst_column_name 是否对应 |
| 自定义字段别名不匹配 | AS 别名不一致 | 源端目标端的 AS 别名必须完全一致 |
| E002R901 Agent is not active | 服务代理未安装 | 前往控制台安装服务代理 |
| MAP 类型 GROUP BY 报错 | 复杂类型无法参与 GROUP BY | 通过 sourceColumns 排除复杂类型字段 |
| 数值字段 min=0/max 偏高 | 目标端含零值或极大值行 | 按字段分组分析，SQL 定位差异行 |

## 并发问题应对

### 触发条件（仅在以下情况激活）
1. 任务执行后大量 job 失败，错误指向并发过高
2. 客户主动询问"并发太高""数据源被打挂"

### 判断标准

满足任一即可判定并发过高：
- 大量 job FAILED/STOPPED，错误含 `connection refused` / `too many connections` / `timeout` / `rejected`
- 客户反馈数据源变慢或连接池耗尽
- 元数据服务在规划阶段报错
- 失败比例 > 30%

### 通过 check_global_params 调节

| 参数 | 默认 | 含义 | 调节方向 |
|------|------|------|---------|
| `query.submit.max-pool-size` | 100 | 单作业 SQL 提交并发 | 数据源承压时调小（如 20-30） |
| `worker.batch.size` | 100 | 单作业处理校验项数 | 缩小单作业处理量 |
| `planner.batch.size` | 100 | 单规划作业处理任务数 | 规划阶段批量过大时调小 |
| `plan.thread.max-pool-size` | 100 | 规划阶段元数据连接并发 | 元数据服务承压时调小（如 20-30） |

### 故障特征 → 推荐参数

| 失败特征 | 承压点 | 优先调节 |
|---------|--------|---------|
| `connection refused` 高频 | 数据源连接池打满 | `query.submit.max-pool-size` 调小 |
| `query timeout` | 数据源处理不过来 | `query.submit.max-pool-size` 调小 |
| 规划阶段卡住 | 元数据连接打满 | `plan.thread.max-pool-size` 调小 |
| RejectedExecutionException | 单作业内部排队溢出 | `worker.batch.size` 调小 |

### 注入方式

`check_global_params` 是文本格式，多参数用换行分隔：
```
query.submit.max-pool-size=20
plan.thread.max-pool-size=30
```

### 重试建议
- 创建新任务时注入更保守的参数
- 把失败的表抽出来新建任务（不复用原失败任务配置）
- 观察新任务失败率，逐步调整
