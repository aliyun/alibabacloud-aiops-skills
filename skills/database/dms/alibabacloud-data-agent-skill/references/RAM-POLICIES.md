# RAM Permission Policies

This Skill requires the following Alibaba Cloud RAM permissions:

## Required Permissions (Recommended)

Use a custom RAM policy with only the actions required by this Skill:

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
        "dms:ListTagMetaAsset",
        "dms:InitDataAgentPersonalWorkspace",
        "dms:ListDataCenterDatabase",
        "dms:ListDataCenterTable",
        "dms:AddDataCenterTable"
      ],
      "Resource": "*"
    }
  ]
}
```

## Optional Managed Policies

Managed full-access policies are broader than this Skill requires. Use them only
for temporary testing or accounts that are already governed by separate access
controls:

| Policy | Description |
|----------|------|
| `AliyunDMSDataAgentFullAccess` | Full access to Data Agent |
| `AliyunDMSFullAccess` | Full access to DMS Data Management Service |

## Configuration Instructions

1. Log in to [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/)
2. Create or select a user
3. Add the custom minimal permission policy to the user
4. Create AccessKey for Skill authentication
