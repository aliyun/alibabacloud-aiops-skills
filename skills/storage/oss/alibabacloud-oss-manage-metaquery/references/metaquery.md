# MetaQuery Query Condition Reference

This document provides query condition formats and examples for MetaQuery scalar and semantic queries.

For script command formats, refer to the Python SDK Scripts section in [related-apis.md](related-apis.md). For the complete workflow and environment setup, refer to SKILL.md.

---

## Scalar Query Conditions

This condition performs an exact match query by filename:

```json
{
  "SubQueries":[
    {
      "Field":"Filename",
      "Value":"video_1.mov",
      "Operation":"eq"
    }
  ],
  "Operation":"and"
}
```

**Condition Description:**
- **Field**: `"Filename"` - Specifies the query field as filename
- **Value**: `"video_1.mov"` - The specific filename to search for, can be replaced with any filename
- **Operation**: `"eq"` - Equals operator, for exact matching

##### `query_time` - Time-Based Query Configuration

This configuration queries based on file creation time and modification time:

```json
{
  "SubQueries":[
    {
      "Field":"OSSTagging.CreateTime",
      "Value":"1672588800000000000",
      "Operation":"eq"
    },{
      "Field":"FileModifiedTime",
      "Value":"2025-11-21T14:50:13.011643661+08:00",
      "Operation":"eq"
    }
  ],
  "Operation":"and"
}
```

**Configuration Description:**
- **First sub-query - Creation time**:
  - **Field**: `"OSSTagging.CreateTime"` - File creation time tag. The CreateTime tag can be optionally attached when uploading files via upload.py.
  - **Value**: `"1672588800000000000"` - Nanosecond timestamp corresponding to the CreateTime tag added during upload
  - **Operation**: `"eq"` - Exact match for this creation time
- **Second sub-query - Modification time**:
  - **Field**: `"FileModifiedTime"` - File modification time
  - **Value**: `"2025-11-21T14:50:13.011643661+08:00"` - Time in RFC3339Nano format
  - **Operation**: `"eq"` - Exact match for this modification time
- **Operation**: `"and"` - Both conditions must be satisfied simultaneously
- **Use case**: Filter files by time range, such as finding files uploaded or modified during a specific period
- **Usage tips**:
  - Creation time uses nanosecond timestamp format
  - Modification time must use RFC3339Nano format, or alternatively, you can use OSS Tags to carry the modification time during upload and search using the `OSSTagging.{TagName}` format
  - Either time condition can be used independently or in combination
  - Supports other operators like `"gt"` (greater than), `"lt"` (less than), etc. for range queries

**Fields supported by scalar index:**
For more supported fields and operators, refer to the official documentation: [Fields and Operators Supported by Scalar Index](https://help.aliyun.com/zh/oss/developer-reference/appendix-supported-fields-and-operators?spm=a2c4g.11186623.help-menu-31815.d_1_0_4_17_4.558820051pvhh4)

### Semantic Query Conditions

#### Pure Vector Semantic Query Configuration

This configuration is used for intelligent search based on content semantics:

```xml
<MetaQuery>
<MediaTypes><MediaType>video</MediaType></MediaTypes>
<Query>person</Query>
</MetaQuery>
```

**Configuration Description:**
- **MediaTypes**: `<MediaType>video</MediaType>` - Restricts search to video-type media files
  - Available values: `video`, `image`, `audio`, `document`
- **Query**: `person` - Semantic search keyword. The system analyzes video content to find videos containing "person"
  - Can be descriptive terms for objects, scenes, actions, etc.

##### `query_body_with_basic` - Combined Vector + Scalar Query Configuration

This configuration combines semantic search with attribute filtering for composite queries:

```xml
<MetaQuery>
<MediaTypes><MediaType>video</MediaType></MediaTypes>
<Query>person</Query>
<SimpleQuery>{
  "SubQueries":[
    {
      "Field":"Size",
      "Value":"30",
      "Operation":"gt"
    },
    {
      "Field":"OSSTagging.CreateTime",
      "Value":"1763722586691406000",
      "Operation":"eq"
    }
  ],
  "Operation":"and"
}</SimpleQuery>
</MetaQuery>
```

**Configuration Description:**
- **MediaTypes**: Restricted to video type (same as pure vector query)
- **Query**: `person` - Semantic search keyword (same as pure vector query)
- **SimpleQuery**: Adds scalar query conditions for further filtering
  - **First condition - File size**:
    - **Field**: `"Size"` - File size (bytes)
    - **Value**: `"30"` - 30 bytes
    - **Operation**: `"gt"` - Greater than operator, filters files larger than 30 bytes
  - **Second condition - Creation time**:
    - **Field**: `"OSSTagging.CreateTime"` - Creation time tag. The CreateTime tag can be optionally attached when uploading files via upload.py.
    - **Value**: `"1763722586691406000"` - Specific nanosecond timestamp
    - **Operation**: `"eq"` - Exact match for this creation time
  - **Operation**: `"and"` - All conditions must be satisfied simultaneously
- **Use case**: Precise queries that need to satisfy both content semantics and file attribute conditions
- **Usage tips**:
  - Scalar query conditions can include file size, creation time, modification time, etc.
  - Operators can be adjusted based on actual needs (eq, gt, lt, gte, lte, etc.)
  - Suitable for scenarios requiring precise control over search results

**Fields supported by vector index:**
For more supported fields and operators, refer to the official documentation: [Fields and Operators Supported by Vector Index](https://help.aliyun.com/zh/oss/developer-reference/appendix-list-of-fields-and-operators-for-vector-retrieval?spm=a2c4g.11186623.help-menu-31815.d_1_0_4_17_5.21777f15U9J2Ih&scm=20140722.H_2848615._.OR_help-T_cn~zh-V_1)

---

**Query Result Response Fields:**
Query results contain rich field information. For detailed descriptions, refer to the official documentation: [DoMetaQuery Response Field Descriptions](https://help.aliyun.com/zh/oss/developer-reference/dometaquery?scm=20140722.S_help%40%40%E6%96%87%E6%A1%A3%40%40419228._.ID_help%40%40%E6%96%87%E6%A1%A3%40%40419228-RL_DoMetaQuery-LOC_doc%7EUND%7Eab-OR_ser-PAR1_212a5d3d17637268919234719ddb6d-V_4-PAR3_o-RE_new5-P0_1-P1_0&spm=a2c4g.11186623.help-search.i26#4fe1eba66eidr)
