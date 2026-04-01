# RAM Permission Policies

This Skill requires the following Alibaba Cloud RAM permissions:

## Required Permissions

| Policy | Description |
|----------|------|
| `AliyunDMSFullAccess` | Full access to DMS Data Management Service |
| `AliyunDMSDataAgentFullAccess` | Full access to Data Agent |

## Minimal Permission Policy (Recommended)

If you only need to use Data Agent features, you can configure the following minimal permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:ListInstances",
        "dms:ListDatabases",
        "dms:ListTables",
        "dms:ListColumns",
        "dms:GetInstance",
        "dms:GetDatabase",
        "dms:GetTableTopology",
        "dms:GetMetaTableDetailInfo",
        "dms:DescribeInstance",
        "dms:CreateDataAgentSession",
        "dms:DescribeDataAgentSession",
        "dms:ListDataAgentSession",
        "dms:SendChatMessage",
        "dms:GetChatContent",
        "dms:DescribeDataAgentUsage",
        "dms:UpdateDataAgentSession",
        "dms:CreateDataAgentFeedback",
        "dms:DescribeFileUploadSignature",
        "dms:FileUploadCallback",
        "dms:ListFileUpload",
        "dms:DeleteFileUpload",
        "dms:ListDataCenterDatabase",
        "dms:ListDataCenterTable",
        "dms:AddDataCenterTable"
      ],
      "Resource": "*"
    }
  ]
}
```

## Configuration Instructions

1. Log in to [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/)
2. Create or select a user
3. Add the above permission policies to the user
4. Create AccessKey for Skill authentication
