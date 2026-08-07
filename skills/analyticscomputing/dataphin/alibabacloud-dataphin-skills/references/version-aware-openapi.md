# 版本感知的 2.0 OpenAPI 清单

> 本文档描述父 skill 如何**先确定环境（公共云 / 独立部署）**、**获取版本**、并**按调用渠道分流**给出当前客户支持的 2.0 OpenAPI 清单。数据文件为同级 [`config/openapi-2.0-versions.json`](./config/openapi-2.0-versions.json)。

## 0. 真值链（为什么需要它）

```
SDK 全量内部接口  ⊃  公共云网关已发布(POP)  ⊇  CLI 插件命令快照
```

- **各版本 2.0 接口全集**来自 `dataphin-openapi-sdk` 各分支 jar（`com.aliyuncs.dataphin_public.model.v20230630.*Request`）。
- **公共云网关已发布集**来自阿里云开放元数据 `api-docs.json`；CLI 插件命令就是它的快照（可能滞后几个，插件更新自愈）。
- 因此有两类接口：
  - **`cli_command`**：已在公共云网关发布 → 可用 `aliyun dataphin-public <kebab>` 调；
  - **`sdk_only`**：SDK 定义但**未在网关发布**（如 `GetServerVersion`、KG / Stream / Tenant / Finance 系列）→ **CLI 无任何入口**，只能泛化调用。

**已真机验证**：`--force` 不能让 CLI 调用未发布接口（PascalCase→`unchecked version`，kebab→`unknown command`）。sdk_only 只能走泛化调用 / CommonRequest。

## 1. Step 0 · 确定环境（分层自动判定，尽量零交互）

用户直接调 skill 时我们并不预知其为公共云还是独立部署。**类型永远由信号自动推断，绝不问"你是哪种类型"**。

> **[硬规则] 环境类型对用户完全不可见**：不做类型选择题；**问题文案里也不得出现"公共云 / 独立部署"字样或"region/endpoint 二选一"这类暴露类型二分的措辞**。第一问只要 AK/SK，类型自动判定后再中性追问下一项。

**首次使用 / profile 为空时的分步收集（严格按序，不暴露类型）**：

1. **第一问：只要 AK/SK。** 向用户索取 AccessKey ID + AccessKey Secret（不得同时提 region / endpoint / 公共云 / 独立部署）。
2. **自动判定（拿到 AK 后，不提问）**：按下面 #2 前缀 + #3 探测（首次默认 `cn-shanghai`）推断类型。
3. **按判定结果中性追问下一项**——**只说索取那一句，禁止解释原因 / 点出部署形态**（不得出现 公网 / 无法识别 / 私有部署 / 独立部署 / 公共云 等；"AccessKey"一词本身可以说）：
   - 判为公共云 → 只问 "你的 Dataphin 在哪个地域？例如 cn-shanghai / cn-hangzhou。" → `aliyun configure set --profile dataphin --mode AK --access-key-id <AK> --access-key-secret <SK> --region <region>`
   - 判为独立部署 → 只问 "请提供你的 Dataphin 服务地址（endpoint），例如 dataphin-openapi.xxx.com。" → `aliyun configure set --profile dataphin-standalone --mode AK --access-key-id <AK> --access-key-secret <SK> --endpoint <endpoint>`

> **反例（禁止）**："这个 AccessKey 在公网网关无法识别，说明你是私有部署……" —— 任何解释判定过程 / 点出部署形态的话都不许出现，直接光秃秃索取 endpoint。

**[硬规则] 以下判定信号纯属 Agent 内部推理，全程对用户不可见**：不得向用户复述、解释或征询任何判定依据（endpoint 主机名 / AK 前缀 / 探测结果 / "倾向公共云/独立部署"等）。Agent 静默按可信度从高到低推断，命中即定，仅在需要时中性追问缺失项（region 或 endpoint），不透出推断过程与结论类型。

1. **已配自定义 endpoint**：profile / 环境变量里 endpoint 主机名非 `*.aliyuncs.com`（如 `dataphin-openapi.poc.lydaas.com`）→ **独立部署**。
2. **AK 前缀启发式（零成本，不发请求）**：阿里云公共云 AccessKey 基本以 `LTAI` 开头；独立部署 AK 由 Dataphin 自签发，通常非 `LTAI`。`LTAI*`→倾向公共云，非 `LTAI`→倾向独立部署。
3. **廉价探测确认（权威，判 AK 归属）**：用当前 AK 对公共云默认 endpoint `dataphin-public.<region>.aliyuncs.com`（首次尚无 `region_id` 时**默认用 `cn-shanghai`**，探测只为验 AK 归属、与最终 region 无关）发一个已发布只读调用——
   - 通过鉴权（返回 OK 或业务错）→ **公共云**，确定。
   - `InvalidAccessKeyId`（公网 RAM 不认此 AK）→ **独立部署**。
   - 连不上 aliyuncs（网络隔离）→ 倾向独立部署，结合 #2 定论。
4. **仅当仍无法定论、或已判独立部署但用户尚未给 endpoint 时** → 才提示用户补 endpoint（对独立部署本就是连网关的硬前提，非额外打扰）。

> `LTAI` 前缀是强信号但非规范保证；#2 只作"倾向"，最终以 #3 探测为权威判据。
> 以上四条信号及其判定结论仅用于内部路由，**不得出现在给用户的任何回复中**。

**[硬规则] 环境锁定（一经确定，不可更换）**：

- **锁定时机**——满足任一条件即视为环境已确定并锁定，本会话内不可更换：
  - 用户显式指定了环境，或提供了 endpoint（= 独立部署）/ 仅提供 region（= 公共云）；
  - 复用了已有 profile（`dataphin` → 公共云；`dataphin-standalone` 或 endpoint 主机名非 `*.aliyuncs.com` → 独立部署）；
  - 上述 #1~#3 判定信号得出结论。
- **已指定则跳过判定**：环境已被用户显式指定或 profile 已明确时，**不再执行 #2 AK 前缀 / #3 探测等判定信号**，直接按指定环境执行。
- **#3 探测仅用于首次判定**：环境锁定后，**不得再对另一环境的网关发任何探测请求**（如已判独立部署后再探 `*.aliyuncs.com`，或已判公共云后再试自定义 endpoint）。
- **失败不改判**：锁定后，任何调用失败（`InvalidAccessKeyId` / 签名错 / 网络不通 / 超时 / 版本获取失败等）都**只在当前环境内排障**（检查 AK/SK、endpoint、OpTenantId、网络），排障无果则**直接向用户抛出该环境下的原始错误并终止**。**严禁**因失败重新触发环境判定，**严禁由公共云切到独立部署、或由独立部署切回公共云再试**。抛错文案只呈现原始错误与排障建议，同样不得暴露部署类型。

## 2. 确定环境后分两条路径

### 2.1 公共云 —— 不获取版本

- 恒为"始终最新"托管服务，不存在版本选择。
- **region 不由 skill 选**：取自 profile `region_id`，插件按 endpoint_map 自动解析为 `dataphin-public.<region>.aliyuncs.com`。
- 支持清单 ≡ 当前网关已发布集 ≡ 已安装 `dataphin-public` 插件命令集，全部按 `cli_command` 处理，**不做版本裁剪、不涉及 sdk_only**。
- `GetServerVersion` 未发布，公共云本就调不到、也不需要。

### 2.2 独立部署 —— 获取版本并裁剪（路由前**强制关卡**，不可跳过）

确认独立部署后、**在路由到任何子 Skill / 收集任何业务参数 / 执行任何接口之前**，必须按序完成：

0. **前置**：已配好 endpoint + AK/SK，且已收集 `OpTenantId`（租户 ID）——泛化调用与后续每条命令都强制要它（见父 SKILL.md §4.1）。
1. 走客户 endpoint 调 `GetServerVersion` → 版本串（如 `v6.3.0.964601`）。它是 `sdk_only`，**没有 CLI 命令**，只能泛化调用（见 §4）；**不要尝试 `aliyun dataphin-public get-server-version`（不存在该命令）**。
2. **归一**：去掉前缀 `v`，取前两段 `major.minor`。例：`v6.3.0.964601`→`6.3`；`6.2.2.1`→`6.2`。
3. **越界钳制**（见数据文件 `version_clamp`）：高于 `above_max`(6.3) 取 6.3；低于 `below_min`(6.0) 提示不支持并回落 6.0。
4. **获取失败兜底**（网络 / 签名 / `Unknown API` / 超时 / 权限）：**不得静默按最高版 6.3 假设继续**；改为中性直接询问「你的 Dataphin 是哪个版本？例如 6.0/6.1/6.2/6.3」，用用户给的版本继续第 5、6 步。**版本获取失败不构成改判环境的理由**——仍按独立部署继续（§1 环境锁定），不得回切公共云重试。
5. 载入数据文件，按 `min_version <= 归一版本` 过滤，得该版本**有效接口集**。
6. **版本闸门**：用户请求的目标接口（含子 Skill 背后 API 与临时直用的 cli_command，如 `CreateDataset`）若 `min_version > 归一版本`（不在有效集内）→ **立即停下**，告知「当前环境为 X 版本，不支持 <该功能>（需 Y+ 版本）」，**不得继续收参 / 执行**。仅在有效集内才放行。

## 3. 数据文件 schema 与消费

`config/openapi-2.0-versions.json`：

```json
{
  "api_version": "2023-06-30",
  "versions": ["6.0", "6.1", "6.2", "6.3"],
  "version_clamp": {"normalize": "major.minor", "above_max": "6.3", "below_min": "6.0"},
  "counts": {"6.0": 338, "6.1": 342, "6.2": 370, "6.3": 383, "gateway_published": 310, "cli_command_total": 310, "sdk_only_at_max": 73},
  "apis": [
    {"name": "GetServerVersion", "min_version": "6.0", "channel": "sdk_only"},
    {"name": "GetProject", "min_version": "6.0", "channel": "cli_command", "cli_command": "get-project"}
  ]
}
```

- `min_version`：接口首次出现的大版本（单调递增，零删减）。
- `channel`：`cli_command`（含 `cli_command` kebab 命令名）或 `sdk_only`。

**消费**：确定版本 `v` → `apis` 中取 `min_version <= v` → 按 `channel` 分流生成调用示例：

| channel | 生成的调用形态 |
|---|---|
| `cli_command` | `aliyun dataphin-public <cli_command> [--endpoint <ep> --skip-secure-verify]（独立部署时）--op-tenant-id <id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id}` |
| `sdk_only` | 泛化调用模板（§4）；**明确标注不能用 CLI / 不能用 `--force`** |

## 4. sdk_only 泛化调用模板（RPC V1 签名，真机验证）

`sdk_only` 接口无 CLI 入口（**不存在 `aliyun dataphin-public get-server-version` 命令，别尝试**），用签名后的原生 HTTP 调用。以下为**已在独立部署 POC 实测通过**的配方（`GetServerVersion` → `{"Data":"v6.3.0.964601","Code":"OK","Success":true}`）；`GetServerVersion` 是独立部署版本获取的唯一手段，调用失败时按 §2.2 第 4 步兜底询问用户版本：

- **方法**：`POST`；**鉴权与业务参数全部放 query string**，body 为空。
- **必填**：`OpTenantId`（租户 ID）。
- **签名**：`HMAC-SHA1`，`SignatureVersion=1.0`，`StringToSign = "POST&" + pe("/") + "&" + pe(sortedCanonQuery)`，key = `SK + "&"`。

```python
import hmac, hashlib, base64, uuid, datetime, urllib.parse, urllib.request, json

AK, SK   = "<AccessKeyId>", "<AccessKeySecret>"
HOST     = "dataphin-openapi.<env>.example.com"   # 独立部署自定义 endpoint
OP_TENANT = "<OpTenantId>"
ACTION   = "GetServerVersion"

pe = lambda s: urllib.parse.quote(str(s), safe='').replace('+','%20').replace('*','%2A').replace('%7E','~')
p = {
    "Action": ACTION, "Version": "2023-06-30", "Format": "JSON",
    "AccessKeyId": AK, "SignatureMethod": "HMAC-SHA1", "SignatureVersion": "1.0",
    "SignatureNonce": uuid.uuid4().hex,
    "Timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "OpTenantId": OP_TENANT,
    # …其它业务参数按各接口 --help / SDK Request 字段补充…
}
canon = "&".join(f"{pe(k)}={pe(p[k])}" for k in sorted(p))
sts   = "POST&" + pe("/") + "&" + pe(canon)                       # 关键：POST
p["Signature"] = base64.b64encode(hmac.new((SK+"&").encode(), sts.encode(), hashlib.sha1).digest()).decode()

url = "https://" + HOST + "/?" + urllib.parse.urlencode(p)        # 关键：参数放 query，POST 空 body
req = urllib.request.Request(url, method="POST")
print(json.loads(urllib.request.urlopen(req).read()))
```

> 公共云同名 sdk_only 接口无法这样调（网关未发布，会被网关拒）。sdk_only 泛化调用只适用于独立部署自有网关。
>
> POC 老网关认 RPC **V1**；更高版本独立部署网关是否需 V3 未验证——若 V1 报签名错可切 V3（`X-Acs-Signature-*` 头 + `ACS3-HMAC-SHA256`）。

## 5. 重建数据文件

> 重建由维护者在内部构建流程中执行（`build-openapi-version-index.sh` 依赖内部 maven 仓库与网关元数据，不随本 skill 分发）：

```bash
# 全量重建（跑 maven 拉 4 个版本 jar + 拉网关元数据）
bash build-openapi-version-index.sh

# 已有提取列表时快速重建（跳过 maven）
USE_CACHE=1 CACHE_DIR=<列表目录> bash build-openapi-version-index.sh
```

产出即 `config/openapi-2.0-versions.json`。校验点：`counts` 中 `6.0/6.1/6.2/6.3 = 338/342/370/383`、`gateway_published=310`、`sdk_only_at_max=73`；`GetServerVersion` 为 `sdk_only`、`GetProject` 为 `cli_command`。
