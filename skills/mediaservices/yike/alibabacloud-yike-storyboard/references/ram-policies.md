# RAM Policies - Yike Storyboard Skill

This document lists the RAM permissions required for the Yike Storyboard skill.

## Required Permissions

### ICE (Intelligent Cloud Editing) Permissions

| Permission | Action | Description |
|------------|--------|-------------|
| Get Upload Credentials | `ice:CreateYikeAssetUpload` | Get Yike asset upload STS credentials |
| Submit Storyboard Job | `ice:SubmitYikeStoryboardJob` | Submit Yike storyboard generation job |
| Query Job Status | `ice:GetYikeStoryboardJob` | Query Yike storyboard job status |

### OSS Permissions

OSS upload uses STS temporary credentials returned by `CreateYikeAssetUpload`. These credentials already include necessary OSS write permissions - no additional configuration required.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ice:CreateYikeAssetUpload",
        "ice:SubmitYikeStoryboardJob",
        "ice:GetYikeStoryboardJob"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Configuration Methods

### Method 1: Use System Policy

Attach the `AliyunICEFullAccess` system policy to your RAM user/role.

### Method 2: Use Custom Policy

1. Log in to [RAM Console](https://ram.console.aliyun.com)
2. Create a custom policy and paste the minimum permission policy above
3. Attach the policy to the corresponding RAM user/role

## Permission Troubleshooting

If you encounter permission-related errors:

1. Verify the current account/role has the permissions listed above
2. Use `aliyun sts get-caller-identity` to confirm current identity
3. Check for RAM policy conflicts (Deny policies take precedence)
4. Ensure the ICE service is activated in your account
