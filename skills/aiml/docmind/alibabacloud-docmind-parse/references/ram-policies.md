# RAM Permission Policies

This skill requires access to the Alibaba Cloud DocMind API service (`docmind-api`). The required RAM permissions are listed below.

## Required API Permissions

| API Name | Action | Description |
|----------|--------|-------------|
| SubmitDocParserJob | `docmind-api:SubmitDocParserJob` | Submit a document parsing task |
| SubmitDocParserJobAdvance | `docmind-api:SubmitDocParserJobAdvance` | Submit a document parsing task (advanced, supports OSS files) |
| QueryDocParserStatus | `docmind-api:QueryDocParserStatus` | Query document parsing task status |
| GetDocParserResult | `docmind-api:GetDocParserResult` | Retrieve document parsing results |

## Least-Privilege Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "docmind-api:SubmitDocParserJob",
        "docmind-api:SubmitDocParserJobAdvance",
        "docmind-api:QueryDocParserStatus",
        "docmind-api:GetDocParserResult"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

## System Policies

Alibaba Cloud does not provide a built-in system policy for the DocMind API. Use the custom policy above instead.

## Resource-Level Authorization

All DocMind API operations do not support resource-level authorization; `Resource` must be set to `*`.

## Credential Configuration

POP mode automatically obtains credentials through the Alibaba Cloud default credential chain, supporting the following methods (in priority order):

1. Environment variables: `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. Config file: `~/.alibabacloud/credentials`
3. ECS/RAM role: automatically obtained from the instance metadata service

In ECS/ACK and similar environments, prefer using instance RAM roles over hard-coded AccessKeys.
