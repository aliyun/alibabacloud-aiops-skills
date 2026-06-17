# RAM Policies for PAI-Rec Diagnosis Skill

This document lists all RAM (Resource Access Management) permissions required by the PAI-Rec Engine Diagnosis and Configuration Validation skill.

## Overview

This skill requires read-only permissions for:
- PAI-EAS (Elastic Algorithm Service) - for service information and logs
- PAI-RecService - for engine configuration management

## Required Permissions

### PAI-EAS Permissions

| API Action | Permission | Purpose |
|------------|-----------|---------|
| `DescribeService` | `eas:DescribeService` | Retrieve EAS service details including configuration and resource IDs |
| `DescribeServiceLog` | `eas:DescribeServiceLog` | Query service logs to trace request processing |

### PAI-RecService Permissions

| API Action | Permission | Purpose |
|------------|-----------|----------|
| `ListEngineConfigs` | `pairecservice:ListEngineConfigs` | List engine configuration versions |
| `GetEngineConfig` | `pairecservice:GetEngineConfig` | Retrieve specific engine configuration details |
| `GetExperimentGroup` | `pairecservice:GetExperimentGroup` | Retrieve experiment group details and override config |
| `GetExperiment` | `pairecservice:GetExperiment` | Retrieve experiment details and override config |

## Complete RAM Policy Document

### Minimal Policy (Read-Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eas:DescribeService",
        "eas:DescribeServiceLog"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "pairecservice:ListEngineConfigs",
        "pairecservice:GetEngineConfig",
        "pairecservice:GetExperimentGroup",
        "pairecservice:GetExperiment"
      ],
      "Resource": "*"
    }
  ]
}
```

### Resource-Specific Policy (Recommended)

For better security, restrict access to specific resources:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eas:DescribeService",
        "eas:DescribeServiceLog"
      ],
      "Resource": [
        "acs:eas:*:*:service/<your-service-name>",
        "acs:eas:*:*:cluster/<your-cluster-id>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "pairecservice:ListEngineConfigs",
        "pairecservice:GetEngineConfig",
        "pairecservice:GetExperimentGroup",
        "pairecservice:GetExperiment"
      ],
      "Resource": [
        "acs:pairecservice:*:*:instance/<your-instance-id>"
      ]
    }
  ]
}
```

## Permission Scope

### Service-Level Permissions

- **EAS Service**: Read access to service configurations and logs
- **PAI-Rec Instance**: Read access to engine configurations

### Data-Level Permissions

- No write permissions required
- No resource creation/deletion permissions required
- Read-only access to configurations and logs

## Applying Permissions

### Using RAM Console

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Users** or **Roles**
3. Select the target principal
4. Click **Add Permissions**
5. Choose **Custom Policy** and paste the policy JSON above
6. Click **OK** to apply

### Using Aliyun CLI

Create a custom policy:

```bash
aliyun ram create-policy \
  --policy-name PAIRecDiagnosisReadOnly \
  --policy-document '{
    "Version": "1",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "eas:DescribeService",
          "eas:DescribeServiceLog",
          "pairecservice:ListEngineConfigs",
          "pairecservice:GetEngineConfig",
          "pairecservice:GetExperimentGroup",
          "pairecservice:GetExperiment"
        ],
        "Resource": "*"
      }
    ]
  }'
```

Attach policy to user:

```bash
aliyun ram attach-policy-to-user \
  --policy-name PAIRecDiagnosisReadOnly \
  --policy-type Custom \
  --user-name <your-user-name>
```

## Troubleshooting Permission Issues

### Common Permission Errors

1. **Forbidden.RAM**
   - Error: User not authorized to perform operation
   - Solution: Ensure all required permissions are granted
   - Check: Verify policy is attached and resources match

2. **InvalidAccessKeyId.NotFound**
   - Error: Access key does not exist
   - Solution: Verify credentials are configured correctly
   - Check: Run `aliyun configure list`

3. **Forbidden.SubUser**
   - Error: Sub-account lacks permissions
   - Solution: Contact account admin to grant permissions
   - Check: Verify you're using the correct account

### Verification Steps

After applying permissions, verify access:

```bash
# Test EAS service access
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name>

# Test PAI-Rec config access
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id>
```

## Security Best Practices

1. **Principle of Least Privilege**: Grant only required permissions
2. **Resource-Specific Policies**: Limit access to specific instances/services
3. **Regular Audits**: Review and update permissions periodically
4. **Separate Roles**: Use different roles for different environments (Prod/Pre)
5. **Credential Rotation**: Rotate access keys regularly
6. **Audit Logging**: Enable ActionTrail to track API calls

## Related Documentation

- [RAM Overview](https://www.alibabacloud.com/help/ram/product-overview/)
- [EAS API Reference](https://www.alibabacloud.com/help/eas/developer-reference/)
- [PAI-RecService API Reference](https://www.alibabacloud.com/help/pai/developer-reference/)
