# 调用前置发现（按应用名 + API 名反查全部调用参数）

> **为什么需要本篇**：`call-data-service-api` 的 §6 假设你已经持有 `appKey`/`appSecret`/`apiId`/`host` 四要素。但真实场景往往只给「应用名 + 要调的 API 名」（例：*让应用「客户管理」查询客户列表*）。本篇给出一条**从零反查这四要素**的可照抄配方，并汇总踩坑点。
>
> 反查走**管理面 OpenAPI**（`aliyun dataphin-public`，RAM AK/Secret）；真正调用走**数据服务网关**（AppKey/AppSecret，用附带脚本签名）——两套凭证、两条链路，不要混用。

## 反查配方（4 步）

设已知：租户 `OpTenantId`、应用名 `<AppName>`、API 名 `<ApiName>`。

### 步骤 A：应用名 → AppId（⚠️ 同名去重）

```bash
aliyun dataphin-public list-data-service-apps \
  --op-tenant-id <OpTenantId> \
  --list-query PageNo=1 PageSize=100 \
  --endpoint <ENDPOINT> --user-agent "AlibabaCloud-Agent-Skills/call-data-service-api/{SESSION_ID}"
```

在返回 `Data.AppList[]` 中按 `AppName` 匹配拿 `AppId`。

> **⚠️ 应用名不唯一**：同一租户下可能存在多个同名应用（例：两个「客户管理」）。**必须用用户给的 AppKey 做唯一确定**——列表接口不返回 AppKey，需在步骤 B 用 `get-data-service-app` 逐个取详情核对 `AppKey`，命中目标 AppKey 的才是正确应用。
>
> 列表还带 `IsMember` 字段：只有 `IsMember=true` 的应用你才能在步骤 B 拿到 AppSecret。

### 步骤 B：AppId → AppKey / AppSecret

```bash
aliyun dataphin-public get-data-service-app \
  --op-tenant-id <OpTenantId> --app-id <AppId> \
  --endpoint <ENDPOINT> --user-agent "AlibabaCloud-Agent-Skills/call-data-service-api/{SESSION_ID}"
```

返回 `Data.AppKey` / `Data.AppSecret`。

> **⚠️ AppKey 是字符串**：返回的 `AppKey` 形如 `"200000326"`，比较时按字符串处理（`str(AppKey) == 目标`），不要当整数比。
> **⚠️ 权限**：非应用成员（`IsMember=false`）调用返回 `DPN.Oltp.MgmtSys.NoAuthorized / 没有操作权限`——换成员账号或让管理员加成员。

### 步骤 C：应用已授权 API 列表 → apiId + 授权返回字段

```bash
aliyun dataphin-public list-authorized-data-service-api-details \
  --op-tenant-id <OpTenantId> \
  --list-query AppKeyStr=<AppKey> Page=1 PageSize=100 \
  --endpoint <ENDPOINT> --user-agent "AlibabaCloud-Agent-Skills/call-data-service-api/{SESSION_ID}"
```

在返回 `Result.Data[]` 中按 `ApiName` 匹配，拿到：
- `ApiId` — 调用用的 API 唯一标识
- `ProjectId` — API 所属项目
- `AuthorizedDevReturnParameters[].ParameterName` / `AuthorizedProdReturnParameters[].ParameterName` — **本应用被授权的返回字段**，直接作为调用时 `returnFields` 的取值来源

> **⚠️ 用 `AppKeyStr`（字符串），不要用 `AppKey`（整型，已弃用）**：`ListQuery.AppKey`（integer）在文档中标注「已弃用，请使用 AppKeyStr」。
> **✅ 这一步比 `list-data-service-published-apis` 更准**：它直接列出「本应用有权调用」的 API 子集，避免在全项目已发布 API 里翻找、还可能撞上未授权的。

### 步骤 D：apiId → API 文档（methodType + 请求参数）

```bash
aliyun dataphin-public get-data-service-api-document \
  --op-tenant-id <OpTenantId> --id <ApiId> \
  --endpoint <ENDPOINT> --user-agent "AlibabaCloud-Agent-Skills/call-data-service-api/{SESSION_ID}"
```

关键返回字段：

| 字段 | 用途 |
|------|------|
| `RequestParamList[]` | 业务请求参数：`Name` / `Type` / `Operator` / 是否必填。填入调用时 `conditions`；**全部可选**时可传 `conditions={}` 查全部 |
| `ResponseParamList[]` | 响应字段名，与步骤 C 授权字段取交集即 `returnFields` |
| `ReturnLimit` | 单次返回上限（分页参考） |
| `IsPagedQuery` | 仅表「是否分页」，**不能单独用来定 methodType**（见下⚠️） |

> **⚠️ methodType 按 API 操作类型 / 命名判断，不要只看 `IsPagedQuery`**：methodType 决定网关路径 `/{methodType}/{apiId}`，共 5 种：
>
> | API 操作 / 命名 | methodType | 路径 |
> |---|---|---|
> | `List*` / `Bulk*` / 分页查询 | `LIST` | `/list/{apiId}` |
> | `Get*` / 单条精确查 | `GET` | `/get/{apiId}` |
> | `Create*` | `CREATE` | `/create/{apiId}` |
> | `Update*` | `UPDATE` | `/update/{apiId}` |
> | `Delete*` | `DELETE` | `/delete/{apiId}` |
>
> `IsPagedQuery=true` **不等于** `LIST`——`GET` 类 API 也可能 `IsPagedQuery=true`（实测 `GetCustomer` 就是 `IsPagedQuery=true` 的 `GET`）。猜错 methodType → 网关返回 `403 The request api path /xxx/{apiId} not bind app {appKey}`，据此换正确动词重试。

至此四要素齐备：`AppKey`（B）、`AppSecret`（B）、`apiId`（C）、`method`+参数（D）；只差 `host`（见下）。

## 网关 host 发现（P1）

`host` 是**数据服务网关地址**，与管理面 OpenAPI 端点（`dataphin-openapi.*`）**不是同一个域名**，也不在任何 OpenAPI 返回里。

### 独立部署命名规律

- 常见形态：`dataphin-dataservice.<租户基础域名>`（例：租户域名 `poc.lydaas.com` → 网关 `dataphin-dataservice.poc.lydaas.com`）。
- 其反代 canonical 名通常落到 `dataphin-os-gateway.*`（可用 `ping` 的 canonical 名侧证）。
- 公共云：从控制台 **数据服务 → 服务管理 → 网络配置** 获取。

### 探测法（把「人工阻塞」变「自助验证」）

数据服务调用路径为 `/{methodType}/{apiId}?appKey=<AppKey>&env=PROD`。用 GET 探一下候选域名即可判断是否命中网关（GET 会被拒，但**拒的方式**能证明域名对不对）：

```bash
curl -sS -k -m 8 "http://<候选host>/list/<apiId>?appKey=<AppKey>&env=PROD"
```

| 返回 | 结论 |
|------|------|
| JSON 且 `code` 以 `DPN-OLTP-` 开头（如 `DPN-OLTP-COMMON-001 "Request method 'GET' not supported"`） | ✅ **命中网关**（它要 POST，调用脚本用 POST） |
| 连接失败 / DNS 不解析 / 404 / 非 DPN-OLTP 响应 | ❌ 换候选域名 |

> HTTP(80) 与 HTTPS(443) 一般都通；POC/私有部署用私有 CA 时，**优先用 HTTP(80) 规避证书校验**（脚本 `--scheme HTTP`，默认端口 80）。若必须 HTTPS 且证书不受信，用脚本 `--scheme HTTPS --ignore-ssl` 跳过校验或导入私有 CA。
> 若探测全失败，才回退到「向环境运维/管理员索取网关地址」。

## 暗坑清单（P2 速查）

| 坑 | 现象 | 规避 |
|----|------|------|
| 应用同名 | 两个「客户管理」，选错就授权/调用错对象 | 用 **AppKey** 唯一确定，不靠名字 |
| AppKey 类型 | 详情接口返回 `"200000326"`（字符串） | 比较用 `str()`；脚本 `appKey` 参数按字符串处理 |
| AppKeyStr vs AppKey | `list-authorized-*` 传 `AppKey`(int) 查不到 | 用 `AppKeyStr`（字符串） |
| returnFields 取值 | 传了未授权字段 → 报错「字段不存在或无权限」 | 取步骤 C 的 `Authorized*ReturnParameters` |
| 字段有值但为 null | 部分字段返回 null | 多为**源库数据本身为空**，非授权问题（无权限会报错而非返回 null） |
| 网关 host 混淆 | 误用 `dataphin-openapi.*` 当网关 | 网关是 `dataphin-dataservice.*`，与 OpenAPI 端点不同 |
| **methodType 猜错** | 网关返 `403 ... not bind app {appKey}` | methodType 按 API 操作类型定（`Get*`→`get`、`List*`/`Bulk*`→`list`、`Create/Update/Delete*` 同名），**不能仅凭 `IsPagedQuery`**（`get` 也可能 `IsPagedQuery=true`） |
| **读错结果键** | `get` 调用成功但取不到数据 | 结果随 methodType 不同：`list` 在 **`results`**（数组），`get` 在 **`result`**（单个对象）；读错键会静默拿到空 |

## 管理面 CLI 不可用时的兜底

管理面 4 步走的是标准阿里云 OpenAPI（产品 `dataphin-public`，版本 `2023-06-30`，RPC 风格）。若 `aliyun` CLI 在当前环境不可用，可改用**任意 OpenAPI 客户端**（如 `alibabacloud_tea_openapi`）以相同 Action 调用：`ListDataServiceApps` / `GetDataServiceApp` / `ListAuthorizedDataServiceApiDetails` / `GetDataServiceApiDocument`。注意对象型参数（如 `ListQuery`）位于 `formData`，标量参数（如 `OpTenantId`）位于 `query`。
