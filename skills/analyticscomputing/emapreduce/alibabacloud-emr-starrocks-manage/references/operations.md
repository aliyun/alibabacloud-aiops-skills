# Daily Operations: Configuration, Maintenance, SSL, Billing, Gateway

## 1. Configuration Changes

### View Current Configuration

```bash
# View all configurations
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx

# View configurations of a specific type
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx --ConfigType fe

# View a specific configuration item
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx --ConfigKey query_timeout

# View only modifiable configurations
aliyun starrocks DescribeInstanceConfigs --InstanceId c-xxx --AllowModify true
```


### View Configuration Change History

```bash
aliyun starrocks DescribeConfigHistory --InstanceId c-xxx
```

## Common Issues

### Configuration Change Failure

| Error Message | Cause | Solution |
|--------------|-------|----------|
| InvalidParameter | Configuration item does not exist | Check if ConfigKey is correct |
| OperationDenied.InstanceStatus | Instance status does not allow the operation | Wait for the instance to reach running status |
| modify reason is empty | Reason parameter not provided | Add `--Reason "modification reason"` parameter |

### Restart Timeout

If the restart has not completed after more than 10 minutes:

1. Query instance status to confirm if it is normal
2. If the issue persists, contact Alibaba Cloud technical support

### Version Upgrade Failure

| Error Message | Cause | Solution |
|--------------|-------|----------|
| VersionNotSupport | Target version not supported | Check available versions returned by QueryUpgradableVersions |
| OperationDenied | Current status does not allow upgrade | Wait for the instance to reach running status |

## Related Documents

- [Instance Full Lifecycle](instance-lifecycle.md) - Planning, creation, management
- [API Parameter Reference](api-reference.md) - Complete parameter documentation
