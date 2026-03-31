# Verification Methods

## Table of Contents

- [1. Verify Bucket Creation](#1-verify-bucket-creation)
- [2. Verify File Upload](#2-verify-file-upload)
- [3. Verify Data Index Status](#3-verify-data-index-status)
- [4. Verify Semantic Search Functionality](#4-verify-semantic-search-functionality)
- [5. Verify AI Content Awareness Results](#5-verify-ai-content-awareness-results)
- [6. Complete Verification Flow](#6-complete-verification-flow)
- [Common Issue Troubleshooting](#common-issue-troubleshooting)

---

## 1. Verify Bucket Creation

### CLI Verification

```bash
# Check if Bucket exists
aliyun ossutil api get-bucket-info --bucket <bucket-name> --user-agent AlibabaCloud-Agent-Skills

# View detailed Bucket information
aliyun ossutil api get-bucket-stat --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators:**
- Command returns Bucket information without errors
- Displays Bucket creation time, region, storage class, and other information

---

## 2. Verify File Upload

### CLI Verification

```bash
# List files in the Bucket
aliyun ossutil ls oss://<bucket-name>/<prefix>/ --user-agent AlibabaCloud-Agent-Skills

# View individual file information
aliyun ossutil api head-object --bucket <bucket-name> --key <object-key> --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators:**
- File list contains the uploaded files
- File size and last modification time are correct

---

## 3. Verify Data Index Status

### CLI Verification

```bash
aliyun ossutil api get-meta-query-status --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators:**
- Command returns JSON result without errors
- `State` is `Running`
- `Phase` is `FullScanning` (full scan in progress) or `IncrementalScanning` (incremental scan, searchable)
- `MetaQueryMode` is `semantic`

---

## 4. Verify Semantic Search Functionality

### CLI Verification

**1. Create query condition file `meta-query.xml`:**

```xml
<MetaQuery>
<MediaTypes>
<MediaType>video</MediaType>
<MediaType>image</MediaType>
</MediaTypes>
<Query>a yard with parked cars</Query>
</MetaQuery>
```

**2. Execute semantic search:**

```bash
aliyun ossutil api do-meta-query --bucket <bucket-name> --meta-query file://meta-query.xml --meta-query-mode semantic --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicators:**
- Command returns XML result without errors
- Result contains a `<Files>` list
- File entries contain `<OSSAIMeta>` fields (with description and summary)

---

## 5. Verify AI Content Awareness Results

### Check Returned AI Metadata

In the semantic search results (XML) from Step 4, check whether each file entry contains the `<OSSAIMeta>` field:

```xml
<File>
  <Filename>test_medias/example.jpg</Filename>
  ...
  <OSSAIMeta>
    <Description>A yard with several parked cars, surrounded by walls and green plants...</Description>
    <Summary>Yard with cars</Summary>
  </OSSAIMeta>
</File>
```

**Success Indicators:**
- Returned files contain the `<OSSAIMeta>` field
- `<Description>` content is approximately 100 characters describing the file content
- `<Summary>` content is no more than 20 characters, a concise summary

---

## 6. Complete Verification Flow

Execute the following CLI commands in order for end-to-end verification:

```bash
# [1/4] Verify Bucket exists
aliyun ossutil api get-bucket-info --bucket <bucket-name> --user-agent AlibabaCloud-Agent-Skills

# [2/4] Verify files are uploaded
aliyun ossutil ls oss://<bucket-name>/<prefix>/ --user-agent AlibabaCloud-Agent-Skills

# [3/4] Verify data index status (confirm State=Running, MetaQueryMode=semantic)
aliyun ossutil api get-meta-query-status --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills

# [4/4] Execute semantic search (create meta-query.xml first, refer to Step 4)
aliyun ossutil api do-meta-query --bucket <bucket-name> --meta-query file://meta-query.xml --meta-query-mode semantic --user-agent AlibabaCloud-Agent-Skills
```

**Verification Pass Criteria:**
1. Bucket information returns successfully
2. File list contains uploaded files
3. Index status `State` is `Running`, `Phase` is `IncrementalScanning`
4. Semantic search results contain `<OSSAIMeta>` (with Description and Summary)

---

## Common Issue Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Index status query fails | Data index not enabled | Enable data index in Console |
| Semantic search returns no results | Index build not complete | Wait for index build to complete (may take hours) |
| No AI metadata | AI content awareness not enabled | Enable image/video content awareness in Console |
| Insufficient permissions | RAM permissions missing | Add `oss:DoMetaQuery` and other required permissions |
| Region not supported | Bucket not in a supported region | Use a region that supports AI content awareness |
