---
name: grant-data-source-permission
description: |-
  给项目生产账号（PRODUCE）授权数据源 SYNC_READ/SYNC_WRITE，是发布到生产的前置条件。 触发场景：发布失败报 DsRead/DsWrite / DATA_SOURCE_AUTH_NO_PERMISSION / 给生产账号授权 / 数据源权限不足 / PublishStatus=0 且 ErrorMessage 含权限报错 / grant-resource-permission / 发布生效校验。 完整流程：get-project-produce-user → grant-resource-permission → publish-object-list → list-publish-records(PublishStatus=1) → list-nodes --env PROD(HasProd=true)。 关键限制：effective-end 必须 yyyy-MM-dd HH:mm:ss 字符串；DATASOURCE.RUN 不能授给 PRODUCE 账号（OpenAPI 限制）。 触发词：发布失败、DsRead、DsWrite、DATA_SOURCE_AUTH_NO_PERMISSION、数据源授权、生产账号授权、grant-resource-permission、PublishStatus=0、发布生效校验、PRODUCE 账号。
---
# 数据源授权给生产账号 skill

## 适用场景

- DEV-PROD 模式项目下，集成任务 / 数据库 SQL 任务发布到 PROD 时报：
  - `DPN.Pipeline.Validate.DsRead` / `DPN.Pipeline.Validate.DsWrite`（集成任务读/写校验失败）
  - `DATA_SOURCE_AUTH_NO_PERMISSION`（数据库 SQL 任务无 RUN 权限）
- 错误 errorData 中含 `accountType: PRODUCE`，意味着**生产账号缺数据源授权**
- 创建数据源后立即给项目生产账号授读写，避免发布失败

## 背景：发布失败的常见根因

`dev publish-object-list` 接口成功（返回 `Code: OK`）≠ 实际发布成功。发布是**异步**的，权限校验在异步阶段执行。最终结果靠 `list-publish-records` 验真：

```bash
aliyun dataphin-public list-publish-records --profile <p> \
  --search-filter '{"ProjectIdList":[<projectId>],"Page":1,"PageSize":10}'
```

返回字段 `PublishStatus`：`0=失败 / 1=成功 / 2=发布中`。失败时看 `ErrorMessage` 里的 `errorData`：

```jsonc
// 集成任务示例
{"dsName":"doris01","envEnum":"PROD","dsId":"7456294505155688832","accountType":"PRODUCE"}

// 数据库 SQL 任务示例
{"dsId":"7456294563313908096","dsName":"pg02","operation":"RUN"}
```

之后用 `ops list-nodes --env PROD` 二次确认 `HasProd: false`（即未生成 PROD 节点）。

## 完整授权流程

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>

# 1) 取项目生产账号 UserId（仅超管可调）
PRODUCE_USER_ID=$(aliyun dataphin-public get-project-produce-user \
  --profile <p> --project-id $PROJECT_ID --output json \
  | jq -r '.User.Id')
# => 304214953

# 2) 拿目标 PROD 数据源精确字符串 ID（避免 JS 浮点截断为 ...000）
aliyun dataphin-public list-data-source-with-config --profile <p> \
  --search-text "doris01" --output json | jq '.PageResult.DataSourceList[] | {Id,Name,Env}'
# 选 Env=PROD 那条的 Id

# 3) 授权 SYNC_READ + SYNC_WRITE（一次可批量多个数据源 + 多个用户）
aliyun dataphin-public grant-resource-permission --profile <p> \
  --resource-type DATASOURCE \
  --operate-list '["SYNC_READ","SYNC_WRITE"]' \
  --resource-list '[{"ResourceId":"<doris01_PROD_id>"},{"ResourceId":"<pg02_PROD_id>"}]' \
  --user-id-list "[\"$PRODUCE_USER_ID\"]" \
  --effective-end "3025-12-31 23:59:59" \
  --reason "发布前置：授权生产账号读写数据源"

# 4) 验证授权已落库
aliyun dataphin-public list-resource-permissions --profile <p> \
  --tab-type DATASOURCE --page 1 --page-size 20 \
  --search-text "doris01" --output json \
  | jq '.PageResult.RecordList[] | {res:.ResourceInfo.Name, env:.ResourceInfo.Env, account:.TargetAccount.Name, type:.TargetAccount.Type, ops:[.PermissionPeriodList[].PermissionType]}'
```

期望输出：
```json
{ "res":"doris01", "env":"PROD", "account":"<projectName>", "type":"PRODUCE", "ops":["SYNC_READ","SYNC_WRITE"] }
```

## 关键参数与陷阱

| 字段 | 取值 | 备注 |
|---|---|---|
| `--resource-type` | `DATASOURCE` | 仅 `TABLE` / `DATASOURCE` 两类（与 `list-resource-permissions --tab-type` 一致） |
| `--operate-list` | `["SYNC_READ","SYNC_WRITE"]` | 集成任务读 / 写 |
| `--resource-list` | `[{"ResourceId":"<dsId字符串>"}]` | **PROD 环境的数据源 ID**；DEV-PROD 双环境项目下 DEV id 不需要单独授（生产账号只读写 PROD） |
| `--user-id-list` | `["<userId>"]` | 生产账号即用 `get-project-produce-user` 返回的 `User.Id` |
| `--effective-end` | **`yyyy-MM-dd HH:mm:ss` 字符串** | ⚠ `--help` 写"毫秒时间戳"是错的，传毫秒报 `Invalid effectiveEndTime`。可用 `3025-12-31 23:59:59` 表示长期 |

## ✗ OpenAPI 不支持的授权（已踩坑）

| 操作 | 报错 | 替代 |
|---|---|---|
| `DATASOURCE.RUN` 给 PRODUCE 账号 | `DPN.Security.NotSupport: DATASOURCE.RUN不支持` | OpenAPI 暂不开放，需在 **页面** 操作：数据源详情 → 成员&账号 → 给生产账号添加 RUN 权限 |
| `effective-end` 传毫秒时间戳（如 `33319785599000`） | `DPN.Commons.InvalidParam: Invalid effectiveEndTime ... valid format: yyyy-MM-dd HH:mm:ss` | 用字符串日期 |

> 验证：实测 `list-resource-permissions` 中历史 `PERSONAL` 账号有 `RUN` 权限，但**不能**通过 OpenAPI 复刻给 PRODUCE 账号——服务端按账号类型分流策略。

## 重发布并确认生效

```bash
# 1) 重新提交（如已有 SubmitId 但发布失败，需重新 submit-pipeline / submit-batch-task）
# 2) publish-object-list
aliyun dataphin-public publish-object-list --profile <p> \
  --submit-id-list '[<SubmitId>]' --comment "授权后重发"

# 3) 校验异步结果（关键！）
aliyun dataphin-public list-publish-records --profile <p> \
  --search-filter '{"ProjectIdList":[<projectId>],"Page":1,"PageSize":3}' \
  | jq '.ListResult.Data[] | {Id,ObjectName,PublishStatus,ErrorMessage:(.ErrorMessage|.[0:200])}'
# PublishStatus="1" 才算真成功

# 4) 终极验证：PROD 节点已生成
aliyun dataphin-public list-nodes --profile <p> --env PROD \
  --node-biz-type SCRIPT --schedule-type NORMAL \
  --search-text "<task-name>" --page 1 --page-size 5 \
  | jq '.PageResult.NodeList[] | {Id,Name,HasProd,HasDev}'
# HasProd=true 即真发布成功
```

## 相关命令

- `aliyun dataphin-public get-project-produce-user` — 仅超管：获取项目生产账号 UserId
- `aliyun dataphin-public list-resource-permissions --tab-type DATASOURCE` — 查现有数据源授权
- `aliyun dataphin-public revoke-resource-permission` — 回收授权
- `aliyun dataphin-public list-publish-records` — 发布生效校验唯一权威接口
- `aliyun dataphin-public list-nodes --env PROD` — 二次确认 PROD 节点存在
- [create-data-source.md](./create-data-source.md) — DEV-PROD 双环境数据源创建
