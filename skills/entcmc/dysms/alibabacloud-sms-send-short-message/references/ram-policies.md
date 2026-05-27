# RAM Policies

This Skill calls the Alibaba Cloud Short Message Service (dysmsapi) OpenAPIs and therefore
requires the following RAM permissions.

## Required Permissions

| Action                       | Description                       | Required |
| ---------------------------- | --------------------------------- | -------- |
| `dysms:SendSms`              | Send an SMS                       | Yes      |
| `dysms:SendBatchSms`         | Batch send SMS (per-recipient sign/template params, up to 100) | Yes      |
| `dysms:GetSmsSign`           | Query signature approval status   | No       |
| `dysms:GetSmsTemplate`       | Query template approval status    | No       |
| `dysms:QuerySmsSignList`     | Query the signature list          | No       |
| `dysms:QuerySmsTemplateList` | Query the template list           | No       |
| `dysms:QuerySendDetails`     | Query SMS send details            | No       |
| `dysms:QuerySendStatistics`  | Query SMS send statistics         | No       |
| `dysms:QuerySmsQualificationRecord`   | List SMS qualification records   | No       |
| `dysms:QuerySingleSmsQualification`   | Get single qualification detail  | No       |

## Minimum Permission Policy

Send SMS only (least privilege). If you also need batch send, add
`dysms:SendBatchSms` to the `Action` list:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dysms:SendSms",
      "Resource": "*"
    }
  ]
}
```

## Full Permission Policy

Send SMS plus query signatures, templates, and send status:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dysms:SendSms",
        "dysms:SendBatchSms",
        "dysms:GetSmsSign",
        "dysms:GetSmsTemplate",
        "dysms:QuerySmsSignList",
        "dysms:QuerySmsTemplateList",
        "dysms:QuerySendDetails",
        "dysms:QuerySendStatistics",
        "dysms:QuerySmsQualificationRecord",
        "dysms:QuerySingleSmsQualification"
      ],
      "Resource": "*"
    }
  ]
}
```

## How to Apply

1. Sign in to the [RAM console](https://ram.console.aliyun.com/).
2. Create a custom policy and paste the JSON above.
3. Attach the policy to the appropriate RAM user or role.
