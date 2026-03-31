# RAM Permission Policies

## Required Permissions

The following RAM permissions are required for each feature of this project:

### Bucket Basic Operations

- `oss:GetBucketInfo` -- Query Bucket basic information (region, storage class, etc.)
- `oss:ListObjects` -- List files in the Bucket (V1)
- `oss:ListObjectsV2` -- List files in the Bucket (V2)

### File Upload and Download

- `oss:GetObject` -- Download (read) file content
- `oss:PutObject` -- Upload (write) files to the Bucket
- `oss:DeleteObject` -- Delete files from the Bucket

### Data Index and Semantic Search

- `oss:OpenMetaQuery` -- Enable metadata management (includes AI content awareness configuration)
- `oss:DoMetaQuery` -- Execute metadata queries (scalar search / vector semantic search)
- `oss:GetMetaQueryStatus` -- Query data index status
- `oss:CloseMetaQuery` -- Close data index

## Minimum Permission Policy

The following is the minimum RAM permission policy JSON required for OSS vector search and AI content awareness features:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetBucketInfo",
        "oss:ListObjects",
        "oss:ListObjectsV2",
        "oss:GetObject",
        "oss:PutObject",
        "oss:OpenMetaQuery",
        "oss:DoMetaQuery",
        "oss:GetMetaQueryStatus",
        "oss:CloseMetaQuery"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name",
        "acs:oss:*:*:your-bucket-name/*"
      ]
    }
  ]
}
```

## Read-Only Query Permissions

If the application only needs to perform semantic searches, the following minimum read-only permissions can be used:

- `oss:DoMetaQuery` -- Execute metadata queries
- `oss:GetMetaQueryStatus` -- Query data index status
- `oss:GetObject` -- Download retrieved files

Corresponding policy JSON:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:DoMetaQuery",
        "oss:GetMetaQueryStatus"
      ],
      "Resource": "acs:oss:*:*:your-bucket-name"
    },
    {
      "Effect": "Allow",
      "Action": "oss:GetObject",
      "Resource": "acs:oss:*:*:your-bucket-name/*"
    }
  ]
}
```

## Service Role Authorization

When using the data index feature for the first time, you need to authorize the OSS service role `AliyunMetaQueryDefaultRole`:

1. The OSS Console will automatically prompt for authorization when enabling data index
2. This role allows the OSS service to manage data indexes in the Bucket

**Service Role Permission Scope:**
- Read file content in the Bucket for AI analysis
- Build and manage vector indexes
- Process incremental file updates

## Important Notes

1. **Resource Scope**: It is recommended to replace `your-bucket-name` with the specific Bucket name to avoid over-authorization
2. **Region Restrictions**: OSS resources are region-level; you can specify region restrictions in the Resource field
3. **Regular Audits**: Regularly review and clean up permissions that are no longer needed
4. **Use STS**: For temporary access scenarios, it is recommended to use STS temporary credentials instead of long-term AccessKeys

## Reference Links

- [OSS Access Control Overview](https://help.aliyun.com/zh/oss/user-guide/access-control-1)
- [RAM Policy Syntax](https://help.aliyun.com/zh/ram/user-guide/policy-syntax-and-structure)
