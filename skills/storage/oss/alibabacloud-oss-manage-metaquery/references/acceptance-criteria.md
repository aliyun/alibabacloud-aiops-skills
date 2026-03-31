# Acceptance Criteria: OSS Vector Search & AI Content Awareness

**Scenario**: OSS Vector Search & AI Content Awareness Semantic Search
**Purpose**: Skill test acceptance criteria

## Table of Contents

- [Operation Dependencies](#operation-dependencies)
- [Correct aliyun ossutil Command Patterns](#correct-aliyun-ossutil-command-patterns)
- [Correct Python SDK Code Patterns](#correct-python-sdk-code-patterns)
- [Correct Java SDK Code Patterns](#correct-java-sdk-code-patterns)
- [Operation Checklist](#operation-checklist)
- [Acceptance Test Cases](#acceptance-test-cases)
- [Common Errors and Troubleshooting](#common-errors-and-troubleshooting)

---

## Operation Dependencies

```
+---------------------------------------------------------------------+
|                    Operation Dependency Flow                         |
+---------------------------------------------------------------------+
|                                                                     |
|  1. Create Bucket -----------------------------------------------+  |
|     (CLI/SDK/Console)                                            |  |
|           |                                                      |  |
|           v                                                      |  |
|  2. Upload Files ----------------------------------------+       |  |
|     (CLI/SDK/Console)                                    |       |  |
|           |                                              |       |  |
|           v                                              |       |  |
|  3. Initial Role Authorization (Console only)            |       |  |
|     AliyunMetaQueryDefaultRole                           |       |  |
|           |                                              |       |  |
|           v                                              |       |  |
|  4. Enable Vector Search + AI Content Awareness <--------+       |  |
|     (SDK/Console)                                                |  |
|     - mode: semantic                                             |  |
|     - WorkflowParameters: VideoInsightEnable, ImageInsightEnable |  |
|     - Filters: File filtering rules (optional)                   |  |
|           |                                                      |  |
|           v                                                      |  |
|  5. Wait for Index Build <---------------------------------------+  |
|     Query status: GetMetaQueryStatus                                |
|     State: Ready -> Running (FullScanning -> IncrementalScanning)   |
|           |                                                         |
|           v                                                         |
|  6. Execute Semantic Search                                         |
|     (CLI/SDK/Console)                                               |
|     DoMetaQuery (mode=semantic)                                     |
|                                                                     |
+---------------------------------------------------------------------+
```

### Dependency Table

| Step | Operation | Dependencies | Implementation Method |
|------|-----------|-------------|----------------------|
| 1 | Create Bucket | None | CLI/SDK/Console |
| 2 | Upload Files | Bucket created | CLI/SDK/Console |
| 3 | Role Authorization | None | **Console only** (first time) |
| 4 | Enable Vector Search + AI Content Awareness | Role authorized | SDK/Console |
| 5 | Query Index Status | Vector search enabled | aliyun ossutil/SDK/Console |
| 6 | Execute Semantic Search | Index build complete (State=Running) | aliyun ossutil/SDK/Console |
| 7 | Close Data Index | Vector search enabled | aliyun ossutil/SDK/Console |

---

## Correct Command Patterns

For correct aliyun ossutil command patterns and core rules, refer to the "Critical Rules" and "Core Workflows" sections in SKILL.md.

---

## Correct Python SDK Code Patterns

For correct and incorrect Python SDK code patterns (import, credential initialization, enabling vector search, semantic search, scalar search), refer to the code examples and script usage in the "Critical Rules" and "Core Workflows" sections of SKILL.md, as well as the verification scripts in [verification-method.md](verification-method.md).

---

## Correct Java SDK Code Patterns

### 1. Dependency Version

#### CORRECT

```xml
<!-- Java SDK 3.18.2+ supports vector search -->
<dependency>
    <groupId>com.aliyun.oss</groupId>
    <artifactId>aliyun-sdk-oss</artifactId>
    <version>3.18.2</version>
</dependency>
```

### 2. Client Initialization

#### CORRECT

```java
EnvironmentVariableCredentialsProvider credentialsProvider = 
    CredentialsProviderFactory.newEnvironmentVariableCredentialsProvider();

ClientBuilderConfiguration clientConfig = new ClientBuilderConfiguration();
clientConfig.setSignatureVersion(SignVersion.V4);  // Must use V4 signature

OSS ossClient = OSSClientBuilder.create()
    .endpoint(endpoint)
    .credentialsProvider(credentialsProvider)
    .clientConfiguration(clientConfig)
    .region(region)
    .build();
```

### 3. Semantic Search Request

#### CORRECT

```java
DoMetaQueryRequest request = new DoMetaQueryRequest(
    bucketName, maxResults, query, sort, 
    MetaQueryMode.SEMANTIC,  // Semantic mode
    mediaTypes, simpleQuery
);
DoMetaQueryResult result = ossClient.doMetaQuery(request);
```

---

## Operation Checklist

### Prerequisite Checks

- [ ] Valid credentials configured (via `aliyun configure` in `~/.aliyun/config.json`)
- [ ] Bucket region supports vector search functionality
- [ ] Correct SDK version installed (Java >= 3.18.2, Python oss2)

### Role Authorization (First time only, Console only)

- [ ] `AliyunMetaQueryDefaultRole` role authorization completed in Console

### Enable Vector Search & AI Content Awareness (SDK/Console)

- [ ] Vector search enabled (mode=semantic)
- [ ] Image content awareness configured (ImageInsightEnable=True)
- [ ] Video content awareness configured (VideoInsightEnable=True)
- [ ] (Optional) File filtering rules configured

### Index Status Check

- [ ] State = `Running` (operational)
- [ ] Phase = `FullScanning` (full scan) or `IncrementalScanning` (incremental scan)

---

## Acceptance Test Cases

> For specific commands and code for the following test cases, refer to the corresponding "Core Workflows" Task sections in SKILL.md.

### Test Case 1: Bucket Creation and File Upload

**Corresponds to**: SKILL.md Task 1

**Prerequisites**: Valid credentials configured (via `aliyun configure` in `~/.aliyun/config.json`)

**Expected Results**:
- Bucket created successfully
- Files uploaded successfully

---

### Test Case 2: Enable Vector Search & AI Content Awareness

**Corresponds to**: SKILL.md Task 2

**Prerequisites**:
- Bucket created
- Role authorization completed (Console required for first time)
- Bucket object count verified (confirm costs if exceeding 1000 objects)

**Expected Results**:
- Successful status code returned (200)
- Index build started
- Content awareness features enabled (VideoInsightEnable and ImageInsightEnable are True)

---

### Test Case 3: Query Index Status

**Corresponds to**: SKILL.md Task 4

**Prerequisites**: Vector search enabled

**Expected Results**:
- State: `Ready` -> `Running`
- Phase: `FullScanning` or `IncrementalScanning`
- MetaQueryMode: `semantic`

---

### Test Case 4: Execute Semantic Search

**Corresponds to**: SKILL.md Task 3

**Prerequisites**: 
- Index state is Running
- Files have been indexed

**Expected Results**:
- Matching file list returned
- Each file contains AI metadata (description, summary)

---

### Test Case 5: AI Content Awareness Result Verification

**Prerequisites**: Test Case 4 completed

**Expected Results**:
- `oss_ai_meta.description`: Approximately 100 characters describing the file content
- `oss_ai_meta.summary`: No more than 20 characters, concise summary

---

### Test Case 6: Close Data Index

**Corresponds to**: SKILL.md Resource Cleanup

**Prerequisites**: Vector search enabled

**Expected Results**:
- Successful status code returned
- Index status changes to `Deleted`

---

## Common Errors and Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `AccessDenied` | Missing permissions | Add `oss:OpenMetaQuery` and other required permissions |
| `BucketNotFound` | Bucket does not exist | Check Bucket name and region |
| `MetaQueryNotOpened` | Vector search not enabled | Call `OpenMetaQuery` first |
| `InvalidMode` | Invalid mode parameter | Use `semantic` or `basic` |
| No search results | Index build incomplete | Wait for index build to complete |
| No AI metadata | Content awareness not enabled | Configure `WorkflowParameters` |
| `0037-00000001` | Bucket region does not support vector search | Create a new Bucket in a supported region; refer to the supported regions list |
| `MetaQueryAlreadyExist` | Bucket already has MetaQuery enabled or is being closed | Use `get-meta-query-status` to check current status |
