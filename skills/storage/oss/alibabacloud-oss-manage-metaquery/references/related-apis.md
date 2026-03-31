# Related APIs and CLI Commands

## Table of Contents

- [ossutil Commands](#ossutil-commands)
- [SDK API](#sdk-api)
- [API Details](#api-details)
  - [OpenMetaQuery (Enable Metadata Management)](#openmetaquery-enable-metadata-management)
  - [GetMetaQueryStatus (Get Index Status)](#getmetaquerystatus-get-index-status)
  - [DoMetaQuery (Execute Query)](#dometaquery-execute-query)
  - [CloseMetaQuery (Close Index)](#closemetaquery-close-index)
- [SDK Version Requirements](#sdk-version-requirements)
- [Reference Links](#reference-links)

---

## ossutil Commands

| Command | Description | Example |
|---------|-------------|---------|
| `Python open_metaquery.py` | Enable metadata management with content awareness | `python scripts/open_metaquery.py --region <region> --bucket <bucket-name>` |
| `get-meta-query-status` | Get metadata index status | `aliyun ossutil api get-meta-query-status --bucket <bucket-name>` |
| `do-meta-query` | Execute metadata query | `aliyun ossutil api do-meta-query --bucket <bucket-name> --meta-query file://meta-query.xml --meta-query-mode semantic` |
| `close-meta-query` | Close metadata management | `aliyun ossutil api close-meta-query --bucket <bucket-name>` |


### do-meta-query Query Conditions

The `--meta-query` parameter of `do-meta-query` requires an XML-formatted query condition file.

For detailed format, field descriptions, and complete examples (including semantic and scalar queries), see [metaquery.md](metaquery.md).


## Python SDK Scripts (Alternative to aliyun ossutil)

When aliyun ossutil is unavailable, you can use the following Python scripts as alternatives. For the complete usage workflow, refer to the "Core Workflows" section in SKILL.md.

| Script | Description | Command Example |
|--------|-------------|-----------------|
| `create_bucket.py` | Create an OSS bucket | `python scripts/create_bucket.py --region <region> --bucket <bucket-name>` |
| `open_metaquery.py` | Enable MetaQuery with content awareness | `python scripts/open_metaquery.py --region <region> --bucket <bucket-name>` |
| `upload.py` | Upload files to OSS | `python scripts/upload.py --region <region> --bucket <bucket-name> --local-path <file> --remote-key <key>` |
| `basic_query.py` | Execute scalar queries (basic search) | `python scripts/basic_query.py --region <region> --bucket <bucket-name> --scalar-query '<json>'` |
| `semantic_query.py` | Execute semantic queries (vector search) | `python scripts/semantic_query.py --region <region> --bucket <bucket-name> --query <term>` |
| `close_metaquery.py` | Disable MetaQuery functionality | `python scripts/close_metaquery.py --region <region> --bucket <bucket-name>` |


## API Details

### OpenMetaQuery (Enable Metadata Management)

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| bucket | string | Yes | Bucket name |
| mode | string | Yes | Search mode: `basic` (scalar search), `semantic` (vector search) |
| role | string | No | RAM role name (required when configuring MNS notifications) |
| MetaQuery | object | No | Configuration container, includes WorkflowParameters, Filters, NotificationAttributes |

**WorkflowParameters - AI Content Awareness Configuration:**

| Parameter Name | Value | Description |
|----------------|-------|-------------|
| `VideoInsightEnable` | `True`/`False` | Video content awareness switch |
| `ImageInsightEnable` | `True`/`False` | Image content awareness switch |

**Filters - File Filtering Rules:**

| Field | Type | Supported Operators | Example |
|-------|------|---------------------|---------|
| Size | Integer | `=`, `!=`, `>`, `>=`, `<`, `<=` | `Size > 1024` |
| Filename | String | `=`, `!=`, `prefix`, `suffix`, `in`, `notin` | `Filename prefix (YWEvYmIv)` |
| FileModifiedTime | String | `=`, `!=`, `>`, `>=`, `<`, `<=` | `FileModifiedTime > 2025-06-03T09:20:47.999Z` |
| OSSTagging.* | String | `=`, `!=`, `!`, `exists`, `prefix`, `suffix`, `in`, `notin` | `OSSTagging.Zm9v == YWJj` |

> **Note**: Filename and OSSTagging values must be URL-safe Base64 encoded

---

### GetMetaQueryStatus (Get Index Status)

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| bucket | string | Yes | Bucket name |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| State | string | Index status |
| Phase | string | Current scan phase |
| CreateTime | string | Creation time (RFC 3339 format) |
| UpdateTime | string | Update time (RFC 3339 format) |
| MetaQueryMode | string | Search mode: `basic` or `semantic` |

**State Values:**

| Value | Description |
|-------|-------------|
| `Ready` | Preparing after creation, data cannot be queried |
| `Running` | Running |
| `Stop` | Paused |
| `Retrying` | Retrying after creation failure |
| `Failed` | Creation failed |
| `Deleted` | Deleted |

**Phase (Scan Phase):**

| Value | Description |
|-------|-------------|
| `FullScanning` | Full scan in progress |
| `IncrementalScanning` | Incremental scan in progress |

---

### DoMetaQuery (Execute Query)

#### Vector Search Mode (mode=semantic)

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| bucket | string | Yes | Bucket name |
| mode | string | Yes | `semantic` |
| Query | string | Yes | Semantic query content, e.g., "aerial view of a snow-covered forest" |
| MaxResults | int | No | Maximum number of results (0-100), default 100 |
| MediaTypes | array | Yes | Media type list |
| SimpleQuery | string | No | Additional filter conditions (JSON) |

**Supported MediaType Values:**

| Value | Description |
|-------|-------------|
| `image` | Image |
| `video` | Video |
| `audio` | Audio |
| `document` | Document |

**SimpleQuery Examples:**

```json
// File size greater than 30 bytes
{"Operation": "gt", "Field": "Size", "Value": "30"}

// Combined conditions
{
  "Operation": "and",
  "SubQueries": [
    {"Operation": "gt", "Field": "Size", "Value": "1000"},
    {"Operation": "prefix", "Field": "Filename", "Value": "videos/"}
  ]
}
```

#### Scalar Search Mode (mode=basic)

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Query | string | Yes | Query conditions (JSON format) |
| Sort | string | No | Sort field |
| Order | string | No | Sort order: `asc` (ascending), `desc` (descending, default) |
| Aggregations | array | No | Aggregation operations |
| NextToken | string | No | Pagination token |

**Query Operators:**

| Operator | Description |
|----------|-------------|
| `eq` | Equal to |
| `gt` | Greater than |
| `gte` | Greater than or equal to |
| `lt` | Less than |
| `lte` | Less than or equal to |
| `match` | Fuzzy match |
| `prefix` | Prefix match |
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Logical NOT |

**Aggregation Operations:**

| Operator | Description |
|----------|-------------|
| `min` | Minimum value |
| `max` | Maximum value |
| `average` | Average |
| `sum` | Sum |
| `count` | Count |
| `distinct` | Distinct count |
| `group` | Group count |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| NextToken | string | Pagination token |
| Files | array | File list |
| Files[].Filename | string | Full file path |
| Files[].Size | int | File size (bytes) |
| Files[].FileModifiedTime | string | Modification time |
| Files[].OSSObjectType | string | Object type: Normal/Appendable/Multipart/Symlink |
| Files[].OSSStorageClass | string | Storage class: Standard/IA/Archive/ColdArchive |
| Files[].ETag | string | ETag value |
| Files[].OSSTagging | array | Tag list |
| Files[].OSSUserMeta | array | Custom metadata |
| Aggregations | array | Aggregation results |

---

### CloseMetaQuery (Close Index)

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| bucket | string | Yes | Bucket name |

---

## Opening MetaQuery via Python Script

Opening MetaQuery must use the Python script. For detailed usage, WorkflowParameters XML configuration, and the enablement process, refer to "Rule 1" and "Task 2: Enable Vector Search & AI Content Awareness" sections in SKILL.md.

## SDK Version Requirements

| SDK | Minimum Version | Package Name |
|-----|-----------------|--------------|
| Java SDK | 3.18.2+ | com.aliyun.oss:aliyun-sdk-oss |
| Python SDK (oss2) | - | oss2 |
| Go SDK V2 | - | github.com/aliyun/alibabacloud-oss-go-sdk-v2 |
| PHP SDK V2 | - | alibabacloud/oss-sdk-php |

## Reference Links

- [OpenMetaQuery API Documentation](https://help.aliyun.com/zh/oss/developer-reference/openmetaquery)
- [GetMetaQueryStatus API Documentation](https://help.aliyun.com/zh/oss/developer-reference/getmetaquerystatus)
- [DoMetaQuery API Documentation](https://help.aliyun.com/zh/oss/developer-reference/dometaquery)
- [OSS Vector Search User Guide](https://help.aliyun.com/zh/oss/user-guide/vector-retrieval/)
- [OSS Java SDK Vector Search](https://help.aliyun.com/zh/oss/developer-reference/vector-search-java-sdk-v1)
- [OSS Python SDK Vector Search](https://help.aliyun.com/zh/oss/developer-reference/vector-search-python-sdk-v2)
- [OSS Go SDK Vector Search](https://help.aliyun.com/zh/oss/developer-reference/vector-search-go-sdk-v2)
- [ossutil Command-Line Tool](https://help.aliyun.com/zh/oss/developer-reference/ossutil)
