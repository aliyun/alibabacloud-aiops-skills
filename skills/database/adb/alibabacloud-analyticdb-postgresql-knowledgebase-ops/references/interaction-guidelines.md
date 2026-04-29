# Interaction Guidelines - ADBPG Knowledge Base Management

## Table of Contents

- [AskUserQuestion Usage Principles](#askuserquestion-usage-principles)
- [Information Collection Strategy](#information-collection-strategy)
- [Smart Defaults](#smart-defaults)
- [Best Practices](#best-practices)

---

## AskUserQuestion Usage Principles

AskUserQuestion should **only be used for limited option selections**, not for free-form input:

| Scenario | Usage |
|----------|-------|
| Chunking strategy selection (General/Technical/FAQ/Legal) | AskUserQuestion |
| Yes/No confirmation | AskUserQuestion |
| Guiding when user intent is unclear | AskUserQuestion |
| File paths, URLs, passwords, instance IDs, knowledge base names | **Collect via text conversation**, not AskUserQuestion |

> **Anti-pattern**: Don't put "Let me input" as an AskUserQuestion option. Users cannot enter free-form text in options. For free-form input, simply ask in your reply text.

---

## Information Collection Strategy

### When Creating a Knowledge Base

Collect via text conversation:

```
Please provide the following information:
1. Instance ID (format: gp-bp1234567890)
2. Manager account name
3. Manager account password
4. Namespace password (needed for upload/search/Q&A, recommend different from manager password)
5. Knowledge base name (lowercase letters and underscores)
```

### When Uploading Documents

Collect via text conversation:

```
Please provide the file source:
- Public URL: Give me the link directly
- Local file: Give me the file path, e.g., /Users/xxx/docs/manual.pdf
- Local directory: Give me the directory path, e.g., /Users/xxx/docs/, I'll scan supported files
```

---

## Smart Defaults

### Text Knowledge Base

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| Namespace | ns_{collection} | Prefixed with collection name, **public is forbidden** |
| EmbeddingModel | text-embedding-v4 | Recommended for text, 1024 dimensions |
| Dimension | 1024 | Vector dimension (text) |
| Metrics | cosine | Cosine similarity |
| TopK | 10 | Return 10 results |
| RerankFactor | 5 | Rerank factor, maximize retrieval precision |
| DocumentLoaderName | ADBPGLoader | Most format support |
| ChunkSize | 500 | Chunk size, works with reranker for precision |
| ChunkOverlap | 50 | Chunk overlap, ~10% of ChunkSize |
| Model (Q&A) | qwen-max | Qwen model |

### Image Knowledge Base

| Parameter | Value | Description |
|-----------|-------|-------------|
| EmbeddingModel | qwen3-vl-embedding | Multimodal vision model |
| Dimension | 2560 | Vision model default dimension |

> **Note**: Image and text knowledge bases cannot share the same Collection due to different EmbeddingModel and Dimension. Create them separately.

### Chunking Strategies

| Scenario | ChunkSize | ChunkOverlap | Suitable Documents |
|----------|-----------|--------------|-------------------|
| **General** (default) | 500 | 50 | Most documents |
| Technical docs | 800 | 100 | Manuals, API docs |
| FAQ / Short text | 256 | 30 | Q&A pairs, knowledge entries |
| Legal / Contracts | 1024 | 200 | Strong clause correlation |

---

## Best Practices

1. **Focus on user goals**, don't expose underlying concepts (namespaces, vector dimensions, HNSW params, etc.) unless user asks
2. **Execute query operations directly** without confirmation
3. **Show key parameters for modification operations** and confirm before execution, don't show all parameters
5. **Execute in sequence when creating knowledge base**: InitVectorDatabase → CreateNamespace → CreateDocumentCollection; **duplicate creates return explicit errors**—handle per [SKILL.md](../SKILL.md) **Create Knowledge Base** pre-checks (not silent idempotency); keep transparent to the user where possible
6. **Collect namespace password when creating knowledge base**, needed for upload/search/Q&A later, don't wait to ask
7. **Auto-poll upload progress after uploading**, query every 5-10 seconds, notify user when complete
8. **Use SDK for local file uploads**, auto-handles OSS transfer, transparent to user
9. **Remember parameters within session**: DBInstanceId, ManagerAccount, NamespacePassword etc., provide once, reuse throughout
10. **Auto-assemble JSON for Q&A**: User only provides question text, agent constructs ModelParams/KnowledgeParams
11. **Free-form input via text conversation, limited choices via AskUserQuestion**: paths, URLs, passwords should not use AskUserQuestion
12. Password parameters involve sensitive info, remind user about security
13. **All CLI commands MUST include** `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops`

---

## Quick Guide

| User Intent | Action |
|-------------|--------|
| "I want to create a knowledge base" | → Collect all info in one round → Auto init + create namespace + create knowledge base |
| "Upload a document" | → Collect file source via text → URL uses CLI / Local uses SDK → Auto-poll progress |
| "Search for xxx" | → Search knowledge base |
| "Ask about xxx" | → Knowledge base Q&A |
| "What's in the knowledge base" | → List documents |

---

## Auto-Create Instance When None Available

When user has no available ADBPG instance (or instance reports `Instance.NotSupportVector`):

1. Look for a skill that can create instances (keywords: `ADBPG` or `AnalyticDB PostgreSQL`)
2. If found, invoke that skill to create instance with recommended config:
   - Version: 7.0
   - Spec: 4C16G
   - Type: HighAvailability
   - Enable vector optimization
3. Wait for instance to be available, then continue knowledge base operations
