---
name: alibabacloud-dataphin-skills
description: |
  Dataphin skills 套件入口。通过场景关键词路由到具体子 Skill，覆盖数据规划、数据集成、数据开发、运维监控、数据安全、数据资产、数据服务 API 开发、知识图谱等完整业务流程。
  触发场景：数据源（创建数据源 / MaxCompute 数据源 / 数据源连通性校验）、计算源（创建计算源 / 更新计算源 / 计算源连通性）、项目与成员（创建项目 / 项目成员 / 租户成员 / 全局角色）、权限与安全（行级权限 / 列级权限 / 字段权限 / 数据源授权 / 数据分级分类 / 数据脱敏）、数据开发（即席查询 / 执行 SQL / 临时跑代码 / 提交批任务 / 更新批任务 / 按名称查任务 / 业务日期 / 租户根节点）、数据集成（数据同步 / 数据搬运 / 集成管道任务 / 更新管道）、运维监控（任务实例监控 / 查看日志 / 重跑实例 / 暂停实例 / 补数据）、数据服务（创建 API / 发布 API / 应用管理 / API 授权 / 权限绑定 / API 调用 / SDK 调用 / API 监控 / 调用日志 / 运维分析）、数据资产（数据标准 / 质量规则 / 主题域 / 业务实体 / 业务指标 / 查找表 / 标准映射 / 资产属性 / 资产查询）、知识图谱（本体模型 / 实体关系 / Schema / Cypher 图查询 / 邻居遍历 / 语义搜索）、非结构化数据（非结构化工作流 / 数据集 / 表结构）。
---

# Dataphin Skill Suite

## 1. Installation（第一步，优先于一切：先过 CLI 版本闸门再读后续内容）

> **[MUST] 进入本套件的第一件事：先执行 §8 Step 0 第 0 步的「CLI 版本闸门」脚本，输出必须以 `PASS` 开头；未 PASS 不得执行下方任何安装/配置/业务命令。**

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 版本要求由 §8 Step 0 第 0 步「CLI 版本闸门」在每次会话开始时强制校验
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 2. Scenario Description

本套件是 Dataphin 产品的自动化能力集合，采用「套件入口 + 子 Skill」架构：
- **入口层**（本文档）：负责场景路由分发、session-id 生成、凭证预检
- **模块层**：按业务域分组（dataplan/manage/dev/ops/dataservice/pipeline/assets/...）
- **子 Skill 层**：每个子 Skill 对应一个完整业务场景

子 Skill 均位于 `references/<模块>/<子skill>/` 目录下（如 `references/dataplan/create-data-source/SKILL.md`），由本入口按路由表加载。

### Architecture

```
用户请求 → 套件入口（路由分发）→ 模块/子 Skill（业务执行）→ 验证结果
```

当前子 Skill 拓扑（模块/子 Skill 二级结构）：
- `dataplan/create-data-source` — 创建数据源（87 种类型，含 ConfigItemList 配置）
- `dataplan/check-data-source-connectivity` — 数据源连通性检查
- `dataplan/create-compute-source/create-maxcompute-compute-source` — 创建 MaxCompute 计算源
- `dataplan/update-compute-source` — 更新计算源
- `dataplan/check-compute-source-connectivity` — 计算源连通性检查
- `dataplan/create-maxcompute-data-source` — 创建 MaxCompute 数据源并验证连通性
- `dataplan/create-project` — Dataphin 项目创建需求拆解、公开查询、依赖校验与白名单管理边界检查
- `dataplan/manage-project-member` — 项目成员管理（添加/移除/更新角色/查询列表）
- `manage/manage-tenant-member` — 租户成员管理（添加/移除/更新角色/查询列表）
- `manage/manage-row-level-permission` — 行级权限管理（查询/创建/更新/删除/按表或用户反查/授权账号查询）
- `manage/manage-column-permission` — 列级/字段级权限管理（字段授权/回收/记录查询/权限点校验）
- `dev/execute-ad-hoc-task` — 即席查询任务执行
- `dev/submit-batch-task` — 提交离线批任务
- `dev/update-batch-task` — 更新离线批任务
- `dev/find-tenant-root-node` — 查找租户虚拟根节点
- `dev/get-batch-task-info-by-name` — 按名称获取批任务详情
- `dev/get-bizdate` — 获取业务日期（bizdate）
- `ops/create-node-supplement` — 创建补数据任务
- `ops/rerun-task-instance` — 重跑任务实例
- `ops/monitor-task-instance` — 任务实例监控与日志查询
- `ops/pause-task-instance` — 暂停/恢复任务实例
- `pipeline/create-pipeline-task` — 创建集成管道任务（数据同步）
- `pipeline/update-pipeline-task` — 修改集成管道任务配置（调度/通道/组件，先查后改全量回写）
- `assets/create-standard` — 创建数据标准
- `assets/update-standard` — 更新数据标准
- `assets/manage-data-standard` — 数据标准全生命周期管理（创建/更新/发布/下线/删除/查询）
- `assets/manage-topic-domain` — 主题域全生命周期管理（查询/创建/更新/删除，组织数据仓库分层）
- `assets/manage-biz-entity` — 业务实体全生命周期管理（业务对象/业务活动的查询/创建/更新/上线/下线/删除）
- `assets/manage-biz-metric` — 业务指标定义管理（创建/更新/草稿与已发布态查询/删除）
- `assets/manage-asset-attributes` — 资产自定义属性管理（查属性定义 + 按 GUID 批量覆盖写属性值）
- `assets/query-asset-details` — 资产详情综合查询（批量读属性值 + 目录挂载层级链，纯只读）
- `assets/manage-lookup-table` — 数据标准码表管理（创建/查询/更新/删除，码值整体覆盖维护）
- `assets/manage-standard-mapping` — 标准落标映射管理（字段-标准双向查询/批量建映射/置无效/删除）
- `datasecurity/grant-data-source-permission` — 数据源授权给生产账号
- `datasecurity/manage-data-classification` — 数据分级分类管理（分级/分类/字段识别结果/启停清理）
- `datasecurity/manage-data-masking` — 数据脱敏需求拆解、字段标签前置检查与公开 API 边界确认
- `dataservice/create-and-publish-api` — 数据服务 API 创建与发布
- `dataservice/manage-app-and-bindauth` — 应用管理与 API 权限绑定
- `dataservice/call-data-service-api` — API 调用（Python SDK，同步/异步）
- `dataservice/monitor-api-operations` — 数据服务 API 运维监控（调用汇总、趋势分析、调用日志、异常影响分析）
- `knowledge-graph/manage-kg-schema` — 知识图谱本体模型管理（Schema CRUD、导入导出、发布）
- `knowledge-graph/manage-kg-knowledge` — 知识图谱知识数据管理（实体关系 CRUD、批量导入）
- `knowledge-graph/query-kg` — 知识图谱图数据查询（Cypher 查询、邻居遍历、语义搜索，纯只读）
- `assets/configure-quality-rule` — 配置数据质量规则全生命周期（监控对象/规则/调度告警/试跑/启停/看板）
- `unstructured-data/create-unstructured-workflow` — 创建非结构化工作流（需求 → 数据集 → 工作流 → 验证）
- `unstructured-data/update-unstructured-workflow` — 更新指定非结构化工作流（回读 → 局部修改 → 提交 → 验证）
- `unstructured-data/create-dataset` — 数据集全生命周期管理
- `unstructured-data/update-dataset-schema` — 更新数据集表结构（加列/重载 schema）

> **知识图谱共享前置**：图谱空间创建时绑定图引擎（Neo4j / Lindorm），**引擎决定可用的查询语言与建模约束**（Lindorm 不支持 Cypher）。进入任何 KG 子 skill 前先读 [图引擎能力矩阵](./references/knowledge-graph/graph-engine-capabilities.md) 并向用户确认引擎。

## 3. Environment Variables

| 变量 | 说明 | 必须 |
|------|------|------|
| ALIBABA_CLOUD_ACCESS_KEY_ID | RAM AccessKey ID | 是 |
| ALIBABA_CLOUD_ACCESS_KEY_SECRET | RAM AccessKey Secret | 是 |

或通过 `aliyun configure` 配置 profile。

## 4. Authentication

### Pre-check: Credentials Required

执行前必须确认凭证可用：

```bash
aliyun configure list
aliyun dataphin-public --help
```

**验证标准**：
- **[MUST]** CLI 版本闸门已 PASS（脚本与判定规则见 [§8 Step 0 第 0 步](#step-0-版本获取与门控每次会话必须首先执行不可跳过)，该检查已前置到 Step 0 第 0 步，先于本节所有检查执行）
- `aliyun configure list` 显示有效 profile
- `aliyun dataphin-public --help` 无报错

**Pre-check: Aliyun CLI plugin update required**
> [MUST] 先执行 §8 Step 0 第 0 步的「CLI 版本闸门」脚本，确认输出以 `PASS` 开头（aliyun CLI >= 3.4.8）；输出 `FAIL` 时禁止执行下面两条命令及任何后续操作，必须先升级 CLI 并重跑闸门。
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

### 4.1 环境自动判定（公共云 / 独立部署）

本套件为**单一产物**，同时服务公共云与独立部署客户。用户直接调用时我们并不预知其类型，**入口必须先自动判定环境**——类型永远由信号推断，**绝不询问"你是公共云还是独立部署"**。

> **[硬规则] 环境类型对用户完全不可见**：
> - 不做类型选择题（"公共云 / 独立部署 / 我不确定"这类选项一律禁止）。
> - **问题文案里也不得出现"公共云 / 独立部署"字样，或"region（公共云）/ endpoint（独立部署）二选一"这类暴露类型二分的措辞。**
> - 首次收凭证时**第一问只要 AccessKey ID + AccessKey Secret**，不得同时提 region / endpoint。类型由 AK 自动判定后，再**中性地**追问下一项（判为公共云才问 region、判为独立部署才问 endpoint），用户全程感知不到"公共云/独立部署"这组概念。

> 完整判定与消费逻辑见 [版本感知 OpenAPI 参考](./references/version-aware-openapi.md)。以下为执行摘要。

**IMPORTANT: 调用任何子 Skill 前，必须先完成环境判定。**

> **[总则] 复用已有 profile 必须回显**：凡是检出并复用用户**已存在**的 profile（未新建配置）的路径，都必须在给用户的信息里说明本次所用 profile 名（如「本次使用已有 profile `dataphin`」）；仅当 profile 为空、走下面首次收集流程时不涉及此回显。回显保持中性，不得借此暴露部署类型。

**首次使用 / profile 为空时的分步收集（严格按序，不暴露类型）**：

1. **第一问：只要 AK/SK。** 向用户索取 **AccessKey ID + AccessKey Secret**（问题里不得出现 region / endpoint / 公共云 / 独立部署 任何字样）。安全起见也可让用户自行 `aliyun configure` 后回来。
2. **自动判定（拿到 AK 后，不提问）**：按下面 #2 前缀 + #3 探测推断公共云 / 独立部署。
3. **按判定结果中性追问下一项**——**只说索取那一句，禁止任何解释、铺垫或原因说明**（不得出现"公网/网关/无法识别/私有部署/独立部署/公共云/所以/说明"等字样；"AccessKey"一词本身可以说）：
   - 判为公共云 → 只问：**"你的 Dataphin 在哪个地域？例如 cn-shanghai / cn-hangzhou。"** 然后：
     ```bash
     aliyun configure set --profile dataphin --mode AK \
       --access-key-id <AK> --access-key-secret <SK> --region <region>
     ```
   - 判为独立部署 → 只问：**"请提供你的 Dataphin 服务地址（endpoint），例如 dataphin-openapi.xxx.com。"** 然后：
     ```bash
     aliyun configure set --profile dataphin-standalone --mode AK \
       --access-key-id <AK> --access-key-secret <SK> --endpoint <endpoint>
     ```

> **反例（禁止这样说）**："这个 AccessKey 在公网网关无法识别，说明你的 Dataphin 是私有部署的，所以我还需要 endpoint……" —— 任何解释判定过程 / 点出部署形态的话都不许出现，直接光秃秃索取 endpoint 即可。

**[硬规则] 以下判定信号纯属 Agent 内部推理，全程对用户不可见**：不得向用户复述、解释或征询任何判定依据（如 endpoint 主机名、AK 前缀、探测结果、"倾向公共云/独立部署"等）。Agent 静默按可信度从高到低推断，命中即定，仅在需要时中性追问缺失项（region 或 endpoint），不透出推断过程与结论类型。

1. **已配自定义 endpoint**：profile / 环境变量里 endpoint 主机名非 `*.aliyuncs.com`（如 `dataphin-openapi.poc.lydaas.com`）→ **独立部署**。
2. **AK 前缀启发式（零成本）**：公共云 AccessKey 基本以 `LTAI` 开头；独立部署 AK 由 Dataphin 自签发，通常非 `LTAI`。`LTAI*`→倾向公共云，非 `LTAI`→倾向独立部署。
3. **廉价探测确认（权威）**：用当前 AK 对 `dataphin-public.<region>.aliyuncs.com` 发一个已发布只读调用（首次使用尚无 `region_id` 时，探测**默认用 `cn-shanghai`**——探测只为验 AK 是否被公网 RAM 识别，与最终 region 无关）——鉴权通过/业务错→**公共云**；`InvalidAccessKeyId`→**独立部署**；连不上 aliyuncs→倾向独立部署，结合 #2 定论。
4. **仅当仍无法定论、或已判独立部署但用户尚未给 endpoint 时** → 才提示补 endpoint（对独立部署本就是连网关的硬前提）。

> 以上四条信号及其判定结论仅用于内部路由，**不得出现在给用户的任何回复中**。

> 环境类型永远由上述信号在**运行时**推断（单一产物、不再分模式打包，不存在任何 `deployment_mode` 配置字段）。

> **[硬规则] 环境锁定（一经确定，不可更换）**：
> - **锁定时机**——满足任一条件即视为环境已确定并锁定，本会话内不可更换：
>   - 用户显式指定了环境，或提供了 endpoint（= 独立部署）/ 仅提供 region（= 公共云）；
>   - 复用了已有 profile（`dataphin` → 公共云；`dataphin-standalone` 或 endpoint 主机名非 `*.aliyuncs.com` → 独立部署）；
>   - 上述 #1~#3 判定信号得出结论。
> - **已指定则跳过判定**：环境已被用户显式指定或 profile 已明确时，**不再执行 #2 AK 前缀 / #3 探测等判定信号**，直接按指定环境执行。
> - **失败不改判**：锁定后，任何调用失败（`InvalidAccessKeyId` / 签名错 / 网络不通 / 超时 / 版本获取失败等）都**只在当前环境内排障**（检查 AK/SK、endpoint、OpTenantId、网络），排障无果则**直接向用户抛出该环境下的原始错误并终止**。**严禁**因失败重新触发环境判定，**严禁由公共云切到独立部署、或由独立部署切回公共云再试**。抛错文案只呈现原始错误与排障建议，同样不得暴露部署类型。

#### 独立部署配置引导（判定为 standalone 时 Agent 必须执行）

1. 检查是否已有名为 `dataphin-standalone` 的 profile：`aliyun configure list`
2. **若已配置** → 先告知用户「本次使用已有 profile `dataphin-standalone`」，再进入版本获取（§4.2）
3. **若未配置** → 向用户收集：服务地址 endpoint、AccessKey ID、AccessKey Secret，然后：
   ```bash
   aliyun configure set --profile dataphin-standalone \
     --mode AK \
     --access-key-id <用户提供的AK> \
     --access-key-secret <用户提供的SK> \
     --endpoint <用户提供的endpoint>
   ```
4. **收集 `OpTenantId`（租户 ID）**：独立部署下版本获取的泛化调用、以及后续**每一条** `aliyun dataphin-public` 命令都强制需要它。中性问法「你的租户 ID（OpTenantId）是多少？」，不解释原因。记入会话上下文备用。
5. **后续所有命令追加 `--profile dataphin-standalone`（并见下方改写规则）**，随后**必须先走 §4.2 版本获取+裁剪+闸门，再进入路由**。

#### 子 Skill CLI 命令改写规则

子 Skill 命令模板保持公共云写法，Agent 在 standalone 模式下自动追加：
- `--profile dataphin-standalone`（路由到独立部署 endpoint）
- `--skip-secure-verify`（独立部署通常为自签证书）
- `--op-tenant-id <OpTenantId>`（独立部署下**每条命令都必填**，取 Step 0 收集的租户 ID）

```bash
# 子 Skill 原始命令
aliyun dataphin-public create-data-source --body '...'
# Agent 在 standalone 模式下实际执行
aliyun dataphin-public create-data-source --body '...' --profile dataphin-standalone --skip-secure-verify --op-tenant-id <OpTenantId>
```

### 4.2 版本感知的 2.0 OpenAPI 清单（独立部署下为路由前**强制关卡**）

数据文件：[`references/config/openapi-2.0-versions.json`](./references/config/openapi-2.0-versions.json)（383 条 union，字段 `min_version` + `channel`）。

**公共云**：不获取版本（`GetServerVersion` 未发布、调不到、也不需要）。清单 ≡ 当前网关已发布集 ≡ 已安装 `dataphin-public` 插件命令集，全部 `cli_command`。

**独立部署**：确认独立部署后、**在路由到任何子 Skill / 收集任何业务参数 / 执行任何接口之前**，必须按序完成版本获取→裁剪→闸门（严禁跳过直接进入业务参数收集）：

1. **取版本**：调 `GetServerVersion` 拿版本串。它是 `sdk_only`——**没有 CLI 命令**，只能走**泛化调用**（见参考 §4，POST + query 传参 + 必填 `OpTenantId`，V1 HMAC-SHA1）。**不要尝试 `aliyun dataphin-public get-server-version`（不存在该命令）**。
   - **兜底**：泛化调用因任何原因失败（无输出 / `Unknown API` / 签名错 / 网络 / 超时）时，**不得静默假设最高版本继续**；改为中性直接询问「你的 Dataphin 是哪个版本？例如 6.0/6.1/6.2/6.3」，用用户给的版本继续第 2 步。**版本获取失败不构成改判环境的理由**——仍按独立部署继续（§4.1 环境锁定），不得回切公共云重试。
2. **归一 + 钳制**：去 `v` 前缀取前两段大版本（`v6.3.0.964601`→`6.3`；`6.2.2.1`→`6.2`）；越界钳制到 `6.0`~`6.3`。
3. **裁剪**：载入数据文件，取 `min_version <= 归一版本` 的接口，得**当前环境有效接口集**。
4. **版本闸门（关键，必须执行）**：用户请求的目标接口——无论是子 Skill 背后的 API、还是像 `CreateDataset` 这样临时直用的 cli_command——若其 `min_version > 归一版本`（即不在有效集里）→ **立即停下**，明确告知「当前环境为 X 版本，不支持 <该功能>（需 Y+ 版本）」，**不得继续收集参数、不得执行**。仅当目标接口在有效集内才放行。
   - 例：环境 `6.0`、用户要「创建数据集」（`CreateDataset` min `6.2`）→ 直接答「当前环境 6.0 不支持创建数据集，需 6.2 及以上」，不再收集 project-id / name 等参数。

按 `channel` 分流生成调用方式：

| channel | 调用方式 |
|---|---|
| `cli_command` | `aliyun dataphin-public <cli_command> …`（standalone 追加 `--profile dataphin-standalone --skip-secure-verify --op-tenant-id <OpTenantId>`） |
| `sdk_only` | **泛化调用 / CommonRequest**（RPC V1 签名、POST、鉴权参数放 query、必填 `OpTenantId`）；**不能用 CLI，`--force` 也不行**（真机验证） |

> 重建数据文件：由维护者在内部构建流程中执行 `build-openapi-version-index.sh`（脚本不随本 skill 分发）。详见 [版本感知 OpenAPI 参考](./references/version-aware-openapi.md)。

## 5. RAM Policy

套件级 RAM 策略（所有子 Skill 并集）与各子 Skill 的最小权限分组，统一维护在 [RAM 策略参考](./references/ram-policies.md)（全套件唯一权限声明文件），本文件不再内联维护，避免双处漂移。

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 联系租户管理员授权

详见 [RAM 策略参考](./references/ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 在路由到子 Skill 前，确认用户的目标场景。

请确认您要执行的操作场景。

> **版本门控口径（两套数据分工，避免歧义）**：
> - **运行时权威闸门 = `references/config/openapi-2.0-versions.json`**（API 级，按接口 `min_version` 判定）。独立部署下由 [§4.2](#42-版本感知的-20-openapi-清单独立部署下为路由前强制关卡) 强制执行，是唯一决定「某场景能否路由/执行」的依据。
> - `references/config/version-manifest.json` 仅作 **skill 级粗粒度登记**（子 Skill → 最低大版本）与自检清单基线，**不作为运行时闸门**。
> - 简言之：能否路由，以 §4.2 的 `openapi-2.0-versions.json` 为准。

| 场景关键词 | 目标子 Skill |
|-----------|-------------|
| 创建数据源、新建数据源、添加数据源、ConfigItemList、JDBC | → `create-data-source` |
| 数据源连通性、检查数据源连接、测试数据源 | → `check-data-source-connectivity` |
| 创建计算源、新建计算引擎、MaxCompute 计算源 | → `create-maxcompute-compute-source` |
| 更新计算源、编辑计算源 | → `update-compute-source` |
| 计算源连通性、检查计算源连接 | → `check-compute-source-connectivity` |
| 创建 MaxCompute 数据源 / 接入 MaxCompute / MC 数据源 | → `create-maxcompute-data-source` |
| 创建项目 / 新建项目 / Dataphin 项目 / 项目初始化 / DevProd / Basic / 项目白名单 / 项目依赖 | → `create-project` |
| 项目成员 / 添加成员 / 移除成员 / 更新角色 / 成员管理 | → `manage-project-member` |
| 租户成员 / 添加租户成员 / 移除租户成员 / 更新全局角色 / 租户成员管理 / tenant member | → `manage-tenant-member` |
| 行级权限、行权限、row permission、按行过滤、管控规则、授权账号、受影响账号 | → `manage-row-level-permission` |
| 列级权限、字段权限、字段级权限、column permission、field permission、敏感字段可见性、PHYSICAL_FIELD | → `manage-column-permission` |
| 即席查询、执行 SQL、临时跑代码、建表 | → `execute-ad-hoc-task` |
| 提交离线任务、任务提交、submit-batch-task | → `submit-batch-task` |
| 更新任务代码、更新调度、update-batch-task | → `update-batch-task` |
| 虚拟根节点、NodeWithoutUpstream、挂默认上游、DagId | → `find-tenant-root-node` |
| 按名称查任务、查任务代码、查任务调度 | → `get-batch-task-info-by-name` |
| 业务日期、bizdate、T-1、今天日期、昨天 | → `get-bizdate` |
| 补数据、补跑、回填、重跑、supplement、backfill | → `create-node-supplement` |
| 重跑实例 / rerun / 任务重跑 / operate-instance / 实例恢复 | → `rerun-task-instance` |
| 实例状态 / 查看日志 / 任务监控 / 实例监控 / WAIT_SCHEDULE / FAILED / taskrun | → `monitor-task-instance` |
| 暂停实例 / 恢复实例 / pause / resume / 暂停调度 / 阻止调度 | → `pause-task-instance` |
| 数据同步、数据搬运、pipeline、reader-writer、MySQL→MaxCompute | → `create-pipeline-task` |
| 修改管道任务、更新管道、修改调度配置、改 cron、修改并发、修改脏数据、update-pipeline | → `update-pipeline-task` |
| 创建数据标准、质量规则、create-standard | → `create-standard` |
| 更新数据标准、更新质量规则、update-standard | → `update-standard` |
| 管理数据标准、数据标准生命周期、发布标准、下线标准、删除标准、标准列表 | → `manage-data-standard` |
| 管理主题域、主题域生命周期、新建/修改/删除主题域、主题域列表、数据仓库分层、数据板块下建主题域 | → `manage-topic-domain` |
| 管理业务实体、业务对象、业务活动、新建/修改/上线/下线/删除业务实体、维度建模、事实建模、业务模型 | → `manage-biz-entity` |
| 管理业务指标、业务口径、指标定义、新建/修改/查询/删除业务指标、GMV、DAU、转化率、指标关系图 | → `manage-biz-metric` |
| 码表、标准代码、码值、代码值、lookup table、创建码表、维护码值 | → `manage-lookup-table` |
| 落标、标准映射、映射关系、字段关联标准、有效映射、无效映射、解除映射 | → `manage-standard-mapping` |
| 数据源授权、生产账号授权、DsRead、DsWrite、PublishStatus=0 | → `grant-data-source-permission` |
| 数据分级分类、分类分级、数据分类、数据分级、安全等级、敏感数据标签、识别结果、C1、C2、C3、C4 | → `manage-data-classification` |
| 数据脱敏、脱敏规则、动态脱敏、字段脱敏、手机号打星、身份证脱敏、邮箱脱敏、白名单、masking、desensitize | → `manage-data-masking` |
| 创建 API、发布 API、SQL API、API 开发 | → `create-and-publish-api` |
| 创建应用、API 授权、权限绑定、应用管理 | → `manage-app-and-bindauth` |
| 调用 API、SDK 调用、Python 调用 | → `call-data-service-api` |
| API 监控、调用日志、运维分析 | → `monitor-api-operations` |
| 知识图谱 Schema、本体模型、实体类型、关系类型、Schema 发布 | → `manage-kg-schema`（先确认图引擎：dataType 可用集合随引擎变） |
| 知识图谱数据、创建实体、创建关系、批量导入 | → `manage-kg-knowledge`（CRUD 引擎无关） |
| 知识图谱查询、Cypher 查询、邻居遍历、图查询、关系路径、语义搜索 | → `query-kg`（**先确认图引擎**：Cypher 仅 Neo4j） |
| 质量监控、质量规则、数据质量校验、质量告警、质量试跑、质量调度、监控对象 | → `configure-quality-rule` |
| 非结构化工作流、创建工作流、知识库构建、文档解析、向量化 | → `create-unstructured-workflow` |
| 更新工作流、修改工作流、调整算子、改提示词、update-pipeline | → `update-unstructured-workflow` |
| 创建数据集、数据集管理、元数据表、向量表 | → `create-dataset` |
| 更新数据集表结构、数据集加列、修改元数据表、update-dataset-schema | → `update-dataset-schema` |

## 7. Observability

生成 session-id（32 字符小写十六进制），全套件复用：

```bash
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
echo "Session ID: $SESSION_ID"
```

所有子 Skill 中的 `aliyun` 命令均需携带：
```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{SESSION_ID}
```

子 Skill 继承父层生成的 session-id，无需重新生成。

## 8. Core Workflow（场景路由表分发）

### Step 0: 版本获取与门控（每次会话必须首先执行，不可跳过）

**顺序：⓪ CLI 版本闸门 → ① 只收 AK/SK → ② 由 AK 自动判定 → ③ 按判定结果中性追问下一项；全程不向用户暴露"公共云/独立部署"概念。**

0. **CLI 版本闸门（[硬规则] 不可跳过，未 PASS 不得执行任何后续步骤）**：进入本 Step 其余步骤（凭证检查、环境判定、路由、业务参数收集）之前，**必须先原样执行**以下脚本并根据输出判定：

   ```bash
   REQUIRED=3.4.8
   CURRENT=$(aliyun version 2>/dev/null | head -n1 | tr -d '[:space:]')
   if [ -z "$CURRENT" ]; then
     echo "FAIL: aliyun CLI 未安装"
   elif [ "$(printf '%s\n' "$REQUIRED" "$CURRENT" | sort -V | head -n1)" = "$REQUIRED" ]; then
     echo "PASS: aliyun CLI $CURRENT (>= $REQUIRED)"
   else
     echo "FAIL: aliyun CLI $CURRENT < $REQUIRED，必须先升级"
   fi
   ```

   - **判定规则**：**仅当输出以 `PASS` 开头才可继续**；输出 `FAIL`、脚本无输出或执行报错，一律视为未通过。禁止目测比较版本号代替本脚本。
   - **失败动作（未通过时）**：
     - **立即停止**，不得进入凭证检查、环境判定、路由或任何业务参数收集；
     - 向用户说明当前版本与要求版本（`3.4.8`），给出升级方式（见 [CLI 安装指南](./references/cli-installation-guide.md) 对应操作系统的一键安装脚本），**经用户确认后再执行升级**（升级属系统变更，遵循 §12 HITL 原则，不做静默自动升级）；
     - 升级/安装完成后**必须重跑本闸门脚本**，输出 `PASS` 才放行进入第 1 步；仍 `FAIL` 则向用户抛出原始输出并终止。

1. `aliyun configure list` 检查是否已有有效凭证。**有凭证（复用已有 profile）→ 先向用户回显本次使用的 profile 名再继续**，例如「本次使用已有 profile `<name>` 继续操作」，然后跳到第 3 步做环境判定。回显文案保持中性，仅说明使用了哪个 profile，不解释判定过程、不暴露部署类型。
2. **无凭证（首次使用 / profile 为空）第一问：只向用户索取 AccessKey ID + AccessKey Secret。** 问题文案里**不得出现** region / endpoint / 公共云 / 独立部署 任何字样。（安全可选：也可让用户自行 `aliyun configure` 后回来。）
3. **拿到 AK 后自动判定（不提问）**：按 [§4.1](#41-环境自动判定公共云--独立部署) 用 #1 endpoint / #2 AK 前缀 / #3 探测（首次默认 `cn-shanghai`）推断环境。
4. **按判定结果中性追问下一项并写 profile**——**只说索取那一句，禁止解释原因 / 点出部署形态**（不得出现 公网 / 网关 / 无法识别 / 私有部署 / 独立部署 / 公共云 等；"AccessKey"一词本身可以说）：
   - 判为公共云 → 只问 **"你的 Dataphin 在哪个地域？例如 cn-shanghai / cn-hangzhou。"** → `aliyun configure set --profile dataphin --mode AK --access-key-id <AK> --access-key-secret <SK> --region <region>`，直接进入 Step 1。
   - 判为独立部署 → 只问 **"请提供你的 Dataphin 服务地址（endpoint），例如 dataphin-openapi.xxx.com。"** → `aliyun configure set --profile dataphin-standalone --mode AK --access-key-id <AK> --access-key-secret <SK> --endpoint <endpoint>`；并按 §4.1 独立部署配置引导**收集 `OpTenantId`（租户 ID）**。本次会话中**所有** `aliyun dataphin-public` 命令都必须追加：
     ```
     --profile dataphin-standalone --skip-secure-verify --op-tenant-id <OpTenantId>
     ```

   > **[硬规则] 环境锁定**：第 3 步的判定结论（或用户显式指定 / 已有 profile 的既定环境）即为**本会话锁定环境**。后续所有步骤（含 §4.2 版本关卡与子 Skill 执行）失败时**不得改判环境**——不得由公共云切到独立部署、也不得由独立部署切回公共云，只在当前环境内排障，排障无果直接向用户抛出原始错误并终止（见 [§4.1 环境锁定](#41-环境自动判定公共云--独立部署)）。

5. **独立部署强制关卡（不可跳过）**：完成上面配置后、进入路由前，**必须先执行 [§4.2](#42-版本感知的-20-openapi-清单独立部署下为路由前强制关卡) 的版本获取→裁剪→闸门**。严禁跳过版本获取直接进入业务参数收集；用户请求的接口若 `min_version` 高于当前环境版本，须在此关卡直接告知不支持并停止。（公共云无此关卡，直接进入 Step 1。）

---

### Step 1~5: 场景路由

1. **识别场景关键词**：从用户请求中提取关键词
2. **版本闸门**（仅独立部署，Step 0 第 5 步已强制执行）：目标接口须已通过 §4.2 版本闸门（`min_version <= 当前环境版本`）才可路由；不在有效集内的接口（如 6.0 环境的 `CreateDataset`）应已在关卡处被拦下并告知「需 Y+ 版本」，不进入下面路由/收参
3. **匹配路由表**：

| 关键词 | 路由目标 |
|-------|--------|
| 支持哪些接口 / 接口清单 / 当前版本 / 某接口能不能用 / 版本支持的 API | §4.2 版本感知清单（父层内联处理，不路由子 Skill）→ [参考](./references/version-aware-openapi.md) |
| 创建数据源 / 新建数据源 / 添加数据源 / ConfigItemList / JDBC / 数据源类型 | [create-data-source](./references/dataplan/create-data-source/SKILL.md) |
| 数据源连通性 / 检查数据源连接 / 测试数据源 | [check-data-source-connectivity](./references/dataplan/check-data-source-connectivity/SKILL.md) |
| 创建计算源 / 新建计算引擎 / MaxCompute 计算源 | [create-maxcompute-compute-source](./references/dataplan/create-compute-source/create-maxcompute-compute-source/SKILL.md) |
| 更新计算源 / 编辑计算源 | [update-compute-source](./references/dataplan/update-compute-source/SKILL.md) |
| 计算源连通性 / 检查计算源连接 | [check-compute-source-connectivity](./references/dataplan/check-compute-source-connectivity/SKILL.md) |
| 创建 MaxCompute 数据源 / 接入 MaxCompute / MC 数据源 / MaxCompute datasource | [create-maxcompute-data-source](./references/dataplan/create-maxcompute-data-source/SKILL.md) |
| 创建项目 / 新建项目 / Dataphin 项目 / 项目初始化 / DevProd / Basic / 项目白名单 / 项目依赖 | [create-project](./references/dataplan/create-project/SKILL.md) |
| 项目成员 / 添加成员 / 移除成员 / 更新角色 / 成员管理 | [manage-project-member](./references/dataplan/manage-project-member/SKILL.md) |
| 即席查询 / 执行 SQL / 临时跑代码 / 建表 / execute-ad-hoc-task | [execute-ad-hoc-task](./references/dev/execute-ad-hoc-task/SKILL.md) |
| 提交离线任务 / 任务提交 / submit-batch-task | [submit-batch-task](./references/dev/submit-batch-task/SKILL.md) |
| 更新任务代码 / 更新调度 / update-batch-task | [update-batch-task](./references/dev/update-batch-task/SKILL.md) |
| 虚拟根节点 / NodeWithoutUpstream / 挂默认上游 / DagId | [find-tenant-root-node](./references/dev/find-tenant-root-node/SKILL.md) |
| 按名称查任务 / 查任务代码 / 查任务调度 / get-batch-task-info-by-name | [get-batch-task-info-by-name](./references/dev/get-batch-task-info-by-name/SKILL.md) |
| 业务日期 / bizdate / T-1 / 今天日期 / 昨天 | [get-bizdate](./references/dev/get-bizdate/SKILL.md) |
| 补数据 / 补跑 / 回填 / 重跑 / supplement / backfill | [create-node-supplement](./references/ops/create-node-supplement/SKILL.md) |
| 重跑实例 / rerun / 任务重跑 / operate-instance / 实例恢复 | [rerun-task-instance](./references/ops/rerun-task-instance/SKILL.md) |
| 实例状态 / 查看日志 / 任务监控 / 实例监控 / WAIT_SCHEDULE / FAILED / taskrun | [monitor-task-instance](./references/ops/monitor-task-instance/SKILL.md) |
| 暂停实例 / 恢复实例 / pause / resume / 暂停调度 / 阻止调度 | [pause-task-instance](./references/ops/pause-task-instance/SKILL.md) |
| 数据同步 / 数据搬运 / pipeline / reader-writer / MySQL→MaxCompute | [create-pipeline-task](./references/pipeline/create-pipeline-task/SKILL.md) |
| 修改管道任务 / 更新管道 / 修改调度配置 / 改 cron / 修改并发 / 修改脏数据 / update-pipeline | [update-pipeline-task](./references/pipeline/update-pipeline-task/SKILL.md) |
| 创建数据标准 / 质量规则 / create-standard | [create-standard](./references/assets/create-standard/SKILL.md) |
| 更新数据标准 / 更新质量规则 / update-standard | [update-standard](./references/assets/update-standard/SKILL.md) |
| 管理数据标准 / 数据标准生命周期 / 发布标准 / 下线标准 / 删除标准 / 标准列表查询 | [manage-data-standard](./references/assets/manage-data-standard/SKILL.md) |
| 管理主题域 / 主题域生命周期 / 新建 / 修改 / 删除主题域 / 主题域列表 / 数据仓库分层 / 数据板块下建主题域 | [manage-topic-domain](./references/assets/manage-topic-domain/SKILL.md) |
| 管理业务实体 / 业务对象 / 业务活动 / 业务实体生命周期 / 新建 / 修改 / 上线 / 下线 / 删除业务实体 / 维度建模 / 事实建模 | [manage-biz-entity](./references/assets/manage-biz-entity/SKILL.md) |
| 管理业务指标 / 业务口径 / 指标定义 / 新建 / 修改 / 查询 / 删除业务指标 / GMV / DAU / 转化率 / 指标关系图 | [manage-biz-metric](./references/assets/manage-biz-metric/SKILL.md) |
| 码表 / 标准代码 / 码值 / 代码值 / lookup table / 创建码表 / 维护码值 / create-standard-lookup-table | [manage-lookup-table](./references/assets/manage-lookup-table/SKILL.md) |
| 落标 / 标准映射 / 映射关系 / 字段关联标准 / 有效映射 / 无效映射 / 解除映射 / create-standard-mapping | [manage-standard-mapping](./references/assets/manage-standard-mapping/SKILL.md) |
| 资产属性 / 自定义属性 / 属性回写 / 批量更新属性 / 资产打标 / update-asset-attributes / AssetAttribute | [manage-asset-attributes](./references/assets/manage-asset-attributes/SKILL.md) |
| 资产画像 / 资产属性查询 / 资产详情 / 目录层级 / 资产挂载目录 / 专题 / DirectoryChain / get-asset-attributes | [query-asset-details](./references/assets/query-asset-details/SKILL.md) |
| 租户成员 / 添加租户成员 / 移除租户成员 / 更新全局角色 / 租户成员管理 / tenant member | [manage-tenant-member](./references/manage/manage-tenant-member/SKILL.md) |
| 行级权限 / 行权限 / row permission / row-level permission / 按行过滤 / 管控规则 / 授权账号 / 受影响账号 | [manage-row-level-permission](./references/manage/manage-row-level-permission/SKILL.md) |
| 列级权限 / 字段权限 / 字段级权限 / column permission / field permission / 敏感字段可见性 / PHYSICAL_FIELD | [manage-column-permission](./references/manage/manage-column-permission/SKILL.md) |
| 数据源授权 / 生产账号授权 / DsRead / DsWrite / PublishStatus=0 | [grant-data-source-permission](./references/datasecurity/grant-data-source-permission/SKILL.md) |
| 数据分级分类 / 分类分级 / 数据分类 / 数据分级 / 安全等级 / 敏感数据标签 / 识别结果 / C1 / C2 / C3 / C4 | [manage-data-classification](./references/datasecurity/manage-data-classification/SKILL.md) |
| 数据脱敏 / 脱敏规则 / 动态脱敏 / 字段脱敏 / 手机号打星 / 身份证脱敏 / 邮箱脱敏 / 白名单 / masking / desensitize | [manage-data-masking](./references/datasecurity/manage-data-masking/SKILL.md) |
| 创建 API / 发布 API / SQL API / API 开发 / 数据服务 API | [create-and-publish-api](./references/dataservice/create-and-publish-api/SKILL.md) |
| 创建应用 / API 授权 / 权限绑定 / 应用管理 / 密钥 | [manage-app-and-bindauth](./references/dataservice/manage-app-and-bindauth/SKILL.md) |
| 调用 API / SDK 调用 / Python 调用 / AppKey | [call-data-service-api](./references/dataservice/call-data-service-api/SKILL.md) |
| API 监控 / 调用日志 / 运维分析 / 异常分析 | [monitor-api-operations](./references/dataservice/monitor-api-operations/SKILL.md) |
| 知识图谱 Schema / 本体模型 / 实体类型 / 关系类型 / Schema 导入导出 / Schema 发布 | [manage-kg-schema](./references/knowledge-graph/manage-kg-schema/SKILL.md) |
| 知识图谱数据 / 创建实体 / 创建关系 / 批量导入 | [manage-kg-knowledge](./references/knowledge-graph/manage-kg-knowledge/SKILL.md) |
| 知识图谱查询 / Cypher 查询 / 邻居遍历 / 图查询 / 关系路径探索 / 语义搜索 | [query-kg](./references/knowledge-graph/query-kg/SKILL.md) |
| 知识图谱图引擎差异 / Neo4j vs Lindorm / 为何 Cypher 报错 / 属性类型支持情况 | [图引擎能力矩阵](./references/knowledge-graph/graph-engine-capabilities.md) |
| 质量监控 / 质量规则 / 数据质量校验 / 质量告警 / 质量试跑 / 质量调度 / 监控对象 | [configure-quality-rule](./references/assets/configure-quality-rule/SKILL.md) |
| 非结构化工作流 / 创建工作流 / 知识库构建 / 文档解析 / PPT 按页 / 向量化 / Embedding 入库 / create-work-flow-by-json | [create-unstructured-workflow](./references/unstructured-data/create-unstructured-workflow/SKILL.md) |
| 更新工作流 / 修改工作流 / 调整算子 / 改提示词 / 换模型 / 增删算子 / update-pipeline | [update-unstructured-workflow](./references/unstructured-data/update-unstructured-workflow/SKILL.md) |
| 创建数据集 / 新建数据集 / 数据集管理 / 元数据表 / 表结构设计 / 向量表 / Milvus / create-dataset / list-datasets / Dataset | [create-dataset](./references/unstructured-data/create-dataset/SKILL.md) |
| 更新数据集表结构 / 数据集加列 / 修改元数据表 / 重新加载表结构 / ALTER TABLE 数据集 / update-dataset-schema | [update-dataset-schema](./references/unstructured-data/update-dataset-schema/SKILL.md) |

4. **加载子 SKILL.md**：委托执行，传递 session-id
5. **汇报结果**：子 Skill 完成后返回执行摘要

## 9. Success Verification

路由分发成功标准：
- CLI 版本闸门已 PASS（§8 Step 0 第 0 步）
- 关键词匹配命中且唯一
- 子 SKILL.md 文件存在且可读
- Session-id 已生成并传递

## 10. Cleanup

各子 Skill 负责各自的资源清理，详见对应子 Skill 的 §10。

## 11. Command Tables

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- 大整数 ID（19 位 snowflake）必须用字符串传参，示例中用引号包住
- 写操作（create/update/delete/grant/publish）执行前必须 HITL 确认
- 独立部署环境 Endpoint 默认规则：
  - 管理面 OpenAPI：`dataphin-openapi.<env>.aliyun.com`
  - 数据服务网关：`dataphin-os-gateway.<env>.aliyun.com`
- 每次操作完成后用 `list-*` 命令反查确认
- **上下文经济性（只读查询必看）**：元数据/列表类只读命令的完整返回往往极大（实测 `get-table-columns` 单表达 18k 字符，一轮探查工具输出 103k 字符≈ 41k tokens，其中 68% 来自未裁剪的字段列表），必须：
  - 查字段/列表时带 `--cli-query '<JMESPath>'` 只取所需字段（如 `ColumnList[].{Name:Name,DataType:DataType,Cn:Cn}`，实测可降 ~86%）
  - **`list-tables` 必带 `--cli-query 'PageResult.TableList[].Name'`**：不带时会返回每张表二十多个字段的全量元数据，**实测单次 115k 字符（占单轮上下文 39%）**；另：该命令是扁平参数 `--catalog/--keyword/--page-no/--page-size`，**没有 `--list-query`**（误传会得空结果）
  - 分页接口给定 `--page-size`，不要默认拉全量；**先取一次 `--cli-query 'PageResult.TotalCount'` 判定总数再决定是否翻页，空页不要重试**（实测曾对已取完的第 2/3 页空转 5 次）
  - 日志类接口（`get-ad-hoc-task-log` / `get-physical-instance-log`）**仅失败或需确认状态时才拉**，先只取状态字段，看正文时再取并取尾部片段
  - 同一对象不重复查（已有返回就复用，不要先 `get-table-columns` 再 `DESC 表`）
  - **不要拉裸 `aliyun dataphin-public --help`**（全量命令帮助实测 44.5k 字符）；找命令名时按关键词检索命令名即可。已知**码表/标准集/标准模板均无 list 类命令**（仅按 ID `get-*`），不要去找 `list-standard-sets`、`list-standard-templates` 之类不存在的命令
- **部署模式相关**：
  - 子 Skill 不感知部署模式，所有 endpoint 适配由父层 profile 配置驱动
  - 环境（公共云 / 独立部署）由 §4.1 **运行时自动判定**（endpoint / AK 前缀 / 探测），不再依赖 `deployment_mode` 字段，也不询问用户类型
  - **环境一经锁定不可切换**（§4.1 硬规则）：调用失败时只在当前环境内排障或直接抛出原始错误终止，不做公共云 ↔ 独立部署的跨环境回退重试
  - 独立部署接口清单按 §4.2 版本感知裁剪；未发布的 `sdk_only` 接口只能泛化调用
