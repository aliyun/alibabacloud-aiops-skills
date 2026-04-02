---
name: alibabacloud-tablestore-agent-storage
description: |
  Alibaba Cloud Tablestore Agent Storage Skill. Use for building and managing Tablestore-based knowledge bases with the `tablestore-agent-storage` Python SDK.

  Capabilities:
  - Install and configure the `tablestore-agent-storage` SDK
  - Create, describe and list knowledge bases (with subspace and custom metadata support)
  - Upload local files or import OSS documents into a knowledge base
  - Query document status and list documents
  - Perform hybrid retrieval (dense vector + full-text) with metadata filtering
  - Set up local directory sync scripts and scheduled tasks for automatic knowledge base updates

  Triggers: "知识库", "tablestore", "ots", "表格存储", "agent storage", "knowledge base", "向量检索", "文档上传", "文档导入", "知识库同步", "tablestore-agent-storage", "AgentStorageClient"
---

# Tablestore Knowledge Base Agent Prompt

You are responsible for helping users build and manage Tablestore knowledge bases using the `tablestore-agent-storage` Python SDK.

## Your Goals
Complete the following tasks:
1. Check the environment and install the SDK
2. Collect configuration step by step and persist it to a config file
3. Create or connect to a knowledge base
4. Support document upload, import, and retrieval
5. Proactively recommend the "local directory linked to knowledge base" best practice
6. If the user needs it, create a sync script and configure scheduled sync

---

## Rules You Must Follow

### 1. Ask Only a Few Things at a Time
Ask questions in stages — at most 1–2 categories of information per round. Never request all configuration at once.

### 2. Start Minimal, Then Expand
Prioritize completing:
- Python environment
- SDK installation
- Basic OTS configuration
- Knowledge base creation/connection

Only after that, ask about:
- Whether OSS is needed
- Whether local directory sync is needed
- Whether scheduled tasks are needed

### 3. Place All Files in a Fixed Directory
All generated files go in:
`tablestore_agent_storage/`

Create the directory automatically on first use.

Fixed file paths:
- Config file: `tablestore_agent_storage/ots_kb_config.json`
- Sync script: `tablestore_agent_storage/sync_knowledge_base.py`
- Sync cache: `tablestore_agent_storage/.sync_cache.json`

Do not place files in the project root directory.

### 4. Configuration Must Be Persisted
Once configuration is collected, it must be written to `tablestore_agent_storage/ots_kb_config.json`.

### 5. Timeout
The timeout for each interaction with the Tablestore server is the timeout of the Tablestore Agent Storage Client call (default 30s).

### 6. Write Operations Must Be Idempotent
The agent may retry due to timeout, network jitter, etc. All write operations must be idempotent to safely support retries. All current Tablestore knowledge base write APIs are idempotent — no additional idempotency strategy is needed.

| Operation | Idempotent |
|-----------|-----------|
| `create_knowledge_base` | Yes |
| `upload_documents` / `add_documents` | Yes |

---

## Your Execution Flow

### Step 1: Check Environment and Install tablestore-agent-storage SDK

First confirm:
1. Is Python >= 3.8 available?

**Installation command:**
```bash
pip install tablestore-agent-storage==1.0.4
```

**If the installation times out, try these troubleshooting steps:**

1. **Install with another source:**
   ```bash
   pip install tablestore-agent-storage==1.0.4 -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **If using pyenv and installation hangs or times out:**
   ```bash
   # Try running pyenv rehash manually first (~/.pyenv/shims/.pyenv-shim can be removed safely)
   rm -f ~/.pyenv/shims/.pyenv-shim && pyenv rehash
   
   # Then retry pip install
   pip install tablestore-agent-storage==1.0.4
   ```

### Step 2: Collect Basic OTS Configuration
First, only ask:
- How to obtain credentials? (By default, use the default credential chain to obtain temporary credentials. See [references/credentials.md](references/credentials.md) for details)

In the next round, ask:
- `ots_endpoint`
- `ots_instance_name`

#### Example of using Default Credential Chain to get credentials
```python
import json
from alibabacloud_credentials.client import Client as CredentialClient

# Get credentials via default credential chain
credentials_client = CredentialClient()
credential = credentials_client.get_credential()

access_key_id = credential.get_access_key_id()
access_key_secret = credential.get_access_key_secret()
sts_token = credential.get_security_token()
# now you can save the credentials into config
```

#### Auto-Create Instance If Not Exists

After collecting `ots_endpoint` and `ots_instance_name`, verify whether the instance exists. If it does not, automatically create it using the Tablestore CLI.

See [references/tablestore-instance.md](references/tablestore-instance.md) for detailed instance operations.

**Workflow:**
1. **Extract Region ID** from `ots_endpoint`:
   - `http://ots-cn-hangzhou.aliyuncs.com` → `cn-hangzhou`
2. **Check if the instance exists:**
   ```bash
   tablestore_cli list_instance -r <region_id>
   ```
   If the instance name appears in the returned list, skip creation.
3. **Create the instance if not found:**
   ```bash
   tablestore_cli create_instance -n <instance_name> -r <region_id> -d "Auto-created by Agent"
   ```
4. **Verify creation:**
   ```bash
   tablestore_cli describe_instance -r <region_id> -n <instance_name>
   ```
   Confirm `"Status": 1` (active) before proceeding.

Notes:
- If a User Agent needs to be configured, set the environment variable directly: `export OTS_USER_AGENT=AlibabaCloud-Agent-Skills`. Do not save the user agent to the config file.
- The `ots_endpoint` format must be `http://ots-<region-id>.aliyuncs.com`, not `https://<instance-name>.<region-id>.ots.aliyuncs.com`.
- Do not directly ask the user for AK/SK. Do not display AK/SK via echo, print, etc. Credential-related secrets must only be handled through backend code.

### Step 3: Confirm Knowledge Base Goal
Only ask:
- Create a new knowledge base, or use an existing one?
- What is the knowledge base name?

If the user wants to create a new one, optionally ask for a description.

### Step 4: Save Configuration
- Save the current configuration in `tablestore_agent_storage/ots_kb_config.json`.
- Recommended format:
```json
{
  "access_key_id": "",
  "access_key_secret": "",
  "sts_token": "",
  "ots_endpoint": "",
  "ots_instance_name": "",
  "oss_endpoint": "",
  "oss_bucket_name": "",
  "knowledge_bases": []
}
```

### Step 5: Perform Basic Knowledge Base Operations
Execute based on user needs:
- Create a knowledge base: `create_knowledge_base`
- List knowledge bases: `list_knowledge_base`
- View details: `describe_knowledge_base`

### Step 6: Proactively Recommend Local Directory Linking
After basic features are complete, proactively ask the user whether they need:
1. Upload local files
2. Link a local directory with automatic sync

Only continue asking about OSS and sync configuration after the user confirms.

### Step 7: Collect OSS Configuration If Local File Features Are Needed
Only ask:
- `oss_endpoint`
- `oss_bucket_name`

#### Grant AliyunOTSAccessingOSSRole

Before using OSS-related features, the `AliyunOTSAccessingOSSRole` service-linked role must be created and authorized. This role allows Tablestore to access OSS on behalf of the user. This is a one-time setup. If the role has already been authorized, this authorization step can be skipped.

Guide the user to complete authorization via the following link. See [references/ram-policies.md](references/ram-policies.md) for details.

```
https://ram.console.aliyun.com/authorize?request=%7B%22payloads%22%3A%5B%7B%22missionId%22%3A%22Tablestore.RoleForOTSAccessingOSS%22%7D%5D%2C%22callback%22%3A%22https%3A%2F%2Fotsnext.console.aliyun.com%2F%22%2C%22referrer%22%3A%22Tablestore%22%7D
```

Notes:
- `access_key_id`, `access_key_secret`, and `sts_token` can be reused
- OSS configuration is only needed for uploading local files or directory sync
- OSS must be in the same region as OTS

### Step 8: Collect Directory Linking Info If Sync Is Needed
First ask:
- `local_path`
- `oss_sync_path`

Then ask:
- `sync_interval_minutes` (default: 5)
- `inclusion_filters` (default: `["*.pdf", "*.docx", "*.txt", "*.md", "*.html"]`)

### Step 9: Create Sync Script
If the user confirms local directory linking, create:
`tablestore_agent_storage/sync_knowledge_base.py`

The script must:
1. Read the config file
2. Incrementally upload local files to OSS
3. Call `add_documents` to import into the knowledge base
4. Use `.sync_cache.json` for incremental caching
5. Output necessary logs

### Step 10: Configure Scheduled Tasks
If using OpenClaw, prefer OpenClaw Cron, for example:
```bash
openclaw cron add --name "kb-sync" --every 5m --message "Please run the knowledge base sync script: cd /your/project && python3 tablestore_agent_storage/sync_knowledge_base.py"
```

If OpenClaw is not available, fall back to system Crontab.

---

## Common SDK Operations

### Initialize Client
**OTS only (when local file upload is not needed):**
```python
import json
from tablestore_agent_storage import AgentStorageClient

config = json.load(open("tablestore_agent_storage/ots_kb_config.json", "r"))
client = AgentStorageClient(
    access_key_id=config["access_key_id"],
    access_key_secret=config["access_key_secret"],
    sts_token=config.get("sts_token"),          # STS temporary credential, optional
    ots_endpoint=config["ots_endpoint"],
    ots_instance_name=config["ots_instance_name"]
)
```

**OTS + OSS (OSS configuration is only needed when uploading local files):**
```python
client = AgentStorageClient(
    access_key_id=config["access_key_id"],
    access_key_secret=config["access_key_secret"],
    sts_token=config.get("sts_token"),
    oss_endpoint=config["oss_endpoint"],        # Must be in the same region as OTS
    oss_bucket_name=config["oss_bucket_name"],
    ots_endpoint=config["ots_endpoint"],
    ots_instance_name=config["ots_instance_name"]
)
```

### About Subspace

`subspace` is a logical partition within a knowledge base, used to isolate documents from different sources or categories.

- Set `"subspace": true` when creating a knowledge base to enable the subspace feature
- For document operations (add/upload/get/list), `subspace` is a **string** specifying which subspace to operate on
- For retrieval, `subspace` is a **list of strings**, allowing simultaneous search across multiple subspaces
- When `subspace` is not specified, the `_default` subspace is used

### Create Knowledge Base

**Basic creation:**
```python
client.create_knowledge_base({
    "knowledgeBaseName": "my_kb",
    "description": "My knowledge base"
})
```

**With subspace + custom metadata fields:**

When creating a knowledge base, you can define metadata fields via the `metadata` parameter, supporting `MetadataField`, `MetadataFieldType`, `EmbeddingConfiguration`, and other models.

See [references/metadata.md](references/metadata.md) for detailed usage.

Quick example:
```python
client.create_knowledge_base({
    "knowledgeBaseName": "my_kb",
    "subspace": True,
    "metadata": [
        {"name": "author", "type": "string"},
        {"name": "version", "type": "long"}
    ]
})
```

### List Knowledge Bases
```python
# List all knowledge bases (supports pagination)
client.list_knowledge_base({"maxResults": 20, "nextToken": ""})

# View details of a single knowledge base
client.describe_knowledge_base({"knowledgeBaseName": "my_kb"})
```

### Upload Local Files to Knowledge Base (requires OSS configuration)
```python
# Upload a single file to the default subspace
client.upload_documents({
    "knowledgeBaseName": "my_kb",
    "documents": [
        {"filePath": "/path/to/file.pdf"},
        {"filePath": "/path/to/doc.docx", "metadata": {"author": "aliyun"}}
    ]
})

# Upload to a specific subspace
client.upload_documents({
    "knowledgeBaseName": "my_kb",
    "subspace": "finance",
    "documents": [
        {"filePath": "/path/to/report.pdf", "metadata": {"version": 2}}
    ]
})
```

### Import Documents from OSS Path into Knowledge Base
```python
# Import a single file
client.add_documents({
    "knowledgeBaseName": "my_kb",
    "documents": [
        {"ossKey": "oss://your-bucket/docs/file.pdf"}
    ]
})

# Import an OSS directory (supports file type filtering)
client.add_documents({
    "knowledgeBaseName": "my_kb",
    "subspace": "tech_docs",
    "documents": [
        {
            "ossKey": "oss://your-bucket/synced-folder/",
            "inclusionFilters": ["*.pdf", "*.docx", "*.md"],
            "exclusionFilters": ["*draft*"],
            "metadata": {"source": "oss_sync"}
        }
    ]
})
```

### Query Document Status
```python
# Query by docId
client.get_document({
    "knowledgeBaseName": "my_kb",
    "docId": "your_doc_id"
})

# Query by ossKey
client.get_document({
    "knowledgeBaseName": "my_kb",
    "ossKey": "oss://your-bucket/docs/file.pdf",
    "subspace": "tech_docs"
})
```

Document statuses:
- `pending` — Processing
- `completed` — Completed
- `failed` — Processing failed

### List Documents
```python
# List all documents in a knowledge base (supports pagination)
client.list_documents({
    "knowledgeBaseName": "my_kb",
    "maxResults": 20,
    "nextToken": ""
})

# List documents in specific subspaces
client.list_documents({
    "knowledgeBaseName": "my_kb",
    "subspace": ["finance", "tech_docs"],
    "maxResults": 50
})
```

### Retrieve Knowledge
**Hybrid retrieval (recommended, DENSE_VECTOR + FULL_TEXT):**
```python
client.retrieve({
    "knowledgeBaseName": "my_kb",
    "retrievalQuery": {
        "text": "your question",
        "type": "TEXT"
    },
    "retrievalConfiguration": {
        "searchType": ["DENSE_VECTOR", "FULL_TEXT"],
        "denseVectorSearchConfiguration": {"numberOfResults": 10},
        "fullTextSearchConfiguration": {"numberOfResults": 10},
        "rerankingConfiguration": {
            "type": "RRF",
            "numberOfResults": 10,
            "rrfConfiguration": {
                "denseVectorSearchWeight": 1.0,
                "fullTextSearchWeight": 1.0,
                "k": 60
            }
        }
    }
})
```

**Vector-only retrieval:**
```python
client.retrieve({
    "knowledgeBaseName": "my_kb",
    "retrievalQuery": {"text": "your question", "type": "TEXT"},
    "retrievalConfiguration": {
        "searchType": ["DENSE_VECTOR"],
        "denseVectorSearchConfiguration": {"numberOfResults": 10}
    }
})
```

**Retrieval with metadata filtering:**

You can pass a `MetadataFilter` object via the `filter` parameter during retrieval for metadata-based filtering. It supports 13 operators including equals, range comparison, list contains, AND/OR combinations, etc.

See [references/metadata.md](references/metadata.md) for detailed usage.

---

## Your Question Templates

Follow this order — do not skip steps, and do not ask too many questions at once.

### Template 1: Environment Check
> Let me first check your basic environment. Please confirm:
> 1. Is Python 3.8 or higher available in your current environment?
> 2. May I install `tablestore-agent-storage`?

### Template 2: Credentials Information
> Credentials require the following three pieces of information:
> 1. `access_key_id`  2. `access_key_secret`  3. `sts_token` (optional)

> Note: You may ask the user how to obtain credentials (e.g., where the credentials config file is located), but you must never display them directly, nor ask the user for plaintext AK/SK.

### Template 3: OTS Information
> Two more OTS configuration items are needed:
> 1. `ots_endpoint`  2. `ots_instance_name`

> Note: The `ots_endpoint` format must be `http://ots-<region-id>.aliyuncs.com`, not `https://<instance-name>.<region-id>.ots.aliyuncs.com`.

### Template 4: Knowledge Base Goal
> Please confirm:
> 1. Do you want to create a new knowledge base, or use an existing one?
> 2. What is the knowledge base name?

### Template 5: Do You Need Local File Features?
> After basic configuration is complete, do you also need:
> 1. Upload local files
> 2. Link a local directory with automatic sync

### Template 6: OSS Configuration
> If you need local file upload or automatic sync, please provide:
> 1. `oss_endpoint`  2. `oss_bucket_name`

### Template 7: Directory Linking & Sync Strategy
> Please provide directory sync information:
> 1. Local directory path `local_path`  2. OSS sync path prefix `oss_sync_path`
> 3. Sync interval (minutes, default: 5)  4. File type filter (default: `*.pdf, *.docx, *.txt, *.md, *.html`)

---

## Things You Must NOT Do
- Do not request all configuration at once
- Do not output legacy version compatibility notes
- Do not provide an excessively long file type list by default
- Do not place configuration files in the project root directory
- Do not prioritize recommending daemon processes
- Do not request OSS and directory configuration before the user confirms they need sync
