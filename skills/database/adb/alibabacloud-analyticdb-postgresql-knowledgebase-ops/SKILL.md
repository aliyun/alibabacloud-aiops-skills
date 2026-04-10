---
name: alibabacloud-analyticdb-postgresql-knowledgebase-ops
description: |
  ADBPG Knowledge Base Management: Create knowledge bases, upload documents, search, Q&A.
  Triggers: "knowledge base", "document library", "document upload", "knowledge search", "RAG", "Q&A", "embedding", "ADBPG", "AnalyticDB PostgreSQL"
---

# ADBPG Knowledge Base Management

Build enterprise knowledge bases in three steps: **Create Knowledge Base → Upload Documents → Search & Q&A**

The system automatically handles document parsing, chunking, vectorization, and index building. Users only need to focus on business logic.

**Architecture**: `ADBPG Instance + Namespace + DocumentCollection + Vector Index + LLM Service`

## Core Concepts

- **Knowledge Base**: Container for documents, automatically manages vector indexes (corresponds to DocumentCollection in API)
- **Document**: Files uploaded to the knowledge base, supports PDF/Word/Markdown/HTML/JSON/CSV/images, etc.
- **Q&A**: Intelligent conversation based on knowledge base + large language model

---

## Environment Setup

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print credential material (including environment-based secrets)
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

### Verify CLI Credentials

```bash
aliyun gpdb describe-regions --user-agent AlibabaCloud-Agent-Skills
```

### Script dependencies (Python)

[`scripts/upload_document_local.py`](scripts/upload_document_local.py) uses the Alibaba Cloud Python SDK. Declare dependencies in [`requirements.txt`](requirements.txt). Install before running the script:

```bash
pip install -r requirements.txt
```

Requires **Python 3.7+** (same baseline as Alibaba Cloud SDK for Python).

---

## RAM Permissions

> **[MUST] RAM Permission Pre-check:** Before executing operations, verify current user has required permissions.
> Use `ram-permission-diagnose` skill to check permissions, then compare against [references/ram-policies.md](references/ram-policies.md).
> If any permission is missing, abort and prompt user.

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|------------------|-------------|---------------|
| biz-region-id | Required | Region ID | cn-hangzhou |
| db-instance-id | Required | Instance ID (format: gp-xxxxx) | - |
| manager-account | Required | Manager account name | - |
| manager-account-password | Required | Manager account password | - |
| namespace | Optional | Namespace name | public |
| namespace-password | Required | Namespace password | - |
| collection | Required | Knowledge base name | - |
| embedding-model | Optional | Embedding model | text-embedding-v4 |
| dimension | Optional | Vector dimension | 1024 |

> **Note**: If the knowledge base is created in a custom namespace, all subsequent operations must specify the same namespace parameter.

For interaction guidelines, smart defaults, and best practices, see [references/interaction-guidelines.md](references/interaction-guidelines.md).

> **Documentation placeholders:** CLI examples use strings like `<manager-account-password>` and `<namespace-password>`. Replace them with real values from the user; **never** commit or log real passwords in docs, tickets, or chat.

---

## Timeout Configuration

> **Timeout Rules:** All operations must complete within reasonable time limits.
>
> - **Standard operations**: ≤10 seconds (create/list/query)
> - **Upload document async**: No timeout limit (async job, poll every 5-10s)

**CLI Timeout Settings:**
```bash
# Add --ConnectTimeout and --ReadTimeout to all commands
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

**Python SDK (default credential chain + timeouts + User-Agent):**

Use `CredentialClient()` with no arguments so the SDK resolves credentials via the **default chain** (same sources as the CLI). Do not parse credential files or pass raw keys in skill code. Set `user_agent` and HTTP timeouts on `Config` (milliseconds).

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

## Core Workflow

### 1. Knowledge Base Management

#### Create Knowledge Base

**Pre-checks** (run in order; **not** silent idempotency):

- **Duplicate names:** If a create step is run again when the resource already exists, the API returns a **clear error** (e.g. conflict / already exists). **Do not** create duplicate resources; interpret **already-exists**-style errors as “this step is satisfied” only when the response clearly indicates the resource is present, then continue the workflow.
- **Retries / ClientToken:** For **network-level retries** (e.g. timeout), use **ClientToken** when the API or `aliyun gpdb` exposes it for that subcommand—check `aliyun gpdb <subcommand> --help`. The examples below omit it when the plugin does not list it globally.

```bash
# 1. Initialize vector database
aliyun gpdb init-vector-database \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Create namespace (naming rule: ns_{collection}, public is forbidden)
aliyun gpdb create-namespace \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Important**: CreateNamespace MUST be executed before CreateDocumentCollection

**Create knowledge base**:

```bash
# 3. Create knowledge base (in the previously created namespace)
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

#### List Knowledge Bases

```bash
aliyun gpdb list-document-collections \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### List Namespaces

```bash
aliyun gpdb list-namespaces \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 2. Document Management

#### Upload Document (Public URL)

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

#### Upload Document (Local File - SDK)

Local files use Python SDK `upload_document_async_advance`. **Do not** paste multi-line Python into the skill; use the packaged script only (default credential chain, `user_agent`, `Config` timeouts, and `RuntimeOptions` timeouts — see `scripts/upload_document_local.py`).

```bash
python3 scripts/upload_document_local.py \
  --region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --file /path/to/local/file.pdf
```

See [scripts/upload_document_local.py](scripts/upload_document_local.py).

#### Poll Upload Progress

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

#### List Documents

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

### 3. Search & Q&A

#### Search Knowledge Base

```bash
aliyun gpdb query-content \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_my_knowledge_base \
  --namespace-password '<namespace-password>' \
  --collection my_knowledge_base \
  --content "How to configure database parameters?" \
  --topk 10 \
  --rerank-factor 5 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Knowledge Base Q&A

```bash
aliyun gpdb chat-with-knowledge-base \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{"Model":"qwen-max","Messages":[{"Role":"user","Content":"User question"}]}' \
  --knowledge-params '{"SourceCollection":[{"Collection":"my_knowledge_base","Namespace":"ns_my_knowledge_base","NamespacePassword":"<namespace-password>","QueryParams":{"TopK":10}}]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Reference Links

| Document | Content |
|----------|---------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI Installation Guide |
| [references/ram-policies.md](references/ram-policies.md) | RAM Permissions List |
| [references/related-apis.md](references/related-apis.md) | Related APIs |
| [references/interaction-guidelines.md](references/interaction-guidelines.md) | Interaction Guidelines & Best Practices |
| [references/verification-method.md](references/verification-method.md) | Verification Method |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance Criteria |
| [references/SKILL.zh-CN.md](references/SKILL.zh-CN.md) | Chinese Version |
| [requirements.txt](requirements.txt) | Python deps for `scripts/` |
