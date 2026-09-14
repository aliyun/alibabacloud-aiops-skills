# DataPhin Pipeline OpenAPI 辅助工具类配置说明文档
update time: 2026-04-16 18:00:00

---

## 目录

- [1. 模块概述](#1-模块概述)
- [3. 基础类（根包）](#3-基础类根包)
- [4. command 包 — 命令类](#4-command-包--命令类)
- [5. query 包 — 查询类](#5-query-包--查询类)
- [6. vo 包 — 结果视图类](#6-vo-包--结果视图类)
- [7. model 包 — 管道配置模型类](#7-model-包--管道配置模型类)
- [8. model.plugin 包 — 组件插件配置](#8-modelplugin-包--组件插件配置)
- [9. model.plugin.datasource 包 — 数据源配置](#9-modelplugindatasource-包--数据源配置)
- [10. model.plugin.input 包 — 输入组件](#10-modelplugininput-包--输入组件)
- [11. model.plugin.output 包 — 输出组件](#11-modelpluginoutput-包--输出组件)
- [12. model.plugin.transform 包 — 转换/流程控制组件](#12-modelplugintransform-包--转换流程控制组件)
- [13. vdm 包 — 调度域配置模型](#13-vdm-包--调度域配置模型)
- [14. utils 包 — 工具类](#14-utils-包--工具类)
- [15. model.plugin.unstructured 包 — 非结构化工作流算子基础配置](#15-modelpluginunstructured-包--非结构化工作流算子基础配置)
- [16. model.plugin.unstructured.neuron 包 — 非结构化工作流算子](#16-modelpluginunstructuredneuron-包--非结构化工作流算子)

---

## 1. 模块概述

本模块定义了 DataPhin 集成管道任务 OpenAPI V2 的完整数据模型。支持通过 API 创建、更新、查询、下线集成管道任务（离线/实时）。核心特点：

- **Builder 模式**：几乎所有配置类均提供 Builder 内部类，支持链式构建
- **序列化基类**：所有配置类继承自 `JsonSerializable`，基于 fastjson 提供序列化/反序列化能力
- **Swagger 注解**：使用 `@ApiModel` / `@ApiModelProperty` 生成 API 文档
- **DAG 管道模型**：组件(Steps)通过连接(Hops)形成有向无环图
- **同步/异步模式**：创建、更新、下线操作支持同步和异步两种执行模式

---

## 3. 基础类（根包）

### 3.1 JsonSerializable

> `com.alibaba.dataphin.pipeline.common.facade.openapi.JsonSerializable`

**用途**：所有配置类的序列化基类（抽象类），实现 `Serializable` 接口，提供基于 fastjson 的 JSON 序列化/反序列化能力。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `serialVersionUID` | long | 序列化版本号，值为 `1L`（静态常量） |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `toJson()` | JSONObject | @Transient | 将当前对象转换为 `JSONObject`（基于 `toJsonString()` 二次解析） |
| `toJsonString()` | String | @Transient | 将当前对象序列化为 JSON 字符串（基于 `JSONObject.toJSONString`） |
| `deserialize(Class<T> clazz)` | T | @Transient | 将当前对象通过 JSON 反序列化为指定类型（深拷贝语义） |
| `deserialize(String json, Class<T> clazz)` | T | static | 静态方法，将 JSON 字符串反序列化为指定类型 |
| `deserialize(String json, Type type)` | T | static | 静态方法，将 JSON 字符串反序列化为指定泛型类型 |
| `jsonCopy(T source, Class<R> clazz)` | R | static | 基于 JSON 的深拷贝，将源对象转换为目标类型 |
| `copySameFields(Object source, Object target)` | void | static | 将源对象与目标对象中同名同类型的字段进行浅拷贝（通过反射） |

### 3.2 OAConstants

> `com.alibaba.dataphin.pipeline.common.facade.openapi.OAConstants`

**用途**：模块常量定义。

| 常量 | 值 | 说明 |
|------|----|------|
| `DOT` | `"."` | 点号分隔符 |

---

## 4. command 包 — 命令类

### 4.1 OARequestContext — 请求上下文

> `com.alibaba.dataphin.pipeline.common.facade.openapi.command.OARequestContext`

**用途**：所有 API 请求的上下文信息，标识租户、用户、项目和操作环境。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tenantId` | Long | 是 | 租户ID |
| `userId` | String | 是 | 当前用户ID |
| `projectId` | Long | 是 | 集成管道任务所属项目ID |
| `env` | String | 是 | 操作环境：`DEV`-开发环境，`PROD`-生产环境 |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OARequestContext.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `tenantId(Long val)` | Long | 设置租户ID |
| `projectId(Long val)` | Long | 设置项目ID |
| `userId(String val)` | String | 设置用户ID |
| `env(String val)` | String | 设置操作环境（DEV/PROD） |
| `build()` | - | 构建 OARequestContext 实例 |

### 4.2 OACreatePipelineCommand — 创建管道任务命令

> `com.alibaba.dataphin.pipeline.common.facade.openapi.command.OACreatePipelineCommand`

**用途**：创建集成管道任务的入参配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `nodeInfo` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OANodeInfo | 是 | - | 管道任务基本信息 |
| `pipelineType` | Integer | 否 | `0` | 管道任务类型：`0`-离线集成，`1`-实时集成，`13`-数据归集，`14`-非结构化工作流 |
| `mode` | String | 否 | `"PIPELINE"` | 配置模式：`PIPELINE`-管道模式，`JSON`-脚本模式 |
| `pipelineConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 条件 | - | 管道模式下的组件配置（mode=PIPELINE时必填） |
| `pipelineJson` | String | 条件 | - | 脚本模式下的JSON配置（mode=JSON时必填） |
| `scheduleConfig` | String | 是 | `"{}"` | 调度配置JSON字符串，可通过 `OAScheduleConfig#toJsonString()` 生成 |
| `settings` | String | 否 | `"{}"` | 通道配置JSON字符串，可通过 `OAPipelineSetting#toJsonString()` 生成 |
| `submit` | Boolean | 否 | `true` | 是否提交 |
| `comment` | String | 否 | - | 备注 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `toJson()` | JSONObject | @Transient | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | @Transient | （继承）将对象序列化为 JSON 字符串 |
| `scheduleConfig()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAScheduleConfig\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAUpStreamConfig\> | @Transient | 将 scheduleConfig JSON 字符串反序列化为 OAScheduleConfig 对象 |
| `pipelineSetting()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting | @Transient | 将 settings JSON 字符串反序列化为 OAPipelineSetting 对象 |
| `settingJson()` | JSONObject | @Transient | 将 settings JSON 字符串解析为 JSONObject |
| `builder()` | Builder | static | 创建 Builder 实例 |

**内部枚举**：

- **OAPipelineType**：`OFFLINE_PIPELINE(0)` 离线 | `REAL_TIME_PIPELINE(1)` 实时 | `UN_STRUCTURED(13)` 数据归集 | `UNSTRUCTURED_PIPELINE(14)` 非结构化工作流
- **OAPipelineMode**：`PIPELINE` 管道模式 | `JSON` 脚本模式

**Builder 类 `OACreatePipelineCommand.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `nodeInfo(OANodeInfo val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OANodeInfo | 设置管道任务基本信息 |
| `pipelineType(int val)` | int | 设置管道类型（0-离线，1-实时） |
| `pipelineType(OAPipelineType val)` | OAPipelineType | 设置管道类型（枚举方式） |
| `mode(String val)` | String | 设置配置模式（PIPELINE/JSON） |
| `mode(OAPipelineMode val)` | OAPipelineMode | 设置配置模式（枚举方式） |
| `pipelineConfig(OAPipelineConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 设置管道组件配置（mode=PIPELINE时使用） |
| `pipelineJson(String val)` | String | 设置脚本模式JSON配置（mode=JSON时使用） |
| `scheduleConfig(OAScheduleConfig<?> val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAScheduleConfig | 设置调度配置（自动序列化为JSON字符串） |
| `scheduleConfig(String val)` | String | 设置调度配置JSON字符串 |
| `settings(OAPipelineSetting val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting | 设置通道配置（自动序列化为JSON字符串） |
| `settings(String val)` | String | 设置通道配置JSON字符串 |
| `submit(Boolean val)` | Boolean | 设置是否提交 |
| `comment(String val)` | String | 设置备注 |
| `build()` | - | 构建 OACreatePipelineCommand 实例 |

### 4.3 OAUpdatePipelineCommand — 更新管道任务命令

> `com.alibaba.dataphin.pipeline.common.facade.openapi.command.OAUpdatePipelineCommand`

**用途**：更新集成管道任务。继承自 `OACreatePipelineCommand`，复用全部字段。更新时需通过 `nodeInfo` 中的 `pipelineId`/`fileId`/`nodeId` 标识目标管道。

**字段（全部继承自 OACreatePipelineCommand）**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `nodeInfo` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OANodeInfo | 是 | - | 管道任务基本信息（需设置pipelineId/fileId/nodeId标识目标） |
| `pipelineType` | Integer | 否 | `0` | 管道任务类型：`0`-离线集成，`1`-实时集成，`13`-数据归集，`14`-非结构化工作流 |
| `mode` | String | 否 | `"PIPELINE"` | 配置模式：`PIPELINE`-管道模式，`JSON`-脚本模式 |
| `pipelineConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 条件 | - | 管道模式下的组件配置（mode=PIPELINE时必填） |
| `pipelineJson` | String | 条件 | - | 脚本模式下的JSON配置（mode=JSON时必填） |
| `scheduleConfig` | String | 是 | `"{}"` | 调度配置JSON字符串 |
| `settings` | String | 否 | `"{}"` | 通道配置JSON字符串 |
| `submit` | Boolean | 否 | `true` | 是否提交 |
| `comment` | String | 否 | - | 备注 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `pipelineId()` | Long | @Transient | 获取 nodeInfo 中的 pipelineId |
| `scheduleConfig()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAScheduleConfig\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAUpStreamConfig\> | @Transient | （继承）反序列化调度配置 |
| `pipelineSetting()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting | @Transient | （继承）反序列化通道配置 |
| `settingJson()` | JSONObject | @Transient | （继承）解析通道配置为JSONObject |
| `builder()` | UpdateBuilder | static | 创建 UpdateBuilder 实例 |

**Builder 类 `OAUpdatePipelineCommand.UpdateBuilder`**

> 继承自 `OACreatePipelineCommand.Builder`，复用全部 Builder 方法。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 OACreatePipelineCommand.Builder 方法）* | | |
| `build()` | - | 构建 OAUpdatePipelineCommand 实例（覆写） |

### 4.4 OAOfflinePipelineCommand — 下线管道任务命令

> `com.alibaba.dataphin.pipeline.common.facade.openapi.command.OAOfflinePipelineCommand`

**用途**：下线（并可选删除）集成管道任务。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pipelineId` | Long | 三选一 | 集成管道主键ID |
| `fileId` | Long | 三选一 | 集成任务文件ID |
| `nodeId` | String | 三选一 | 集成任务调度节点ID（如 `n_123`） |
| `delete` | Boolean | 是 | 是否删除 |
| `comment` | String | 否 | 备注 |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAOfflinePipelineCommand.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `pipelineId(Long val)` | Long | 设置管道ID |
| `fileId(Long val)` | Long | 设置文件ID |
| `nodeId(String val)` | String | 设置节点ID |
| `delete(Boolean val)` | Boolean | 设置是否删除 |
| `comment(String val)` | String | 设置备注 |
| `build()` | - | 构建 OAOfflinePipelineCommand 实例 |

---

## 5. query 包 — 查询类

### 5.1 OAQueryId — 管道查询参数

> `com.alibaba.dataphin.pipeline.common.facade.openapi.query.OAQueryId`

**用途**：根据ID查询管道任务，支持三种ID方式查询（三选一）。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `pipelineId` | Long | 集成管道主键ID |
| `fileId` | Long | 集成任务文件ID |
| `nodeId` | String | 集成任务调度节点ID（如 `n_123`） |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAQueryId.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `pipelineId(Long val)` | Long | 设置管道ID |
| `fileId(Long val)` | Long | 设置文件ID |
| `nodeId(String val)` | String | 设置节点ID |
| `build()` | - | 构建 OAQueryId 实例 |

---

## 6. vo 包 — 结果视图类

### 6.1 OACreateResult — 创建结果

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OACreateResult`

**用途**：同步创建管道任务的返回结果。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `hostMachine` | String | 服务端执行机器信息（格式：`hostName:hostIp`） |
| `pipelineId` | Long | 创建成功后的管道ID |
| `nodeId` | String | 管道任务调度节点ID |
| `submitId` | Long | 待发布列表的submitId，通过发布域进行发布 |
| `version` | String | 提交生成的版本号 |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OACreateResult.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `hostMachine(String val)` | String | 设置服务端执行机器信息 |
| `pipelineId(Long val)` | Long | 设置管道ID |
| `nodeId(String val)` | String | 设置调度节点ID |
| `submitId(Long val)` | Long | 设置待发布ID |
| `version(String val)` | String | 设置版本号 |
| `build()` | - | 构建 OACreateResult 实例 |

### 6.2 OAUpdateResult — 更新结果

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAUpdateResult`

**用途**：同步更新管道任务的返回结果。继承自 `OACreateResult`，字段与方法一致。

**字段（全部继承自 OACreateResult）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `hostMachine` | String | 服务端执行机器信息 |
| `pipelineId` | Long | 管道ID |
| `nodeId` | String | 管道任务调度节点ID |
| `submitId` | Long | 待发布ID |
| `version` | String | 版本号 |

### 6.3 OAOfflineResult — 下线结果

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAOfflineResult`

**用途**：同步下线管道任务的返回结果。继承自 `OACreateResult`，字段与方法一致。

**字段（全部继承自 OACreateResult）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `hostMachine` | String | 服务端执行机器信息 |
| `pipelineId` | Long | 管道ID |
| `nodeId` | String | 管道任务调度节点ID |
| `submitId` | Long | 待发布ID |
| `version` | String | 版本号 |

### 6.4 OAAsyncResult — 异步执行结果

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAAsyncResult`

**用途**：异步操作（创建/更新/下线）的执行结果。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `asyncId` | Long | 异步执行查询ID |
| `status` | String | 执行状态：`SUCCESS`-成功，`FAILED`-失败，`RUNNING`-执行中 |
| `errorCode` | String | 异常码（如 `DPN.Pipeline.InnerError`） |
| `errorMessage` | String | 异常信息 |
| `hostMachine` | String | 服务端主机信息 |
| `pipelineId` | Long | 管道主键ID |
| `nodeId` | String | 调度节点ID |
| `submitId` | Long | 待发布ID |
| `version` | String | 版本号 |

**内部枚举 OAAsyncStatusEnum**：

| 枚举值 | 说明 |
|--------|------|
| `SUCCESS` | 执行成功 |
| `FAILED` | 执行失败 |
| `RUNNING` | 执行中 |

**OAAsyncStatusEnum 方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `isComplete(String status)` | boolean | 静态方法，判断是否已完成（SUCCESS 或 FAILED） |
| `isSuccess(String status)` | boolean | 静态方法，判断是否成功 |
| `isFailed(String status)` | boolean | 静态方法，判断是否失败 |

### 6.5 OAPipelineNodeVO — 管道任务详情

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAPipelineNodeVO`

**用途**：查询管道任务返回的完整信息。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nodeInfo` | com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OANodeInfoVO | - | 管道任务基本信息（含desc字段） |
| `pipelineType` | Integer | `0` | 管道任务类型 |
| `mode` | String | `"PIPELINE"` | 配置模式 |
| `pipelineConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | - | 管道组件配置 |
| `pipelineJson` | String | - | 脚本模式配置 |
| `scheduleConfig` | String | - | 调度配置JSON字符串，通过 `OAScheduleConfigVO` 反序列化 |
| `settings` | String | - | 通道配置JSON字符串，通过 `OAPipelineSetting` 反序列化 |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAPipelineNodeVO.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `oaNodeInfoVO(OANodeInfoVO val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OANodeInfoVO | 设置管道任务基本信息 |
| `pipelineType(int val)` | int | 设置管道类型（0-离线，1-实时） |
| `pipelineType(OAPipelineType val)` | OAPipelineType | 设置管道类型（枚举方式） |
| `mode(String val)` | String | 设置配置模式（PIPELINE/JSON） |
| `mode(OAPipelineMode val)` | OAPipelineMode | 设置配置模式（枚举方式） |
| `pipelineConfig(OAPipelineConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 设置管道组件配置 |
| `pipelineJson(String val)` | String | 设置脚本模式JSON配置 |
| `scheduleConfig(OAScheduleConfigVO val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAScheduleConfigVO | 设置调度配置（自动序列化为JSON字符串） |
| `scheduleConfig(String val)` | String | 设置调度配置JSON字符串 |
| `settings(JSONObject val)` | JSONObject | 设置通道配置（自动序列化为JSON字符串） |
| `build()` | - | 构建 OAPipelineNodeVO 实例 |

### 6.6 OANodeInfoVO — 节点信息详情

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OANodeInfoVO`

**用途**：查询结果中的节点基本信息。继承自 `OANodeInfo`，新增 `desc` 字段。

**字段（含继承自 OANodeInfo 的字段）**：

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `pipelineId` | Long | 继承 | 管道任务ID |
| `fileId` | Long | 继承 | 管道文件ID |
| `nodeId` | String | 继承 | 调度节点ID |
| `nodeName` | String | 继承 | 集成管道任务名称 |
| `directory` | String | 继承 | 节点目录（默认 `"/"`) |
| `desc` | String | 新增 | 调度节点描述 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | VOBuilder | 静态方法，创建 VOBuilder 实例 |

**Builder 类 `OANodeInfoVO.VOBuilder`**

> 继承自 `OANodeInfo.Builder`，复用全部父类 Builder 方法。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `projectId(Long val)` | Long | （继承）设置项目ID |
| `pipelineId(Long val)` | Long | （继承）设置管道ID |
| `fileId(Long val)` | Long | （继承）设置文件ID |
| `nodeId(String val)` | String | （继承）设置节点ID |
| `nodeName(String val)` | String | （继承）设置任务名称 |
| `directory(String val)` | String | （继承）设置目录（默认 `"/"`） |
| `desc(String val)` | String | 设置调度节点描述 |
| `build()` | - | 构建 OANodeInfoVO 实例 |

### 6.7 OAScheduleConfigVO — 调度配置详情

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAScheduleConfigVO`

**用途**：查询结果中的调度配置详情。继承自 `OAScheduleConfig<OAUpStreamVO>`。

**字段（含继承自 OAScheduleConfig 的全部27个字段 + 4个新增字段）**：

*继承自 OAScheduleConfig 的字段详见 [7.5 OAScheduleConfig](#75-oascheduleconfigt--调度配置)，此处仅列出新增字段：*

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `nodeDesc` | String | 新增 | 节点描述 |
| `published` | Boolean | 新增 | 是否已发布 |
| `needPublish` | Boolean | 新增 | 是否需要发布 |
| `hasDevNode` | Boolean | 新增 | 是否存在开发调度节点 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `deserializeVO(String json)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAScheduleConfigVO | 静态方法，从 JSON 字符串反序列化为 OAScheduleConfigVO |
| `addUpstream(OAUpStreamVO upstream)` | void | （继承）添加上游依赖 |

### 6.8 OAUpStreamVO — 上游依赖详情

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vo.OAUpStreamVO`

**用途**：查询结果中的上游依赖详情。继承自 `OAUpStreamConfig`。

**字段（含继承自 OAUpStreamConfig 的全部字段）**：

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `valid` | Boolean | 继承 | 是否生效（默认 `true`） |
| `autoParse` | Boolean | 继承 | 是否自动解析（默认 `true`） |
| `dependencyPeriod` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyPeriod | 继承 | 依赖周期配置 |
| `dependencyStrategy` | String | 继承 | 依赖策略 |
| `nodeName` | String | 继承 | 依赖任务节点名称 |
| `nodeOutputTableName` | String | 继承 | 依赖节点输出表名 |
| `dependFields` | List\<String\> | 继承 | 依赖的字段 |
| `bizUnitId` | String | 继承 | 业务板块ID |
| `nodeId` | String | 继承 | 调度节点ID |
| `selfDepend` | boolean | 继承 | 是否自依赖（默认 `false`） |
| `nodeType` | String | 新增 | 节点任务分类（如 `PIPELINE_NODE`、`DATA_PROCESS`） |
| `subBizType` | String | 新增 | 任务类型（如 `DLINK`、`SHELL`、`SPARK`） |
| `nodeOutputName` | String | 新增 | 依赖任务节点输出名 |
| `scheduleIntervalType` | String | 新增 | 依赖任务调度周期 |
| `projectId` | String | 新增 | 依赖任务所在项目ID |
| `effectFields` | List\<String\> | 新增 | 影响的字段 |
| `customIntervalConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig | 新增 | 自定义调度间隔配置 |
| `customIntervalConfigs` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig\> | 新增 | 多个自定义间隔配置 |
| `customIntervalConfigType` | String | 新增 | 自定义配置间隔类型 |

---

## 7. model 包 — 管道配置模型类

### 7.1 OANodeInfo — 任务节点基本信息

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OANodeInfo`

**用途**：集成任务节点的基本标识信息。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `pipelineId` | Long | 条件 | - | 管道任务ID（创建时为空，更新时三选一） |
| `fileId` | Long | 条件 | - | 管道文件ID（创建时为空，更新时三选一） |
| `nodeId` | String | 条件 | - | 调度节点ID（创建时为空，更新时三选一） |
| `nodeName` | String | 是 | - | 集成管道任务名称 |
| `directory` | String | 否 | `"/"` | 节点目录（需预先创建offlinePipeline类型目录） |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OANodeInfo.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `projectId(Long val)` | Long | 设置项目ID |
| `pipelineId(Long val)` | Long | 设置管道ID |
| `fileId(Long val)` | Long | 设置文件ID |
| `nodeId(String val)` | String | 设置节点ID |
| `nodeName(String val)` | String | 设置任务名称 |
| `directory(String val)` | String | 设置目录（默认 `"/"`） |
| `build()` | - | 构建 OANodeInfo 实例 |

### 7.2 OAPipelineConfig — 管道配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig`

**用途**：集成管道任务的核心配置，定义组件(Steps)和连接(Hops)形成 DAG。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `steps` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig\> | 是 | 所有组件的详细配置列表 |
| `hops` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAHopConfig\> | 是 | DAG有向无环图连接关系 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `addStep(OAStepConfig step)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 添加单个组件配置 |
| `addSteps(List<OAStepConfig> steps)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 批量添加组件配置 |
| `addHop(OAHopConfig hop)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 添加单个连接 |
| `addHops(List<OAHopConfig> hops)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 批量添加连接 |
| `inputSteps()` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig\> | @Transient，获取所有输入组件 |
| `outputSteps()` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig\> | @Transient，获取所有输出组件 |
| `create(OABaseInputPluginConfig<? extends OAColumn> input, OABaseOutputPluginConfig<? extends OAColumnMapping> output)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 静态方法，创建仅含输入→输出的管道 |
| `create(OABaseInputPluginConfig<? extends OAColumn> input, OABaseTransformPluginConfig transform, OABaseOutputPluginConfig<? extends OAColumnMapping> output)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 静态方法，创建输入→转换→输出的管道 |
| `newOAPipelineConfig()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 静态方法，创建空的管道配置 |
| `deserialize(String json)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineConfig | 静态方法，从JSON字符串反序列化管道配置 |

### 7.3 OAStepConfig — 组件配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig`

**用途**：管道中每个组件的配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stepName` | String | 是 | 组件名称（管道内唯一） |
| `stepType` | String | 是 | 组件类型：`input`/`output`/`transform`/`process` |
| `key` | String | 是 | 插件唯一标识（如 `mysqlinput`、`maxcomputeoutput`） |
| `isDistribute` | Boolean | 否 | 数据分发方式：`true`-轮流分发（默认），`false`-全量复制 |
| `pluginConfig` | String | 是 | 组件配置JSON字符串 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `isInput()` | boolean | @Transient | 判断是否为输入组件 |
| `isOutput()` | boolean | @Transient | 判断是否为输出组件 |
| `stepTypeEqual(String other)` | boolean | @Transient | 判断组件类型是否与指定值相同（忽略大小写） |
| `builder()` | Builder | static | 创建 Builder 实例 |

**内部枚举 OAStepType**：

*以下为离线集成管道、数据归集任务、实时集成管道专用：*

| 值 | 标识 | 说明 |
|----|------|------|
| `INPUT` | `"input"` | 输入组件 |
| `OUTPUT` | `"output"` | 输出组件 |
| `TRANSFORM` | `"transform"` | 转换组件 |
| `PROCESS` | `"process"` | 流程控制组件 |

*以下为非结构化工作流任务专用：*

| 值 | 标识 | 说明 |
|----|------|------|
| `TEXT` | `"text"` | 文本算子 |
| `DOCUMENT` | `"document"` | 文档算子 |
| `IMAGE` | `"image"` | 图片算子 |
| `VIDEO` | `"video"` | 视频算子 |
| `AUDIO` | `"audio"` | 音频算子 |
| `VECTOR` | `"vector"` | 向量算子 |
| `NORMAL` | `"normal"` | 通用算子 |

**Builder 类 `OAStepConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `stepName(String val)` | String | 设置组件名称 |
| `stepType(String val)` | String | 设置组件类型（input/output/transform/process） |
| `stepType(OAStepType val)` | OAStepType | 设置组件类型（枚举方式） |
| `key(String val)` | String | 设置插件唯一标识 |
| `isDistribute(boolean val)` | boolean | 设置数据分发方式 |
| `pluginConfig(String val)` | String | 设置组件配置JSON字符串 |
| `pluginConfig(OABasePluginConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABasePluginConfig | 设置组件配置对象（自动提取 stepType/key/pluginConfig） |
| `build()` | - | 构建 OAStepConfig 实例 |

### 7.4 OAHopConfig — 组件连接配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAHopConfig`

**用途**：定义组件之间的 DAG 连接关系。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | String | 是 | 上游组件名称（对应 `OAStepConfig.stepName`） |
| `target` | String | 是 | 下游组件名称 |
| `sendTo` | Boolean | 否 | 条件分发组件专用：`true`-条件为真时发送 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAHopConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `source(String val)` | String | 设置上游组件名称 |
| `source(OAStepConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig | 设置上游组件（自动提取 stepName） |
| `target(String val)` | String | 设置下游组件名称 |
| `target(OAStepConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAStepConfig | 设置下游组件（自动提取 stepName） |
| `sendTo(Boolean val)` | Boolean | 设置条件分发标识 |
| `build()` | - | 构建 OAHopConfig 实例 |

### 7.5 OAScheduleConfig\<T\> — 调度配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAScheduleConfig`

**用途**：集成管道任务的完整调度配置，泛型参数 `T` 为上游依赖类型。继承自 `JsonSerializable`。

#### 基本信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nodeId` | String | - | 调度节点ID（首次创建为空，更新时必填） |
| `owner` | String | 当前用户 | 运维负责人ID |
| `opsOwnerList` | List\<String\> | - | 多个运维负责人ID |
| `developOwner` | String | 当前用户 | 开发负责人ID |
| `developOwnerList` | List\<String\> | - | 多个开发负责人ID |
| `taskTagList` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmTag\> | - | 标签列表 |
| `nodeType` | Integer | `1` | 节点调度类型：`1`-周期调度，`3`-手动调度，`5`-实时节点 |

#### 运行参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `params` | String | 调度参数，多个逗号分割，如 `paramKey=${yyyyMMdd}` |

#### 调度配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `baseScheduleTemplateId` | Long | - | 基础调度模板ID |
| `baseScheduleTemplateName` | String | - | 基础调度模板名称 |
| `nodeStatus` | Integer | `1` | 调度状态：`1`-正常，`2`-暂停，`3`-空跑 |
| `priority` | Integer | `5` | 优先级（1-9，值越小越高） |
| `scheduleIntervalType` | String | `"DAILY"` | 调度周期 |
| `cronExpression` | String | `"0 0 0 * * ?"` | cron表达式（必填） |
| `customCronExpression` | Boolean | `false` | 是否自定义调度周期 |
| `customIntervalConfigType` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfigTypeEnum | - | 自定义间隔类型 |
| `customIntervalConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig | - | 自定义间隔配置 |
| `customIntervalConfigs` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig\> | - | 多个自定义间隔 |
| `conditionScheduleEnable` | Boolean | - | 是否开启条件调度 |
| `conditionScheduleTemplateId` | Long | - | 条件调度模板ID |
| `conditionScheduleTemplateName` | String | - | 条件调度模板名称 |
| `conditionScheduleParamDTOList` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmConditionScheduleParam\> | - | 条件调度配置 |

#### 调度依赖

| 字段 | 类型 | 说明 |
|------|------|------|
| `taskUpstreamNodes` | List\<T\> | 上游依赖（可不配，系统自动解析输入组件依赖） |

#### 本节点输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `nodeOutputNameList` | List\<String\> | 节点输出名称（首次创建可不设，系统生成） |

#### 运行配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `executeTimeOutConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteTimeOutConfig | 运行超时配置 |
| `executeRerunConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteRerunConfig | 失败自动重跑配置 |
| `retryOnTimeoutEnable` | Boolean | 是否允许超时失败自动重跑 |

#### 工作流算子配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `dirtyDataStrategy` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmNeuronDirtyDataStrategy | 工作流算子脏数据处理策略（仅非结构化工作流算子生效，通过工作流创建时默认为 IGNORE） |

#### 资源组配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `resourceGroupId` | String | `"default"` | 生产资源组ID |
| `resourceGroupName` | String | `"default"` | 生产资源组名称 |
| `devResourceGroupId` | String | `"default"` | 开发环境资源组ID |
| `devResourceGroupName` | String | `"default"` | 开发环境资源组名称 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `addUpstream(T upstream)` | void | 添加一个上游依赖 |
| `deserialize(String json)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAScheduleConfig | 静态方法，从JSON反序列化 |
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAScheduleConfig.Builder<T>`**

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| `nodeId(String val)` | String | - | 设置调度节点ID |
| `owner(String val)` | String | - | 设置运维负责人ID |
| `opsOwnerList(List<String> val)` | List\<String\> | - | 设置多个运维负责人ID |
| `developOwner(String val)` | String | - | 设置开发负责人ID |
| `developOwnerList(List<String> val)` | List\<String\> | - | 设置多个开发负责人ID |
| `taskTagList(List<VdmTag> val)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmTag\> | - | 设置标签列表 |
| `nodeType(Integer val)` | Integer | `1` | 设置节点调度类型 |
| `nodeType(VdmTaskScheduleTypeEnum val)` | VdmTaskScheduleTypeEnum | - | 设置节点调度类型（枚举方式） |
| `params(String val)` | String | - | 设置调度参数 |
| `baseScheduleTemplateId(Long val)` | Long | - | 设置基础调度模板ID |
| `baseScheduleTemplateName(String val)` | String | - | 设置基础调度模板名称 |
| `nodeStatus(Integer val)` | Integer | `1` | 设置调度状态 |
| `nodeStatus(VdmNodeStatusEnum val)` | VdmNodeStatusEnum | - | 设置调度状态（枚举方式） |
| `priority(Integer val)` | Integer | `5` | 设置优先级（1-9） |
| `scheduleIntervalType(String val)` | String | `"DAILY"` | 设置调度周期 |
| `scheduleIntervalType(VdmScheduleIntervalTypeEnum val)` | VdmScheduleIntervalTypeEnum | - | 设置调度周期（枚举方式） |
| `cronExpression(String val)` | String | `"0 0 0 * * ?"` | 设置cron表达式 |
| `customCronExpression(Boolean val)` | Boolean | `false` | 设置是否自定义调度 |
| `customIntervalConfigType(VdmCustomIntervalConfigTypeEnum val)` | VdmCustomIntervalConfigTypeEnum | - | 设置自定义间隔类型 |
| `customIntervalConfig(VdmCustomIntervalConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig | - | 设置自定义间隔配置 |
| `customIntervalConfigs(List<VdmCustomIntervalConfig> val)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig\> | - | 设置多个自定义间隔 |
| `conditionScheduleEnable(Boolean val)` | Boolean | - | 设置是否开启条件调度 |
| `conditionScheduleTemplateId(Long val)` | Long | - | 设置条件调度模板ID |
| `conditionScheduleTemplateName(String val)` | String | - | 设置条件调度模板名称 |
| `conditionScheduleParamDTOList(List<VdmConditionScheduleParam> val)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmConditionScheduleParam\> | - | 设置条件调度配置 |
| `taskUpstreamNodes(List<T> val)` | List\<T\> | - | 设置上游依赖列表 |
| `nodeOutputNameList(List<String> val)` | List\<String\> | - | 设置节点输出名称 |
| `executeTimeOutConfig(VdmExecuteTimeOutConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteTimeOutConfig | - | 设置超时配置 |
| `executeRerunConfig(VdmExecuteRerunConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteRerunConfig | - | 设置重跑配置 |
| `retryOnTimeoutEnable(Boolean val)` | Boolean | - | 设置超时重跑 |
| `dirtyDataStrategy(VdmNeuronDirtyDataStrategy val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmNeuronDirtyDataStrategy | - | 设置工作流算子脏数据处理策略（仅非结构化工作流生效） |
| `resourceGroupId(String val)` | String | `"default"` | 设置生产资源组ID |
| `resourceGroupName(String val)` | String | `"default"` | 设置生产资源组名称 |
| `devResourceGroupId(String val)` | String | `"default"` | 设置开发资源组ID |
| `devResourceGroupName(String val)` | String | `"default"` | 设置开发资源组名称 |
| `build()` | - | - | 构建 OAScheduleConfig 实例 |

### 7.6 OAUpStreamConfig — 上游依赖配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAUpStreamConfig`

**用途**：管道任务的上游依赖配置，支持自动解析和手动指定两种方式。继承自 `JsonSerializable`。

#### 通用配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `valid` | Boolean | `true` | 是否生效 |
| `autoParse` | Boolean | `true` | 是否自动解析 |
| `dependencyPeriod` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyPeriod | - | 依赖周期配置 |
| `dependencyStrategy` | String | - | 依赖策略（参考 `VdmDependencyStrategyTypeEnum`） |

#### 自动解析回显

| 字段 | 类型 | 说明 |
|------|------|------|
| `nodeName` | String | 依赖任务节点名称 |
| `nodeOutputTableName` | String | 依赖节点输出表名 |
| `dependFields` | List\<String\> | 依赖的字段 |
| `bizUnitId` | String | 业务板块ID |

#### 手动配置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nodeId` | String | - | 调度节点ID |
| `selfDepend` | boolean | `false` | 是否自依赖 |

**方法（继承自 JsonSerializable）**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | 将对象转换为 JSONObject |
| `toJsonString()` | String | 将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAUpStreamConfig.Builder`**

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| `valid(Boolean val)` | Boolean | `true` | 设置是否生效 |
| `autoParse(Boolean val)` | Boolean | `true` | 设置是否自动解析 |
| `dependencyPeriod(VdmDependencyPeriod val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyPeriod | - | 设置依赖周期 |
| `dependencyStrategy(String val)` | String | - | 设置依赖策略 |
| `nodeName(String val)` | String | - | 设置依赖任务节点名称 |
| `nodeOutputTableName(String val)` | String | - | 设置依赖节点输出表名 |
| `dependFields(List<String> val)` | List\<String\> | - | 设置依赖字段 |
| `bizUnitId(String val)` | String | - | 设置业务板块ID |
| `nodeId(String val)` | String | - | 设置调度节点ID |
| `selfDepend(boolean val)` | boolean | `false` | 设置是否自依赖 |
| `build()` | - | - | 构建 OAUpStreamConfig 实例 |

### 7.7 OAPipelineSetting — 通道配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting`

**用途**：集成管道任务的运行通道配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `errorLimit` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OAErrorLimit | `record=0` | 容错配置 |
| `speed` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OASpeed | `concurrent=3` | 全局并发度 |
| `requiredResource` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OARequiredResource | `cpus=0.5, memoryInMb=1024` | JVM资源配置 |
| `sqlTimeout` | Integer | `30` | SQL执行超时（分钟） |
| `noFlowTimeout` | Integer | `30` | 无流量超时（分钟） |
| `timeZone` | String | `"Asia/Shanghai"` | JVM时区 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （覆写）将对象转换为 JSONObject，包含 otherSettings |
| `toJsonString()` | String | （覆写）将对象序列化为 JSON 字符串，包含 otherSettings |
| `addOtherSetting(JSONObject otherSettings)` | void | 添加自定义通道配置（JSONObject方式） |
| `addOtherSetting(String otherSettings)` | void | 添加自定义通道配置（JSON字符串方式） |
| `deserialize(String json)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting | 静态方法，从JSON反序列化 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**内部类**：
- **OAErrorLimit**：`record`(Integer, 默认0) — 最大允许脏数据记录数
- **OASpeed**：`concurrent`(Integer, 默认3) — 并发数
- **OARequiredResource**：`cpus`(Double, 默认0.5) + `memoryInMb`(Long, 默认1024) — CPU/内存配置

**Builder 类 `OAPipelineSetting.Builder`**

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| `errorLimit(OAErrorLimit val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OAErrorLimit | `record=0` | 设置容错配置 |
| `speed(OASpeed val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OASpeed | `concurrent=3` | 设置并发度 |
| `requiredResource(OARequiredResource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineSetting.OARequiredResource | `cpus=0.5, memoryInMb=1024` | 设置JVM资源 |
| `sqlTimeout(Integer val)` | Integer | `30` | 设置SQL超时（分钟） |
| `noFlowTimeout(Integer val)` | Integer | `30` | 设置无流量超时（分钟） |
| `timeZone(String val)` | String | `"Asia/Shanghai"` | 设置JVM时区 |
| `build()` | - | - | 构建 OAPipelineSetting 实例 |

### 7.8 OAPipelineDataTypeEnum — 管道数据类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineDataTypeEnum`

**用途**：定义管道中间层的字段数据类型。

| 枚举值 | 数据类型 | 说明 |
|--------|----------|------|
| `LONG` | Long | 整形 |
| `STRING` | String | 字符串 |
| `DOUBLE` | Double | 浮点型 |
| `BOOLEAN` | Boolean | 布尔型 |
| `BOOL` | Boolean | 布尔型（BOOLEAN的别名） |
| `BYTES` | Bytes | 二进制 |
| `DATE` | Date | 日期型 `yyyy-mm-dd` |
| `TIME` | Time | 时间型 `hh:mm:ss` |
| `DATETIME` | DateTime | 日期时间 `yyyy-MM-dd hh:mm:ss` |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `getDataType()` | String | 获取数据类型字符串 |
| `of(String dataType)` | OAPipelineDataTypeEnum | 静态方法，根据数据类型字符串获取枚举（忽略大小写，"Bool"映射到BOOLEAN） |

### 7.9 OAPluginFactory — 插件工厂

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPluginFactory`

**用途**：通过反射自动收集所有 `OABasePluginConfig` 子类并注册，可通过 `stepKey` 获取插件实例。

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `get(String stepKey)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABasePluginConfig | 静态方法，根据 stepKey 获取对应的插件配置实例 |

---

## 8. model.plugin 包 — 组件插件配置

### 8.1 OABasePluginConfig（抽象基类）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABasePluginConfig`

**用途**：所有组件配置的抽象基类，定义数据源和组件标识的通用属性。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 数据源分类（参考 `OADataSourceCategoryEnum`） |
| `accessMode` | String | - | 访问模式：`DataSource` 或 `OneCatalog`（参考 `OAAccessMode`） |
| `catalogType` | String | - | OneCatalog模式下的类型（参考 `OAOneCatalogTypeEnum`） |
| `dsProjectId` | String | - | 计算源绑定的项目ID |
| `dsId` | String | - | 数据源ID（与dsName二选一） |
| `dsName` | String | - | 数据源名称（与dsId二选一） |
| `version` | String | - | 数据集版本（仅dataSourceCategory=DATA_SET时使用） |
| `timeZoneFrom` | String | `"datasource"` | 时区来源：`datasource`-数据源配置，`jvm`-管道配置（参考 `OATimeZoneFrom`） |

**抽象方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepType()` | String | @Transient abstract | 返回组件类型（input/output/transform/process） |
| `stepKey()` | String | @Transient abstract | 返回组件唯一标识 |
| `oneTableWithFullName()` | String | @Transient abstract | 返回完整表名（格式：`[catalog.][schema.]table`） |
| `dsType()` | String | @Transient abstract | 返回数据源类型 |
| `schema()` | String | @Transient abstract | 返回表的上级限定（database or schema） |

**实例方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `datasource()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | @Transient | 根据当前配置自动构建对应类型的数据源对象 |
| `setDatasource(BaseOADatasource)` | void | @Transient | 根据传入的数据源类型自动设置对应字段 |
| `setDatasetDatasource(OADatasetDatasource)` | void | @Transient | 设置数据集数据源（自动设置 dataSourceCategory/dsId/version） |
| `toJson()` | JSONObject | @Transient | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | @Transient | （继承）将对象序列化为 JSON 字符串 |

**Builder 类 `OABasePluginConfig.BaseBuilder<T>`**（抽象）

> 所有输入/输出组件 Builder 的基类，提供数据源快捷设置和基础字段配置。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `datasource(BaseOADatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | 设置数据源（自动识别类型并委托对应方法） |
| `physicalDatasource(OAPhysicalDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAPhysicalDatasource | 设置物理数据源（自动设置 dataSourceCategory/dsId/dsName） |
| `projectComputeDatasource(OAProjectComputeDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAProjectComputeDatasource | 设置项目计算源（自动设置 dataSourceCategory/dsProjectId/dsId） |
| `oneCatalogDatasource(OAOneCatalogDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAOneCatalogDatasource | 设置OneCatalog数据源（自动设置 accessMode/catalogType/dsId/dsName） |
| `datasetDatasource(OADatasetDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OADatasetDatasource | 设置数据集数据源（自动设置 dataSourceCategory/dsId/version） |
| `dataSourceCategory(String val)` | String | 设置数据源分类 |
| `accessMode(String val)` | String | 设置访问模式 |
| `accessMode(OAAccessMode val)` | OAAccessMode | 设置访问模式（枚举方式） |
| `catalogType(String val)` | String | 设置OneCatalog类型 |
| `dsProjectId(String val)` | String | 设置计算源项目ID |
| `dsId(String val)` | String | 设置数据源ID |
| `dsName(String val)` | String | 设置数据源名称 |
| `timeZoneFrom(String val)` | String | 设置时区来源 |
| `timeZoneFrom(OATimeZoneFrom val)` | OATimeZoneFrom | 设置时区来源（枚举方式） |
| `version(String val)` | String | 设置数据集版本（仅dataSourceCategory=DATA_SET时使用） |
| `build()` | - | 抽象方法，由子类实现 |

### 8.2 OABaseInputPluginConfig\<U\>（抽象）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABaseInputPluginConfig`

**用途**：输入组件基类，`stepType` 固定为 `"input"`。继承自 `OABasePluginConfig`。

**字段（含继承自 OABasePluginConfig 的字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承 | 数据源分类 |
| `accessMode` | String | - | 继承 | 访问模式 |
| `catalogType` | String | - | 继承 | OneCatalog模式下的类型 |
| `dsProjectId` | String | - | 继承 | 计算源绑定的项目ID |
| `dsId` | String | - | 继承 | 数据源ID |
| `dsName` | String | - | 继承 | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承 | 时区来源 |
| `column` | List\<U extends com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | - | 新增 | 读取字段列表（支持元数据查询的数据源可不配） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `stepType()` | String | 固定返回 `"input"` |
| `datasource()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | （继承）构建数据源对象 |
| `setDatasource(BaseOADatasource)` | void | （继承）设置数据源 |

**Builder 类 `OABaseInputPluginConfig.BaseInputBuilder<U,T>`**

> 继承自 `BaseBuilder<T>`，新增输入字段列表设置。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder 方法）* | | |
| `newColumn(String columnName)` | U | 抽象方法，根据字段名创建字段对象（由子类实现） |
| `column(List<U> val)` | List\<U\> | 设置读取字段列表 |
| `addColumn(U column)` | BaseInputBuilder\<U,T\> | 添加单个字段对象 |
| `addColumn(String columnName)` | BaseInputBuilder\<U,T\> | 根据字段名添加单个字段（调用 newColumn） |
| `columnNames(List<String> columnNames)` | BaseInputBuilder\<U,T\> | 根据字段名列表批量设置字段 |
| `columnNames(String... columnNames)` | BaseInputBuilder\<U,T\> | 根据字段名可变参数批量设置字段 |

### 8.3 OABaseOutputPluginConfig\<U\>（抽象）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABaseOutputPluginConfig`

**用途**：输出组件基类，`stepType` 固定为 `"output"`。继承自 `OABasePluginConfig`。

**字段（含继承自 OABasePluginConfig 的字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承 | 数据源分类 |
| `accessMode` | String | - | 继承 | 访问模式 |
| `catalogType` | String | - | 继承 | OneCatalog模式下的类型 |
| `dsProjectId` | String | - | 继承 | 计算源绑定的项目ID |
| `dsId` | String | - | 继承 | 数据源ID |
| `dsName` | String | - | 继承 | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承 | 时区来源 |
| `columnMappings` | List\<U extends com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping\> | - | 新增 | 字段映射列表 |
| `loadStrategy` | String | - | 新增 | 加载策略 |
| `prodTableNotExistAction` | String | `"ignore"` | 新增 | 生产表不存在时策略 |
| `prodTableDdl` | String | - | 新增 | 生产建表DDL |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `stepType()` | String | 固定返回 `"output"` |
| `datasource()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | （继承）构建数据源对象 |
| `setDatasource(BaseOADatasource)` | void | （继承）设置数据源 |

**加载策略枚举 OALoadStrategy**：`OVER_WRITE`("overwrite") | `TRUNCATE_ALL`("truncateAll") | `APPEND`("append") | `UPDATE`("update")

**表不存在策略 TableNotExistAction**：`IGNORE`("ignore") | `AUTO_CREATE`("autocreate")

**Builder 类 `OABaseOutputPluginConfig.BaseOutputBuilder<U,T>`**

> 继承自 `BaseBuilder<T>`，新增输出组件特有字段设置。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder 方法）* | | |
| `columnMappings(List<U> val)` | List\<U\> | 设置字段映射列表 |
| `loadStrategy(String val)` | String | 设置加载策略 |
| `loadStrategy(OALoadStrategy val)` | OALoadStrategy | 设置加载策略（枚举方式） |
| `prodTableNotExistAction(String val)` | String | 设置生产表不存在时策略 |
| `prodTableNotExistAction(TableNotExistAction val)` | TableNotExistAction | 设置生产表不存在时策略（枚举方式） |
| `prodTableDdl(String val)` | String | 设置生产建表DDL |

### 8.4 OABaseTransformPluginConfig（抽象）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OABaseTransformPluginConfig`

**用途**：转换/流程控制组件基类。继承自 `OABasePluginConfig`。`oneTableWithFullName()`、`dsType()`、`schema()` 固定返回 `null`。

**字段（全部继承自 OABasePluginConfig）**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 数据源分类 |
| `accessMode` | String | - | 访问模式 |
| `catalogType` | String | - | OneCatalog模式下的类型 |
| `dsProjectId` | String | - | 计算源绑定的项目ID |
| `dsId` | String | - | 数据源ID |
| `dsName` | String | - | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 时区来源 |

### 8.5 OAColumn — 字段定义

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn`

**用途**：输入组件的字段配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `index` | Integer | 字段位置（从0开始，读文件类组件需配置） |
| `name` | String | 字段名称 |
| `originalType` | String | 字段原始数据类型 |
| `type` | String | 映射到管道中间层的字段类型（参考 `OAPipelineDataTypeEnum`） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `create(String... columnName)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | 静态方法，根据字段名快速创建字段列表 |
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAColumn.Builder<T>`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `index(Integer val)` | Integer | 设置字段位置（从0开始） |
| `name(String val)` | String | 设置字段名称 |
| `originalType(String val)` | String | 设置原始数据类型 |
| `type(String val)` | String | 设置管道中间层字段类型 |
| `type(OAPipelineDataTypeEnum val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineDataTypeEnum | 设置管道中间层字段类型（枚举方式） |
| `build()` | - | 构建 OAColumn 实例 |

### 8.6 OAColumnMapping — 字段映射

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping`

**用途**：输出组件的输入→输出字段映射配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `sourceColumn` | String | 输入字段名 |
| `targetColumn` | String | 输出字段名 |
| `originalType` | String | 目标字段原始类型 |
| `type` | String | 映射到管道中间层的字段类型 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAColumnMapping.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `sourceColumn(String val)` | String | 设置输入字段名 |
| `targetColumn(String val)` | String | 设置输出字段名 |
| `originalType(String val)` | String | 设置目标字段原始类型 |
| `type(String val)` | String | 设置管道中间层字段类型 |
| `build()` | - | 构建 OAColumnMapping 实例 |

### 8.7 OAKey — 字段常量

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAKey`

**用途**：组件配置中的常用 JSON Key。

| 常量 | 值 | 说明 |
|------|----|------|
| `CATALOG` | `"catalog"` | catalog字段 |
| `SCHEMA` | `"schema"` | schema字段 |
| `COLUMN_MAPPINGS` | `"columnMappings"` | 字段映射 |
| `TABLES` | `"tables"` | 多表 |
| `TABLE` | `"table"` | 单表 |

---

## 9. model.plugin.datasource 包 — 数据源配置

### 9.1 OADataSourceCategoryEnum — 数据源分类

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OADataSourceCategoryEnum`

| 枚举值 | 说明 |
|--------|------|
| `DATA_SOURCE` | Dataphin物理数据源 |
| `PROJECT_COMPUTE_SOURCE` | 单引擎模式绑定项目的计算源 |
| `ONE_CATALOG` | 多引擎模式（OneCatalog）的计算源或catalog |
| `DATA_SET` | Dataphin数据集（非结构化工作流专用） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `equals(String category)` | boolean | 忽略大小写比较字符串与枚举名称 |

### 9.2 OAAccessMode — 访问模式

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAAccessMode`

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `ONE_CATALOG` | `"OneCatalog"` | OneCatalog模式 |
| `DATASOURCE` | `"DataSource"` | 数据源模式 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `equal(String other)` | boolean | 忽略大小写比较 |

### 9.3 OAOneCatalogTypeEnum — OneCatalog类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAOneCatalogTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `COMPUTE_CLUSTER` | 计算集群 |
| `DATA_SOURCE` | Dataphin物理数据源 |

### 9.4 BaseOADatasource（抽象基类）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource`

**用途**：所有数据源配置的抽象基类。继承自 `JsonSerializable`，无自身字段。

### 9.5 OAPhysicalDatasource — 物理数据源

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAPhysicalDatasource`

**用途**：Dataphin物理数据源配置。继承自 `BaseOADatasource`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `dsId` | String | 物理数据源ID（与dsName二选一） |
| `dsName` | String | 物理数据源名称（与dsId二选一，需唯一） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAPhysicalDatasource.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dsId(String val)` | String | 设置物理数据源ID |
| `dsName(String val)` | String | 设置物理数据源名称 |
| `build()` | - | 构建 OAPhysicalDatasource 实例 |

### 9.6 OAProjectComputeDatasource — 项目计算源

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAProjectComputeDatasource`

**用途**：Dataphin单引擎模式绑定项目的计算源。继承自 `BaseOADatasource`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `dsProjectId` | String | 条件 | 绑定的项目ID（与dsProjectName二选一） |
| `dsProjectName` | String | 条件 | 绑定的项目名称 |
| `dsId` | String | 是 | 计算源ID |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAProjectComputeDatasource.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dsProjectId(String val)` | String | 设置绑定项目ID |
| `dsProjectName(String val)` | String | 设置绑定项目名称 |
| `dsId(String val)` | String | 设置计算源ID |
| `build()` | - | 构建 OAProjectComputeDatasource 实例 |

### 9.7 OAOneCatalogDatasource — OneCatalog数据源

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OAOneCatalogDatasource`

**用途**：Dataphin多引擎模式（OneCatalog）下的catalog数据源。继承自 `BaseOADatasource`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `oneCatalogType` | String | OneCatalog类型（参考 `OAOneCatalogTypeEnum`） |
| `dsId` | String | 数据源/计算源ID（与dsName二选一） |
| `dsName` | String | 数据源/计算源名称 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OAOneCatalogDatasource.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `oneCatalogType(String val)` | String | 设置OneCatalog类型 |
| `dsId(String val)` | String | 设置数据源/计算源ID |
| `dsName(String val)` | String | 设置数据源/计算源名称 |
| `build()` | - | 构建 OAOneCatalogDatasource 实例 |

### 9.8 OATimeZoneFrom — 时区来源

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OATimeZoneFrom`

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `DATASOURCE` | `"datasource"` | 使用数据源配置的时区 |
| `JVM` | `"jvm"` | 使用管道配置的JVM时区 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `getValue()` | String | 获取枚举对应的值 |

### 9.9 OADatasetDatasource — 数据集数据源

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OADatasetDatasource`

**用途**：Dataphin数据集配置，用于非结构化工作流任务的算子输入/输出数据集。继承自 `BaseOADatasource`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `dsId` | String | 数据集ID |
| `version` | String | 数据集版本 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |

**Builder 类 `OADatasetDatasource.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dsId(String val)` | String | 设置数据集ID |
| `dsId(Long val)` | Long | 设置数据集ID（Long类型，自动转为字符串） |
| `version(String val)` | String | 设置数据集版本 |
| `build()` | - | 构建 OADatasetDatasource 实例 |

---

## 10. model.plugin.input 包 — 输入组件

### 10.1 OARdbmsInputConfig — 通用关系型数据库输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OARdbmsInputConfig`

**stepKey**：`rdbmsinput` | **dsType**：动态指定 | 继承自 `OABaseInputPluginConfig<OAColumn>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `column` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | - | 继承(OABaseInputPluginConfig) | 读取字段列表 |
| `stepKey` | String | - | 新增 | 动态指定stepKey |
| `dsType` | String | - | 新增 | 动态指定dsType |
| `multiTable` | boolean | `false` | 新增 | 是否多表模式 |
| `tableNamePattern` | String | - | 新增 | 多表正则模式（如 `test_[1-9]`） |
| `prefix` | String | - | 新增 | 同 tableNamePattern |
| `schemaName` | String | - | 新增 | schema/database名称 |
| `tables` | List\<String\> | - | 新增 | 输入表名列表（必填） |
| `splitKey` | String | - | 新增 | 切分主键（整形或时间类型） |
| `where` | String | - | 新增 | 过滤条件 |
| `encoding` | String | - | 新增 | 编码格式 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 返回 stepKey 或默认 `"rdbmsinput"` |
| `dsType()` | String | @Transient | 返回动态指定的 dsType |
| `schema()` | String | @Transient | 返回 schemaName |
| `oneTableWithFullName()` | String | @Transient | 返回 `[schema.]table` 格式的完整表名 |
| `setTable(String table)` | void | - | 添加单张表（同时设置 prefix 和 tables） |
| `datasource()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | @Transient | （继承）构建数据源对象 |
| `builder()` | RdbmsInputBuilder | static | 创建 Builder 实例 |

**Builder 类 `OARdbmsInputConfig.RdbmsInputBuilder`**

> 继承自 `BaseInputBuilder<OAColumn, OARdbmsInputConfig>`，包含全部 BaseBuilder + BaseInputBuilder 方法。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder + BaseInputBuilder 方法）* | | |
| `newColumn(String columnName)` | OAColumn | 根据字段名创建 OAColumn 实例 |
| `stepKey(String val)` | String | 动态指定 stepKey |
| `dsType(String val)` | String | 动态指定 dsType |
| `multiTable(boolean val)` | boolean | 设置是否多表模式 |
| `tableNamePattern(String val)` | String | 设置多表正则模式 |
| `prefix(String val)` | String | 设置表名前缀 |
| `schemaName(String val)` | String | 设置 schema 名称 |
| `tables(List<String> val)` | List\<String\> | 设置输入表名列表 |
| `table(String val)` | String | 添加单张表（代理到 addTable） |
| `addTable(String val)` | String | 添加一张输入表 |
| `splitKey(String val)` | String | 设置切分主键 |
| `where(String val)` | String | 设置过滤条件 |
| `encoding(String val)` | String | 设置编码格式 |
| `build()` | - | 构建 OARdbmsInputConfig 实例 |

### 10.2 OAMysqlInputConfig — MySQL输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAMysqlInputConfig`

**stepKey**：`mysqlinput` | **dsType**：`MYSQL` | 继承自 `OARdbmsInputConfig`

字段与 OARdbmsInputConfig 完全一致，仅 `stepKey()` 固定返回 `"mysqlinput"`，`dsType()` 固定返回 `"MYSQL"`。

### 10.3 OAOracleInputConfig — Oracle输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAOracleInputConfig`

**stepKey**：`oracleinput` | **dsType**：`ORACLE` | 继承自 `OARdbmsInputConfig`

字段与 OARdbmsInputConfig 完全一致，仅 `stepKey()` 固定返回 `"oracleinput"`，`dsType()` 固定返回 `"ORACLE"`。

### 10.4 OAPgInputConfig — PostgreSQL输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAPgInputConfig`

**stepKey**：`postgresqlinput` | **dsType**：`POSTGRE_SQL` | 继承自 `OARdbmsInputConfig`

字段与 OARdbmsInputConfig 完全一致，仅 `stepKey()` 固定返回 `"postgresqlinput"`，`dsType()` 固定返回 `"POSTGRE_SQL"`。

### 10.5 OASqlServerInputConfig — SQL Server输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OASqlServerInputConfig`

**stepKey**：`sqlserverinput` | **dsType**：`SQL_SERVER` | 继承自 `OARdbmsInputConfig`

字段与 OARdbmsInputConfig 完全一致，仅 `stepKey()` 固定返回 `"sqlserverinput"`，`dsType()` 固定返回 `"SQL_SERVER"`。

### 10.6 OACustomRdbmsInputConfig — 自定义RDBMS输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OACustomRdbmsInputConfig`

继承自 `OARdbmsInputConfig`，可通过设置 `stepKey` 和 `dsType` 自定义组件标识。新增字段：

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `table` | String | 新增 | 仅支持单表（覆写 `setTable` 方法） |

### 10.7 OAOdpsInputConfig — MaxCompute(ODPS)输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAOdpsInputConfig`

**stepKey**：`maxcomputeinput` | **dsType**：`MAX_COMPUTE` | 继承自 `OABaseInputPluginConfig<OAColumn>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `column` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | - | 继承(OABaseInputPluginConfig) | 读取字段列表 |
| `table` | String | - | 新增 | 输入表名 |
| `partition` | String | - | 新增 | 分区表达式 |
| `strategyOnNoPartition` | String | `"fail"` | 新增 | 无分区时策略 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"maxcomputeinput"` |
| `dsType()` | String | @Transient | 固定返回 `"MAX_COMPUTE"` |
| `schema()` | String | @Transient | 固定返回 `null` |
| `oneTableWithFullName()` | String | @Transient | 返回 table |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAOdpsInputConfig.Builder`**

> 继承自 `BaseInputBuilder<OAColumn, OAOdpsInputConfig>`，包含全部 BaseBuilder + BaseInputBuilder 方法。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder + BaseInputBuilder 方法）* | | |
| `newColumn(String columnName)` | OAColumn | 根据字段名创建 OAColumn 实例 |
| `table(String val)` | String | 设置输入表名 |
| `partition(String val)` | String | 设置分区表达式 |
| `strategyOnNoPartition(String val)` | String | 设置无分区时策略（默认 `"fail"`） |
| `build()` | - | 构建 OAOdpsInputConfig 实例 |

### 10.8 OAHiveInputConfig — Hive输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAHiveInputConfig`

**stepKey**：`hadoophiveinput` | **dsType**：`HIVE` | 继承自 `OABaseInputPluginConfig<OAColumn>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `column` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | - | 继承(OABaseInputPluginConfig) | 读取字段列表 |
| `catalog` | String | - | 新增 | catalog名称 |
| `schema` | String | - | 新增 | schema名称 |
| `table` | String | - | 新增 | 输入表名 |
| `partition` | String | - | 新增 | 分区表达式 |
| `fileCode` | String | - | 新增 | 文件编码 |
| `nullFormat` | String | `"\\N"` | 新增 | 空值字符串 |
| `zipType` | String | - | 新增 | 压缩格式 |
| `separator` | String | `"\\u0001"` | 新增 | 字段分隔符 |
| `successIfNoData` | Boolean | `false` | 新增 | 无数据是否允许成功 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"hadoophiveinput"` |
| `dsType()` | String | @Transient | 固定返回 `"HIVE"` |
| `schema()` | String | - | 返回 schema 字段 |
| `oneTableWithFullName()` | String | @Transient | 返回 `[catalog.][schema.]table` 格式 |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAHiveInputConfig.Builder`**

> 继承自 `BaseInputBuilder<OAColumn, OAHiveInputConfig>`，包含全部 BaseBuilder + BaseInputBuilder 方法。

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| *（继承全部 BaseBuilder + BaseInputBuilder 方法）* | | | |
| `newColumn(String columnName)` | OAColumn | - | 根据字段名创建 OAColumn 实例 |
| `catalog(String val)` | String | - | 设置 catalog |
| `schema(String val)` | String | - | 设置 schema |
| `table(String val)` | String | - | 设置输入表名 |
| `partition(String val)` | String | - | 设置分区表达式 |
| `fileCode(String val)` | String | - | 设置文件编码 |
| `nullFormat(String val)` | String | `"\\N"` | 设置空值字符串 |
| `zipType(String val)` | String | - | 设置压缩格式 |
| `separator(String val)` | String | `"\\u0001"` | 设置字段分隔符 |
| `successIfNoData(Boolean val)` | Boolean | `false` | 设置无数据是否允许成功 |
| `build()` | - | - | 构建 OAHiveInputConfig 实例 |

### 10.9 OAJsonInputConfig — JSON输入

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.input.OAJsonInputConfig`

**stepKey**：`jsoninput` | 继承自 `OABaseInputPluginConfig<OAColumn>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `column` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | - | 继承(OABaseInputPluginConfig) | 读取字段列表 |
| `innerParameter` | String | - | 新增 | JSON脚本配置 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | - | 固定返回 `"jsoninput"` |
| `dsType()` | String | - | 固定返回 `null` |
| `schema()` | String | - | 固定返回 `null` |
| `oneTableWithFullName()` | String | - | 从 innerParameter JSON 中解析 tables 数组第一个表名 |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAJsonInputConfig.Builder`**

> 继承自 `BaseInputBuilder<OAColumn, OAJsonInputConfig>`，包含全部 BaseBuilder + BaseInputBuilder 方法。

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder + BaseInputBuilder 方法）* | | |
| `newColumn(String columnName)` | OAColumn | 根据字段名创建 OAColumn 实例 |
| `innerParameter(String val)` | String | 设置JSON脚本配置 |
| `build()` | - | 构建 OAJsonInputConfig 实例 |

---

## 11. model.plugin.output 包 — 输出组件

### 11.1 OARdbmsOutputConfig — 通用关系型数据库输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OARdbmsOutputConfig`

**stepKey**：`rdbmsoutput` | **dsType**：动态指定 | 继承自 `OABaseOutputPluginConfig<OAColumnMapping>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `columnMappings` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping\> | - | 继承(OABaseOutputPluginConfig) | 字段映射列表 |
| `loadStrategy` | String | - | 继承(OABaseOutputPluginConfig) | 加载策略 |
| `prodTableNotExistAction` | String | `"ignore"` | 继承(OABaseOutputPluginConfig) | 生产发布表不存在时处理策略 |
| `prodTableDdl` | String | - | 继承(OABaseOutputPluginConfig) | 生产建表DDL |
| `stepKey` | String | - | 新增 | 动态指定stepKey |
| `dsType` | String | - | 新增 | 动态指定dsType |
| `schemaName` | String | - | 新增 | schema名称 |
| `table` | String | - | 新增 | 输出表名 |
| `batchByteSize` | Long | `33554432L` | 新增 | 批次字节大小 |
| `batchSize` | Long | `2048L` | 新增 | 批次记录数 |
| `preSql` | String | - | 新增 | 前置SQL |
| `postSql` | String | - | 新增 | 后置SQL |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 返回 stepKey 或默认 `"rdbmsoutput"` |
| `dsType()` | String | @Transient | 返回动态指定的 dsType |
| `schema()` | String | @Transient | 返回 schemaName |
| `oneTableWithFullName()` | String | @Transient | 返回 `[schema.]table` 格式的完整表名 |
| `stepType()` | String | - | （继承）固定返回 `"output"` |
| `datasource()` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.BaseOADatasource | @Transient | （继承）构建数据源对象 |
| `builder()` | RdbmsOutputBuilder | static | 创建 Builder 实例 |

**内部枚举 OARdbmsLoadStrategy**：

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `TRUNCATE` | `"overwrite"` | 覆盖 |
| `APPEND` | `"append"` | 追加 |
| `NON_CONFLICT` | `"update"` | 更新 |
| `COPY` | `"copy"` | AdbForPG writer的Copy模式 |

**Builder 类 `OARdbmsOutputConfig.RdbmsOutputBuilder`**

> 继承自 `OABaseOutputPluginConfig.BaseOutputBuilder<OAColumnMapping, OARdbmsOutputConfig>`

构造器默认：`loadStrategy` = `"overwrite"`（OARdbmsLoadStrategy.TRUNCATE）

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| *（继承全部 BaseOutputBuilder 方法）* | | | |
| `stepKey(String val)` | String | - | 设置动态stepKey |
| `dsType(String val)` | String | - | 设置动态dsType |
| `schemaName(String val)` | String | - | 设置schema名称 |
| `table(String val)` | String | - | 设置输出表名 |
| `batchByteSize(Long val)` | Long | `33554432L` | 设置批次字节大小 |
| `batchSize(Long val)` | Long | `2048L` | 设置批次记录数 |
| `preSql(String val)` | String | - | 设置前置SQL |
| `postSql(String val)` | String | - | 设置后置SQL |
| `loadStrategy(OARdbmsLoadStrategy val)` | OARdbmsLoadStrategy | - | 设置加载策略（枚举方式，自动转换为字符串值） |
| `build()` | - | - | 构建 OARdbmsOutputConfig 实例 |

### 11.2 OAMysqlOutputConfig — MySQL输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAMysqlOutputConfig`

**stepKey**：`mysqloutput` | **dsType**：`MYSQL` | 继承自 `OARdbmsOutputConfig`

字段与 OARdbmsOutputConfig 完全一致，仅 `stepKey()` 固定返回 `"mysqloutput"`，`dsType()` 固定返回 `"MYSQL"`。

### 11.3 OAOracleOutputConfig — Oracle输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAOracleOutputConfig`

**stepKey**：`oracleoutput` | **dsType**：`ORACLE` | 继承自 `OARdbmsOutputConfig`

字段与 OARdbmsOutputConfig 完全一致，仅 `stepKey()` 固定返回 `"oracleoutput"`，`dsType()` 固定返回 `"ORACLE"`。

### 11.4 OAPgOutputConfig — PostgreSQL输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAPgOutputConfig`

**stepKey**：`postgresqloutput` | **dsType**：`POSTGRE_SQL` | 继承自 `OARdbmsOutputConfig`

字段与 OARdbmsOutputConfig 完全一致，仅 `stepKey()` 固定返回 `"postgresqloutput"`，`dsType()` 固定返回 `"POSTGRE_SQL"`。

### 11.5 OASqlServerOutputConfig — SQL Server输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OASqlServerOutputConfig`

**stepKey**：`sqlserveroutput` | **dsType**：`SQL_SERVER` | 继承自 `OARdbmsOutputConfig`

字段与 OARdbmsOutputConfig 完全一致，仅 `stepKey()` 固定返回 `"sqlserveroutput"`，`dsType()` 固定返回 `"SQL_SERVER"`。

### 11.6 OACustomRdbmsOutputConfig — 自定义RDBMS输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OACustomRdbmsOutputConfig`

继承自 `OARdbmsOutputConfig`，无新增字段。可通过设置 `stepKey` 和 `dsType` 自定义组件标识。Builder 构造时 `loadStrategy` 默认为 `null`（不支持加载策略）。

### 11.7 OAOdpsOutputConfig — MaxCompute(ODPS)输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAOdpsOutputConfig`

**stepKey**：`maxcomputeoutput` | **dsType**：`MAX_COMPUTE` | 继承自 `OABaseOutputPluginConfig<OAColumnMapping>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `columnMappings` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping\> | - | 继承(OABaseOutputPluginConfig) | 字段映射列表 |
| `loadStrategy` | String | - | 继承(OABaseOutputPluginConfig) | 加载策略（默认 `"overwrite"`） |
| `prodTableNotExistAction` | String | `"ignore"` | 继承(OABaseOutputPluginConfig) | 生产发布表不存在时处理策略 |
| `prodTableDdl` | String | - | 继承(OABaseOutputPluginConfig) | 生产建表DDL |
| `table` | String | - | 新增 | 输出表名 |
| `partition` | String | - | 新增 | 分区表达式 |
| `preSql` | String | - | 新增 | 前置SQL |
| `postSql` | String | - | 新增 | 后置SQL |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"maxcomputeoutput"` |
| `dsType()` | String | @Transient | 固定返回 `"MAX_COMPUTE"` |
| `schema()` | String | @Transient | 固定返回 `null` |
| `oneTableWithFullName()` | String | @Transient | 返回 table |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAOdpsOutputConfig.Builder`**

> 继承自 `OABaseOutputPluginConfig.BaseOutputBuilder<OAColumnMapping, OAOdpsOutputConfig>`

构造器默认：`loadStrategy` = `"overwrite"`（OALoadStrategy.OVER_WRITE）

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseOutputBuilder 方法）* | | |
| `table(String val)` | String | 设置输出表名 |
| `partition(String val)` | String | 设置分区表达式 |
| `preSql(String val)` | String | 设置前置SQL |
| `postSql(String val)` | String | 设置后置SQL |
| `build()` | - | 构建 OAOdpsOutputConfig 实例 |

### 11.8 OAHiveOutputConfig — Hive输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAHiveOutputConfig`

**stepKey**：`hadoophiveoutput` | **dsType**：`HIVE` | 继承自 `OABaseOutputPluginConfig<OAColumnMapping>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `columnMappings` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping\> | - | 继承(OABaseOutputPluginConfig) | 字段映射列表 |
| `loadStrategy` | String | - | 继承(OABaseOutputPluginConfig) | 加载策略（默认 `"truncateAll"`） |
| `prodTableNotExistAction` | String | `"ignore"` | 继承(OABaseOutputPluginConfig) | 生产发布表不存在时处理策略 |
| `prodTableDdl` | String | - | 继承(OABaseOutputPluginConfig) | 生产建表DDL |
| `catalog` | String | - | 新增 | catalog名称 |
| `schema` | String | - | 新增 | schema名称 |
| `table` | String | - | 新增 | 输出表名 |
| `partition` | String | - | 新增 | 分区表达式 |
| `preSql` | String | - | 新增 | 前置SQL |
| `postSql` | String | - | 新增 | 后置SQL |
| `fileCode` | String | `"UTF-8"` | 新增 | 文件编码 |
| `nullFormat` | String | `"\\N"` | 新增 | 空值字符串 |
| `zipType` | String | - | 新增 | 压缩格式 |
| `separator` | String | `"\\u0001"` | 新增 | 字段分隔符 |
| `lineDelimsConflict` | Long | - | 新增 | 行分隔符冲突处理策略 |
| `lineDelimsReplacement` | String | - | 新增 | 行分隔符冲突替换值 |
| `colDelimsConflict` | Long | - | 新增 | 列分隔符冲突处理策略 |
| `colDelimsReplacement` | String | - | 新增 | 列分隔符冲突替换值 |
| `perfConfig` | String | - | 新增 | hadoop参数配置 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"hadoophiveoutput"` |
| `dsType()` | String | @Transient | 固定返回 `"HIVE"` |
| `schema()` | String | @Transient | 返回 schema 字段 |
| `oneTableWithFullName()` | String | @Transient | 返回 `[catalog.][schema.]table` 格式 |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAHiveOutputConfig.Builder`**

> 继承自 `OABaseOutputPluginConfig.BaseOutputBuilder<OAColumnMapping, OAHiveOutputConfig>`

构造器默认：`loadStrategy` = `"truncateAll"`（OALoadStrategy.TRUNCATE_ALL）

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| *（继承全部 BaseOutputBuilder 方法）* | | | |
| `catalog(String val)` | String | - | 设置catalog名称 |
| `schema(String val)` | String | - | 设置schema名称 |
| `table(String val)` | String | - | 设置输出表名 |
| `partition(String val)` | String | - | 设置分区表达式 |
| `preSql(String val)` | String | - | 设置前置SQL |
| `postSql(String val)` | String | - | 设置后置SQL |
| `fileCode(String val)` | String | `"UTF-8"` | 设置文件编码 |
| `nullFormat(String val)` | String | `"\\N"` | 设置空值字符串 |
| `zipType(String val)` | String | - | 设置压缩格式 |
| `separator(String val)` | String | `"\\u0001"` | 设置字段分隔符 |
| `lineDelimsConflict(Long val)` | Long | - | 设置行分隔符冲突处理策略 |
| `lineDelimsReplacement(String val)` | String | - | 设置行分隔符冲突替换值 |
| `colDelimsConflict(Long val)` | Long | - | 设置列分隔符冲突处理策略 |
| `colDelimsReplacement(String val)` | String | - | 设置列分隔符冲突替换值 |
| `perfConfig(String val)` | String | - | 设置hadoop参数配置 |
| `build()` | - | - | 构建 OAHiveOutputConfig 实例 |

### 11.9 OAJsonOutputConfig — JSON脚本输出

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.output.OAJsonOutputConfig`

**stepKey**：`jsonoutput` | 继承自 `OABaseOutputPluginConfig<OAColumnMapping>`

**字段（含全部继承字段）**：

| 字段 | 类型 | 默认值 | 来源 | 说明 |
|------|------|--------|------|------|
| `dataSourceCategory` | String | `"DATA_SOURCE"` | 继承(OABasePluginConfig) | 数据源分类 |
| `accessMode` | String | - | 继承(OABasePluginConfig) | 访问模式 |
| `catalogType` | String | - | 继承(OABasePluginConfig) | OneCatalog类型 |
| `dsProjectId` | String | - | 继承(OABasePluginConfig) | 计算源绑定项目ID |
| `dsId` | String | - | 继承(OABasePluginConfig) | 数据源ID |
| `dsName` | String | - | 继承(OABasePluginConfig) | 数据源名称 |
| `timeZoneFrom` | String | `"datasource"` | 继承(OABasePluginConfig) | 时区来源 |
| `columnMappings` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumnMapping\> | - | 继承(OABaseOutputPluginConfig) | 字段映射列表 |
| `loadStrategy` | String | - | 继承(OABaseOutputPluginConfig) | 加载策略 |
| `prodTableNotExistAction` | String | `"ignore"` | 继承(OABaseOutputPluginConfig) | 生产发布表不存在时处理策略 |
| `prodTableDdl` | String | - | 继承(OABaseOutputPluginConfig) | 生产建表DDL |
| `innerParameter` | String | - | 新增 | JSON脚本配置（包含table、parameter、columnMapping等） |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | - | 固定返回 `"jsonoutput"` |
| `dsType()` | String | - | 固定返回 `null` |
| `schema()` | String | - | 固定返回 `null` |
| `oneTableWithFullName()` | String | - | 从 innerParameter JSON 中解析 table 字段 |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAJsonOutputConfig.Builder`**

> 继承自 `OABaseOutputPluginConfig.BaseOutputBuilder<OAColumnMapping, OAJsonOutputConfig>`

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseOutputBuilder 方法）* | | |
| `innerParameter(String val)` | String | 设置JSON脚本配置 |
| `build()` | - | 构建 OAJsonOutputConfig 实例 |

---

## 12. model.plugin.transform 包 — 转换/流程控制组件

### 12.1 OAFieldSelectConfig — 字段选择

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFieldSelectConfig`

**stepKey**：`ziduanxuanze` | **stepType**：`transform` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `column` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFieldSelectConfig.OASelectColumn\> | 字段选择组件中选择的字段列表 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"ziduanxuanze"` |
| `stepType()` | String | @Transient | 固定返回 `"transform"` |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAFieldSelectConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `column(List<OASelectColumn> val)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFieldSelectConfig.OASelectColumn\> | 设置字段列表 |
| `addColumn(OASelectColumn val)` | OASelectColumn | 逐个添加字段（自动初始化列表） |
| `build()` | - | 构建 OAFieldSelectConfig 实例（自动补全 inputName/name 互填） |

**内部类 OASelectColumn**（继承自 `JsonSerializable`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 输出字段名称 |
| `inputName` | String | 原字段名（重命名时表示原字段名，name为重命名后的名称） |
| `type` | String | 映射到pipeline的中间字段类型（参见 OAPipelineDataTypeEnum） |

方法：`newBuilder()` 创建 Builder 实例

**Builder 类 `OASelectColumn.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `name(String val)` | String | 设置输出字段名称 |
| `inputName(String val)` | String | 设置原字段名（重命名时使用） |
| `type(String val)` | String | 设置字段类型 |
| `type(OAPipelineDataTypeEnum val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.OAPipelineDataTypeEnum | 设置字段类型（枚举方式） |
| `build()` | - | 构建 OASelectColumn 实例 |

### 12.2 OAFiledCalculateConfig — 字段计算

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFiledCalculateConfig`

**stepKey**：`ziduanjisuan` | **stepType**：`transform` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `column` | List\<? extends com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | 字段计算组件列表（只需配置新增字段，上游字段自动拉取） |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"ziduanjisuan"` |
| `stepType()` | String | @Transient | 固定返回 `"transform"` |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OAFiledCalculateConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `column(List<? extends OAColumn> val)` | List\<? extends com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\> | 设置字段计算列表 |
| `addColumn(T extends OAColumn val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn | 逐个添加字段（自动初始化列表） |
| `build()` | - | 构建 OAFiledCalculateConfig 实例 |

**内部类 OACalculateColumn**（继承自 `OAColumn`）：

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `name` | String | 继承(OAColumn) | 字段名称 |
| `type` | String | 继承(OAColumn) | 字段类型 |
| `expression` | String | 新增 | 新增计算表达式 |
| `recombinationType` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFiledCalculateConfig.RecombinationType | 新增 | 新增字段标识（自动生成） |

方法：`newBuilder()` 创建 Builder 实例

**Builder 类 `OACalculateColumn.Builder`**

> 继承自 `OAColumn.Builder<T>`

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 OAColumn.Builder 方法：name, type）* | | |
| `expression(String val)` | String | 设置计算表达式 |
| `recombinationType(RecombinationType val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFiledCalculateConfig.RecombinationType | 设置新增字段标识（通常无需手动设置，build时自动生成） |
| `build()` | - | 构建 OACalculateColumn 实例（自动设置 recombinationType.main = type） |

**内部类 RecombinationType**（继承自 `JsonSerializable`）：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `main` | String | - | 映射到pipeline的中间字段类型（默认自动从 OAColumn.type 拉取） |
| `sub` | String | `"YYYY-MM-DD hh:mm:ss"` | 字段默认日期格式（目前尚未使用，使用默认值即可） |

**Builder 类 `RecombinationType.Builder`**

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| `main(String val)` | String | - | 设置中间字段类型（默认自动从 OAColumn.type 拉取） |
| `sub(String val)` | String | `"YYYY-MM-DD hh:mm:ss"` | 设置字段默认日期格式 |
| `build()` | - | - | 构建 RecombinationType 实例 |

### 12.3 OAFieldFilterConfig — 数据过滤

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAFieldFilterConfig`

**stepKey**：`guolv` | **stepType**：`transform` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `condition` | String | - | 过滤条件（建议使用脚本模式，aviator表达式） |
| `conditionObject` | String | - | 过滤条件配置（@Deprecated，不建议使用表单模式） |
| `_conditionConfigMode` | String | `"CODE"` | 配置模式：`FORM`-表单，`CODE`-脚本模式 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"guolv"` |
| `stepType()` | String | @Transient | 固定返回 `"transform"` |
| `builder()` | Builder | static | 创建 Builder 实例 |

**内部枚举 OAConditionConfigMode**：

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `FORM` | `"FORM"` | 表单模式 |
| `CODE` | `"CODE"` | 脚本模式 |

**Builder 类 `OAFieldFilterConfig.Builder`**

| Builder 方法 | 参数类型 | 默认值 | 说明 |
|------------|----------|--------|------|
| `condition(String val)` | String | - | 设置过滤条件（aviator表达式） |
| `conditionObject(String val)` | String | - | 设置过滤条件配置（@Deprecated） |
| `_conditionConfigMode(String val)` | String | `"CODE"` | 设置配置模式 |
| `_conditionConfigMode(OAConditionConfigMode val)` | OAConditionConfigMode | `CODE` | 设置配置模式（枚举方式） |
| `build()` | - | - | 构建 OAFieldFilterConfig 实例 |

**过滤条件操作符映射（表单模式 -> aviator表达式）**：

| 表单操作符 | aviator表达式 |
|------------|-------------------|
| `LIKE` / `CONTAINS` | `string.indexOf(column_name,'key_word') > -1` |
| `NOT LIKE` / `NOT_CONTAINS` | `string.indexOf(column_name,'key_word') < -1` |
| `START_WITH` | `string.startsWith(column_name,'key_word')` |
| `END_WITH` | `string.endsWith(column_name,'key_word')` |
| `IS_NULL` | `column_name == nil` |
| `IS_NOT_NULL` | `column_name != nil` |
| `AND` | `&&` |
| `OR` | `\|\|` |
| `NOT` | `!` |

### 12.4 OAEncryptionConfig — 字段加密

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig`

**stepKey**：`fieldencryption` | **stepType**：`transform` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `encryColumns` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.OAEncryptColumn\> | 加密字段列表（必填） |
| `encryName` | String | 加密算法名称 |
| `secretName` | String | 密钥名称（与 entryKey 二选一） |
| `entryKey` | Long | 密钥ID（与 secretName 二选一） |
| `isAdvance` | Boolean | 是否启用高级配置 |
| `encryMode` | String | 加密模式 |
| `fill` | String | 填充模式 |
| `encode` | String | 编码格式 |
| `offset` | String | 偏移量 |
| `compatibility` | String | 输出目标数据源类型（针对SM4，如 `adb_for_pg`） |
| `encryInterval` | String | 加密区间 |
| `ranges` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.RangeConfig\> | 区间配置列表 |
| `options` | Map\<String, String\> | 加密字典配置 |
| `errorCompatible` | String | 异常兼容模式 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `stepKey()` | String | 固定返回 `"fieldencryption"` |
| `stepType()` | String | 固定返回 `"transform"` |
| `builder()` | Builder | 创建 Builder 实例（支持 `algorithmConfig()` 方法直接传入算法配置对象） |

**Builder 类 `OAEncryptionConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `encryColumns(List<OAEncryptColumn> val)` | List\<OAEncryptColumn\> | 设置加密字段列表 |
| `encryName(String val)` | String | 设置加密算法名称 |
| `encryName(EncryptionAlgorithmEnum val)` | EncryptionAlgorithmEnum | 设置加密算法（枚举方式） |
| `secretName(String val)` | String | 设置密钥名称 |
| `entryKey(Long val)` | Long | 设置密钥ID |
| `isAdvance(Boolean val)` | Boolean | 设置是否启用高级配置 |
| `encryMode(String val)` | String | 设置加密模式 |
| `fill(String val)` | String | 设置填充模式 |
| `fill(PaddingModeEnum val)` | PaddingModeEnum | 设置填充模式（枚举方式） |
| `encode(String val)` | String | 设置编码格式 |
| `encode(EnCoderModeEnum val)` | EnCoderModeEnum | 设置编码格式（枚举方式） |
| `offset(String val)` | String | 设置偏移量 |
| `compatibility(String val)` | String | 设置输出目标数据源类型 |
| `encryInterval(String val)` | String | 设置加密区间 |
| `encryInterval(EncryptionRangeEnum val)` | EncryptionRangeEnum | 设置加密区间（枚举方式） |
| `ranges(List<RangeConfig> val)` | List\<RangeConfig\> | 设置区间配置列表 |
| `addRange(RangeConfig val)` | RangeConfig | 逐个添加区间配置 |
| `options(Map<String, String> val)` | Map\<String, String\> | 设置加密字典配置 |
| `options(EncryptionDictionaryConfig val)` | EncryptionDictionaryConfig | 设置加密字典（自动序列化为Map） |
| `errorCompatible(String val)` | String | 设置异常兼容模式 |
| `errorCompatible(ErrorCompatibleModeEnum val)` | ErrorCompatibleModeEnum | 设置异常兼容模式（枚举方式） |
| `algorithmConfig(BaseAlgorithmConfig val)` | BaseAlgorithmConfig | 传入算法配置对象（自动分发到对应的重载方法） |
| `algorithmConfig(AlgorithmWithEncryptionModeConfig val)` | AlgorithmWithEncryptionModeConfig | 传入 AES/DES/3DES/RSA 算法配置 |
| `algorithmConfig(SM2AlgorithmConfig val)` | SM2AlgorithmConfig | 传入 SM2 算法配置 |
| `algorithmConfig(SM4AlgorithmConfig val)` | SM4AlgorithmConfig | 传入 SM4 算法配置 |
| `algorithmConfig(FF1AlgorithmConfig val)` | FF1AlgorithmConfig | 传入 FF1 算法配置 |
| `build()` | - | 构建 OAEncryptionConfig 实例 |

#### 12.4.1 内部类 OAEncryptColumn（继承自 `JsonSerializable`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 加密字段名称 |

方法：`newColumn(String name)` 静态工厂方法

#### 12.4.2 枚举 EncryptionAlgorithmEnum — 加密算法

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `AES` | `"AES"` | AES加密 |
| `DES` | `"DES"` | DES加密 |
| `_3DES` | `"3DES"` | 3DES加密 |
| `SM4` | `"SM4"` | SM4国密加密 |
| `SM2` | `"SM2"` | SM2国密加密 |
| `RSA` | `"RSA"` | RSA加密 |
| `FF1` | `"FF1"` | FF1格式保留加密 |

#### 12.4.3 枚举 EncryptionModeEnum — 加密模式

| 枚举值 |
|--------|
| `NONE` |
| `ECB` |
| `CBC` |
| `CFB` |
| `CTR` |
| `OFB` |

#### 12.4.4 枚举 PaddingModeEnum — 填充模式

| 枚举值 | 值 |
|--------|-----|
| `NONE` | `"NoPadding"` |
| `PKCS5Padding` | `"PKCS5Padding"` |
| `PKCS7Padding` | `"PKCS7Padding"` |

#### 12.4.5 枚举 EnCoderModeEnum — 编码格式

| 枚举值 | 值 |
|--------|-----|
| `BASE64` | `"Base64"` |
| `HEX` | `"Hex"` |

#### 12.4.6 枚举 EncryptionRangeEnum — 加密区间

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `RANGE` | `"Interval"` | 区间加密 |
| `ALL` | `"All"` | 全部加密 |

#### 12.4.7 枚举 ErrorCompatibleModeEnum — 异常兼容模式

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `EXCEPTION` | `"exception"` | 抛出异常 |
| `NULL` | `"null"` | 返回空值 |
| `RAW` | `"original"` | 返回明文 |

#### 12.4.8 枚举 EncryptionDictionaryEnum — 加密字典

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| `NUMBER` | `"NUMBER"` | 数字 |
| `UPPER_EN` | `"UPPER_EN"` | 大写英文字母 |
| `LOWER_EN` | `"LOWER_EN"` | 小写英文字母 |
| `NUMBER_UPPER_EN` | `"NUMBER_UPPER_EN"` | 数字+大写英文字母 |
| `NUMBER_LOWER_EN` | `"NUMBER_LOWER_EN"` | 数字+小写英文字母 |
| `NUMBER_UPPER_LOWER_EN` | `"NUMBER_UPPER_LOWER_EN"` | 数字+英文字母（大小写） |
| `SPECIAL_SYMBOL` | `"SPECIAL_SYMBOL"` | 特殊符号 |
| `CUSTOM` | `"CUSTOM"` | 自定义 |

#### 12.4.9 内部类 EncryptionDictionaryConfig — 字典配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `alphabetType` | String | 加密字典类型 |
| `alphabetUseSpace` | boolean | 使用空格 |
| `alphabetUseTab` | boolean | 使用tab |
| `alphabetUseUnixEnter` | boolean | 使用unix系统回车符 |
| `alphabetUseWindowsEnter` | boolean | 使用windows系统回车符 |
| `alphabet` | String | 加密字符 |

方法：`builder()` 创建 Builder 实例

**Builder 类 `EncryptionDictionaryConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `alphabetType(String val)` | String | 设置加密字典类型 |
| `alphabetType(EncryptionDictionaryEnum val)` | EncryptionDictionaryEnum | 设置加密字典类型（枚举方式） |
| `alphabetUseSpace(boolean val)` | boolean | 设置是否使用空格 |
| `alphabetUseTab(boolean val)` | boolean | 设置是否使用tab |
| `alphabetUseUnixEnter(boolean val)` | boolean | 设置是否使用unix回车符 |
| `alphabetUseWindowsEnter(boolean val)` | boolean | 设置是否使用windows回车符 |
| `alphabet(String val)` | String | 设置加密字符 |
| `build()` | - | 构建 EncryptionDictionaryConfig 实例 |

#### 12.4.10 内部类 RangeConfig — 区间配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `startPosition` | Integer | 起始位置 |
| `endPosition` | Integer | 结束位置 |
| `rangeLength` | Integer | 范围长度 |
| `options` | Map\<String, String\> | 加密字典配置 |

方法：`builder()` 创建 Builder 实例

**Builder 类 `RangeConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `startPosition(Integer val)` | Integer | 设置起始位置 |
| `endPosition(Integer val)` | Integer | 设置结束位置 |
| `rangeLength(Integer val)` | Integer | 设置范围长度 |
| `options(Map<String, String> val)` | Map\<String, String\> | 设置加密字典配置 |
| `options(EncryptionDictionaryConfig val)` | EncryptionDictionaryConfig | 设置加密字典（自动序列化为Map） |
| `build()` | - | 构建 RangeConfig 实例 |

#### 12.4.11 内部类 SecretConfig — 密钥配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `secretName` | String | 指定密钥名称 |
| `secretId` | Long | 指定密钥ID |

方法：`builder()` 创建 Builder 实例

**Builder 类 `SecretConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `secretName(String val)` | String | 设置密钥名称 |
| `secretId(Long val)` | Long | 设置密钥ID |
| `build()` | - | 构建 SecretConfig 实例 |

#### 12.4.12 内部类 EncryptionModeConfig — 加密模式配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `encryMode` | String | 加密模式 |
| `fill` | String | 填充模式 |
| `encode` | String | 编码格式 |
| `offset` | String | 偏移量 |
| `compatibility` | String | 输出目标数据源类型 |

方法：`builder()` 创建 Builder 实例

**Builder 类 `EncryptionModeConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `encryMode(String val)` | String | 设置加密模式 |
| `encryMode(EncryptionModeEnum val)` | EncryptionModeEnum | 设置加密模式（枚举方式） |
| `fill(String val)` | String | 设置填充模式 |
| `fill(PaddingModeEnum val)` | PaddingModeEnum | 设置填充模式（枚举方式） |
| `encode(String val)` | String | 设置编码格式 |
| `encode(EnCoderModeEnum val)` | EnCoderModeEnum | 设置编码格式（枚举方式） |
| `offset(String val)` | String | 设置偏移量 |
| `compatibility(String val)` | String | 设置输出目标数据源类型 |
| `build()` | - | 构建 EncryptionModeConfig 实例 |

#### 12.4.13 内部类 BaseAlgorithmConfig — 加密算法配置基类（抽象类）

| 字段 | 类型 | 说明 |
|------|------|------|
| `algorithmName` | String | 加密算法名称 |
| `secretConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.SecretConfig | 密钥配置 |

**Builder 抽象基类 `BaseAlgorithmConfig.BaseBuilder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `algorithmName(String val)` | String | 设置加密算法名称 |
| `algorithmName(EncryptionAlgorithmEnum val)` | EncryptionAlgorithmEnum | 设置加密算法（枚举方式） |
| `secretConfig(SecretConfig val)` | SecretConfig | 设置密钥配置 |
| `build()` | - | 抽象方法，由子类实现 |

#### 12.4.14 内部类 AlgorithmWithEncryptionModeConfig（继承自 `BaseAlgorithmConfig`）

用于 AES/DES/3DES/RSA 算法配置。

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `algorithmName` | String | 继承 | 加密算法名称 |
| `secretConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.SecretConfig | 继承 | 密钥配置 |
| `encryptionModeConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.EncryptionModeConfig | 新增 | 加密模式配置（可选，传入后自动启用高级配置） |

方法：`builder()` 创建 Builder 实例

**Builder 类 `AlgorithmWithEncryptionModeConfig.Builder`**

> 继承自 `BaseAlgorithmConfig.BaseBuilder`

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder 方法）* | | |
| `encryModeConfig(EncryptionModeConfig val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.EncryptionModeConfig | 设置加密模式配置（可选，传入后自动启用高级配置） |
| `build()` | - | 构建 AlgorithmWithEncryptionModeConfig 实例 |

#### 12.4.15 内部类 SM4AlgorithmConfig（继承自 `AlgorithmWithEncryptionModeConfig`）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `algorithmName` | String | 继承 | 固定为 `"SM4"` |
| `secretConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.SecretConfig | 继承 | 密钥配置 |
| `encryptionModeConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.EncryptionModeConfig | 继承 | 加密模式配置 |
| `compatibility` | String | 新增 | 输出目标数据源类型（如 `adb_for_pg`） |

方法：`builder()` 创建 Builder 实例

**Builder 类 `SM4AlgorithmConfig.Builder`**

> 继承自 `AlgorithmWithEncryptionModeConfig.Builder`

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 AlgorithmWithEncryptionModeConfig.Builder 方法）* | | |
| `compatibility(String val)` | String | 设置输出目标数据源类型（如 `adb_for_pg`） |
| `build()` | - | 构建 SM4AlgorithmConfig 实例（自动设置 algorithmName="SM4"） |

#### 12.4.16 内部类 SM2AlgorithmConfig（继承自 `BaseAlgorithmConfig`）

SM2加密算法配置，`algorithmName` 固定为 `"SM2"`。无新增字段。

#### 12.4.17 内部类 FF1AlgorithmConfig（继承自 `BaseAlgorithmConfig`）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `algorithmName` | String | 继承 | 固定为 `"FF1"` |
| `secretConfig` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.SecretConfig | 继承 | 密钥配置 |
| `encryInterval` | String | 新增 | 加密区间 |
| `ranges` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAEncryptionConfig.RangeConfig\> | 新增 | 区间配置 |
| `options` | Map\<String, String\> | 新增 | 加密字典配置 |
| `errorCompatible` | String | 新增 | 异常兼容模式 |

方法：`builder()` 创建 Builder 实例

**Builder 类 `FF1AlgorithmConfig.Builder`**

> 继承自 `BaseAlgorithmConfig.BaseBuilder`

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| *（继承全部 BaseBuilder 方法）* | | |
| `encryInterval(String val)` | String | 设置加密区间 |
| `encryInterval(EncryptionRangeEnum val)` | EncryptionRangeEnum | 设置加密区间（枚举方式） |
| `ranges(List<RangeConfig> val)` | List\<RangeConfig\> | 设置区间配置列表 |
| `addRange(RangeConfig val)` | RangeConfig | 逐个添加区间配置 |
| `options(Map<String, String> val)` | Map\<String, String\> | 设置加密字典配置 |
| `options(EncryptionDictionaryConfig val)` | EncryptionDictionaryConfig | 设置加密字典（自动序列化为Map） |
| `errorCompatible(String val)` | String | 设置异常兼容模式 |
| `errorCompatible(ErrorCompatibleModeEnum val)` | ErrorCompatibleModeEnum | 设置异常兼容模式（枚举方式） |
| `build()` | - | 构建 FF1AlgorithmConfig 实例（自动设置 algorithmName="FF1"） |

### 12.5 OADecryptionConfig — 字段解密

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OADecryptionConfig`

**stepKey**：`fieldDecryption` | 继承自 `OAEncryptionConfig`

字段与 OAEncryptionConfig 完全一致，仅 `stepKey()` 覆写为 `"fieldDecryption"`。

### 12.6 OAConditionDispatchConfig — 条件分发

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OAConditionDispatchConfig`

**stepKey**：`tiaojianfenfa` | **stepType**：`process` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `condition` | String | 分发条件（aviator表达式，同 OAFieldFilterConfig） |
| `conditionObject` | String | 分发条件配置（@Deprecated） |
| `sendTrueTo` | String | 条件满足时发送的下游步骤名称 |
| `sendFalseTo` | String | 条件不满足时发送的下游步骤名称 |
| `stepColumn` | Map\<String, List\<? extends com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.OAColumn\>\> | 下游步骤对应的输出字段列表 |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"tiaojianfenfa"` |
| `stepType()` | String | @Transient | 固定返回 `"process"` |
| `builder()` | Builder | static | 创建 Builder 实例（支持 `addSendTo()` 方法同时设置分发目标和字段） |

**Builder 类 `OAConditionDispatchConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `condition(String val)` | String | 设置分发条件（aviator表达式） |
| `conditionObject(String val)` | String | 设置分发条件配置（@Deprecated） |
| `addSendTo(String sendTo, boolean isTrue, List<? extends OAColumn> columns)` | String, boolean, List | 添加分发目标：isTrue=true设置sendTrueTo，否则设置sendFalseTo，同时设置该目标的输出字段 |
| `build()` | - | 构建 OAConditionDispatchConfig 实例 |

### 12.7 OASpeedLimitConfig — 限速

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.transform.OASpeedLimitConfig`

**stepKey**：`xiansu` | **stepType**：`process` | 继承自 `OABaseTransformPluginConfig`

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recordSpeed` | Integer | 基于数据量限制（条/秒） |
| `byteSpeed` | Long | 基于字节限制（单位MB） |

**方法**：

| 方法签名 | 返回类型 | 注解 | 说明 |
|----------|----------|------|------|
| `stepKey()` | String | @Transient | 固定返回 `"xiansu"` |
| `stepType()` | String | @Transient | 固定返回 `"process"` |
| `builder()` | Builder | static | 创建 Builder 实例 |

**Builder 类 `OASpeedLimitConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `recordSpeed(Integer val)` | Integer | 设置基于数据量限制（条/秒） |
| `byteSpeed(Long val)` | Long | 设置基于字节限制（单位MB） |
| `build()` | - | 构建 OASpeedLimitConfig 实例 |

---

## 13. vdm 包 — 调度域配置模型

### 13.1 VdmTag — 标签

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmTag`

**用途**：调度任务标签配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `tagId` | String | 标签ID |
| `tagName` | String | 标签名称 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例（支持 `tagId(Long)` 和 `tagId(String)` 两种重载） |

**Builder 类 `VdmTag.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `tagId(String val)` | String | 设置标签ID |
| `tagId(Long val)` | Long | 设置标签ID（Long类型，自动转为字符串） |
| `tagName(String val)` | String | 设置标签名称 |
| `build()` | - | 构建 VdmTag 实例 |

### 13.2 VdmConditionScheduleParam — 条件调度参数

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmConditionScheduleParam`

**用途**：调度条件参数配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `enable` | Boolean | 是否启用 |
| `conditionName` | String | 条件名称 |
| `followScheduleParam` | Boolean | 是否跟随调度参数 |
| `nodeStatus` | Integer | 节点状态 |
| `cronExpression` | String | cron表达式 |
| `scheduleTime` | String | 调度时间 |
| `scheduleConditionDTO` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleCondition | 调度条件配置 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmConditionScheduleParam.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `enable(Boolean val)` | Boolean | 设置是否启用 |
| `conditionName(String val)` | String | 设置条件名称 |
| `followScheduleParam(Boolean val)` | Boolean | 设置是否跟随调度参数 |
| `nodeStatus(Integer val)` | Integer | 设置节点状态 |
| `cronExpression(String val)` | String | 设置cron表达式 |
| `scheduleTime(String val)` | String | 设置调度时间 |
| `scheduleCondition(VdmScheduleCondition val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleCondition | 设置调度条件配置 |
| `build()` | - | 构建 VdmConditionScheduleParam 实例 |

### 13.3 VdmCustomIntervalConfig — 调度间隔配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfig`

**用途**：自定义调度间隔配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `customIntervalPeriod` | String | 间隔周期类型（参见 VdmCustomIntervalPeriodEnum） |
| `customInterval` | Integer | 自定义间隔值 |
| `customIntervalUnit` | String | 间隔单位（参见 VdmCustomIntervalUnitEnum） |
| `startTime` | String | 开始时间（格式 `HH:mm`） |
| `endTime` | String | 结束时间（格式 `HH:mm`） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmCustomIntervalConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `customIntervalPeriod(String val)` | String | 设置间隔周期类型 |
| `customInterval(Integer val)` | Integer | 设置自定义间隔值 |
| `customIntervalUnit(String val)` | String | 设置间隔单位 |
| `startTime(String val)` | String | 设置开始时间（格式 `HH:mm`） |
| `endTime(String val)` | String | 设置结束时间（格式 `HH:mm`） |
| `build()` | - | 构建 VdmCustomIntervalConfig 实例 |

### 13.4 VdmDependencyPeriod — 依赖周期配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyPeriod`

**用途**：依赖周期配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `dependencyPeriodType` | String | 依赖周期类型（参见 VdmDependencyPeriodTypeEnum） |
| `periodOffset` | Integer | 周期偏移量（dependencyPeriodType=LAST_N_PERIOD时须传值） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmDependencyPeriod.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dependencyPeriodType(String val)` | String | 设置依赖周期类型 |
| `periodOffset(Integer val)` | Integer | 设置周期偏移量 |
| `build()` | - | 构建 VdmDependencyPeriod 实例 |

### 13.5 VdmExecuteRerunConfig — 重跑配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteRerunConfig`

**用途**：任务重跑配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `followSystem` | Boolean | 是否跟随系统配置 |
| `customRerunTimes` | String | 自定义重跑次数 |
| `customRerunInterval` | String | 自定义重跑间隔 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmExecuteRerunConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `followSystem(Boolean val)` | Boolean | 设置是否跟随系统配置 |
| `customRerunTimes(String val)` | String | 设置自定义重跑次数 |
| `customRerunInterval(String val)` | String | 设置自定义重跑间隔 |
| `build()` | - | 构建 VdmExecuteRerunConfig 实例 |

### 13.6 VdmExecuteTimeOutConfig — 超时配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExecuteTimeOutConfig`

**用途**：任务执行超时配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `followSystem` | Boolean | 是否跟随系统配置 |
| `customValues` | String | 自定义超时值 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmExecuteTimeOutConfig.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `followSystem(Boolean val)` | Boolean | 设置是否跟随系统配置 |
| `customValues(String val)` | String | 设置自定义超时值 |
| `build()` | - | 构建 VdmExecuteTimeOutConfig 实例 |

### 13.7 VdmExpression — 表达式

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpression`

**用途**：调度条件表达式。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `expressionType` | String | 表达式类型 |
| `operator` | String | 操作符 |
| `expressionValueDTO` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpressionValue | 表达式值 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmExpression.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `expressionType(String val)` | String | 设置表达式类型 |
| `operator(String val)` | String | 设置操作符 |
| `expressionValue(VdmExpressionValue val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpressionValue | 设置表达式值 |
| `build()` | - | 构建 VdmExpression 实例 |

### 13.8 VdmExpressionValue — 表达式值

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpressionValue`

**用途**：调度条件表达式值配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `inputParamName` | String | 输入参数名称 |
| `inputParamType` | String | 输入参数类型 |
| `expressionValueType` | String | 表达式值类型 |
| `publicCalendarName` | String | 公共日历名 |
| `publicCalendarCode` | String | 公共日历code |
| `type` | String | 类型（日期类型/标签） |
| `period` | String | 日历周期（星期/月份/日期） |
| `values` | List\<String\> | 值列表 |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmExpressionValue.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `inputParamName(String val)` | String | 设置输入参数名称 |
| `inputParamType(String val)` | String | 设置输入参数类型 |
| `expressionValueType(String val)` | String | 设置表达式值类型 |
| `publicCalendarName(String val)` | String | 设置公共日历名 |
| `publicCalendarCode(String val)` | String | 设置公共日历code |
| `type(String val)` | String | 设置类型（日期类型/标签） |
| `period(String val)` | String | 设置日历周期 |
| `values(List<String> val)` | List\<String\> | 设置值列表 |
| `build()` | - | 构建 VdmExpressionValue 实例 |

### 13.9 VdmScheduleCondition — 调度条件

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleCondition`

**用途**：调度条件配置（支持嵌套子条件）。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | String | 条件类型 |
| `operator` | String | 操作符 |
| `expression` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpression | 表达式 |
| `subConditions` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleCondition\> | 子条件列表（支持嵌套） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `toJson()` | JSONObject | （继承）将对象转换为 JSONObject |
| `toJsonString()` | String | （继承）将对象序列化为 JSON 字符串 |
| `builder()` | Builder | 创建 Builder 实例 |

**Builder 类 `VdmScheduleCondition.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `type(String val)` | String | 设置条件类型 |
| `operator(String val)` | String | 设置操作符 |
| `expression(VdmExpression val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmExpression | 设置表达式 |
| `subConditions(List<VdmScheduleCondition> val)` | List\<com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleCondition\> | 设置子条件列表 |
| `build()` | - | 构建 VdmScheduleCondition 实例 |

### 13.10 VdmTaskScheduleTypeEnum — 任务调度类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmTaskScheduleTypeEnum`

| 枚举值 | code | 名称 | 说明 |
|--------|------|------|------|
| `NORMAL` | 1 | 正常 | 正常任务 |
| `MANUAL` | 3 | 手动 | 手动触发任务 |
| `REAL_TIME` | 5 | 实时节点 | 实时节点 |

**方法**：`getCode()` 返回 code | `getName()` 返回名称 | `getDesc()` 返回描述

### 13.11 VdmScheduleIntervalTypeEnum — 调度周期

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmScheduleIntervalTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `YEARLY` | 年调度 |
| `MONTHLY` | 月调度 |
| `WEEKLY` | 周调度 |
| `DAILY` | 天调度 |
| `HOURLY` | 小时调度 |
| `MINUTELY` | 分钟调度 |

### 13.12 VdmNodeStatusEnum — 节点状态

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmNodeStatusEnum`

| 枚举值 | code | 名称 | 说明 |
|--------|------|------|------|
| `NORMAL` | 1 | 正常 | 正常调度 |
| `PAUSED` | 2 | 暂停调度 | 暂停调度 |
| `IDLE` | 3 | 空跑 | 空跑调度 |

**方法**：`getCode()` 返回 code | `getName()` 返回名称 | `getDesc()` 返回描述

### 13.13 VdmNodeTypeEnum — 任务节点类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmNodeTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `BBOX_LOGIC_TABLE_NODE` | 逻辑表 |
| `BBOX_LOGIC_FIELD_NODE` | 逻辑字段 |
| `BBOX_LOGIC_FIELD_GROUP_NODE` | 逻辑字段组 |
| `BBOX_INNER_TEMP_NODE` | 内部临时节点 |
| `DATA_PROCESS` | 代码任务 |
| `STREAM_TASK_NODE` | 实时研发 |
| `ONE_ID_LABEL` | 标签 |
| `ONE_ID_RULE` | 规则 |
| `ONE_ID_SYSTEM` | 系统 |
| `PIPELINE_NODE` | 集成管道任务 |
| `FLINK_BATCH` | flink批任务 |
| `ODM_NODE` | ODM节点 |
| `ONE_ID_LABEL_LOGICAL_TABLE` | 标签逻辑表 |
| `ONE_ID_FACTORY_LABEL` | 工厂标签 |
| `ONE_ID_STATISTICS_LABEL` | 统计标签 |

### 13.14 VdmDependencyPeriodTypeEnum — 依赖周期类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyPeriodTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `CURRENT_PERIOD` | 本周期（当日） |
| `LAST_PERIOD` | 上周期（前1日） |
| `LAST_N_PERIOD` | 前N周期（前N日） |
| `LAST_24_HOUR` | 最近24小时 |

### 13.15 VdmDependencyStrategyTypeEnum — 依赖策略类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmDependencyStrategyTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `ALL` | 全部实例 |
| `FIRST` | 第一个实例 |
| `LAST` | 最后一个实例 |
| `NEAR` | 最近一个实例 |
| `NEAR_LAST` | 上游<=下游的最近一个实例 |

### 13.16 VdmCustomIntervalConfigTypeEnum — 自定义间隔类型

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalConfigTypeEnum`

| 枚举值 | 说明 |
|--------|------|
| `TIME_POINT` | 时间点 |
| `TIME_PERIOD` | 时间段 |
| `CUSTOM_TIME_POINT` | 自定义时间点 |
| `CUSTOM_TIME_PERIOD` | 自定义时间段 |

### 13.17 VdmCustomIntervalPeriodEnum — 间隔周期

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalPeriodEnum`

| 枚举值 | 说明 |
|--------|------|
| `DAY` | 天范围 |
| `HOUR` | 小时范围 |

### 13.18 VdmCustomIntervalUnitEnum — 间隔单位

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmCustomIntervalUnitEnum`

| 枚举值 | 说明 |
|--------|------|
| `MINUTE` | 分钟 |
| `HOUR` | 小时 |

### 13.19 VdmNeuronDirtyDataStrategy — 脏数据处理策略

> `com.alibaba.dataphin.pipeline.common.facade.openapi.vdm.VdmNeuronDirtyDataStrategy`

**用途**：非结构化工作流算子的脏数据处理策略。通过工作流创建的 OpenAPI 默认脏数据处理策略为忽略。

| 枚举值 | 说明 |
|--------|------|
| `IGNORE` | 忽略脏数据 |
| `FAILED` | 置为失败 |

---

## 14. utils 包 — 工具类

### 14.1 OAStringUtils — 字符串工具

> `com.alibaba.dataphin.pipeline.common.facade.openapi.utils.OAStringUtils`

**用途**：字符串处理工具类，提供空白判断和包含关系判断。

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `isBlank(CharSequence cs)` | boolean | 判断字符序列是否为空白（null、空字符串、纯空白字符） |
| `isNotBlank(CharSequence cs)` | boolean | 判断字符序列是否非空白 |
| `contains(CharSequence seq, CharSequence searchSeq)` | boolean | 判断字符序列是否包含指定子序列 |

### 14.2 OALists — 集合工具

> `com.alibaba.dataphin.pipeline.common.facade.openapi.utils.OALists`

**用途**：ArrayList 创建工具类。

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `newArrayList(E... elements)` | ArrayList\<E\> | 创建包含指定元素的 ArrayList（带初始容量优化） |

### 14.3 OAInts — 整数工具

> `com.alibaba.dataphin.pipeline.common.facade.openapi.utils.OAInts`

**用途**：整数转换工具类。

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `saturatedCast(long value)` | int | 将 long 值安全转换为 int（超出范围时返回 `Integer.MAX_VALUE` 或 `Integer.MIN_VALUE`） |

---

## 15. model.plugin.unstructured 包 — 非结构化工作流算子基础配置

### 15.1 BaseOAUnstructuredNeuronConfig（抽象基类）

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.BaseOAUnstructuredNeuronConfig`

**用途**：非结构化工作流算子的配置抽象基类，每个算子继承该类并定义自己的 `stepKey()` 和 `stepType()`。继承自 `OABaseTransformPluginConfig`。构造时自动设置 `dataSourceCategory = DATA_SET`。

算子配置整体包含五部分：
1. 算子输入（neuronInput）
2. 算子模型（neuronModel）
3. 算子参数（neuronParameters）
4. 算子输出（neuronOutput）
5. 算子系统设置（setting）

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `neuronInput` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronInput | 算子输入配置 |
| `neuronModel` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronModel | 算子模型配置 |
| `neuronParameters` | Map\<String, String\> | 算子参数配置 |
| `neuronOutput` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronOutput | 算子输出配置 |
| `setting` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OAWorkflowSetting | 算子系统设置（如资源配置等） |

**Builder 类 `BaseOAUnstructuredNeuronConfig.Builder`**（抽象）

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `neuronInput(OANeuronInput val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronInput | 设置算子输入配置 |
| `neuronModel(OANeuronModel val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronModel | 设置算子模型配置 |
| `neuronParameters(Map<String, String> val)` | Map\<String, String\> | 设置算子参数 |
| `addNeuronParameters(String key, String value)` | String, String | 逐个添加算子参数 |
| `neuronOutput(OANeuronOutput val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronOutput | 设置算子输出配置 |
| `setting(OAWorkflowSetting val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OAWorkflowSetting | 设置算子系统设置 |
| `build()` | - | 抽象方法，由子类实现 |

### 15.2 OANeuronInput — 算子输入配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronInput`

**用途**：算子的输入配置，包括输入数据集、过滤条件、字段映射等。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `datasetId` | String | 是 | 输入数据集ID |
| `datasetVersion` | String | 是 | 输入数据集版本 |
| `filters` | List\<String\> | 否 | 输入数据集过滤条件 |
| `inputColumn` | List\<OANeuronInputColumn\> | 条件 | 算子输入字段与数据集字段的映射（取决于算子类型） |
| `embeddingType` | OAEmbeddingType | 否 | 嵌入类型（仅向量化算子需要配置） |

**内部枚举 OAEmbeddingType**：

| 枚举值 | 说明 |
|--------|------|
| `TEXT` | 文本嵌入 |
| `IMAGE` | 图片嵌入 |

**内部类 OANeuronInputColumn**（继承自 `JsonSerializable`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `columnName` | String | 算子输入字段名 |
| `sourceColumnName` | String | 输入数据集字段名 |

方法：`builder()` 创建 Builder 实例 | `create(String columnName, String sourceColumnName)` 静态工厂方法

**Builder 类 `OANeuronInputColumn.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `columnName(String val)` | String | 设置算子输入字段名 |
| `sourceColumnName(String val)` | String | 设置数据集字段名 |
| `build()` | - | 构建 OANeuronInputColumn 实例 |

**Builder 类 `OANeuronInput.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dataset(OADatasetDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OADatasetDatasource | 通过数据集数据源对象同时设置 datasetId 和 datasetVersion |
| `datasetId(String val)` | String | 设置输入数据集ID |
| `datasetId(Long val)` | Long | 设置输入数据集ID（Long类型） |
| `datasetVersion(String val)` | String | 设置输入数据集版本 |
| `filters(List<String> val)` | List\<String\> | 设置过滤条件 |
| `inputColumn(List<OANeuronInputColumn> val)` | List\<OANeuronInputColumn\> | 设置输入字段映射列表 |
| `addInputColumn(OANeuronInputColumn val)` | OANeuronInputColumn | 逐个添加输入字段映射 |
| `addInputColumn(OANeuronInputColumn... val)` | OANeuronInputColumn[] | 批量添加输入字段映射 |
| `embeddingType(OAEmbeddingType val)` | OAEmbeddingType | 设置嵌入类型 |
| `build()` | - | 构建 OANeuronInput 实例 |

### 15.3 OANeuronModel — 算子模型配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronModel`

**用途**：算子的模型配置，包括模型来源、模型ID、提示词、参数等。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `modelSource` | OAModelSourceEnum | 是 | - | 模型来源 |
| `modelId` | String | 是 | - | 模型ID |
| `modelPrompt` | String | 否 | - | 模型提示词（取决于算子） |
| `maxTokens` | Integer | 否 | - | 最大生成 tokens 数 |
| `enableOnlineSearch` | Boolean | 否 | - | 是否启用在线搜索 |
| `enableDeepThink` | Boolean | 否 | - | 是否启用深度思考 |
| `enableOutputMultiColumn` | Boolean | 否 | `false` | 是否启用多列输出 |
| `modelParameters` | Map\<String, Object\> | 否 | - | 其他模型参数配置 |
| `outputColumnName` | String | 条件 | - | 输出字段名称（单一输出字段时指定） |
| `customOutputColumns` | List\<OANeuronModelColumn\> | 条件 | - | 自定义多列输出（与 outputColumnName 二选一） |

**内部枚举 OAModelSourceEnum**：

| 枚举值 | 说明 |
|--------|------|
| `BUILTIN` | 系统内置模型 |
| `MULTIMODAL` | 外部多模态大模型 |

**内部类 OANeuronModelColumn**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 字段名称 |
| `type` | String | 字段类型 |
| `comment` | String | 描述 |
| `example` | String | 示例 |

方法：`builder()` 创建 Builder 实例 | `create(String name, String type)` | `create(String name, String type, String comment)` | `create(String name, String type, String comment, String example)` 静态工厂方法

**Builder 类 `OANeuronModelColumn.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `name(String val)` | String | 设置字段名称 |
| `type(String val)` | String | 设置字段类型 |
| `comment(String val)` | String | 设置描述 |
| `example(String val)` | String | 设置示例 |
| `build()` | - | 构建 OANeuronModelColumn 实例 |

**Builder 类 `OANeuronModel.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `modelSource(OAModelSourceEnum val)` | OAModelSourceEnum | 设置模型来源 |
| `modelId(String val)` | String | 设置模型ID |
| `modelId(Long val)` | Long | 设置模型ID（Long类型） |
| `modelPrompt(String val)` | String | 设置模型提示词 |
| `maxTokens(Integer val)` | Integer | 设置最大生成tokens数 |
| `enableOnlineSearch(Boolean val)` | Boolean | 设置是否启用在线搜索 |
| `enableDeepThink(Boolean val)` | Boolean | 设置是否启用深度思考 |
| `enableOutputMultiColumn(Boolean val)` | Boolean | 设置是否启用多列输出 |
| `modelParameters(Map<String, Object> val)` | Map\<String, Object\> | 设置模型参数 |
| `addModelParameters(String key, Object value)` | String, Object | 逐个添加模型参数 |
| `outputColumnName(String val)` | String | 设置输出字段名称（单一输出） |
| `customOutputColumns(List<OANeuronModelColumn> val)` | List\<OANeuronModelColumn\> | 设置自定义多列输出（自动启用多列输出） |
| `addCustomOutputColumns(OANeuronModelColumn val)` | OANeuronModelColumn | 逐个添加自定义输出列（自动启用多列输出） |
| `build()` | - | 构建 OANeuronModel 实例 |

### 15.4 OANeuronOutput — 算子输出配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronOutput`

**用途**：算子的输出配置，包括输出数据集、加载策略、字段映射等。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `datasetId` | String | 是 | - | 输出数据集ID |
| `datasetVersion` | String | 是 | - | 输出数据集版本 |
| `outputFilePath` | String | 否 | - | 文件输出路径（取决于算子） |
| `outputFileName` | String | 否 | - | 文件输出名称（取决于算子） |
| `enableOutputPictureUrl` | Boolean | 否 | `false` | 输出的markdown文本是否包含图片url |
| `loadStrategy` | OALoadStrategy | 是 | - | 加载策略 |
| `columnMappings` | List\<OANeuronOutputColumnMapping\> | 条件 | - | 输出字段映射（取决于算子） |

**内部枚举 OALoadStrategy**：

| 枚举值 | 说明 |
|--------|------|
| `APPEND` | 追加（insert） |
| `OVERWRITE` | 覆盖（truncate + insert） |
| `UPSERT` | 主键更新（update on duplicate key update） |

**内部类 OANeuronOutputColumnMapping**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `sourceColumn` | String | 输入字段 |
| `targetColumn` | String | 输出字段 |

方法：`builder()` 创建 Builder 实例 | `create(String sourceColumn, String targetColumn)` 静态工厂方法

**Builder 类 `OANeuronOutputColumnMapping.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `sourceColumn(String val)` | String | 设置输入字段 |
| `targetColumn(String val)` | String | 设置输出字段 |
| `build()` | - | 构建 OANeuronOutputColumnMapping 实例 |

**Builder 类 `OANeuronOutput.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `dataset(OADatasetDatasource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.datasource.OADatasetDatasource | 通过数据集数据源对象同时设置 datasetId 和 datasetVersion |
| `datasetId(String val)` | String | 设置输出数据集ID |
| `datasetId(Long val)` | Long | 设置输出数据集ID（Long类型） |
| `datasetVersion(String val)` | String | 设置输出数据集版本 |
| `loadStrategy(OALoadStrategy val)` | OALoadStrategy | 设置加载策略 |
| `columnMappings(List<OANeuronOutputColumnMapping> val)` | List\<OANeuronOutputColumnMapping\> | 设置输出字段映射列表 |
| `addColumnMapping(OANeuronOutputColumnMapping val)` | OANeuronOutputColumnMapping | 逐个添加输出字段映射 |
| `addColumnMapping(OANeuronOutputColumnMapping... val)` | OANeuronOutputColumnMapping[] | 批量添加输出字段映射 |
| `outputFilePath(String val)` | String | 设置文件输出路径 |
| `outputFileName(String val)` | String | 设置文件输出名称 |
| `enableOutputPictureUrl(Boolean val)` | Boolean | 设置是否输出图片url |
| `build()` | - | 构建 OANeuronOutput 实例 |

### 15.5 OANeuronResource — 算子资源配置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronResource`

**用途**：算子的资源配置。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `cpus` | String | 算子所需CPU核数（可选，默认为算子的默认CPU核数） |
| `mem` | String | 算子所需内存MB（可选，默认为算子的默认内存） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |
| `create(String cpus, String mem)` | OANeuronResource | 静态工厂方法 |
| `create(float cpus, int mem)` | OANeuronResource | 静态工厂方法（数值类型） |

**Builder 类 `OANeuronResource.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `cpus(String val)` | String | 设置CPU核数 |
| `cpus(float val)` | float | 设置CPU核数（数值类型） |
| `mem(String val)` | String | 设置内存MB |
| `mem(int val)` | int | 设置内存MB（数值类型） |
| `build()` | - | 构建 OANeuronResource 实例 |

### 15.6 OAWorkflowSetting — 算子系统设置

> `com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OAWorkflowSetting`

**用途**：算子的系统配置，包括资源设置和系统变量。继承自 `JsonSerializable`。

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `requiredResource` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronResource | 算子所需资源（可选） |
| `variables` | Map\<String, String\> | 算子系统变量配置（可选） |

**方法**：

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `builder()` | Builder | 静态方法，创建 Builder 实例 |
| `create(String cpus, String mem)` | OAWorkflowSetting | 静态工厂方法，仅设置资源 |
| `create(float cpus, int mem)` | OAWorkflowSetting | 静态工厂方法（数值类型） |
| `create(OANeuronResource resource, Map<String, String> variables)` | OAWorkflowSetting | 静态工厂方法，同时设置资源和变量 |

**Builder 类 `OAWorkflowSetting.Builder`**

| Builder 方法 | 参数类型 | 说明 |
|------------|----------|------|
| `requiredResource(OANeuronResource val)` | com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.OANeuronResource | 设置算子资源 |
| `variables(Map<String, String> val)` | Map\<String, String\> | 设置系统变量 |
| `addVariable(String key, String val)` | String, String | 逐个添加系统变量 |
| `build()` | - | 构建 OAWorkflowSetting 实例 |

---

## 16. model.plugin.unstructured.neuron 包 — 非结构化工作流算子

> 包路径：`com.alibaba.dataphin.pipeline.common.facade.openapi.model.plugin.unstructured.neuron`

本包包含 32 个具体算子配置类，**全部继承自 `BaseOAUnstructuredNeuronConfig`**。每个算子类的结构完全一致，仅 `stepKey()` 和 `stepType()` 不同。每个算子类均提供：
- 无参构造方法和 `Builder` 构造方法
- `builder()` 静态方法创建 Builder 实例
- 内部 `Builder` 类，继承自 `BaseOAUnstructuredNeuronConfig.Builder`，复用全部 Builder 方法（`neuronInput`、`neuronModel`、`neuronParameters`、`neuronOutput`、`setting` 等）

### 16.1 算子汇总表

按 `stepType` 分组列出所有算子：

#### TEXT 类算子（文本处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OAChineseConversionNeuronConfig` | `chinese_conversion` | 简繁体转换算子 |
| `OAFileBasicInfoNeuronConfig` | `file_basic_info` | 文件基本信息算子 |
| `OAHtmlExtractionNeuronConfig` | `html_extraction` | HTML正文提取算子 |
| `OAPiiMaskingNeuronConfig` | `pii_masking` | 隐私信息打码（PII脱敏）算子 |
| `OASimhashDedupNeuronConfig` | `simhash_dedup` | SimHash去重算子 |
| `OASpecialCharacterRemovalNeuronConfig` | `special_character_removal` | 特殊字符清除算子 |
| `OATextChunkerNeuronConfig` | `text_chunking` | 文本分块算子 |
| `OATextInferenceNeuronConfig` | `LLM_INFERENCE` | 文本推理算子 |
| `OATextQualityScoreNeuronConfig` | `text_quality_score` | 文本质量分算子 |
| `OAViolationContentReplacerNeuronConfig` | `violation_content_replacer` | 违规内容替换算子 |

#### DOCUMENT 类算子（文档处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OADocumentParserNeuronConfig` | `PDF_PARSER` | PDF解析算子 |

#### IMAGE 类算子（图片处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OAImageAestheticScoreNeuronConfig` | `image_aesthetic_score` | 图片美学评分算子 |
| `OAImageCaptionNeuronConfig` | `image_understanding` | 图片描述算子 |
| `OAImageEmbeddingNeuronConfig` | `image_embedding` | 图片向量化算子 |
| `OAImageOCRNeuronConfig` | `image_ocr` | 图片OCR算子 |
| `OAImageQualityScoreNeuronConfig` | `image_quality_score` | 图片质量分算子 |
| `OANsfwDetectionNeuronConfig` | `nsfw_detection` | 图片NSFW检测算子 |

#### VIDEO 类算子（视频处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OAVideoAudioExtractorNeuronConfig` | `VIDEO_AUDIO_EXTRACTOR` | 视频提取音频算子 |
| `OAVideoBasicInfoNeuronConfig` | `video_basic_info` | 视频基本信息算子 |
| `OAVideoQualityScoreNeuronConfig` | `video_quality_score` | 视频画质质量分算子 |

#### AUDIO 类算子（音频处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OAAudioBasicInfoNeuronConfig` | `audio_basic_info` | 音频基本信息算子 |
| `OAAudioChunkerNeuronConfig` | `audio_chunk` | 音频切片算子 |
| `OAAudioDiarizationNeuronConfig` | `audio_diarization` | 音频说话人分离算子 |
| `OAAudioEnhancementNeuronConfig` | `audio_enhancement` | 音频增强算子 |
| `OAAudioLanguageDetectionNeuronConfig` | `audio_language_detection` | 音频语种检测算子 |
| `OAAudioQualityScoreNeuronConfig` | `audio_quality_score` | 音频质量分算子 |
| `OAAudioTimestampNeuronConfig` | `audio_timestamp` | 音频时间戳算子 |
| `OAAudioToTextNeuronConfig` | `audio_to_text` | 音频转文本算子 |
| `OAAudioTranscodeNeuronConfig` | `audio_transcoding` | 音频转码算子 |
| `OAAudioVadNeuronConfig` | `audio_vad` | 音频人声检测算子 |

#### VECTOR 类算子（向量化处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OATextEmbeddingNeuronConfig` | `text_embedding` | 文本向量化算子 |

#### NORMAL 类算子（通用处理）

| 类名 | stepKey | 说明 |
|------|---------|------|
| `OAMd5DedupNeuronConfig` | `md5_dedup` | MD5求值并去重算子 |

### 16.2 算子使用说明

所有算子类的使用方式完全一致，以 `OATextChunkerNeuronConfig`（文本分块算子）为例：

```java
// 构建算子配置
OATextChunkerNeuronConfig config = OATextChunkerNeuronConfig.builder()
    .neuronInput(
        OANeuronInput.builder()
            .datasetId("输入数据集ID")
            .datasetVersion("输入数据集版本")
            .build()
    )
    .neuronModel(
        OANeuronModel.builder()
            .modelSource(OANeuronModel.OAModelSourceEnum.BUILTIN)
            .modelId("模型ID")
            .build()
    )
    .neuronParameters(Map.of("key", "value"))  // 算子特有参数
    .neuronOutput(
        OANeuronOutput.builder()
            .datasetId("输出数据集ID")
            .datasetVersion("输出数据集版本")
            .loadStrategy(OANeuronOutput.OALoadStrategy.APPEND)
            .build()
    )
    .setting(
        OAWorkflowSetting.builder()
            .requiredResource(OANeuronResource.create("2", "4096"))
            .build()
    )
    .build();
```

其他算子只需将 `OATextChunkerNeuronConfig` 替换为对应的算子类名即可，Builder 方法完全相同。各算子的具体参数（`neuronParameters`）请参考对应算子的业务文档。
