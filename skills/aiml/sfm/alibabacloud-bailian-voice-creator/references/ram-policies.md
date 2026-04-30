# RAM Policies for Bailian Voice Creator

This skill requires the following Alibaba Cloud RAM permissions to function properly.

## Required Permissions

| Service | Action | Description |
|---------|--------|-------------|
| modelstudio | `modelstudio:ListWorkspaces` | List workspaces (to obtain workspace ID) |
| modelstudio | `modelstudio:CreateApiKey` | Create a DashScope API Key |
| modelstudio | `modelstudio:DeleteApiKey` | Delete a DashScope API Key |

## Minimum Required Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelstudio:ListWorkspaces",
        "modelstudio:CreateApiKey",
        "modelstudio:DeleteApiKey"
      ],
      "Resource": "*"
    }
  ]
}
```

## How to Apply

1. Go to [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/users)
2. Select the target RAM user
3. Click "Add Permissions"
4. Choose one of the following:
   - **System Policy**: Search and select `AliyunBailianFullAccess`
   - **Custom Policy**: Create a custom policy using the JSON above and attach it

## Notes

- Permission changes may take up to 30 seconds to take effect
- If you encounter `403 Forbidden` errors, verify that the RAM user has been granted the permissions above
- If you only need TTS/ASR (not API Key management), no RAM permissions are required -- only a valid DASHSCOPE_API_KEY
