# 数据校验工作流函数参考

`scripts/common.py` 封装了 LHM 数据校验的常用操作（网络层通过 aliyun CLI 调用 aliyun-cli-lhm 插件），适合直接嵌入 Python 项目或通过 AI 生成代码调用。本文档按需查阅，不必在每次执行时完整加载。

---

## common.py 函数清单

| 函数 | 说明 |
|------|------|
| `check_env()` | 检查 API 凭证、aliyun CLI 与 aliyun-cli-lhm 插件是否就绪 |
| `build_client(region='hangzhou')` | 构建 LHM 客户端（网络层走 aliyun CLI，支持杭州/新加坡双节点） |
| `check_resp(resp, action)` | 统一响应校验，失败抛 RuntimeError |
| `run_count_check()` | 一键逐表数据量校验 |
| `run_metric_check()` | 一键逐表指标校验（threshold 默认 None） |
| `run_batch_check()` | 一键批量模式校验（支持 match_rule） |
| `poll_exec_status()` | 轮询执行状态至终态 |
| `list_failed_tasks()` | 查询不通过/异常任务列表 |
| `download_report()` | 一键下载报告 |
| `diagnose_failed()` | 诊断不通过原因 |
| `summarize_batch()` | 查看批次概况 |
| `rerun_failed()` | 重跑失败/不通过/被终止的表 |
| `full_check_pipeline()` | 端到端：执行 → 轮询 → 下载 → 诊断 |
| `list_templates()` | 列出可用校验模板（支持 checkType/isBuiltin/name 筛选） |
| `get_template_detail()` | 查看模板完整配置（规则、ds-engine 映射） |
| `create_template()` | 创建自定义校验模板（指标/弱内容） |
| `update_template()` | 更新模板（upsert 语义，内部自动拆分 basic/complexMetricRules） |
| `delete_templates()` | 批量删除模板 |
| `format_batch_summary()` | 将批次概览格式化为 Markdown 表格 |
| `format_diagnosis_report()` | 将诊断结果格式化为分层 Markdown 报告 |
| `format_table_list()` | 将表级结果列表格式化为 Markdown 表格 |

独立脚本入口：

- `scripts/01_count_per_table.py`
- `scripts/02_count_batch.py`
- `scripts/03_metric_per_table.py`

这些脚本已使用 `format_batch_summary()` 输出概览，并在存在失败表时自动调用 `format_diagnosis_report()` 展示诊断摘要。

---

## 原子 Skill

如需通过命令行直接调用单一职责能力，或嵌入外部调度系统、CI/CD，可使用 `atomic-skills/` 下的原子 Skill。完整清单与使用约定见 `atomic-skills/README.md`。
