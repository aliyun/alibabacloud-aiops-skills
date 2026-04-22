# RAM Policies

This document lists the minimum RAM permissions required for PAI-EAS service diagnosis.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eas:DescribeService",
        "eas:DescribeServiceLog",
        "eas:DescribeServiceEvent",
        "eas:DescribeServiceDiagnosis",
        "eas:DescribeServiceInstanceDiagnosis",
        "eas:ListServiceInstances",
        "eas:ListServiceContainers",
        "eas:DescribeServiceEndpoints",
        "eas:ListServices",
        "eas:DescribeResource",
        "eas:ListResources",
        "eas:DescribeGateway",
        "eas:ListGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

### EAS Service Diagnosis Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `eas:DescribeService` | Query service details | Check service status, get error messages |
| `eas:DescribeServiceLog` | Query service logs | View error logs, diagnose issues |
| `eas:DescribeServiceEvent` | Query service events | Understand event timeline, troubleshoot issues |
| `eas:DescribeServiceDiagnosis` | Service diagnosis report | Get diagnostic suggestions |
| `eas:DescribeServiceInstanceDiagnosis` | Instance diagnosis | Diagnose individual instance issues |
| `eas:ListServiceInstances` | List instances | Check instance status |
| `eas:ListServiceContainers` | List containers | Check container restart count |
| `eas:DescribeServiceEndpoints` | Query service endpoints | Get access URLs, troubleshoot network issues |
| `eas:ListServices` | List services | View service list, filter abnormal services |
| `eas:DescribeResource` | Query resource group details | Check dedicated resource group status |
| `eas:ListResources` | List resource groups | View available resource groups |
| `eas:DescribeGateway` | Query gateway details | Check gateway status, troubleshoot access issues |
| `eas:ListGateway` | List gateways | View available gateways |

## Permission Characteristics

This Skill only includes **read-only permissions** and does not involve any write operations:

- All permissions are `Describe*` or `List*` type
- Will not modify, create, or delete any resources
- Suitable for security auditing and issue diagnosis scenarios

## Permission Check

Use the following command to check current user permissions:

```bash
aliyun ram get-login-profile --UserName <username>
```

Or view user authorization policies through the RAM console.

## Least Privilege Principle

This Skill follows the principle of least privilege:

1. Only requests read-only permissions needed for diagnosis
2. Does not request any write permissions (e.g., `CreateService`, `DeleteService`)
3. Does not use wildcard permissions (e.g., `eas:*`)
