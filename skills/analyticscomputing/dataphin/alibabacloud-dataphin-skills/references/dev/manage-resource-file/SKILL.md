---
name: manage-resource-file
description: |-
  管理 Dataphin 资源文件（上传 JAR/配置文件等 UDF 资源并创建/更新/查询/删除 Dataphin 资源）。
  当用户场景涉及上传资源文件、创建资源、UDF 所需 JAR、更新资源、查询资源版本、删除资源时进入。

  触发场景：
  - 上传 JAR/配置文件作为 Dataphin 资源（UDF 依赖的 JAR 包等）
  - 创建资源（create-resource）
  - 查询资源最新版本或指定版本
  - 更新资源（先 get-resource 再 update-resource）
  - 删除资源

  触发词：上传资源、资源文件、UDF 资源、JAR 资源、创建资源、create-resource、get-resource、get-resource-by-version、update-resource、delete-resource、get-file-storage-credential、ossutil、minio mc、ceph。

  关键限制：StorageType 决定上传工具（oss 用 ossutil，ceph 用 minio mc）；oss 凭证带临时 SecurityToken（sts-token），ceph 无；create-resource 的 compute-engine-type 仅 UDF 资源需指定引擎，非 UDF 用 NONE；19 位 ID 一律字符串传参。
---

# 资源文件管理 Skill

## 1. Scenario Description

场景：需要把本地文件（JAR 包、配置文件等）上传为 Dataphin 资源，供 UDF 或其他任务引用；以及对已有资源的查询、更新、删除。

### Architecture

```
用户请求 → 确认参数
  1) get-file-storage-credential 获取对象存储凭证（StorageType=oss/ceph）
  2) 按存储类型上传本地文件
     - oss：ossutil cp（带 sts-token）
     - ceph：minio mc 配置 alias 后 cp
  3) create-resource / update-resource / get-resource / delete-resource
```

### 涉及 Dataphin OpenAPI

- `GetFileStorageCredential` — 获取对象存储上传凭证
- `CreateResource` — 创建资源
- `GetResource` — 获取资源最新版本
- `GetResourceByVersion` — 获取资源指定版本
- `UpdateResource` — 更新资源
- `DeleteResource` — 删除资源

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

> **Security Rules:**
> - **NEVER** 读取、回显或打印凭证环境变量（禁止对 AccessKey ID / Secret 做任何输出或日志）
> - **NEVER** 要求用户在本会话或命令行直接输入 AK/SK
> - **NEVER** 使用 `aliyun configure set` 写入字面量凭证
> - **ONLY** 使用 `aliyun configure list` 检查凭证状态
>
> ```bash
> aliyun configure list
> ```
> 检查输出中是否存在有效 profile（AK、STS 或 OAuth 身份）。
>
> **如果没有有效 profile，请在此停止。**
> 1. 从 [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) 获取凭证
> 2. 在会话外配置（终端执行 `aliyun configure`，或在 shell profile 中设置环境变量）
> 3. 重新运行 `aliyun configure list` 确认有效后再继续

### Pre-check: Aliyun CLI plugin update required

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
>
> 执行前确认 CLI 与插件版本：
> ```bash
> aliyun version
> aliyun plugin list
> ```

## 5. RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `../../ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

本 skill 最小权限见 [../../ram-policies.md](../../ram-policies.md)。

## 6. IMPORTANT: Parameter Confirmation

创建/更新资源前，**任何未由用户显式提供的参数都必须主动询问用户**，禁止猜测或假设默认值（除 `--directory` 可默认 `/`、`--description`/`--comment` 未明确时可填 resource-name、非 UDF 资源 `--compute-engine-type` 可默认 NONE 外）。

### 必须获取的参数

| 参数 | 说明 | 是否必须询问 |
|------|------|-------------|
| `--tenant-id` | 租户 ID；优先从 profile 读取，未配置则必须询问 | 条件必须 |
| `--project-id` | 项目 ID；优先从 profile 读取，未配置则必须询问 | 条件必须 |
| `--resource-name` | 资源名称 | **必须** |
| `--resource-type` | 资源类型 | **必须** |
| `--directory` | 资源目录；未明确时默认 `/` | 可选确认 |
| `--storage-address` | 上传后的对象存储目标文件名（来自 get-file-storage-credential 的 ObjectName） | 由上传流程产出 |
| `--description` | 资源描述；未明确时默认填 resource-name | 可选确认 |
| `--comment` | 资源注释；未明确时默认填 resource-name | 可选确认 |
| `--compute-engine-type` | 计算引擎类型；仅 UDF 所需资源需指定，非 UDF 用 `NONE` | 条件必须 |

### 询问模板

当用户说"上传资源/创建资源"但未给出具体信息时，按以下顺序追问：

1. **环境确认**："请在 DEV 还是 PROD 环境执行？（默认 PROD）"
2. **项目确认**："请提供项目 ID 或项目名。"
3. **资源名称**："请提供资源名称。"
4. **资源类型**："请指定资源类型（如 Archive/Java/Python 等）。是否为 UDF 所需资源？"
5. **本地文件**："请提供要上传的本地文件路径。"
6. **目录**："资源存放目录？（默认 `/`）"
7. **描述/注释**："资源描述和注释？（未明确将默认填资源名）"
8. **引擎类型**（仅 UDF）："UDF 所需资源请指定计算引擎类型；非 UDF 将使用 `NONE`。"

> **在所有必填参数确认完整之前，禁止调用 `create-resource` / `update-resource`。**

## 7. Observability

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

本 Skill 属于 `alibabacloud-dataphin-skills` 套件，**继承父 Skill `alibabacloud-dataphin-skills` 的 session-id**，子 Skill 不再重新生成。

所有调用 Alibaba Cloud API 的 `aliyun dataphin-public` 命令必须携带：

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"
```

其中 `{session-id}` 替换为父 Skill 生成的 32 位小写十六进制字符串。

> 本地工具命令（`ossutil`、`mc`）不携带 `--user-agent`。

## 8. Core Workflow

### 步骤 0：会话级预检

由父 skill 完成 CLI/凭证预检（§4 + §8 Step 0）。

### 步骤 1：获取对象存储凭证

```bash
TENANT_ID="<tenant-id>"
PROJECT_ID="<project-id>"
ENV=PROD
USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"

aliyun dataphin-public get-file-storage-credential \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --purpose RESOURCE \
  --user-agent "$USER_AGENT" --format json \
  | jq '.StorageCredential | {
       StorageType, AccessId, AccessKey, Endpoint, Bucket, ObjectName, SecurityToken
     }'
```

> **SecurityToken 字段仅 oss 存在**，ceph 无该字段。**禁止回显 AccessId / AccessKey / SecurityToken 明文**，仅用变量承接。

### 步骤 2：按存储类型上传本地文件

> **工具安装**：ossutil / minio mc 的分平台（macOS / Linux / Windows）详细安装步骤见 [./references/ossutil-mc-install.md](./references/ossutil-mc-install.md)。

#### a. StorageType = oss

1. 检查 ossutil 是否安装（`ossutil version`），未安装则按 [ossutil-mc-install.md §一](./references/ossutil-mc-install.md) 安装（使用 v1，支持 `--sts-token`）。
2. 上传：

```bash
# 变量来自上一步（禁止打印）
# OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / OSS_ENDPOINT / OSS_BUCKET / OSS_OBJECT / OSS_STS_TOKEN

ossutil cp <local-file> oss://${OSS_BUCKET}/${OSS_OBJECT} \
  --access-key-id "$OSS_ACCESS_KEY_ID" \
  --access-key-secret "$OSS_ACCESS_KEY_SECRET" \
  --endpoint "$OSS_ENDPOINT" \
  --sts-token "$OSS_STS_TOKEN"
```

#### b. StorageType = ceph

1. 检查 minio mc 是否安装（`mc --version`），未安装则按 [ossutil-mc-install.md §二](./references/ossutil-mc-install.md) 安装。
2. 配置 alias：

```bash
mc alias set ceph "$CEPH_ENDPOINT" "$CEPH_ACCESS_KEY_ID" "$CEPH_ACCESS_KEY_SECRET"
```

3. 上传：

```bash
mc cp <local-file> ceph/${CEPH_BUCKET}/${CEPH_OBJECT}
```

### 步骤 3：创建 Dataphin 资源

```bash
aliyun dataphin-public create-resource \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --resource-name "<resource-name>" \
  --resource-type "<resource-type>" \
  --directory "/" \
  --storage-address "${OSS_OBJECT}" \
  --description "<resource-name>" \
  --comment "<resource-name>" \
  --compute-engine-type NONE \
  --user-agent "$USER_AGENT" --format json
```

- `--description` / `--comment` 未明确时填 `<resource-name>`。
- `--compute-engine-type`：仅 UDF 所需资源指定引擎，非 UDF 用 `NONE`。
- `--directory` 未明确时默认 `/`。
- `--storage-address` 用步骤 1/2 产出的目标文件名（ObjectName）。

## 9. 查询 / 更新 / 删除

### 9.1 获取资源最新版本

> `get-resource` 按**资源名**查询，不是 resource-id。

```bash
aliyun dataphin-public get-resource \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --resource-name "<resource-name>" \
  --user-agent "$USER_AGENT" --format json
```

### 9.2 获取资源指定版本

> `get-resource-by-version` 同样按**资源名**查询。
> 版本参数名是 `--version-id`（int，从 1 开始递增），**不是 `--version`**（[实测确认]：传 `--version` 直接报 `unknown flag: --version`，CLI 会提示 `Did you mean: --version-id`）。

```bash
aliyun dataphin-public get-resource-by-version \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --resource-name "<resource-name>" \
  --version-id <version-id-int> \
  --user-agent "$USER_AGENT" --format json
```

### 9.3 更新资源

> 必须先 `get-resource` 回读最新版本信息，拿到资源 `Id`，再 `update-resource`。
> `update-resource` 用 `--id`（int）定位，必填 `--resource-name` / `--description` / `--comment` / `--compute-engine-type` / `--storage-address`；
> 注意 update 的 `--compute-engine-type` 仅 `MAX_COMPUTE` / `HADOOP`（**无 NONE**），与 create 不同；
> update-resource 不接受 `--directory` / `--resource-type`。
>
> **`--storage-address` 是必填项，替换文件正是靠它完成**（[实测确认]）：不传直接报 `Error: --storage-address is required`；传入新上传的 `ObjectName` 后更新成功，版本自动递增（1→2），旧版本的 `StorageAddress` 被追加 `.bak` 后缀归档。因此“更新文件内容”的完整链路是**重新取凭证 → 上传新文件 → update-resource 携带新 ObjectName**，没有额外的平台侧替换入口。

```bash
# 1) 先查询拿 Id（get-resource 按资源名查）
aliyun dataphin-public get-resource \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --resource-name "<resource-name>" \
  --user-agent "$USER_AGENT" --format json
# 取 .ResourceInfo.Id

# 2) 替换文件：重复步骤 1~2 重新 get-file-storage-credential 并上传新文件
#    每次取凭证都会返回一个全新的一次性 ObjectName（UUID），需记下供下一步使用

# 3) 更新资源（update-resource 用 --id 定位，--storage-address 传上一步的新 ObjectName）
aliyun dataphin-public update-resource \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --id "<resource-id-int>" \
  --resource-name "<resource-name>" \
  --storage-address "<new-object-name>" \
  --description "<desc>" \
  --comment "<comment>" \
  --compute-engine-type MAX_COMPUTE \
  --user-agent "$USER_AGENT" --format json
```

> **换资源文件后无需 `update-udf`，SQL 行为即时切换**（[实测确认]）：同一条 UDF 查询在 `update-resource` 前后分别返回 V1 / V2 两种结果（星号掩码 → 短横线掩码），UDF 定义全程未改动。

### 9.4 删除资源

> `delete-resource` 用 `--resource-id`（int）定位，必填 `--comment`（提交备注）。

```bash
aliyun dataphin-public delete-resource \
  --dataphin-profile <p> --env $ENV \
  --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
  --resource-id "<resource-id-int>" \
  --comment "<删除备注>" \
  --user-agent "$USER_AGENT" --format json
```

删除后用 `get-resource` 反查，返回 `ResourceInfo` 全字段为 null 即确认删除成功。

## 10. Success Verification

端到端校验三步法：

1. **同步 Code:OK** — `create-resource` / `update-resource` / `delete-resource` 返回 `Code: "OK"` 或对应成功结构。`create-resource` 成功时资源 ID 在响应的 `Data` 字段。
2. **list/get 反查** — 创建后用 `get-resource` 回读，确认资源存在且字段正确。**必须核对返回的 `ProjectId` 与目标项目一致**，防止多租户/多 profile 场景下请求被路由到错误项目。
3. **版本核对** — 更新后用 `get-resource-by-version --version-id <新版本号>` 核对文件地址变化，**不要用 `get-resource`**（原因见下方说明）。

> **`StorageAddress` 回读会短于传入值，不是 bug**（[实测确认]）：`create-resource` 传入的 `--storage-address` 是 `get-file-storage-credential` 给的完整 `ObjectName`（形如 `<tenant-id>/<project-id>/<uuid>`），但 `get-resource` 回读时服务端会剥掉租户段，只返回 `<project-id>/<uuid>`。核对时按后缀匹配，不要因为两者不全等就判定写入失败并重试。

> **⚠️ 更新场景下 `get-resource` 的 `StorageAddress` 不跟随新版本**（[实测确认，两个资源上重复复现]）：`update-resource` 成功后，`get-resource`（不带版本）返回的 `Description` 等元信息已是新版，但 `StorageAddress` **仍指向初始版本的 ObjectName**（且不带 `.bak`）。此时若拿它与刚上传的新 `ObjectName` 做后缀匹配，**会误判为更新失败**。正确做法：
>
> | 查询方式 | 返回的 StorageAddress | 是否可用于核对新版 |
> |---|---|---|
> | `get-resource` | 初始版 uuid（无 `.bak`） | ❌ 会误判 |
> | `get-resource-by-version --version-id <新版本号>` | 新上传的 uuid | ✅ 以此为准 |
> | `get-resource-by-version --version-id <旧版本号>` | 旧版 uuid + `.bak` | ✅ 可确认归档 |

### 502 真假失败判定（写操作必读）

`create-resource` 返 `Dataphin.OpenAPI.BadGateway`（502）时，**错误码本身不携带任何可用信息**——同一个 502 在不同环境下含义完全相反（均为真机实测）：

| 环境 | `create-resource` 返回 | `get-resource` 反查 | 实际含义 |
|---|---|---|---|
| HDFS 不可写的 Hadoop 集群 | 502 | `ResourceInfo` 全字段 null | **真失败** |
| 正常的 Hadoop 集群 | 502 | `Id` / `Engine` / `ProjectId` / `StorageAddress` 字段齐全 | **假失败，已创建成功** |

**强制处理流程**：

1. 收到 502 后，**禁止直接重试**（假失败时重试会撞名称重复类报错，如 `DuplicateFileName`）。
2. 先跑 `get-resource --resource-name <name>` 反查：
   - `ResourceInfo.Id` 非 null → **已成功**，直接拿该 `Id` 继续后续步骤（如 `create-udf --ref-resource-id-list`），不要重建。
   - `ResourceInfo` 全 null → 真失败，才考虑重试（重试前先重新取凭证并重传）。
3. 同样适用于 `create-udf` / `update-resource` / `delete-resource`：任何 5xx 后都先反查再决定。

> **为何 Hadoop 下 502 频发**：推测服务端 HDFS 转存耗时较长触发网关超时，但后台仍在继续执行，因此出现“报错但成功”。此推论未经服务端日志证实，仅作为理解参考；不影响上述处理流程的必要性。

### MaxCompute 与 Hadoop 的机制差异（影响失败面）

实测发现两种引擎的资源登记路径不同：

| | MaxCompute | Hadoop |
|---|---|---|
| 对象存储的角色 | 基本即终点 | **仅为暂存**，服务端还会二次转存进 HDFS |
| `create-resource` 失败面 | 主要是元数据 / 权限 | 额外包含 **HDFS 写入失败**（`RegisterHdfsResourceFailedWithMessage`） |
| 隐式依赖 | 对象存储可达 | 额外依赖 Dataphin 服务端 ↔ Hadoop 集群链路健康 |

**结论：Hadoop 引擎下“对象存储上传 HTTP 200”完全不代表资源能创建成功。** 因此 Hadoop 路径需额外做 §12 第 9 条的连通性预检；而 MaxCompute 未观测到同步引擎写入（但也未证明它完全不碰引擎，UDF 最终能执行说明 JAR 在某个时点确实进了 MaxCompute）。

## 11. Command Tables

| 命令 | 用途 | 关键参数 |
|------|------|----------|
| `get-file-storage-credential` | 获取对象存储上传凭证 | `--purpose RESOURCE` |
| `create-resource` | 创建资源 | `--resource-name` `--resource-type` `--directory` `--storage-address` `--description` `--comment` `--compute-engine-type` |
| `get-resource` | 获取资源最新版本 | `--resource-name`（按资源名，非 id） |
| `get-resource-by-version` | 获取资源指定版本 | `--resource-name` `--version-id`（int，不是 `--version`） |
| `update-resource` | 更新资源（含换文件） | `--id`（int 定位）+ `--resource-name` `--storage-address`（必填，传新 ObjectName）`--description` `--comment` `--compute-engine-type`（仅 MAX_COMPUTE/HADOOP；不接受 directory/resource-type） |
| `delete-resource` | 删除资源 | `--resource-id`（int）+ `--comment` |

## 12. Best Practices

> **UDF 资源的基类与 SQL 类型随引擎而变，JAR 不可互用**（[实测确认，两种引擎均已端到端跑通]）：
>
> | 引擎 | UDF 基类 | 验证用 operator-type |
> |---|---|---|
> | MaxCompute | `com.aliyun.odps.udf.UDF` | `MaxCompute_SQL` |
> | Hadoop | `org.apache.hadoop.hive.ql.exec.UDF`（Hive UDF） | `Hive_SQL` |
>
> 两者基类不同，**同一个 JAR 不能跨引擎复用**。无需下载引擎 SDK 即可本地编译：手写一个空的同名同包桩基类仅用于 `javac`，**打包时排除桩类**（只装自己的 UDF 类），运行时由引擎提供真实基类；用 `javap` 校验 `extends` 与 `evaluate` 签名，用 `--release 8` 保证字节码兼容。

1. **先取凭证再上传** — `get-file-storage-credential` 返回的 AccessId/AccessKey/SecurityToken 均为临时凭证，过期需重新获取。
2. **StorageType 分支** — oss 用 `ossutil`（带 `--sts-token`），ceph 用 `minio mc`（先 `alias set`）。不要混用。
3. **不回显凭证** — 凭证只写入 shell 变量供工具使用，禁止 `echo`/日志打印。
4. **更新必先回读** — `update-resource` 前先 `get-resource` 拿最新版本信息，避免覆盖式更新丢字段。
5. **19 位 ID 字符串传参** — tenant-id / project-id / resource-id 等大整数一律字符串。
6. **UDF 才指定引擎** — `--compute-engine-type` 仅 UDF 所需资源指定，非 UDF 用 `NONE`。
7. **删除前确认下游引用** — 被引用的资源删除可能影响 UDF，删除前 HITL 确认。
8. **UDF 资源必须先做引擎前置检查**（[实测确认]）：`--compute-engine-type` 的 `MAX_COMPUTE` / `HADOOP` 必须与目标项目实际绑定的计算引擎一致。上传前按下列三步执行：

   ```bash
   # 1) 取项目绑定的 ComputeSourceId
   #    注：DEV_PROD 项目的 get-project 默认返 PROD 侧；要用 --env DEV 写资源时，
   #    真正相关的是 DEV 侧计算源，需用 list-compute-sources 按 BindProjectName=<project>_dev 找
   aliyun dataphin-public get-project --project-id "$PROJECT_ID" --tenant-id "$TENANT_ID" \
     --cli-query 'ProjectInfo.{Name:Name,ComputeSourceId:ComputeSourceId}'

   # 2) 判引擎类型（注意参数名是 --compute-source-id，不是 --id）
   aliyun dataphin-public get-compute-source --compute-source-id "$COMPUTE_SOURCE_ID" --tenant-id "$TENANT_ID" \
     --cli-query 'ComputeSourceInfo.Type'

   # 2b) [必备兜底] 上一步返 null 时，用 --type 反查计数定引擎
   for TY in MAX_COMPUTE HADOOP; do
     aliyun dataphin-public list-compute-sources --tenant-id "$TENANT_ID" --type $TY \
       --cli-query 'PageResult.TotalCount'
   done

   # 3) 仅当引擎为 HADOOP 时，追加连通性预检（见第 9 条）
   aliyun dataphin-public check-compute-source-connectivity-by-id \
     --compute-source-id "$COMPUTE_SOURCE_ID" --tenant-id "$TENANT_ID" --cli-query 'Data'
   ```

   - **`get-compute-source` 的 `Type` 不可靠**（[实测确认]）：多个租户下该字段返 `null`（实测两个 Hadoop 租户均为 null，而 MaxCompute 租户返 `"MAX_COMPUTE"`）。**不要因为 `Type` 为 null 就判定无法确认引擎**，改用 2b 的 `--type` 反查：哪个枚举的 `TotalCount > 0` 就是该租户在用的引擎。
   - 引擎既非 `MAX_COMPUTE` 也非 `HADOOP`（例如 SelectDB/Doris、Hologres、ADB）时，该项目**无法承载 Java UDF 资源**——停下并告知用户改选项目，不要硬传引擎类型去试。

9. **Hadoop 引擎：上传前做连通性预检，但只当预警不当闸门**（[实测确认]）：

   - `Data: true` → 继续，但**不承诺** `create-resource` 一定成功（实测出现过预检通过但 `create-resource` 仍报 502 的情况）。
   - 非 `true`（含 502 / 任何报错）→ **不要静默继续、也不要直接终止**，而是向用户告知原始错误码并说明风险：“继续上传可能在 `create-resource` 阶段失败，并在对象存储留下无法自动清理的孤立文件”，由用户 HITL 决定是否继续。
   - 引擎为 MaxCompute 时**跳过这一步**，不做无用调用。
   - 实测依据：不通的 CDP 集群预检返 502，后续 `create-resource` 确实失败；可用的 Hadoop 集群预检返 `Data: true`，后续全链路走通——两边结论都与最终结果一致。

10. **大文件可选：1 字节探针**：连通性预检探不到 HDFS 写权限、目录配额、引擎插件状态。上传大 JAR 前可先用一个极小临时文件跑完整的 `create-resource`，成功再删探针并上传真实文件——用 1 字节失败，而不是传完大文件才发现写不进去。

11. **失败会在对象存储留孤立文件**（[实测确认]）：`get-file-storage-credential` **不做后续步骤的可行性预检**，无论权限不足还是 HDFS 写入失败，凭证照发、上传照成功，而 `create-resource` 失败后已上传的对象**无任何自动清理机制**，Dataphin 侧也没有记录指向它。多次重试会持续累积垃圾。因此：失败后应在给用户的汇报里**明确列出遗留的 ObjectName**，提示需人工到对象存储清理。

12. **Python UDF 的 `--class-name` 模块名取「资源注册名」，不是本地文件名**（[实测确认]）：MaxCompute Python UDF 的 class-name 格式为 `<模块名>.<类名>`，其中模块名 = `create-resource` 时 `--resource-name` 去掉 `.py` 后缀，**与本地上传的文件名无关**。例如本地文件是 `mask_phone.py`、但注册名为 `mask_phone_udfverify.py` 时，必须写 `mask_phone_udfverify.MaskPhone`；写成 `mask_phone.MaskPhone` 会导致 SQL 执行期报 `ODPS-0123055: ImportError: No module named mask_phone`。

    该失败**不会体现在 `get-ad-hoc-task-result` 上**（它对「运行中」和「已失败」一律返回 `Code: OK` + 空 `Result`），必须用 `get-ad-hoc-task-log --sub-task-id 0 --offset 0` 看 `TaskStatus`（`FAILED`）与堆栈才能定位。UDF 验证阶段务必以 task-log 判定成败，不要只轮询 result。

## 13. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| 凭证过期 / 上传 403 | 临时 SecurityToken 已过期 | 重新调用 `get-file-storage-credential` |
| ossutil 找不到命令 | 未安装 ossutil | 按 [ossutil-mc-install.md](./references/ossutil-mc-install.md) §一 安装 |
| `mc` 找不到命令 | 未安装 minio mc | 按 [ossutil-mc-install.md](./references/ossutil-mc-install.md) §二 安装 |
| ceph alias 未配置 | 跳过了 `mc alias set` | 先 `mc alias set ceph ...` |
| create-resource 缺 `--compute-engine-type` | UDF 资源未指定引擎 | UDF 资源显式指定引擎，非 UDF 用 `NONE` |
| update-resource 覆盖丢字段 | 未先 `get-resource` 回读 | 先回读再在回读结果上更新 |
| UDF 资源引擎类型与项目不匹配 | 目标项目计算引擎非 MaxCompute/Hadoop | 按 §12 第 8 条做引擎前置检查，不匹配则换项目 |
| `get-resource` 回读 `StorageAddress` 比传入值短 | 服务端剥掉了租户段前缀，属正常行为 | 按后缀匹配核对，不要重试重传（见 §10 说明） |
| `update-resource` 后 `get-resource` 的 `StorageAddress` 还是旧 uuid | `get-resource` 的该字段不跟随新版本，属已知行为 | 改用 `get-resource-by-version --version-id <新版本号>` 核对，不要判定更新失败（见 §10 说明） |
| `Error: --storage-address is required`（update-resource） | `--storage-address` 是必填项，替换文件依赖它 | 先重新取凭证并上传新文件，再把新 `ObjectName` 传给 `update-resource`（见 §9.3） |
| `unknown flag: --version`（get-resource-by-version） | 参数名是 `--version-id`（int） | 改用 `--version-id <int>`，不要加引号（见 §9.2） |
| SQL 报 `ODPS-0123055: ImportError: No module named xxx` | Python UDF 的 `--class-name` 模块名写成了本地文件名，未对齐资源注册名 | 模块名取 `--resource-name` 去掉 `.py`，用 `update-udf --class-name` 修正（见 §12 第 12 条） |
| `DPN.Filter.NoPermission：您无此资源操作权限！`（HTTP **400**） | **项目成员层**缺失：当前账号不是目标项目成员（或无资源角色权限），与 RAM 无关 | 用 `list-project-members --env <ENV>` 查现有成员，请项目 Owner / SuperAdmin 添加并授权。注意：此错误下 `get-file-storage-credential` 仍会成功且上传能完成，孤立对象需手工清理 |
| HTTP **403** 或 ErrorCode 含 `Forbidden` | **RAM 层**缺失：AccessKey 未获授对应 OpenAPI 的调用权限，与项目成员无关 | 按 [../../ram-policies.md](../../ram-policies.md) 中 `manage-resource-file` 分组申请 6 个 Action（`GetFileStorageCredential`/`CreateResource`/`GetResource`/`GetResourceByVersion`/`UpdateResource`/`DeleteResource`），确认策略 Resource 范围覆盖目标租户 |
| `DPN.Resource.RegisterHdfsResourceFailedWithMessage：上传HDFS资源失败` | Hadoop 引擎下服务端向 HDFS 二次转存失败（报文会带 `HdfsStorageExecutor` 等插件信息） | 不是参数问题；查 Dataphin 服务端 ↔ Hadoop 集群的网络 / Kerberos / 引擎插件状态，并用 `check-compute-source-connectivity-by-id` 交叉验证 |
| `Dataphin.OpenAPI.BadGateway`（502） | 可能是真失败，**也可能是假失败（已创建成功）** | **禁止凭错误码下结论、禁止直接重试**，必须先 `get-resource` 反查（见 §10 “502 真假失败判定”） |

## Reference Links

- [CLI 安装指南](./references/cli-installation-guide.md)
- [ossutil / minio mc 安装指南](./references/ossutil-mc-install.md)
- [../../ram-policies.md](../../ram-policies.md)（套件级 RAM）
- [验收标准](./references/acceptance-criteria.md)
- [相关命令](./references/related-commands.md)
