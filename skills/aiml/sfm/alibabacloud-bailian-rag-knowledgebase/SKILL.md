---
name: alibabacloud-bailian-rag-knowledgebase
description: "Alibaba Cloud Bailian Knowledge Base Retrieval Tool. Use HTTPS API to query and retrieve knowledge base content. Use when: User needs to query knowledge base, retrieve document content, or answer questions based on knowledge base. Prerequisites: (1) Configure DashScope API Key (2) Activate Bailian Knowledge Base service."
---

# Bailian Knowledge Base Retrieval

This Skill provides query and retrieval capabilities for Alibaba Cloud Bailian Knowledge Base via HTTPS API.

## API Key Security Management

Scripts automatically handle key retrieval via `api_key.py`. The Agent does not need to and should not manually extract, set, or pass API Key values.

- **Key retrieval is automated**: Scripts internally call `api_key.py` to automatically obtain keys from config files/environment variables. The Agent only needs to run the script command.
- **Never hardcode any form of key**: Including `api_key = "sk-..."`, `export DASHSCOPE_API_KEY="sk-..."`, and assigning keys in shell scripts.
- **Never extract keys from CLI output**: The Agent must not write key values into any script, variable, or file.
- **Never expose keys in any output**: Including generated scripts, shell commands, log files, and terminal output containing strings starting with `sk-`.
- **Never read or print keys from config files**: Do not use `cat`, `jq`, `python -c`, or other commands to read and output API Key values.
- **Mandatory self-check before task completion**: Run `grep -rn "sk-" <output_directory>/` to check all output files; if any strings starting with `sk-` are found (excluding `sk-xxx` placeholders), delete the affected files and regenerate.

## 🚀 Initial Setup (Required for First-time Use)

### 1. Configure API Key

API Keys are managed by the unified `scripts/api_key.py` module, with the following retrieval priority:
1. Alibaba Cloud CLI config `~/.aliyun/config.json` current profile's `dashscope.api_key`
2. Environment variable `DASHSCOPE_API_KEY`
3. Auto-create and save when Alibaba Cloud CLI is available (`generate_api_key()`)

```python
# All scripts use this unified approach
from api_key import get_api_key
api_key = get_api_key()  # Returns str, raises ValueError if not found
```

Manual environment variable configuration:
```bash
export DASHSCOPE_API_KEY=sk-xxx
```

| Item | Description |
|------|-------------|
| **Key Format** | `sk-xxx` (standard DashScope API Key) |
| **Not Supported** | `sk-sp-xxx` (Coding Plan Key, does not support knowledge base services) |
| **Get Key** | https://bailian.console.aliyun.com/cn-beijing/?tab=app#/api-key |

### Alibaba Cloud CLI Configuration (API Key Auto-Create/Delete)

The `scripts/api_key.py` module creates and deletes API Keys via `aliyun modelstudio` commands. Complete the following setup before use:

**1. Update Plugins**

```bash
# Update plugins to latest version
aliyun plugin update
```

**2. Install ModelStudio Plugin** (if not already installed)

```bash
aliyun plugin install --names aliyun-cli-modelstudio --enable-pre
```

**CLI Commands Used**:

| Command | Purpose | Called From |
|---------|---------|-------------|
| `aliyun modelstudio list-workspaces` | Get Bailian Workspace ID | `api_key.py: _get_workspace_id()` |
| `aliyun modelstudio create-api-key` | Create DashScope API Key | `api_key.py: generate_api_key()` |
| `aliyun modelstudio delete-api-key` | Delete cloud API Key | `api_key.py: _delete_cloud_api_key()` |

### 2. Important Prerequisite: Activate Bailian Knowledge Base Service

**Before using this skill, you must first activate the knowledge base service in the Alibaba Cloud Bailian console!**

1. Visit [Bailian Knowledge Base page](https://bailian.console.aliyun.com/cn-beijing/?tab=app#/knowledge-base)
2. Click the **"Activate Now"** button
3. Confirm activation and wait for the service to take effect (usually 1-2 minutes)

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) and export it as `SKILL_SESSION_ID`. This value must remain constant for the entire skill session.

Every `aliyun` CLI command and HTTPS API call must include a `User-Agent` identifier for traceability.

### User-Agent Format

```
AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase/{session-id}
```

- `{session-id}` = value of `SKILL_SESSION_ID` environment variable (32-char lowercase hex string)
- Scripts read it via `os.environ.get("SKILL_SESSION_ID", "")`; if empty, generate one with `secrets.token_hex(16)`

### Per-Command --user-agent (CLI)

Every `aliyun modelstudio` business command MUST carry `--user-agent` on the command line:

```bash
aliyun modelstudio list-workspaces --region cn-beijing \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase/{session-id}"
```

> **Prohibited**: Do NOT set User-Agent via global configuration commands. Only per-command `--user-agent` is allowed.

### HTTPS User-Agent Header

All HTTPS API requests set the `User-Agent` HTTP header:

```python
"User-Agent": f"AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase/{session_id}"
```

### Applied Locations

| Location | Mechanism |
|----------|----------|
| `scripts/list_indices.py` | HTTPS `User-Agent` header via `_get_user_agent()` |
| `scripts/retrieve.py` | HTTPS `User-Agent` header via `_get_user_agent()` |
| `scripts/api_key.py` → `_get_workspace_id()` | `aliyun modelstudio list-workspaces --user-agent ...` |
| `scripts/api_key.py` → `generate_api_key()` | `aliyun modelstudio create-api-key --user-agent ...` |
| `scripts/api_key.py` → `_delete_cloud_api_key()` | `aliyun modelstudio delete-api-key --user-agent ...` |

## Available Scripts

All scripts are located in the `scripts/` directory:

| Script | Purpose | Parameters |
|--------|---------|------------|
| `api_key.py` | API Key management (get, create, delete) | - |
| `list_indices.py` | Query knowledge base list | `[page_number] [page_size]` |
| `retrieve.py` | Retrieve from specified knowledge base | `index_id query [top_n]` |

## Workflow

### Step 1: Query Knowledge Base List

Run `scripts/list_indices.py` to get all available knowledge bases:

```bash
python3 scripts/list_indices.py
```

Return format:
```json
[
  {
    "id": "qf91w6402d",
    "name": "Product Documentation",
    "description": "Contains product user manuals, API documentation, etc."
  },
  {
    "id": "ip93d2pyvz",
    "name": "Customer Service Q&A",
    "description": "FAQ, customer service scripts"
  }
]
```

**Pagination:** page_number starts from 1 (default), page_size defaults to 10. If current page is not fully retrieved, continue to retrieve next page:
```bash
python3 scripts/list_indices.py 2 10
```

### Step 2: Intelligent Knowledge Base Selection

Based on the user's question and knowledge base descriptions, select **1-3 most relevant knowledge bases** for retrieval.

Selection Strategy:
- Match keywords (keywords in question vs knowledge base name/description)
- Prioritize knowledge bases that explicitly contain relevant fields in their descriptions
- If uncertain, select all or let user manually select

### Step 3: Execute Retrieval

For each selected knowledge base, run `scripts/retrieve.py index_id query [top_n]`:

```bash
python3 scripts/retrieve.py lj3hgbq60t "java" 5
```

Parameters:
- `index_id` (required): Knowledge base ID
- `query` (required): Search query text
- `top_n` (optional): Number of top results to return, default 5, max 20

The retrieve API uses the following configuration:
- `dense_similarity_top_k`: 100
- `sparse_similarity_top_k`: 100
- `enable_reranking`: true
- `rerank`: qwen3-rerank-hybrid with similar mode

Return format, content inside each chunk represents chunk content, doc_name represents source document, score represents match score, title represents chunk section title:
```json
{
  "indexId": "lj3hgbq60t",
  "chunks": [
    {
      "content": "Document chunk content...",
      "score": 0.6040189862251282,
      "doc_name": "example-doc.pdf",
      "title": "Section Title"
    }
  ]
}
```

### Step 4: Integrate Answer

Based on retrieval results:
1. Sort by relevance (score descending)
2. Extract key information
3. Organize answer in natural language
4. Please annotate the information source at the end of the generated answer (knowledge base name; document name; section name), can reference multiple documents and sections.

## Common Errors

### 401 Unauthorized
```json
{"code": "InvalidApiKey", "message": "Invalid API-KEY"}
```
API Key is incorrect or not configured. Guide user to check their API Key configuration.

### 403 Forbidden
```json
{"code": "Forbidden", "message": "Service not activated"}
```
User has not activated the Bailian Knowledge Base service. Guide user to activate it.

## Usage Example

**User:** "What authentication methods does our product support?"

**Flow:**
1. Query knowledge base → Returns 3 knowledge bases
2. Select knowledge base → "Product Documentation" (most relevant)
3. Retrieve → Get authentication-related document chunks
4. Answer → "According to product documentation, OAuth2.0, SAML, and API Key authentication methods are supported..."

## Notes

- API Key is automatically retrieved by scripts, Agent should never handle key values directly
- When retrieving from multiple knowledge bases, merge results and deduplicate
- Sort retrieval results by score, prioritize high-relevance content

**API Key Auto-Retrieval Flow**:
1. Read `~/.aliyun/config.json` current profile's `dashscope.api_key` → Return if found
2. Read environment variable `DASHSCOPE_API_KEY` → Return if found
3. Alibaba Cloud CLI available → Auto-create via `generate_api_key()` and save to config
4. All above fail → Error with setup instructions
