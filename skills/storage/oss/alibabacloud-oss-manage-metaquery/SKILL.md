---

name: alibabacloud-oss-manage-metaquery
description: |
  Alicloud OSS AI Content Awareness Skill. Use for enabling and querying OSS semantic search with AI-powered content understanding.
  Triggers: "OSS AI Content Awareness", "OSS semantic search", "OSS vector search", "search by text", "text-to-image search", "text-to-video search", "OSS MetaQuery", "OSS data index", "OSS AI内容感知", "OSS语义检索", "OSS向量检索", "以文搜图", "以文搜视频", "OSS数据索引"

---

# OSS Vector Search & AI Content Awareness
Leverage multimodal AI models to extract semantic descriptions and concise summaries from images, videos, audio, and documents stored in OSS Buckets. Build searchable vector indexes to enable advanced retrieval capabilities such as text-to-image and text-to-video search.

## Prerequisites
1. Aliyun CLI (>= 3.3.3)
> **Pre-check: Aliyun CLI >= 3.3.3 required**
> This skill uses Aliyun CLI for all OSS operations except opening MetaQuery.
If Aliyun CLI is already installed, ossutil does not need to be installed separately.
> Run the following command to verify the version: `aliyun version`
> If not installed or the version is below 3.3.3,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or refer to [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
>
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.
2. Update the aliyun ossutil plugin
> **Troubleshooting: `--user-agent` unknown flag error**
> If you encounter `Error: unknown flag: --user-agent` when running a command, the ossutil plugin version is too old. Run the following command to update to the latest version:
> ```bash
> aliyun ossutil update
> ```
> After the update, re-run the original command.
```bash
# Python SDK dependencies
pip install oss2==2.19.1 alibabacloud-credentials==1.0.8
```
> Notes:
> - Required: Aliyun CLI, Python dependencies oss2 and alibabacloud-credentials
> - Not required: ossutil
> - The only operation that requires Python: opening MetaQuery (AI Content Awareness + semantic search)
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery`

## Architecture
```
User Request -> OSS Bucket -> AI Content Awareness Engine -> Semantic Feature Extraction -> Vector Index -> Semantic Search
                    |
         Images/Videos/Audio/Docs -> Detailed Description (~100 chars) + Concise Summary (<=20 chars)
```
**Core Components**: `OSS Bucket + Data Index + Vector Search + AI Content Awareness`

## Usage Restrictions
### Supported Regions
| Region Category | Region List |
|----------------|-------------|
| East China | cn-hangzhou, cn-shanghai |
| North China | cn-qingdao, cn-beijing, cn-zhangjiakou |
| South China | cn-shenzhen, cn-guangzhou |
| Southwest China | cn-chengdu |
| Other | cn-hongkong, ap-southeast-1 (Singapore), us-east-1 (Virginia) |
> **Note**: If the user's Bucket is in a region not listed above, vector-mode MetaQuery and content awareness cannot be enabled, and an EC Code `0037-00000001` error will be returned. Guide the user to create a new Bucket in a supported region.

### File Types
- **Supported**: Images, videos, audio, documents
- **Multipart uploads**: Only objects that have been assembled via `CompleteMultipartUpload` are shown

---

## Performance Reference
### OSS Internal Bandwidth and QPS
| Region | Internal Bandwidth | Default QPS |
|--------|-------------------|-------------|
| cn-beijing, cn-hangzhou, cn-shanghai, cn-shenzhen | 10Gbps | 1250 |
| Other regions | 1Gbps | 1250 |
> This bandwidth and QPS is provided exclusively for vector search and does not consume the Bucket's QoS quota.

### Existing File Index Build Time
| File Type | 10 Million Files | 100 Million Files | 1 Billion Files |
|-----------|-----------------|-------------------|-----------------|
| Structured data & images | 2-3 hours | 1 day | ~10 days |
| Videos, documents, audio | 2-3 days | 7-9 days | - |

### Incremental Updates and Search Latency
- **Incremental updates**: When QPS < 1250, latency is typically minutes to hours
- **Search response**: Sub-second, default timeout 30 seconds

---

## Dangerous Operation Confirmation
Before executing any of the following dangerous operations, **you MUST confirm with the user first** and obtain explicit consent before proceeding:
- **Delete Bucket**: `aliyun ossutil rm oss://<bucket-name> -b --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` -- Deletes the entire Bucket, irreversible
- **Delete Object**: `aliyun ossutil rm oss://<bucket-name>/<object-key> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` -- Deletes a specific file
- **Batch Delete Objects**: `aliyun ossutil rm oss://<bucket-name>/ --recursive --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` -- Recursively deletes all files in the Bucket
- **Close MetaQuery**: `aliyun ossutil api close-meta-query --bucket <bucket-name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` -- Closes the metadata index; all indexed data will be cleared
- **Open MetaQuery**: `python scripts/open_metaquery.py --region <your-region> --bucket <your-bucket-name> --endpoint <your-endpoint>` -- Opens the metadata index; existing data will start being indexed. If the bucket has more than 1000 objects, confirm with the user first.
- **Create Bucket**: `aliyun ossutil api put-bucket --bucket <bucket> --region <region-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` -- Creates a Bucket

When confirming, explain the following to the user:
1. The specific operation to be performed
2. The scope of impact (which files/resources will be deleted or closed)
3. Whether the operation is reversible (most delete operations are irreversible)

## RAM Permissions
See [references/ram-policies.md](references/ram-policies.md)

---

## Critical Rules (Must Follow)
### Rule 1: Opening MetaQuery MUST use the Python script
**PROHIBITED:**
```bash
aliyun ossutil api open-meta-query oss://my-bucket --mode semantic
```
**REQUIRED:**
```bash
python scripts/open_metaquery.py --region cn-hangzhou --bucket my-bucket
```
**Reason:** Only the Python script or SDK can correctly configure `WorkflowParameters` to enable AI Content Awareness (ImageInsightEnable and VideoInsightEnable). Without this, semantic search quality will be severely degraded.

### Rule 2: Must ask the user when Bucket name conflicts
When creating a Bucket and encountering a `BucketAlreadyExists` error:
1. **Immediately stop** all subsequent operations
2. Inform the user: "The Bucket name is already taken"
3. **Ask the user** to choose:
   - Option 1: Use the existing bucket (requires explicit user confirmation)
   - Option 2: Choose a new bucket name (user provides the new name)
4. **Wait for the user's response** before continuing
**PROHIBITED:**
- Automatically modifying the bucket name (e.g., appending `-2`, `-new`, etc.)
- Using an existing bucket without asking the user

### Rule 3: Use Aliyun CLI by default for all operations except opening MetaQuery
The following operations should use Aliyun CLI by default:
- Create Bucket
- Query Bucket info
- Query Bucket statistics
- Upload files
- Query MetaQuery status
- Execute semantic search
- Close MetaQuery
- Delete Object / Bucket
**Goal: Use the `aliyun` command uniformly, minimizing dependency on ossutil.**

### Rule 4: If Aliyun CLI is installed, ossutil is not needed
This skill does not require ossutil to be installed by default.
As long as Aliyun CLI >= 3.3.3 is installed and the following has been executed:
```bash
aliyun configure set --auto-plugin-install true
```
It can be used as the default execution tool.

## Core Workflows
### Task 1: Create Bucket and Upload Files
Always confirm with the user before creating a bucket. Proceed only after the user agrees.
```bash
# 1.1 Create Bucket
aliyun ossutil api put-bucket --bucket examplebucket --region <region-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
# 1.2 Download files
aliyun ossutil cp oss://example-bucket/test_medias/ /tmp/test_medias_download/ -r --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
# 1.3 Upload files
aliyun ossutil cp /tmp/test_medias_download/ oss://example-bucket/test_medias/ -r --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```

### Task 2: Enable Vector Search & AI Content Awareness (Python script or SDK only)
> WARNING: You MUST use `python scripts/open_metaquery.py` to open MetaQuery. Using `aliyun ossutil api open-meta-query` is STRICTLY PROHIBITED (it cannot configure WorkflowParameters, which prevents enabling AI Content Awareness features ImageInsightEnable and VideoInsightEnable, severely degrading semantic search quality).

#### Using the Python Script (Mandatory)
Before executing the Python script, complete the following environment setup:

**1. Install Python dependencies:**
```bash
pip install oss2==2.19.1 alibabacloud-credentials==1.0.8
```

**2. Configure credentials:**
The Python script uses the `alibabacloud-credentials` default credential chain to automatically discover credentials (supporting environment variables, `~/.aliyun/config.json`, ECS instance roles, etc.). No explicit AK/SK handling is needed in the code. Ensure credentials are configured via the `aliyun configure` command.

**3. Verify RAM permissions:**
Users must have the minimum RAM permissions required for MetaQuery. See [references/ram-policies.md](references/ram-policies.md).
If the user encounters an `AccessDenied` error, check that RAM permissions are correctly configured.

**Enablement Process:**
1. **Prepare the Bucket**:
   **a. If the user requests creating a new Bucket:**
   - Run `aliyun ossutil api put-bucket --bucket examplebucket --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery` with the user-specified bucket name
   - If creation fails with a `BucketAlreadyExists` error:
     - **Immediately stop the operation**
     - Inform the user: "The Bucket name `<bucket-name>` is already taken (it may have been created by you or another user)"
     - **You MUST ask the user**: "Would you like to: 1) Use this existing bucket? or 2) Choose a new bucket name?"
     - **Wait for the user's explicit response before continuing**. Do not modify the bucket name or use the existing bucket without permission.
   **b. If the user provides an existing bucket:**
   - First verify the bucket exists using `aliyun ossutil api get-bucket-info --bucket <bucket-name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery`
   - If it does not exist, ask the user whether to create it

2. **Verify Bucket object count**: After the user provides a bucket, check the object count. If it exceeds 1000, warn the user that enabling MetaQuery will incur costs.
   Use the following command to get the bucket's object count:
   ```bash
   aliyun ossutil api get-bucket-stat --bucket <your-bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
   ```
   The `ObjectCount` field in the response indicates the number of objects.
   - If the object count exceeds 1000, warn the user that enabling MetaQuery will incur costs and confirm whether to proceed.
   - If the object count is 0, ask the user which files to upload. Upload command:
     ```bash
     aliyun ossutil api put-object --bucket <your-bucket-name> --key <object-key> --body file://<local-file-path> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
     ```

3. **Run the Python script**: After the above steps are complete, attempt to open MetaQuery using the Python script.
**Python script example:**
```bash
python scripts/open_metaquery.py --region <your-region> --bucket <your-bucket-name> --endpoint <your-endpoint>
```

#### Troubleshooting MetaQuery Enablement Issues
Use the `get-meta-query-status` command to check MetaQuery status:
```bash
aliyun ossutil api get-meta-query-status --bucket <your-bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
Based on the returned status:
- **Status is `Deleted`**: MetaQuery is being closed. The user should retry later.
- **Status is `Running` or `Ready`**: MetaQuery has already been created. Check the following two conditions:
  - Whether `MetaQueryMode` is `semantic`
  - Whether `WorkflowParameters` contains the following configuration:
    ```xml
    <WorkflowParameters>
      <WorkflowParameter><Name>ImageInsightEnable</Name><Value>True</Value></WorkflowParameter>
      <WorkflowParameter><Name>VideoInsightEnable</Name><Value>True</Value></WorkflowParameter>
    </WorkflowParameters>
    ```
  If `MetaQueryMode=semantic` and both `VideoInsightEnable` and `ImageInsightEnable` are `True`, the user has successfully enabled MetaQuery in vector mode with content awareness (which greatly improves semantic search quality). No further action is needed.
  If these conditions are not met, recommend the user switch to a different bucket and start over.

### Task 3: Execute Semantic Search
#### Prerequisites for MetaQuery Search
Before using MetaQuery for search, confirm the following:
1. **Verify MetaQuery is enabled**:
   ```bash
   aliyun ossutil api get-meta-query-status --bucket <your-bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
2. **If MetaQuery is not enabled**: Complete the enablement process first. Refer to Task 2 to enable it using the Python script.
3. **Check index scan status**: The `Phase` field from `get-meta-query-status` indicates the current scan phase:
    - `FullScanning`: Full scan in progress. **Search is not available yet**. Wait for the full scan to complete.
    - `IncrementalScanning`: Incremental scan in progress. The index has been largely built and search can be performed normally.
4. **Verify MetaQuery state is `Running`**: MetaQuery is only available when `State` is `Running`. If the state is `Ready` or any non-`Running` state, you may need to wait or re-enable it.

**1. Prepare the meta-query.xml file:**
Create a `meta-query.xml` file to define query conditions. For detailed format, field descriptions, and complete examples, see [references/metaquery.md](references/metaquery.md).
Example of semantic vector search for video files containing "person" (MediaTypes can only be one of: video, image, audio, document):
```xml
<MetaQuery>
<MediaTypes><MediaType>video</MediaType></MediaTypes>
<Query>person</Query>
</MetaQuery>
```
Example of scalar search where file size > 30B and file modification time > 2025-06-03T09:20:47.999Z:
```xml
<MetaQuery>
<Query>{"SubQueries":[{"Field":"Size","Value":"30","Operation":"gt"},{"Field":"FileModifiedTime","Value":"2025-06-03T09:20:47.999Z","Operation":"gt"}],"Operation":"and"}</Query>
</MetaQuery>
```

**2. Execute the search command:**
This example uses semantic vector search. The `meta-query.xml` file defines the query conditions, and search results return the most similar files.
```bash
aliyun ossutil api do-meta-query --bucket <bucket-name> --meta-query file://meta-query.xml --meta-query-mode semantic --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
For scalar search, use `--meta-query-mode basic`
> For detailed command parameters, see the DoMetaQuery section in [references/related-apis.md](references/related-apis.md).

**3. Optimizing search result display:**
After search completes, when displaying results to the user, use the `x-oss-process` parameter to generate preview images or cover frames for image and video files, making it easier for the user to visually review search results. If the user's current channel supports multimedia files, send them directly to the user.

**Video files -- Get video cover snapshot:**
```bash
aliyun ossutil presign oss://<bucket-name>/<video-object-key> --query-param x-oss-process=video/snapshot,t_0,f_png,w_0,h_0 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
Parameters: `t_0`: Capture frame at 0ms as cover; `f_png`: Output format PNG; `w_0,h_0`: Width/height 0 means original resolution.

**Image files -- Get image preview link:**
```bash
aliyun ossutil presign oss://<bucket-name>/<image-object-key> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
> **Note**: The `aliyun ossutil presign` command generates a signed temporary access URL that can be opened directly in a browser for preview during its validity period. For image files, you can also add image processing parameters via `x-oss-process` (e.g., resize, crop):
> ```bash
> aliyun ossutil presign oss://<bucket-name>/<image-object-key> --query-param x-oss-process=image/resize,w_200 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
> ```
> This generates a thumbnail preview to reduce loading time.

### Troubleshooting MetaQuery Search Issues
#### User asks "Why wasn't a specific file found?"
When a user reports that a specific uploaded file is missing from search results, troubleshoot based on the MetaQuery configuration:

**a. Content awareness is NOT enabled:**
If the user's MetaQuery does not have content awareness enabled (i.e., `VideoInsightEnable` or `ImageInsightEnable` is not `True` in `WorkflowParameters`), possible reasons include:
- The file's metadata index has not been fully built yet. Wait for the index scan to complete (check the `Phase` field via `aliyun ossutil api get-meta-query-status --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery`).
- Without content awareness, search is based only on basic file metadata (filename, size, type, etc.) and cannot perform semantic understanding of file contents, resulting in limited search effectiveness.
- **Recommendation**: Suggest the user enable content awareness to improve search quality. Since existing MetaQuery configurations cannot be directly modified, recommend the user switch to a new bucket and re-enable MetaQuery with content awareness following the Task 2 process.

**b. Content awareness IS enabled:**
If the user's MetaQuery has content awareness enabled but a specific file still cannot be found, possible reasons include:
- **File is still being processed**: Content awareness requires deep analysis of files (e.g., image recognition, video understanding), which takes longer, especially for video files. Check the `Phase` field via `aliyun ossutil api get-meta-query-status --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery`:
  - `FullScanning`: The overall index is still in full scan mode. Wait patiently.
  - `IncrementalScanning`: Newly uploaded files are being processed incrementally. Usually wait a few minutes.
- **Unsupported file format**: Some file formats may not be supported by content awareness. In this case, search can only use basic metadata.
- **Search keywords don't match**: The user's search keywords may not semantically match the file content. Suggest the user try adjusting their search keywords to use descriptions closer to the actual file content.

### Task 4: Query Data Index Status (aliyun ossutil)
```bash
aliyun ossutil api get-meta-query-status --bucket <bucket-name> --output-format json --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
> For detailed descriptions of returned fields (State, Phase, MetaQueryMode, etc.), see the GetMetaQueryStatus section in [references/related-apis.md](references/related-apis.md).

## Verification
See [references/verification-method.md](references/verification-method.md)

## Resource Cleanup
```bash
# Close the data index. (Dangerous operation -- confirm with the user first)
aliyun ossutil api close-meta-query --bucket <bucket-name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery
```
> **Warning**: After closing the data index, all indexed data will be cleared. (Dangerous operation -- confirm with the user first)

## Alternative Python Scripts for OSS Operations
When aliyun ossutil is unavailable, you can use Python scripts as alternatives. See the Python SDK Scripts section in [references/related-apis.md](references/related-apis.md).

---
