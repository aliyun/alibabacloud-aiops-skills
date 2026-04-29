# Verification Method - ADBPG Knowledge Base Management

This document describes how to verify that ADBPG Knowledge Base operations executed successfully.

## Table of Contents

- [1. Environment Verification](#1-environment-verification)
- [2. Knowledge Base Management Verification](#2-knowledge-base-management-verification)
- [3. Document Management Verification](#3-document-management-verification)
- [4. Search & Q&A Verification](#4-search--qa-verification)
- [Common Error Troubleshooting](#common-error-troubleshooting)

---

## 1. Environment Verification

### 1.1 CLI Version Verification

```bash
aliyun version
```

**Success Criteria**: Version >= 3.3.3

### 1.2 Credential Verification

```bash
aliyun configure list
```

**Success Criteria**: Shows valid profile configuration

### 1.3 API Connectivity Verification

```bash
aliyun gpdb describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**: Returns region list JSON

---

## 2. Knowledge Base Management Verification

### 2.1 Initialize Vector Database

```bash
aliyun gpdb init-vector-database \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `RequestId`
- No error messages

**Verification Command**: If the call succeeds, no extra verification; if the operation was already applied, expect an **explicit API error**—handle duplicate / already-exists per [SKILL.md](../SKILL.md) create pre-checks.

### 2.2 Create Namespace

```bash
aliyun gpdb create-namespace \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --namespace ns_test_kb \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `RequestId`
- No error messages

**Verification Command**: No direct namespace query API, verify through subsequent operations

### 2.3 Create Knowledge Base

```bash
aliyun gpdb create-document-collection \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<manager-account-password>' \
  --collection test_knowledge_base \
  --embedding-model text-embedding-v4 \
  --dimension 1024 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `RequestId`
- No error messages

**Verification Command**:

```bash
aliyun gpdb list-document-collections \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace-password '<namespace-password>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Verification Criteria**: Result contains `test_knowledge_base`

---

## 3. Document Management Verification

### 3.1 Upload Document

```bash
aliyun gpdb upload-document-async \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace-password '<namespace-password>' \
  --collection test_knowledge_base \
  --file-name "test.pdf" \
  --file-url "https://example.com/test.pdf" \
  --document-loader-name ADBPGLoader \
  --chunk-size 500 \
  --chunk-overlap 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `JobId`
- Status is `running` or `completed`

**Verification Command** (poll progress):

```bash
aliyun gpdb get-upload-document-job \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace-password '<namespace-password>' \
  --collection test_knowledge_base \
  --job-id "job-xxxxx" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Verification Criteria**:
- `Status` is `completed`
- `Progress` is `100`

### 3.2 List Documents

```bash
aliyun gpdb list-documents \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace-password '<namespace-password>' \
  --collection test_knowledge_base \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns document list
- Contains uploaded document name

---

## 4. Search & Q&A Verification

### 4.1 Search Knowledge Base

```bash
aliyun gpdb query-content \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace-password '<namespace-password>' \
  --collection test_knowledge_base \
  --content "test query" \
  --topk 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `Matches` array
- Each result contains `Content` and `Score`

### 4.2 Knowledge Base Q&A

```bash
aliyun gpdb chat-with-knowledge-base \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{"Model":"qwen-max","Messages":[{"Role":"user","Content":"test question"}]}' \
  --knowledge-params '{"SourceCollection":[{"Collection":"test_knowledge_base","NamespacePassword":"<namespace-password>","TopK":10}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-knowledgebase-ops
```

**Success Criteria**:
- Returns `Response` field
- Contains LLM-generated answer

---

## Common Error Troubleshooting

| Error Code | Cause | Solution |
|------------|-------|----------|
| InvalidAccessKeyId.NotFound | AK doesn't exist | Check AK configuration |
| SignatureDoesNotMatch | SK is incorrect | Check SK configuration |
| Instance.NotSupportVector | Instance doesn't support vector features | Upgrade instance or enable vector engine |
| role "knowledgebasepub" does not exist | Namespace not created | Execute CreateNamespace first |
| Collection.NotFound | Knowledge base doesn't exist | Check knowledge base name |
| Namespace.PasswordInvalid | Namespace password incorrect | Check if password is correct |
