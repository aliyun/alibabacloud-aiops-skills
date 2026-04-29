# RAM Policies - ADBPG Knowledge Base Management

This document lists the RAM permissions required for ADBPG Knowledge Base Management.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gpdb:DescribeRegions",
        "gpdb:DescribeDBInstances",
        "gpdb:InitVectorDatabase",
        "gpdb:CreateNamespace",
        "gpdb:CreateDocumentCollection",
        "gpdb:UploadDocumentAsync",
        "gpdb:GetUploadDocumentJob",
        "gpdb:CancelUploadDocumentJob",
        "gpdb:ListDocuments",
        "gpdb:DescribeDocument",
        "gpdb:UpsertChunks",
        "gpdb:QueryContent",
        "gpdb:QueryKnowledgeBasesContent",
        "gpdb:ChatWithKnowledgeBase"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

| API | Permission Action | Description |
|-----|------------------|-------------|
| DescribeRegions | gpdb:DescribeRegions | Query available regions |
| DescribeDBInstances | gpdb:DescribeDBInstances | Query instance list |
| InitVectorDatabase | gpdb:InitVectorDatabase | Initialize vector database |
| CreateNamespace | gpdb:CreateNamespace | Create namespace |
| ListNamespaces | gpdb:ListNamespaces | List namespaces |
| CreateDocumentCollection | gpdb:CreateDocumentCollection | Create knowledge base |
| ListDocumentCollections | gpdb:ListDocumentCollections | List knowledge bases |
| UploadDocumentAsync | gpdb:UploadDocumentAsync | Upload document |
| GetUploadDocumentJob | gpdb:GetUploadDocumentJob | Query upload progress |
| CancelUploadDocumentJob | gpdb:CancelUploadDocumentJob | Cancel upload job |
| ListDocuments | gpdb:ListDocuments | List documents |
| DescribeDocument | gpdb:DescribeDocument | View document details |
| UpsertChunks | gpdb:UpsertChunks | Upload custom chunks |
| QueryContent | gpdb:QueryContent | Search knowledge base |
| QueryKnowledgeBasesContent | gpdb:QueryKnowledgeBasesContent | Cross-knowledge base search |
| ChatWithKnowledgeBase | gpdb:ChatWithKnowledgeBase | Knowledge base Q&A |

## Permissions by Function

### Basic Query (Read-only)

```json
{
  "Effect": "Allow",
  "Action": [
    "gpdb:DescribeRegions",
    "gpdb:DescribeDBInstances",
    "gpdb:ListDocumentCollections",
    "gpdb:ListDocuments",
    "gpdb:DescribeDocument",
    "gpdb:QueryContent",
    "gpdb:QueryKnowledgeBasesContent",
    "gpdb:ChatWithKnowledgeBase",
    "gpdb:GetUploadDocumentJob"
  ],
  "Resource": "*"
}
```

### Knowledge Base Management (Read-Write)

```json
{
  "Effect": "Allow",
  "Action": [
    "gpdb:InitVectorDatabase",
    "gpdb:CreateNamespace",
    "gpdb:ListNamespaces",
    "gpdb:CreateDocumentCollection"
  ],
  "Resource": "*"
}
```

### Document Management (Read-Write)

```json
{
  "Effect": "Allow",
  "Action": [
    "gpdb:UploadDocumentAsync",
    "gpdb:CancelUploadDocumentJob",
    "gpdb:UpsertChunks"
  ],
  "Resource": "*"
}
```

## Additional Permissions for SDK Local File Upload

If you need to upload local files via SDK (SDK internally uses OSS for transfer), you also need the following OSS permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "oss:PutObject",
    "oss:GetObject"
  ],
  "Resource": "acs:oss:*:*:gpdb-*"
}
```

## Permission Verification

Use the following commands to verify current user has required permissions:

```bash
# Test basic permissions
aliyun gpdb describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops

# Test instance query permission
aliyun gpdb describe-dbinstances --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

## Reference Documentation

- [ADBPG API Documentation](https://help.aliyun.com/zh/analyticdb-for-postgresql/developer-reference/api-reference)
- [RAM Permission Management](https://ram.console.aliyun.com/)
