# Related APIs - ADBPG Knowledge Base Management

This document lists all APIs and CLI commands involved in ADBPG Knowledge Base Management.

## API List

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| GPDB | `aliyun gpdb describe-regions` | DescribeRegions | Query available regions |
| GPDB | `aliyun gpdb describe-dbinstances` | DescribeDBInstances | Query instance list |
| GPDB | `aliyun gpdb init-vector-database` | InitVectorDatabase | Initialize vector database |
| GPDB | `aliyun gpdb create-namespace` | CreateNamespace | Create namespace |
| GPDB | `aliyun gpdb list-namespaces` | ListNamespaces | List namespaces |
| GPDB | `aliyun gpdb create-document-collection` | CreateDocumentCollection | Create knowledge base |
| GPDB | `aliyun gpdb list-document-collections` | ListDocumentCollections | List knowledge bases |
| GPDB | `aliyun gpdb upload-document-async` | UploadDocumentAsync | Upload document (async) |
| GPDB | `aliyun gpdb get-upload-document-job` | GetUploadDocumentJob | Query upload progress |
| GPDB | `aliyun gpdb cancel-upload-document-job` | CancelUploadDocumentJob | Cancel upload job |
| GPDB | `aliyun gpdb list-documents` | ListDocuments | List documents |
| GPDB | `aliyun gpdb describe-document` | DescribeDocument | View document details |
| GPDB | `aliyun gpdb upsert-chunks` | UpsertChunks | Upload custom chunks |
| GPDB | `aliyun gpdb query-content` | QueryContent | Search knowledge base |
| GPDB | `aliyun gpdb query-knowledge-bases-content` | QueryKnowledgeBasesContent | Cross-knowledge base search |
| GPDB | `aliyun gpdb chat-with-knowledge-base` | ChatWithKnowledgeBase | Knowledge base Q&A |

## Grouped by Function

### Instance Management

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun gpdb describe-regions` | DescribeRegions | Query available regions |
| `aliyun gpdb describe-dbinstances` | DescribeDBInstances | Query instance list |
| `aliyun gpdb init-vector-database` | InitVectorDatabase | Initialize vector database |

### Namespace Management

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun gpdb create-namespace` | CreateNamespace | Create namespace |
| `aliyun gpdb list-namespaces` | ListNamespaces | List namespaces |

### Knowledge Base Management

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun gpdb create-document-collection` | CreateDocumentCollection | Create knowledge base |
| `aliyun gpdb list-document-collections` | ListDocumentCollections | List knowledge bases |

### Document Management

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun gpdb upload-document-async` | UploadDocumentAsync | Upload document (async) |
| `aliyun gpdb get-upload-document-job` | GetUploadDocumentJob | Query upload progress |
| `aliyun gpdb cancel-upload-document-job` | CancelUploadDocumentJob | Cancel upload job |
| `aliyun gpdb list-documents` | ListDocuments | List documents |
| `aliyun gpdb describe-document` | DescribeDocument | View document details |
| `aliyun gpdb upsert-chunks` | UpsertChunks | Upload custom chunks |

### Search & Q&A

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun gpdb query-content` | QueryContent | Search knowledge base |
| `aliyun gpdb query-knowledge-bases-content` | QueryKnowledgeBasesContent | Cross-knowledge base search |
| `aliyun gpdb chat-with-knowledge-base` | ChatWithKnowledgeBase | Knowledge base Q&A |

## Common Parameters

### General Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--biz-region-id` | String | Region ID, e.g., cn-hangzhou |
| `--db-instance-id` | String | Instance ID, format: gp-xxxxx |
| `--user-agent` | String | User agent identifier, must be set to `AlibabaCloud-Agent-Skills` |

### Authentication Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--manager-account` | String | Manager account name |
| `--manager-account-password` | String | Manager account password |
| `--namespace` | String | Namespace name |
| `--namespace-password` | String | Namespace password |

### Knowledge Base Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--collection` | String | Knowledge base name |
| `--embedding-model` | String | Embedding model name |
| `--dimension` | Integer | Vector dimension |
| `--metrics` | String | Similarity algorithm: cosine/l2/ip |

### Document Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--file-name` | String | File name |
| `--file-url` | String | File URL |
| `--document-loader-name` | String | Document loader name |
| `--chunk-size` | Integer | Chunk size |
| `--chunk-overlap` | Integer | Chunk overlap |

### Search Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--content` | String | Search content |
| `--topk` | Integer | Number of results to return |
| `--rerank-factor` | Integer | Rerank factor |
| `--filter` | String | SQL WHERE format filter condition |

## CLI Help Commands

```bash
# View product help
aliyun gpdb --help

# View specific command help
aliyun gpdb create-document-collection --help
aliyun gpdb upload-document-async --help
aliyun gpdb query-content --help
```

## Reference Documentation

- [ADBPG OpenAPI Documentation](https://api.aliyun.com/product/gpdb)
- [ADBPG Knowledge Base API Reference](https://help.aliyun.com/zh/analyticdb-for-postgresql/developer-reference/api-reference)
