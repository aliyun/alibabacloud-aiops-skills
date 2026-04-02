# RAM Policies for alibabacloud-video-editor

This document lists the RAM permissions required to use this Skill.

## Required Permissions

### ICE (Intelligent Media Services) Permissions

- `ice:SubmitMediaProducingJob` — Submit media editing and synthesis tasks
- `ice:GetMediaProducingJob` — Query media editing and synthesis task status
- `ice:GetMediaInfo` — Get media information (used to obtain the authenticated URL of the output video)

### OSS (Object Storage Service) Permissions

If you need to upload local materials to OSS, the following permissions are also required:

- `oss:PutObject` — Upload files to OSS
- `oss:GetObject` — Read OSS files
- `oss:ListBuckets` — List Buckets (used to select the output Bucket)

## Recommended System Policies

You can choose to use the following system policies for quick authorization:

- `AliyunICEFullAccess` — Full access permissions for ICE service
- `AliyunOSSFullAccess` — Full access permissions for OSS service (if OSS upload functionality is required)

## Minimum Permission Policy Example

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ice:SubmitMediaProducingJob",
        "ice:GetMediaProducingJob",
        "ice:GetMediaInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

## Official RAM Documentation

- [RAM User Authorization Documentation](https://help.aliyun.com/zh/ims/user-guide/create-and-authorize-a-ram-user-1)
- [ICE Permissions Documentation](https://help.aliyun.com/zh/ims/developer-reference/China Site/Chinese8China Site/Chinese0China Site/Chinese8China Site/Chinese2China Site/Chinese8)
