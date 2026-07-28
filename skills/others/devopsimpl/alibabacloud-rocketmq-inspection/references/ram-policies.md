# RAM Policies Required

This skill is **read-only**. Grant the following minimal read-only RAM permissions to the IAM/RAM user/role whose AccessKey is configured for `aliyun` CLI.

## Quick policy (recommended for AIOps users)

Attach these AliCloud system policies:

| System Policy | Purpose |
|---|---|
| `AliyunCloudMonitorReadOnlyAccess` | CMS `DescribeMetricList` / `DescribeMetricMetaList` |
| `AliyunMQReadOnlyAccess` | ONS (RocketMQ 4.x) read-only APIs |
| `AliyunRocketMQReadOnlyAccess` | RocketMQ 5.x read-only APIs |
| `AliyunSTSAssumeRoleAccess` (optional) | Only if using `--mode RamRoleArn` for cross-account access |

`sts:GetCallerIdentity` is allowed by default and does not require any explicit policy.

## Custom policy (least privilege)

If you prefer a single custom policy with only the exact actions this skill calls, use the following JSON:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "cms:DescribeMetricMetaList"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "mq:OnsInstanceInServiceList",
        "mq:OnsInstanceBaseInfo",
        "mq:OnsGroupList",
        "mq:OnsTopicList",
        "mq:OnsConsumerStatus"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rocketmq:ListInstances",
        "rocketmq:GetInstance",
        "rocketmq:ListConsumerGroups",
        "rocketmq:ListTopics",
        "rocketmq:GetConsumerGroup",
        "rocketmq:ListConsumerConnections",
        "rocketmq:GetConsumerGroupLag"
      ],
      "Resource": "*"
    }
  ]
}
```

## What this skill MUST NOT have

Per the skill's read-only policy declared in `SKILL.md`, do **not** grant any of the following permissions. They are not used and granting them broadens the blast radius unnecessarily:

- `cms:Create*`, `cms:Delete*`, `cms:Modify*`, `cms:Put*`
- `mq:On(s)Create*`, `mq:On(s)Delete*`, `mq:On(s)Modify*`, `mq:On(s)Mute*`
- `rocketmq:Create*`, `rocketmq:Delete*`, `rocketmq:Update*`, `rocketmq:Modify*`, `rocketmq:Send*`, `rocketmq:Reset*`
- Any `Write` or `*` actions on the above products

## Verifying

After attaching policies, run preflight:

```bash
bash scripts/preflight.sh
```

It exercises one API from each product (`sts get-caller-identity`, `cms describe-metric-meta-list`, `ons ons-instance-in-service-list`, `rocketmq list-instances`). All four must return success for full functionality.

## Multi-account / cross-account inspection

If inspecting RocketMQ instances in a different AliCloud account than the one whose AccessKey is configured, configure a profile with `--mode RamRoleArn` pointing to a role in the target account that has the policies above. See [aliyun CLI configure docs](https://help.aliyun.com/document_detail/121258.html).
