---
name: create-data-source
description: |-
  新建 Dataphin 数据源（87 种类型）。 触发场景：创建数据源 / 新建数据源 / 添加数据源 / 注册数据源 / create-data-source / ConfigItemList 怎么填 / JDBC URL 格式 / DEV-PROD 数据源分离。 Type 决定 ConfigItemList 内 Key/Value 的组合完全不同（MySQL / MaxCompute / DORIS / POSTGRE_SQL / CLICKHOUSE / HANA 等）。 DEV_PROD 项目需先建 PROD 数据源再建 DEV 并关联 ProdDataSourceId（大整数必须字符串传递）。 触发词：创建数据源、新建数据源、添加数据源、create-data-source、ConfigItemList、JDBC、DEV PROD 数据源、ProdDataSourceId、数据源类型。
---
# 新建数据源 skill

## 适用场景

- 需要为 dev / prod 环境各创建数据源
- 需要依据数据源类型（Type）定制 `ConfigItemList` 的 Key/Value
- Agent 读到 "创建 MySQL/MaxCompute/Hive/... 数据源" 类指令时直接查本 skill

## 命令 & 官方文档

- CLI：`aliyun dataphin-public create-data-source --help`
- OpenAPI：[CreateDataSource](https://next.api.aliyun.com/document/dataphin-public/2023-06-30/CreateDataSource)

## 顶层参数骨架

```text
--tenant-id <int>                 必填 | 租户 ID
--prod-data-source-create <JSON>     可选 | 生产环境数据源体
--dev-data-source-create <JSON>      可选 | 开发环境数据源体（可关联 ProdDataSourceId）
```

生产体与开发体至少提供其一。若项目为 dev-prod 模式，建议同时提供，`DevDataSourceCreate.ProdDataSourceId` 对齐生产 ID。

## ProdDataSourceCreate JSON 结构（通用骨架）

```jsonc
{
  "Type": "<枚举值>",              // 必填，详见下方"Type 枚举与 Key 清单"
  "Name": "<string>",              // 必填，数据源名
  "Description": "<string>",       // 可选
  "CheckActivity": true,           // 可选，默认 true；创建时是否校验连通性
  "ConfigItemList": [              // 必填，连接配置项，不同 Type 的 Key 完全不同
    { "Key": "<配置 key>", "Value": "<配置值>" }
  ]
}
```

## Type 枚举与 ConfigItemList Key 清单

Dataphin 支持 **87 种** 数据源类型，不同 Type 的 ConfigItemList Key/Value 组合完全不同。
为控制 SKILL.md 体积，完整清单（MySQL / MaxCompute / DORIS / POSTGRE_SQL / CLICKHOUSE /
HANA / HIVE / SELECTDB 等）抽离到独立 reference：

> 📖 详见 [references/type-config.md](references/type-config.md)

常用规则速查：
- **大整数 ID 必须字符串化**（JS Number 精度丢失）：`prod-data-source-id` 等
- **DEV-PROD 项目**：先创建 PROD 数据源 → 再创建 DEV 并填 `ProdDataSourceId`
- **JDBC URL**：MySQL 用 `jdbc:mysql://host:port/db`，PostgreSQL 用 `jdbc:postgresql://...`
- **MaxCompute** 必填：`endPoint` / `project` / `accessId` / `accessKey`

# DevDataSourceCreate 结构

```jsonc
{
  "ProdDataSourceId": "7456935852434808960",  // ⚠ 必须为字符串！见下方"大整数精度"警告
  "DataSourceCreate": {                         // 结构与 ProdDataSourceCreate 完全一致
    "Type": "...",
    "Name": "...",
    "ConfigItemList": [ ... ]
  }
}
```

> ⚠ **DEV 数据源必须关联 PROD**：`ProdDataSourceId` 字段在数据库中为 `NOT NULL` 约束，独立创建 DEV 数据源（不传或传 null）会报 `null value in column "prod_data_source_id" violates not-null constraint`。**必须先建 PROD，拿到 PROD Id 后再建 DEV**。
>
> ⚠ **大整数 ID 精度截断（已踩坑）**：Dataphin 数据源 ID 为 19 位大整数（如 `7456935852434808960`），超过 JS `Number.MAX_SAFE_INTEGER`（2^53）。如果 `ProdDataSourceId` 用数字格式传入（`"ProdDataSourceId": 7456935852434808960`），CLI 的 JSON.parse 会将尾数截断为 `7456935852434809000`，导致关联失败并报 `DevDataSourceInfo=None`。**解决方案：始终用字符串形式传递**（`"ProdDataSourceId": "7456935852434808960"`）。

## 创建后连通性验证（必做）

数据源创建成功不代表真正可用，**必须通过连通性测试才算完成**。

```bash
# 1. 获取刚创建的数据源 ID（字符串格式，避免 JS 精度丢失）
aliyun dataphin-public list-data-source-with-config \
  --profile <profile> --page 1 --page-size 10 --output json \
  | jq '[.PageResult.DataSourceList[] | select(.ProdDataSourceInfo.Name == "<数据源名>") | .ProdDataSourceInfo.Id]'

# 2. 用 ID 做连通性测试
aliyun dataphin-public check-data-source-connectivity-by-id \
  --profile <profile> --data-source-id <数据源ID> --output json
```

- 返回 `"Success": true` 才代表连通。
- 若失败，检查 ConfigItemList Key 是否正确、网络是否可达，修正后使用 `update-data-source-config --data-source-id <ID> --config-item-list '<JSON>'` 更新配置再重试。

> **关于页面连通性状态的说明**：本技能通过 CLI 调用 `check-data-source-connectivity-by-id` 执行连通性检查，CLI 返回结果即为实时检查结论（`Success: true/false`）。但当前 OpenAPI **不会将检查结果回写到数据库**，因此 Dataphin 控制台页面上该数据源的「连通性检查」状态不会因本次 CLI 调用而变更。这**不影响数据源的实际使用**——只要 CLI 检查返回 `Success: true`，数据源即可正常用于后续任务（建表、同步等）。如需页面状态同步更新，可在控制台手动点击一次「连通性测试」。

## 常见坑

1. **JSON 双重编码**：早期版本传 `--prod-data-source-create` 会被二次转义；已在 CLI 中修复，直接传原始 JSON 字符串即可（见 startup enhanced 记录）
2. **shell 单引号 vs 双引号**：`bash` 建议外单内双 `'{"Type":"MYSQL",...}'`；`zsh` 若报错可改为 `$'...'` 或写到文件再 `--prod-data-source-create "$(cat x.json)"`
3. **Key 大小写**：`jdbc.url` 必须小写，服务端大小写敏感
4. **密码特殊字符**：含 `!`、`$`、`` ` `` 的密码在 bash 单引号中安全，在双引号中会被插值；优先使用单引号
5. **CheckActivity=true 失败**：说明 Key 清单或网络路由有问题，先用 `check-data-source-connectivity`（见同目录 skill）独立验证连接，再回来建源
10. **DEV 数据源独立创建报 null constraint violation**：`prod_data_source_id` 为 NOT NULL，DEV 必须关联已存在的 PROD 数据源。建源顺序必须是：先 PROD → 拿 PROD Id → 再 DEV
11. **大整数 ProdDataSourceId 精度截断**：19 位数据源 ID 作为 JSON number 传入会被 JS JSON.parse float64 截断尾数（如 `...960` → `...000`）。**必须用字符串形式传递**：`"ProdDataSourceId": "7456935852434808960"`
6. **MySQL JDBC URL 安全参数**：必须追加 `?allowUrlInLocalInfile=false&autoDeserialize=false&allowLocalInfile=false&allowLoadLocalInfile=false`，否则返回 `DATASOURCE_CONNECT_URL_NOT_SAFE_V2`
7. **VPC 数据源需完整 VPC 三件套**：`vpc.id` + `vpc.region.id` + `vpc.instance.id` 缺一不可，否则 VPC 反向访问链路建不起来
8. **StarRocks/Doris Type 枚举名**：分别为 `STARROCKS` 和 `DORIS`（连写全大写），**不是** `STAR_ROCKS`（下划线分隔），填错报 `No enum constant PhysicalDataSourceTypeEnum.STAR_ROCKS`
9. **StarRocks/Doris `fenodes` 与 `load.url` 必须同时填写**：仅填 `load.url` 会导致页面 "Load URL" 字段显示为空，因为页面展示读的是 `fenodes` Key。两者值相同（FE HTTP 端口列表）。两种数据源的 ConfigItemList 结构完全相同

## 相关命令

- `aliyun dataphin-public check-data-source-connectivity` — 建源前/建源失败时独立校验 ConfigItemList，见 [check-data-source-connectivity.md](./check-data-source-connectivity.md)
- `aliyun dataphin-public update-data-source-config` — 更新已建数据源的 ConfigItemList（通过 Id）
- `aliyun dataphin-public list-data-source-with-config` — 列出现有数据源及其 ConfigItemList，可用于参考已存在 Type 的 Key 清单
