# RAM Policies for Video Translation Skill

This document lists all RAM permissions required for the Video Translation Skill.

## Permission List

### ICE (Intelligent Cloud Editing) Permissions

| Permission | Description | Usage |
|------------|-------------|-------|
| `ice:RegisterMediaInfo` | Register media info | Get MediaId |
| `ice:SubmitIProductionJob` | Submit intelligent production job | Subtitle extraction (CaptionExtraction) |
| `ice:QueryIProductionJob` | Query intelligent production job | Query subtitle extraction job status |
| `ice:GetSmartHandleJob` | Query intelligent job result | Query video translation job status |
| `ice:SubmitVideoTranslationJob` | Submit video translation job | Video translation core functionality |
| `ice:GetMediaInfo` | Query media info | Get final video URL |

### OSS Permissions

| Permission | Description | Usage |
|------------|-------------|-------|
| `oss:GetObject` | Read OSS object | Read input video |
| `oss:PutObject` | Write OSS object | Write translation result |
| `oss:ListObjects` | List OSS objects | Verify file existence |

## Complete RAM Policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ice:RegisterMediaInfo",
        "ice:SubmitIProductionJob",
        "ice:QueryIProductionJob",
        "ice:GetSmartHandleJob",
        "ice:SubmitVideoTranslationJob",
        "ice:GetMediaInfo"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:<your-input-bucket>/*",
        "acs:oss:*:*:<your-output-bucket>/*"
      ]
    }
  ]
}
```

## Permission Configuration Steps

1. Login to [RAM Console](https://ram.console.aliyun.com/)
2. Create a custom permission policy, paste the JSON above (replace bucket names)
3. Grant the policy to the RAM user or role that needs to use video translation

## Important Notes

- **Principle of Least Privilege**: Recommend limiting OSS permissions to specific buckets
- **Region Restriction**: If further restriction is needed, specify region in Resource
- **Subscription Purchase**: Even with `AliyunICEFullAccess` granted, if you encounter "not subscribed" error, you need to purchase a subscription package at [IMS Video Translation Product Page](https://help.aliyun.com/zh/ims/video-translation) before using the service