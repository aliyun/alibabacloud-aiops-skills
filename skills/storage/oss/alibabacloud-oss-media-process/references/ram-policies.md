# RAM Permissions

Required RAM permissions for this Skill.

## OSS Permissions (required for all operations)

`oss:GetObject` — Read objects from the OSS bucket (used for url/download/info modes)

`oss:PutObject` — Write objects to the OSS bucket (used for save mode and upload operations)

`oss:ProcessObject` — Execute media processing operations on objects (used for save mode and async operations)

`oss:PostProcessTask` — Submit asynchronous processing tasks (used for async video/audio operations via x-oss-async-process)

`oss:DeleteObject` — Delete temporary objects from the OSS bucket (used by blindwatermark-embed in download/url mode to clean up temp files, and by --uri auto-cleanup)

`oss:SignUrl` — Generate signed URLs for processed media (used for url output mode)

## Check Permissions (required for check_permissions.py)

`oss:GetBucketInfo` — Verify bucket accessibility and permissions

## IMM Permissions (required for image-intelligent operations)

`imm:CreateDecodeBlindWatermarkTask` — Create a blind watermark extraction task

`imm:GetTask` — Query task status during blind watermark extraction polling

`imm:GetDecodeBlindWatermarkResult` — Retrieve blind watermark extraction results

## IMM Administration Permissions (required for imm_admin.py)

`imm:CreateProject` — Create an IMM project

`imm:ListProjects` — List all IMM projects

`imm:GetProject` — Get details of an IMM project

`imm:DeleteProject` — Delete an IMM project

`imm:AttachOSSBucket` — Bind an OSS bucket to an IMM project

`imm:DetachOSSBucket` — Unbind an OSS bucket from an IMM project

## Recommended Policy

For basic media processing (image + video + audio):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:ProcessObject",
        "oss:PostProcessTask",
        "oss:DeleteObject",
        "oss:SignUrl",
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:<your-bucket>",
        "acs:oss:*:*:<your-bucket>/*"
      ]
    }
  ]
}
```

For media processing + IMM operations:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:ProcessObject",
        "oss:PostProcessTask",
        "oss:DeleteObject",
        "oss:SignUrl",
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:<your-bucket>",
        "acs:oss:*:*:<your-bucket>/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "imm:CreateDecodeBlindWatermarkTask",
        "imm:GetTask",
        "imm:GetDecodeBlindWatermarkResult",
        "imm:GetProject",
        "imm:CreateProject",
        "imm:ListProjects",
        "imm:DeleteProject",
        "imm:AttachOSSBucket",
        "imm:DetachOSSBucket"
      ],
      "Resource": "*"
    }
  ]
}
```
