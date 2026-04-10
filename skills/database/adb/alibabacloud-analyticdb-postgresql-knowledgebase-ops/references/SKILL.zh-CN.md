---
name: alibabacloud-analyticdb-postgresql-knowledgebase-ops
description: |
  ADBPG 知识库管理：创建知识库、上传文档、检索、问答。
  Triggers: "知识库", "文档库", "文档上传", "知识检索", "RAG", "问答", "embedding", "ADBPG", "AnalyticDB PostgreSQL"
---

# ADBPG 知识库管理

三步构建企业知识库：**创建知识库 → 上传文档 → 检索问答**

系统自动处理文档解析、切片、向量化、索引构建，用户只需关注业务。

**Architecture**: `ADBPG Instance + Namespace + DocumentCollection + Vector Index + LLM Service`

> 英文版见 [SKILL.md](../SKILL.md)。

## 核心概念

- **知识库**: 文档的容器，自动管理向量索引（对应 API 中的 DocumentCollection）
- **文档**: 上传到知识库的文件，支持 PDF/Word/Markdown/HTML/JSON/CSV/图片等
- **问答**: 基于知识库 + 大模型的智能对答

---

## 环境准备

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [cli-installation-guide.md](cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print credential material（含基于环境变量的密钥）
> - **NEVER** ask the user to paste long-lived secrets directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

### 验证 CLI 凭证

```bash
aliyun gpdb describe-regions --user-agent AlibabaCloud-Agent-Skills
```

### 脚本依赖（Python）

[`scripts/upload_document_local.py`](../scripts/upload_document_local.py) 依赖阿里云 Python SDK。依赖声明见仓库根目录 [`requirements.txt`](../requirements.txt)。运行脚本前安装：

```bash
pip install -r requirements.txt
```

需要 **Python 3.7+**（与阿里云 Python SDK 一致）。

---

## RAM 权限

> **[MUST] RAM Permission Pre-check:** Before executing operations, verify current user has required permissions.
> Use `ram-permission-diagnose` skill to check permissions, then compare against [ram-policies.md](ram-policies.md).
> If any permission is missing, abort and prompt user.

---

## 参数确认

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| 参数 | 必需/可选 | 说明 | 默认值 |
|------|----------|------|--------|
| biz-region-id | 必需 | 地域 ID | cn-hangzhou |
| db-instance-id | 必需 | 实例 ID（格式 gp-xxxxx） | - |
| manager-account | 必需 | 管理账号 | - |
| manager-account-password | 必需 | 管理账号密码 | - |
| namespace | 可选 | 命名空间名称 | public |
| namespace-password | 必需 | 命名空间密码 | - |
| collection | 必需 | 知识库名称 | - |
| embedding-model | 可选 | 向量模型 | text-embedding-v4 |
| dimension | 可选 | 向量维度 | 1024 |

> **注意**：如果知识库创建在自定义命名空间，后续所有操作必须指定相同的命名空间参数。

交互规范、智能默认值和最佳实践详见 [interaction-guidelines.md](interaction-guidelines.md)。

> **文档占位符：** 命令示例中的 `<manager-account-password>`、`<namespace-password>` 须替换为用户真实口令；**禁止**在文档、工单或对话中粘贴或长期保存明文密码。

---

## 超时配置

> **超时规则**: 所有操作必须在合理的时间内完成。
>
> - **标准操作**: ≤10 秒（创建/列表/查询）
> - **异步上传文档**: 无超时限制（异步任务，每 5-10 秒轮询）

**CLI 超时设置**:
```bash
# 为所有命令添加 --ConnectTimeout 和 --ReadTimeout
aliyun gpdb create-document-collection \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --namespace ns_my_knowledge_base \
  --collection my_knowledge_base \
  --embedding-model text-embedding-v4 \
  --dimension 1024 \
  --user-agent AlibabaCloud-Agent-Skills \
  --ConnectTimeout 10 \
  --ReadTimeout 10
```

**Python SDK（默认凭证链 + 超时 + User-Agent）：**

使用无参 `CredentialClient()`，由 SDK 按**默认凭证链**解析（与 CLI 一致）；**不要**在技能代码中解析凭证文件或传入明文密钥。在 `Config` 上设置 `user_agent` 与 HTTP 超时（毫秒）。

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_gpdb20160503.client import Client
from alibabacloud_tea_openapi.models import Config

client = Client(Config(
    credential=CredentialClient(),
    region_id='cn-hangzhou',
    endpoint='gpdb.aliyuncs.com',
    connect_timeout=10000,
    read_timeout=10000,
    user_agent='AlibabaCloud-Agent-Skills',
))
```

---

## 核心工作流

### 一、知识库管理

#### 创建知识库

**前置检查**（按顺序执行；**并非**静默幂等）：

- **重名：** 若资源已存在再次执行创建，接口通常返回**明确错误**（冲突、已存在等）。**不得**重复创建同名资源；仅当响应明确表明资源已存在时，可将该错误视为**本步已满足**并继续后续流程，否则须排查。
- **重试与 ClientToken：** 针对**网络超时等重试**，若 API 或 `aliyun gpdb` 该子命令支持 **ClientToken**，应使用（见 `aliyun gpdb <子命令> --help`）。若插件未列出该参数，则以下示例不强行写死；以错误处理与帮助为准。

```bash
# 1. 初始化向量数据库
aliyun gpdb init-vector-database \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --user-agent AlibabaCloud-Agent-Skills

# 2. 创建命名空间（命名规则：ns_{collection}，禁止使用 public）
aliyun gpdb create-namespace \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **关键**：CreateNamespace 必须在 CreateDocumentCollection 之前执行

**创建知识库**：

```bash
# 3. 创建知识库（在先前创建的命名空间下）
aliyun gpdb create-document-collection \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --namespace ns_my_knowledge_base \
  --collection my_knowledge_base \
  --embedding-model text-embedding-v4 \
  --dimension 1024 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 查看知识库列表

```bash
aliyun gpdb list-document-collections \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 查看命名空间列表

```bash
aliyun gpdb list-namespaces \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 二、文档管理

#### 上传文档（公网 URL）

```bash
aliyun gpdb upload-document-async \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --file-name "user_manual.pdf" \
  --file-url "https://example.com/user_manual.pdf" \
  --document-loader-name ADBPGLoader \
  --chunk-size 500 \
  --chunk-overlap 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 上传文档（本地文件 - SDK）

本地文件使用 Python SDK `upload_document_async_advance`。**不要**在技能中粘贴多行 Python；仅使用封装脚本（默认凭证链、`user_agent`、`Config` 与 `RuntimeOptions` 超时，见 `scripts/upload_document_local.py`）：

```bash
python3 ../scripts/upload_document_local.py \
  --region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --file /path/to/local/file.pdf
```

见 [scripts/upload_document_local.py](../scripts/upload_document_local.py)。

#### 轮询上传进度

```bash
aliyun gpdb get-upload-document-job \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --job-id "job-xxxxx" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 查看文档列表

```bash
aliyun gpdb list-documents \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 三、检索与问答

#### 检索知识库

```bash
aliyun gpdb query-content \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --content "如何配置数据库参数？" \
  --topk 10 \
  --rerank-factor 5 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 知识库问答

```bash
aliyun gpdb chat-with-knowledge-base \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{"Model":"qwen-max","Messages":[{"Role":"user","Content":"用户问题"}]}' \
  --knowledge-params '{"SourceCollection":[{"Collection":"my_knowledge_base","Namespace":"ns_my_knowledge_base","NamespacePassword":"<namespace-password>","QueryParams":{"TopK":10}}]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## 参考链接

| 文档 | 内容 |
|------|------|
| [cli-installation-guide.md](cli-installation-guide.md) | CLI 安装指南 |
| [ram-policies.md](ram-policies.md) | RAM 权限清单 |
| [related-apis.md](related-apis.md) | 相关 API 列表 |
| [interaction-guidelines.md](interaction-guidelines.md) | 交互规范与最佳实践 |
| [verification-method.md](verification-method.md) | 验证方法 |
| [acceptance-criteria.md](acceptance-criteria.md) | 验收标准 |
| [../requirements.txt](../requirements.txt) | `scripts/` 的 Python 依赖 |
