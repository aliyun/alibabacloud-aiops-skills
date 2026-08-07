# 相关命令

> 本 skill（configure-quality-rule）涉及的 `aliyun dataphin-public` 命令清单（插件模式 kebab-case）。
> **执行通道按部署形态区分**（见 [`../SKILL.md`](../SKILL.md) §3）：公共云(A) 用下表 CLI；独立部署(B) 因 CLI 有 `bad file descriptor` bug，改用 Python SDK **直调括号内标注的 OpenAPI Action**（参数 kebab→camelCase，`verify=False`）。
> 命令名与参数以插件 `aliyun-cli-dataphin-public`（>= 0.5.4）实测为准；响应字段为 **PascalCase**（`WatchId`/`RuleId`/`ScheduleId`）。
> 复杂对象参数（`--table-info`/`--data-source-info`/`--quality-alert-info`/`--validate-condition-list`/`--form-property-list`）为内嵌 JSON string / list，元素结构详见 [`quality-config-matrix.md`](quality-config-matrix.md)。

## 监控对象与元数据

| 命令 | 用途 | 关键参数 |
|---|---|---|
| （OpenAPI 直调）`ListQualityWatches` | **按多维过滤列现有监控对象**（用于“先查现有 watch”；把用户给的信息全部映射成过滤参数，别只靠 keyword；旧名 `PagedQueryQualityWatches` POC 报 `Unknown API`） | `--watch-type-list` `--biz-unit-name-list`(板块) `--project-name-list`(项目) `--index-owner-list`/`--table-owner-list`/`--quality-owner-list` `--data-source-id-list`/`--data-source-type-list` `--keyword`(仅表名) `--page-no` `--page-size` |
| `aliyun dataphin-public get-quality-watch-by-object-id` | 按对象 ID 精确查监控对象 | `--watch-type` `--watch-object-id` |
| `aliyun dataphin-public upsert-quality-watch` | 创建/更新监控对象 | `--type` `--quality-owner` `--table-info` / `--data-source-info` / `--index-info` |
| `aliyun dataphin-public get-quality-watch-task` | 查监控任务详情 | `--watch-task-id` |
| `aliyun dataphin-public list-tables` | 定位已采集表（拿表名/项目） | `--catalog` `--keyword` |
| `aliyun dataphin-public get-table-columns` | 拉已采集表字段列表 | `--catalog` `--table-name` |

## 规则与模板

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `aliyun dataphin-public list-quality-templates` | 查质量规则模板（对应 OpenAPI `ListQualityTemplates`） | `--watch-type-list` `--template-source-list` `--catalog-list` `--template-type-list` `--page-no` `--page-size` |
| `aliyun dataphin-public get-quality-template` | 查单个质量模板详情 | `--quality-template-id` |
| `aliyun dataphin-public upsert-quality-rule` | 创建/更新质量规则 | `--quality-rule-name` `--strength` `--template-id` `--template-type` `--watch-id` `--catalog-list` `--form-property-list` `--validate-condition-list` |
| `aliyun dataphin-public list-quality-rules` | 按 watchId 查规则定义与状态 | `--watch-id` |
| `aliyun dataphin-public update-quality-rule-switch` | 开启/关闭规则校验开关 | `--open` `--rule-id-list` |

## 调度与告警

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `aliyun dataphin-public get-quality-schedules-by-watch-id` | 查已有调度 | `--watch-id` |
| `aliyun dataphin-public upsert-quality-schedule` | 创建/更新调度 | `--upsert-quality-schedule-name` `--type` `--watch-id` `--cron-expression` `--partition-type` `--partition-expression` `--trigger-type` `--validate-partition-type` |
| `aliyun dataphin-public assign-quality-rule-of-all-rule-scope-schedules` | 绑定调度到规则 | `--watch-id` `--rule-id-list` `--schedule-id-list` |
| `aliyun dataphin-public remove-quality-rule-schedules` | 解除调度绑定 | `--watch-id` `--rule-id` `--schedule-id-list` |
| `aliyun dataphin-public upsert-quality-watch-alert` | 配置告警 | `--watch-id` `--quality-alert-info` |
| `aliyun dataphin-public get-quality-alert-of-all-rule-scope-by-watch-id` | 查询告警设置 | `--watch-id` |

## 试跑与结果

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `aliyun dataphin-public submit-quality-rule-tasks` | 提交试跑/正式任务 | `--is-test-run` `--watch-rule-id-list` `--partition-expression-from` `--partition-expression` `--biz-date` `--schedule-id` |
| `aliyun dataphin-public get-quality-rule-task` | 查任务状态与校验结果 | `--rule-task-id` |
| `aliyun dataphin-public get-quality-rule-task-log` | 查任务执行日志，排查 FAILED | `--rule-task-id` |
| `aliyun dataphin-public list-quality-rule-tasks` | 按监控任务查每条规则结果 | `--watch-task-id` |

## 未采集数据源表取字段 / 读分区值（数据库SQL任务，A/B 通用）

> 公共云插件**无 JDBC 五步链路**（`create-jdbc-connection` / `exec-sql-by-jdbc` / `query-sql-task-status` / `fetch-sql-result` / `close-jdbc-connection` 均不存在）。
> 统一改用「计算任务-数据库SQL任务」即席执行：指定数据源直连跑 SQL，既能取未采集表字段，也能读分区值。独立部署 / 公共云同一套方式。

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `aliyun dataphin-public list-data-source-with-config` | 查数据源拿 `DataSourceId` | `--page` `--page-size` `--data-source-name` |
| `aliyun dataphin-public execute-ad-hoc-task` | 执行数据库SQL任务（取字段 / 读分区） | `--code` `--operator-type` `--project-id` `--data-source-id`（`--data-source-schema` / `--data-source-catalog` 按库类型可选） |
| `aliyun dataphin-public get-ad-hoc-task-result` | 取执行结果（字段元信息 / 分区值） | `--task-id` `--sub-task-id` `--project-id` |
| `aliyun dataphin-public get-ad-hoc-task-log` | 查执行日志 | `--project-id`（详见 `--help`） |
| `aliyun dataphin-public stop-ad-hoc-task` | 停止任务兜底 | 详见 `--help` |
