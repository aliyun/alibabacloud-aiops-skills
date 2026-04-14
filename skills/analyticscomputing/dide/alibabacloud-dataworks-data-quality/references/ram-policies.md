# DataWorks Data Quality RAM Policies

This document lists all RAM permissions required to use the DataWorks Data Quality skill.

> **Read-Only Skill**: All operations in this skill are read-only (Get/List). No write permissions are required.

## Permission Matrix

### Workspace Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListProjects | dataworks:ListProjects | List |

### Rule Template Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListDataQualityTemplates | dataworks:ListDataQualityTemplates | List |
| GetDataQualityTemplate | dataworks:GetDataQualityTemplate | Read |

### Data Quality Monitor Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListDataQualityScans | dataworks:ListDataQualityScans | List |
| GetDataQualityScan | dataworks:GetDataQualityScan | Read |

### Alert Rule Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListDataQualityAlertRules | dataworks:ListDataQualityAlertRules | List |
| GetDataQualityAlertRule | dataworks:GetDataQualityAlertRule | Read |

### Scan Run Permissions

| API Action | RAM Permission | Access Level |
|------------|----------------|--------------|
| ListDataQualityScanRuns | dataworks:ListDataQualityScanRuns | List |
| GetDataQualityScanRun | dataworks:GetDataQualityScanRun | Read |
| GetDataQualityScanRunLog | dataworks:GetDataQualityScanRunLog | Read |

## RAM Policy Example

### Minimum Permission Policy (Read-Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListProjects",
        "dataworks:ListDataQualityTemplates",
        "dataworks:GetDataQualityTemplate",
        "dataworks:ListDataQualityScans",
        "dataworks:GetDataQualityScan",
        "dataworks:ListDataQualityAlertRules",
        "dataworks:GetDataQualityAlertRule",
        "dataworks:ListDataQualityScanRuns",
        "dataworks:GetDataQualityScanRun",
        "dataworks:GetDataQualityScanRunLog"
      ],
      "Resource": "*"
    }
  ]
}
```

## Common Permission Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.Access` | Insufficient RAM permissions | Add the corresponding `dataworks:<Action>` permission |
| `PermissionDenied` | No operation permission | Check if the RAM policy is attached to the correct identity |
| `InvalidAccessKeyId.NotFound` | Invalid AccessKey | Check AccessKey configuration via `aliyun configure list` |
| `SignatureDoesNotMatch` | Signature mismatch | Check AccessKeySecret |

## References

- [DataWorks RAM Permission Guide](https://help.aliyun.com/zh/dataworks/user-guide/dataworks-ram-permissions)
- [RAM Console](https://ram.console.aliyun.com/)
