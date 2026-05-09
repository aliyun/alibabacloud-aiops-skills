## VVP 产品概念模型

### 实体层次与关系

Workspace（工作空间）
 └─ Namespace（项目空间）：作业管理和资源隔离的基本单元，所有配置、作业、权限均在单个 Namespace 下
     ├─ DeploymentDraft（作业草稿）：作业草稿的配置定义（模板），包含代码 artifact、资源规格、运行参数. 部署上线后, 生成对应的Deployment
     ├─ Deployment（作业部署）：作业的配置定义（模板），包含代码 artifact、资源规格、运行参数
     │    └─ Job（作业实例）：Deployment 的一次运行实例 [1:N]，Job 是 Deployment 的快照，绝大部分字段不可变，对作业的变更主要通过修改部署后重启Job实现(HotUpdate除外)。
     │         └─ Savepoint（快照）：Job 运行时的状态快照 [1:N]，用于有状态恢复
     ├─ SessionCluster（Session 集群）：仅用于开发测试的共享集群，不支持监控告警和自动调优
     ├─ ResourceQueue（资源队列）：计算资源的分配单元，Deployment 需要部署到资源队列或SessionCluster上运行
     └─ Catalog（SQL元数据）：管理用户SQL类作业中使用的数据库、表、字段等元数据信息
          └─ Database → Table

- 用户通过 deployment_id 定位一个部署配置，通过 job_id 定位一个具体的运行实例
- 所有 API path 中的 {namespace} 自动替换为当前项目空间

### 作业类型（artifact.kind）

| 枚举值 | 说明 |
|--------|------|
| SQLSCRIPT | SQL 作业 |
| MATERIALIZED_TABLE | 物化表作业（SQL 子类型） |
| JAR | JAR 作业 |
| PYTHON | Python 作业 |
| YAML | Flink CDC 数据摄入作业（SQL 子类型）（VVR 8.0.9+） |

### 执行模式 ExecutionMode
deployment 和 job 的执行模式在创建时确定，不能更改。

| 枚举值 | 说明 |
|--------|------|
| STREAMING | 流模式，持续运行处理无界数据流。一个 deployment 只能有一个非终态的 job。 |
| BATCH | 批模式，处理有界数据集后结束。一个 deployment 可以有多个非终态的 job。 |

### 作业状态（Job state）

STARTING → RUNNING → FINISHED / CANCELLED / FAILED

| 状态 | 类别 | 说明 |
|------|------|------|
| STARTING | 过渡态 | 作业正在启动 |
| RUNNING | 稳定态 | 作业正在运行 |
| FINISHED | 终态 | 批作业或有限流作业完成，或流作业触发stop-with-savepoint并完成。 |
| CANCELLED | 终态 | 用户主动停止 |
| FAILED | 终态 | 作业运行失败 |

### 引擎及版本

VVR和Flash均是VVP提供的商业版Flink引擎。

`engineVersion` 或 `versionName` 字段是引擎版本的展示名，在 `workspace` 下唯一，示例: "vvr-8.0.6-flink-1.17"。

引擎版本标记：推荐版本 > 稳定版本 > 普通版本 > EOS 版本。

部分功能有版本要求（如动态参数更新需 VVR 8.0.1+，算子 TTL 需 VVR 8.0.7+，YAML 作业需 VVR 8.0.9+）。
