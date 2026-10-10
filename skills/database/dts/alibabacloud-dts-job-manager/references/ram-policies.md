# RAM permissions

This Skill calls Alibaba Cloud DTS only through `dtscli`, using the caller's existing Alibaba Cloud CLI identity (OAuth, STS token, or AccessKey). It does not create RAM users, roles, or policies. The identity must be allowed to call the APIs in the [API allowlist](api-allowlist.md). Product code is `dts`, API version is `2020-01-01`, and each RAM action is `dts:<ApiName>`.

When a call fails with access denied, show this document and ask a RAM administrator to grant the missing actions. Do not request an AccessKey, change the profile, or call an API outside the allowlist to work around the denial.

## Actions

| Action | Access | Purpose |
| --- | --- | --- |
| `dts:DescribeDtsJobDetail` | Read | Read one synchronization job |
| `dts:DescribeDtsJobs` | Read | List jobs, find a job by name, or verify a purchase |
| `dts:DescribePreCheckStatus` | Read | Read precheck status |
| `dts:DescribeDtsInstancePrice` | Read | Quote a synchronization instance class |
| `dts:DescribeInstances` | Read | Resolve a cloud database instance ID from its name |
| `dts:RunEndpointLinkTest` | Read | Test source and destination connectivity before purchase |
| `dts:CreateDtsInstance` | Manage | Purchase the synchronization instance |
| `dts:ConfigureDtsJob` | Manage | Configure the purchased instance |
| `dts:ModifyDtsJobName` | Manage | Rename a job |
| `dts:StartDtsJob` | Manage | Start or resume a job |
| `dts:SuspendDtsJob` | Manage | Suspend a job and keep the instance |

Read actions are enough to list jobs, inspect status, and query a price. Creating, configuring, renaming, starting, or suspending a job also needs the matching manage action.

## Example policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dts:DescribeDtsJobDetail",
        "dts:DescribeDtsJobs",
        "dts:DescribePreCheckStatus",
        "dts:DescribeDtsInstancePrice",
        "dts:DescribeInstances",
        "dts:RunEndpointLinkTest",
        "dts:CreateDtsInstance",
        "dts:ConfigureDtsJob",
        "dts:ModifyDtsJobName",
        "dts:StartDtsJob",
        "dts:SuspendDtsJob"
      ],
      "Resource": "*"
    }
  ]
}
```

Narrow `Resource` only when the account's DTS resource ARN scheme is known. Do not omit an action that this Skill's allowlist still calls.
