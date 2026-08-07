# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制。

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case，如 `upsert-*` / `list-*`）。
- 不使用传统 API 格式 `aliyun dataphin-public SaveQualityRule`。
- **双环境通用**：公共云（A）与独立部署（B）共用同一套命令，仅由 profile/endpoint 区分（环境由父 SKILL.md §4.1 自动判定，见 SKILL.md §3/§4）。

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认；不硬编码 tenant-id / watchId / ruleId 等。
- 监控对象类型必须先确认：`TABLE` / `DATASOURCE_TABLE` / `DATASOURCE` / `INDEX` / `REALTIME_LOGICAL_TABLE`，不能仅凭对象名默认成表。
- 监控对象名称（WatchName/tableName）禁止让用户填写，必须由元数据自动推导并回查校验。
- 调度、告警**分别单独确认是否需要**，即使用户初始需求未提及。
- `templateId` 必须用 `list-quality-templates` 按目标租户/对象类型实测获取，不能照搬文档示例 ID。
- 模板级 `formProperties` 必须按界面和模板定义补齐；`FormPropertyList=null` 不代表无必填项。特别是 `TABLE_SCHEMA_CHECK`/2600 必须传 `dataSourceTable`。
- `validateCondition` 必须显式配置或明确告知「不配置的后果」后再继续。

## L1 静态合规（check.sh，创建时必做）

```bash
bash .qoder/skills/create-dp-skills/tests/check.sh alibabacloud-dataphin-skills/references/assets/configure-quality-rule
bash .qoder/skills/create-dp-skills/tests/check.sh alibabacloud-dataphin-skills
```
要求：父子两次均 **0 fail**。

## L2 命令可达性（运行时，需联网 + 凭证）

逐条 `aliyun dataphin-public <cmd> --help` 验证命令存在，重点覆盖：
`get-quality-watch-by-object-id` / `upsert-quality-watch` / `list-quality-templates` / `get-quality-template` / `upsert-quality-rule` /
`submit-quality-rule-tasks` / `assign-quality-rule-of-all-rule-scope-schedules` / `update-quality-rule-switch`；
元数据与即席链路 `list-tables` / `get-table-columns` / `execute-ad-hoc-task` / `get-ad-hoc-task-result` / `list-data-source-with-config`。

> ⚠️ 质量类 Action 为 Dataphin 质量模块接口，其 kebab-case 命令在目标 endpoint 的实际可达性以运行时 `--help` / 真实调用为准（本 skill 参数结构源自 POC 环境 Python 直连验证）。

## L3 端到端验证（需联网 + 凭证）

按 §8 Core Workflow 逐步执行并对照：
1. `upsert-quality-watch` 返回非空 `WatchId`；`get-quality-watch-by-object-id` 可反查到，且界面展示名符合自动生成全名规则。
2. `list-quality-templates` 已按当前 `watchType` 查到真实模板；所用 `templateId` / `templateType` / `catalog` 与返回一致。
3. `upsert-quality-rule` 返回非空 `RuleId`；`list-quality-rules` / `get-quality-rule` 反查命中，`validateCondition` 非空，模板级 `formProperties` 在界面可回显完整。
4. 若创建 `TABLE_SCHEMA_CHECK`/2600，界面“选择校验表”必须已回显具体表，`dataSourceTable` 不为空。
5. `submit-quality-rule-tasks`（试跑）→ `get-quality-rule-task` 状态轮询：
   - `SUCCESS`+`validateResult=true` → 通过；`SUCCESS`+`false` → 校验不通过（规则有效）；`FAILED` → 执行报错，查 `get-quality-rule-task-log`。
6. 分区表试跑必须钉真实单分区，无 `full scan` 报错。

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/watch/rule ID。
- ❌ 使用 `dataphin` 旧 CLI 二进制命令 / PascalCase Action。
- ❌ 未带 `--user-agent` 调用 aliyun API 命令。
- ❌ 未先确认监控对象类型，或让用户手写 WatchName/tableName/复杂对象 JSON。
- ❌ 创建规则前未复述配置清单并请求确认。
- ❌ 未通过 `list-quality-templates` 查询真实模板 ID，直接照搬文档示例。
- ❌ `upsert-quality-rule` 未传模板级必填 `formProperties`（如 2600 缺 `dataSourceTable`）。
- ❌ `upsert-quality-rule` 未传 `validateCondition`（导致规则「未配置」、试跑失败）。
- ❌ 分区表试跑不指定单分区（触发全表扫描被拒）。
