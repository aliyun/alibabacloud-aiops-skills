# develop-metric · 相关命令

所有命令前缀 `aliyun dataphin-public`，均需携带 `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"`。
本 skill **自身只发只读命令**，写操作全部委托给其他子 skill。

## 本 skill 直接使用（全部只读）

| 命令 | OpenAPI Action | 用途 | 关键约束 |
|---|---|---|---|
| `list-catalog-assets` | `ListCatalogAssets` | Step 0 找现成结果表 / Step 5 核验指标注册 | 只覆盖**已上架**资产；`--asset-type TABLE` / `INDEX` |
| `list-tables` | `ListTables` | Step 1 找来源表 | 扁平参数，**无 `--list-query`**；必带 `--cli-query`；先取 `TotalCount` 再翻页；空页不重试 |
| `get-table-columns` | `GetTableColumns` | Step 2 校验字段 | 走 **catalog 维度**：`--catalog <项目英文名>` + `--table-name`；**不认** `--project-id` / `--env` |
| `get-catalog-asset-details` | `GetCatalogAssetDetails` | 需要资产详情/字段时 | 按 `--guid` 查 |

### 常用投影写法

```bash
# 表总数
--cli-query 'PageResult.TotalCount'
# 表名清单
--cli-query 'PageResult.TableList[].Name'
```

> ⚠️ 投影会吞错：服务端返回错误体时 JMESPath 匹配不到 → 输出字面 `null` 且退出码 0。拿到 `null` **必须去掉 `--cli-query` 原样重跑**核实是真空值还是接口报错（如 `Forbidden: Miss openAPI <x> feature` = 租户功能未开通，换命令换参数一律无效）。

## 委托给其他子 skill 的写操作

| 需求 | 委托 skill | 涉及命令 |
|---|---|---|
| 试算口径 | [`execute-ad-hoc-task`](../../../dev/execute-ad-hoc-task/SKILL.md) | `execute-ad-hoc-task` / `get-ad-hoc-task-result` / `get-ad-hoc-task-log` |
| 新建/修改计算任务 | [`update-batch-task`](../../../dev/update-batch-task/SKILL.md) | `create-batch-task` / `update-batch-task` |
| 提交并发布任务 | [`submit-batch-task`](../../../dev/submit-batch-task/SKILL.md) | `submit-batch-task` / `publish-object-list` |
| 挂默认上游 | [`find-tenant-root-node`](../../../dev/find-tenant-root-node/SKILL.md) | — |
| 跑历史数据 | [`create-node-supplement`](../../../ops/create-node-supplement/SKILL.md) | 补数据相关 |
| 关联到业务指标 | [`manage-biz-metric`](../../manage-biz-metric/SKILL.md) | `update-biz-metric` |

### 即席查询两个实测要点

- `get-ad-hoc-task-result` 必填 `--project-id` / `--task-id` / `--sub-task-id`，**`--sub-task-id` 是 0 起始下标**（传 1 报 `DPN.DataProcess.CodeNotFound`）。
- 响应 `Result:""` = 任务仍在运行需继续轮询，**不是失败**。

## ✗ 不存在的命令（实测 0.7.1 穷举确认，不要尝试）

| 期望能力 | 状态 | 替代 |
|---|---|---|
| 创建自定义指标（`CUSTOM_INDEX`） | **无命令** | 控制台人工建（Step 4 指引） |
| 创建规范建模原子/派生指标 | **无命令** | 控制台人工建 |
| 资产上架 / 注册到资产目录 | **无命令** | 控制台人工上架 |
| 技术指标分页列表 | **无专用命令** | 借 `list-catalog-assets --asset-type INDEX`（仅已上架） |

> 验证方式：`aliyun dataphin-public --help | grep -iE "metric|index"` 仅返回业务指标 4 个命令 + 资产目录 2 个命令。

## 全局 flag

| flag | 用途 |
|---|---|
| `--cli-dry-run` | 只打印请求体不实际调用 |
| `--format json` | 结构化输出 |
| `--cli-query <jmespath>` | 输出投影（注意上文的吞错风险） |
