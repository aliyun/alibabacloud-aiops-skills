# Terminology Dictionary

> Related: [entities.md](entities.md), [metrics.md](metrics.md), [SKILL.md](../SKILL.md)

59 terms for NL2SQL intent recognition, organized by type: metric (22), dimension (6), and table (31).

## Metric Terms

| Term | Synonyms | Binding |
|---|---|---|
| **存储占用** | 存储大小、空间占用、表大小、存储量、storage size, storage usage | 数据源: TABLES | 列: `data_length` | 换算: `data_length / 1073741824` = GB |
| **表热度** | 热点表、高频访问表、热表、访问频繁、查询最多 | 数据源: TASKS_HISTORY | 表达式: `COUNT(*)` 按 input_tables/output_tables 引用频次 | 或 TABLE_ACCESS_INFO 列: `access_count` |
| **任务失败率** | 作业失败率、失败比例、失败最多、失败趋势 | 数据源: TASKS_HISTORY | 列: `status` | 表达式: `SUM(CASE WHEN status='Failed' THEN 1 ELSE 0 END)*100.0/COUNT(*)` (%) |
| **新鲜度** | 数据滞后、时效性、分区新鲜度 | 数据源: PARTITIONS 列: `last_modified_time` | 或 TABLES 列: `last_modified_time` | 表达式: `DATEDIFF(GETDATE(), last_modified_time, 'dd')` (天) |
| **任务CPU消耗** | cpu时间、CPU时间、CPU消耗 | 数据源: TASKS_HISTORY | 列: `cost_cpu` (DOUBLE) | 换算: `cost_cpu / 100 / 3600` = CU*hour |
| **任务执行时长** | 运行时长、执行时长、墙钟时间、作业时长、任务耗时 | 数据源: TASKS_HISTORY | 表达式: `DATEDIFF(end_time, start_time, 'ss')` (秒) |
| **input_bytes** | 输入字节、输入数据量、读取数据量 | 数据源: TASKS_HISTORY | 列: `input_bytes` | 单位: 字节 |
| **output_bytes** | 输出字节、输出数据量、写出数据量 | 数据源: TASKS_HISTORY | 列: `output_bytes` | 单位: 字节 |
| **data_length** | 数据量、数据存储大小、表数据量 | 数据源: TABLES | 列: `data_length` | 换算: `data_length / 1073741824` = GB |
| **lifecycle** | 生命周期、自动回收天数、TTL | 数据源: TABLES | 列: `lifecycle` | 单位: 天 |
| **last_modified_time** | 最后修改时间、最近更新时间 | 数据源: TABLES 列: `last_modified_time` (DATETIME) | 或 PARTITIONS 列: `last_modified_time` (DATETIME) |
| **排队等待** | 排队时间、等待时间 | **INFORMATION_SCHEMA 视图中无此字段**，无法直接查询排队时间。TASKS_HISTORY 仅有 start_time/end_time，不含排队起止时间。 |
| **upload_bytes** | 上传量、上传字节、上传数据量 | 数据源: TUNNELS_HISTORY | 列: `data_size` (WHERE operate_type='UPLOADLOG') | 单位: 字节 |
| **download_bytes** | 下载量、下载字节、下载数据量 | 数据源: TUNNELS_HISTORY | 列: `data_size` (WHERE operate_type='DOWNLOADLOG') | 单位: 字节 |
| **partition_lifecycle** | 分区生命周期、分区管理、分区清理 | 数据源: PARTITIONS | 列: `lifecycle_enabled` | TABLES 列: `lifecycle` (表级) |
| **CU时** | CU时消耗、CU消耗、CU*hour, CU小时 | 数据源: TASKS_HISTORY | 列: `cost_cpu` (DOUBLE) | 换算: `SUM(cost_cpu) / 100.0 / 3600` = CU*hour |
| **Quota CPU使用率** | CPU配额使用率、计算资源使用、CPU资源消耗 | 数据源: QUOTA_USAGE | 列: `cpu_elastic_quota_used` / `cpu_elastic_quota_max` | 表达式: `cpu_elastic_quota_used / cpu_elastic_quota_max * 100` (%) |
| **Quota 内存使用率** | 内存配额使用率、内存资源使用、内存消耗 | 数据源: QUOTA_USAGE | 列: `mem_elastic_quota_used` / `mem_elastic_quota_max` | 表达式: `mem_elastic_quota_used / mem_elastic_quota_max * 100` (%) |
| **任务内存消耗** | 内存消耗、mem消耗 | 数据源: TASKS_HISTORY | 列: `cost_mem` (DOUBLE) | 单位: MB*seconds |
| **MCP执行** | MCP查询、结构化API、MCP工具 | 非SQL指标 — 通过 maxcompute-catalog MCP 工具执行查询或获取元数据 |
| **成本预估** | cost_sql、费用预估、CU预估 | 非SQL指标 — MCP `cost_sql` 工具估算执行CU，支持用户表和 IS 视图（2026-04 验证） |
| **元数据浏览** | 表列表(MCP)、列信息(MCP)、分区信息(MCP) | 非SQL指标 — MCP 结构化 API（list_tables / get_table_schema / get_partition_info）获取元数据，无需写SQL |

## Dimension Terms

| Term | Synonyms | Description |
|---|---|---|
| **权限暴露** | 授权暴露、高危授权、越权风险 | 表权限授权范围、主体数量与权限类型组合形成的风险视角 |
| **僵尸表** | 无效表、废弃表 | 长时间未被访问且无下游依赖的表 |
| **通道类型** | 通道类型、传输类型 | 数据通道类型，包括 UPLOAD 和 DOWNLOAD |
| **角色分配** | 角色分配、用户角色、权限分配 | 用户角色分配关系 |
| **数据血缘** | 血缘追踪、数据依赖、上下游关系、血缘分析、表血缘 | 基于 TASKS_HISTORY 的 input_tables/output_tables 追踪表级数据依赖关系 |
| **项目配置** | 项目设置、CATALOGS设置、项目安全配置、备份配置、IP白名单 | CATALOGS.settings 字段中存储的 JSON 格式项目配置 |

## Table Terms

| Term | Synonyms | Description |
|---|---|---|
| **CATALOGS** | 项目列表、Catalog视图、项目信息 | MaxCompute INFORMATION_SCHEMA 项目列表视图 |
| **CATALOG_PRIVILEGES** | 项目权限、项目级权限、Catalog权限 | 项目级的权限授权信息 |
| **SCHEMAS** | Schema列表、Schema信息、数据库 | 项目下 Schema 信息 |
| **TABLES** | 表信息、表列表、表元数据 | 各个项目下的表信息 |
| **COLUMNS** | 字段信息、列信息、字段列表 | 各个项目下的表字段信息 |
| **TABLE_ACCESS_INFO** | 表访问统计、表访问信息、访问频率 | 各个项目下表的访问统计信息 |
| **TABLE_LABELS** | 表LABEL、表标签、表安全标签 | 各个项目下表的 LABEL 信息 |
| **TABLE_LABEL_GRANTS** | LABEL授权、标签授权、表标签授权 | LABEL 授权信息 |
| **TABLE_PRIVILEGES** | 表权限、表授权、表级权限 | 各个项目下表的权限信息 |
| **COLUMN_LABELS** | 字段LABEL、列标签、字段安全标签 | 各个项目下表字段级的 LABEL 信息 |
| **COLUMN_LABEL_GRANTS** | 字段LABEL授权、列标签授权 | 各个项目下表字段的 LABEL 授权信息 |
| **COLUMN_PRIVILEGES** | 字段权限、列权限、字段级权限 | 各个项目下表字段级的权限信息 |
| **PARTITIONS** | 分区信息、分区列表、表分区 | 各个项目下的表分区信息 |
| **PARTITION_ACCESS_INFO** | 分区访问统计、分区访问信息、分区热度 | 各个项目下表分区的访问统计信息 |
| **USERS** | 用户列表、用户信息、账号列表 | 用户列表 |
| **ROLES** | 角色列表、角色信息、权限角色 | 各个项目级别以及账号级别的角色列表 |
| **USER_ROLES** | 用户角色、用户角色关系、角色分配 | 用户拥有的角色信息 |
| **INSTALLED_PACKAGES** | 已安装Package、包列表、Package信息 | 各个项目下已安装的 Package 信息 |
| **PACKAGE_PRIVILEGES** | Package权限、包权限、Package授权 | Package 的授权信息 |
| **PACKAGE_OBJECTS** | Package对象、包对象、Package内容 | Package 中的对象信息 |
| **UDFS** | UDF列表、自定义函数、UDF信息 | 各个项目下的 UDF 信息 |
| **UDF_PRIVILEGES** | UDF权限、函数权限、UDF授权 | 各个项目下的 UDF 授权信息 |
| **UDF_RESOURCES** | UDF资源、函数资源依赖、UDF依赖 | 各个项目下 UDF 的资源依赖 |
| **RESOURCES** | 资源列表、资源信息、资源文件 | 各个项目下的资源信息 |
| **RESOURCE_PRIVILEGES** | 资源权限、资源授权、资源访问权限 | 各个项目下资源的权限信息 |
| **TASKS** | 运行中任务、实时任务、当前任务、任务快照 | 运行中作业的实时快照，用于实时监控作业 |
| **TASKS_HISTORY** | 任务历史、作业历史、历史任务 | 各个项目内已完成的作业历史，保留近 14 天数据 |
| **TUNNELS_HISTORY** | 数据通道历史、Tunnel历史、传输历史 | 数据通道批量上传下载的历史数据，保留近 14 天数据 |
| **QUOTA_USAGE** | Quota使用量、资源配额使用、配额监控、Quota监控 | 包年包月计算 Quota 的资源使用实时快照 |
| **VOLUMES** | Volume列表、Volume信息、外部存储 | MaxCompute Volume 视图 |
| **FOREIGN_SERVERS** | ForeignServer、外部服务器、外部数据源 | MaxCompute ForeignServer 视图 |
