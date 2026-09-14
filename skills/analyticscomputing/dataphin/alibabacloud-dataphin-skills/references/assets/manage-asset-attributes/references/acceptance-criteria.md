# 验收标准

## 正确模式

### 1. 调用通道与契约
- 统一走 [`../scripts/`](../scripts/) 手写签名脚本（V6.3 新增 Action，CLI 插件未收录且官方文档入参形态有误）
- API 版本 `2023-06-30`；业务参数**参与签名并平铺放 JSON body**，`OpTenantId` / `OpUserId` 留 query
- 包裹参数名以实测为准：`UpdateCommand` / `SubmitCommand` / `QueryCommand`；`GetAssetTypeAttributeCodes` 无包裹
- 19 位 snowflake ID 一律字符串传参

### 2. 写入前置
- 先 `codes --writable-only` 拿到**可写**属性（`EditableIn` 非空）与合法枚举 `Value`
- 覆盖写前用 `read` 读出原值另存（覆盖不可自动回滚）
- 按 `MaxLength` 与 InputMode 自校验；单值属性不要传多值
- 清空只能对 `DROPDOWN_MULTI`（多选）属性用 `values=[]`；非多选属性需清空时改用**覆盖为新值**，不得依赖 `[]`（未定义行为）

### 3. 端到端校验（三步法）
1. `Data.FailCount=0`
2. 逐条核对 `ResultList[i].Success=true`
3. **必做**：`read` 回读，确认 `silentlyDropped` 为空 —— 只看 `Success=true` **不足以**说明值已落库

### 4. 上架流程
- 用 `shelve` 直接提交（失败无副作用，兼作预检）
- 退出码 3 时**逐项告知用户缺什么**，区分 `fixableViaApi` 真假
- 缺失值一律**向用户索要**；用户提供不了则明确告知「仅保存不上架，请到界面补齐后再上架」并结束

### 5. 参数确认
- 租户、GUID、AttributeCode、Values、上架范围等执行前需用户确认
- 不硬编码 tenant-id / GUID / 资源名 / AK / SK

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/GUID；在会话或日志中打印凭证值
- ❌ 业务参数放 query（会报网关 502 `AddFieldOperator is not applicable to JsonNull`，且易被误判为权限问题）
- ❌ 未经 HITL 确认直接批量写入 / 清空属性 / 提交上架
- ❌ 单次批量超 50 条
- ❌ **只看 `Success=true` 就认定写入成功**（引用型属性会静默丢弃）
- ❌ 自行编造归属目录 ID 等引用型属性值
- ❌ 上架被拒后反复重试，而不向用户索要缺失信息
- ❌ 依赖服务端拦截非法值：写非法 `AttributeCode`、超长文本、未登记的目录/标签值，均可能返回成功
- ❌ 假定「部分成功」是属性级的 —— 实际是**资产级**，同一资产任一属性非法则整条不写入
- ❌ 对非多选属性依赖 `values=[]` 清空（仅 `DROPDOWN_MULTI` 有设计保证，其它属未定义行为）

## 已知缺陷（验收时不应判为脚本 bug）

| 现象 | 性质 |
|---|---|
| `shelve_directory_ids` / `shelve_tags` 写非法值返回成功但值为空 | 平台缺陷：引用型属性静默过滤，且属性定义元数据未标注 `SYSTEM_REFERENCE` |
| `shelve_directory_ids` 写非数字抛 `InternalError` | 平台缺陷：后端缺入参格式校验，应返回 `InvalidAttributeValue` |
| 上架「可见范围」无任何 AttributeCode 可写 | 能力缺口：必须由用户在界面配置 |
| 归属目录 ID 无查询接口 | 能力缺口：需用户提供 |
| PRD §8.3.2 / Pop 定义把「`[]` 表示清空」写成不分类型的通用规则 | 文档缺陷：缺少「仅多选」限定 |
| 非多选属性传 `[]` 实际也被清空 | 实现宽于设计，属未定义行为，不得依赖 |

## 不属于缺陷的正常行为

| 现象 | 为何正常 |
|---|---|
| `shelve_display_name` / `shelve_description` 传 `values=[]` 或 `[""]` 无效 | 二者非多选属性，设计上本就只保证 `DROPDOWN_MULTI` 的 `[]` 清空；需清空请覆盖为新值或到界面操作 |
| 上架失败返回 HTTP 200 + `Code=OK` | 上架是逐条结果语义，失败体现在 `FailCount` 与 `ResultList[i]`，不是整体请求失败 |
