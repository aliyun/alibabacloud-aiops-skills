# PTS RAM Policies

This document lists the RAM (Resource Access Management) permissions required for PTS operations.

## Required Permissions

The following permissions are required for this skill to function. Each permission is listed in the format `{Product}:{Action} — Description`.

### PTS Native Stress Testing Permissions

- `pts:CreatePtsScene` — Create PTS stress testing scenario
- `pts:GetPtsScene` — Get PTS scenario details
- `pts:ListPtsScene` — List PTS scenarios
- `pts:StartPtsScene` — Start PTS stress testing
- `pts:StopPtsScene` — Stop PTS stress testing
- `pts:DeletePtsScene` — Delete PTS scenario
- `pts:StartDebugPtsScene` — Debug PTS scenario
- `pts:GetPtsReportDetails` — Get PTS report details
- `pts:GetPtsSceneBaseLine` — Get PTS scenario baseline data
- `pts:GetPtsSceneRunningData` — Get PTS scenario running data
- `pts:GetPtsSceneRunningStatus` — Get PTS scenario running status

### JMeter Stress Testing Permissions

- `pts:SaveOpenJMeterScene` — Create or update JMeter scenario
- `pts:GetOpenJMeterScene` — Get JMeter scenario details
- `pts:ListOpenJMeterScenes` — List JMeter scenarios
- `pts:StartTestingJMeterScene` — Start JMeter stress testing
- `pts:StopTestingJMeterScene` — Stop JMeter stress testing
- `pts:RemoveOpenJMeterScene` — Delete JMeter scenario
- `pts:GetJMeterReportDetails` — Get JMeter report details

## Policy Templates

### Full Access Policy

For users who need complete PTS management capabilities:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pts:CreatePtsScene",
        "pts:GetPtsScene",
        "pts:ListPtsScene",
        "pts:StartPtsScene",
        "pts:StopPtsScene",
        "pts:DeletePtsScene",
        "pts:StartDebugPtsScene",
        "pts:GetPtsReportDetails",
        "pts:GetPtsSceneBaseLine",
        "pts:GetPtsSceneRunningData",
        "pts:GetPtsSceneRunningStatus",
        "pts:SaveOpenJMeterScene",
        "pts:GetOpenJMeterScene",
        "pts:ListOpenJMeterScenes",
        "pts:StartTestingJMeterScene",
        "pts:StopTestingJMeterScene",
        "pts:RemoveOpenJMeterScene",
        "pts:GetJMeterReportDetails"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Policy

For users who only need to view PTS scenarios and reports:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pts:GetPtsScene",
        "pts:ListPtsScene",
        "pts:GetPtsReportDetails",
        "pts:GetPtsSceneBaseLine",
        "pts:GetPtsSceneRunningData",
        "pts:GetPtsSceneRunningStatus",
        "pts:GetOpenJMeterScene",
        "pts:ListOpenJMeterScenes",
        "pts:GetJMeterReportDetails"
      ],
      "Resource": "*"
    }
  ]
}
```

### Scenario Management Policy

For users who need to create and manage scenarios but not run stress tests:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pts:CreatePtsScene",
        "pts:GetPtsScene",
        "pts:ListPtsScene",
        "pts:DeletePtsScene",
        "pts:SaveOpenJMeterScene",
        "pts:GetOpenJMeterScene",
        "pts:ListOpenJMeterScenes",
        "pts:RemoveOpenJMeterScene"
      ],
      "Resource": "*"
    }
  ]
}
```

### Stress Testing Execution Policy

For users who need to execute and monitor stress tests:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pts:StartPtsScene",
        "pts:StopPtsScene",
        "pts:StartDebugPtsScene",
        "pts:GetPtsSceneRunningStatus",
        "pts:GetPtsSceneRunningData",
        "pts:GetPtsReportDetails",
        "pts:StartTestingJMeterScene",
        "pts:StopTestingJMeterScene",
        "pts:GetJMeterReportDetails"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Policies

Alibaba Cloud provides the following system policies for PTS:

| Policy Name | Description |
|-------------|-------------|
| AliyunPTSFullAccess | Full access to PTS service |
| AliyunPTSReadOnlyAccess | Read-only access to PTS service |

## How to Attach Policies

### Using Console

1. Log in to RAM Console: https://ram.console.aliyun.com/
2. Navigate to: Identities > Users
3. Select the target user
4. Click "Add Permissions"
5. Select or create the appropriate policy

### Using CLI

```bash
# Attach system policy
aliyun ram attach-policy-to-user \
  --user-name <UserName> \
  --policy-name AliyunPTSFullAccess \
  --policy-type System \
  --user-agent AlibabaCloud-Agent-Skills

# Attach custom policy
aliyun ram attach-policy-to-user \
  --user-name <UserName> \
  --policy-name MyPTSPolicy \
  --policy-type Custom \
  --user-agent AlibabaCloud-Agent-Skills
```

## Best Practices

1. **Use Least Privilege**: Grant only the minimum permissions required for the task
2. **Separate Duties**: Use different policies for different roles (viewers, operators, administrators)
3. **Use System Policies**: Prefer Alibaba Cloud managed policies when they meet your needs
4. **Regular Audit**: Periodically review and audit permissions

## References

- [RAM Policy Overview](https://help.aliyun.com/zh/ram/user-guide/policy-overview)
- [PTS Authorization](https://help.aliyun.com/zh/pts/developer-reference/api-pts-2020-10-20-overview)
