# RAM Permission Policies

This skill involves the following Alibaba Cloud Chat App Message Service (CAMS) APIs and requires corresponding RAM permissions.

## Required Permissions

| API Name | Permission Action | Description |
|----------|-------------------|-------------|
| SendChatappMessage | `cams:SendChatappMessage` | Send messages |
| SendChatappMassMessage | `cams:SendChatappMassMessage` | Batch send messages |
| ListChatappTemplate | `cams:ListChatappTemplate` | Query template list |
| GetChatappTemplateDetail | `cams:GetChatappTemplateDetail` | Query template detail |
| ListChatappMessage | `cams:ListChatappMessage` | Query message list |

## Minimum Permission Policy (JSON)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cams:SendChatappMessage",
        "cams:SendChatappMassMessage",
        "cams:ListChatappTemplate",
        "cams:GetChatappTemplateDetail",
        "cams:ListChatappMessage"
      ],
      "Resource": "*"
    }
  ]
}
```

## Built-in Policies

Alibaba Cloud does not currently provide an independent built-in policy for CAMS. It is recommended to authorize via the custom policy above.

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
