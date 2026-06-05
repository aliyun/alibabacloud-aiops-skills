# RAM Policies — Required Permissions

Product: `zero2staff`

## Required Actions

| Permission | API Action | Description |
|------------|-----------|-------------|
| `zero2staff:CreateAIStaffConversation` | CreateAIStaffConversation | Create conversation with site instance |
| `zero2staff:CreateAIStaffChat` | CreateAIStaffChat | Fire async chat message |
| `zero2staff:RetryAIStaffChat` | RetryAIStaffChat | Retry a failed chat |
| `zero2staff:ListAIStaffChatEvents` | ListAIStaffChatEvents | Fetch incremental SSE events |
| `zero2staff:ListAIStaffChatMessages` | ListAIStaffChatMessages | Query chat messages |
| `zero2staff:GetAIStaffPreviewUrl` | GetAIStaffPreviewUrl | Get site preview URL |

## Least-Privilege Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "zero2staff:CreateAIStaffConversation",
        "zero2staff:CreateAIStaffChat",
        "zero2staff:RetryAIStaffChat",
        "zero2staff:ListAIStaffChatEvents",
        "zero2staff:ListAIStaffChatMessages",
        "zero2staff:GetAIStaffPreviewUrl"
      ],
      "Resource": "*"
    }
  ]
}
```
