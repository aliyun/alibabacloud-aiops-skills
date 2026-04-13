# Success Verification Methods

## 1. ListTaskInstances Verification

### Expected Response Structure

```json
{
  "RequestId": "xxx-xxx-xxx",
  "PagingInfo": {
    "TotalCount": 10,
    "PageSize": 100,
    "PageNumber": 1,
    "TaskInstances": [
      {
        "Id": 12345,
        "TaskId": 1001,
        "TaskName": "ods_user_log",
        "Status": "Failure",
        "Bizdate": 1743350400000,
        "TriggerTime": 1743436800000,
        "Owner": "xxx"
      }
    ]
  }
}
```

### Verification Steps

1. Check response contains `PagingInfo` field
2. Check `TaskInstances` array contains queried instances
3. Check each instance contains `Id`, `Status`, `TaskName` and other key fields

### Verification Command

```bash
# Query and check returned instance count
aliyun dataworks-public list-task-instances \
  --region cn-hangzhou \
  --project-id <PROJECT_ID> \
  --bizdate <BIZDATE> \
  --status Failure \
  --user-agent AlibabaCloud-Agent-Skills | jq '.PagingInfo.TotalCount'
```

## 2. GetTaskInstanceLog Verification

### Expected Response Structure

```json
{
  "RequestId": "xxx-xxx-xxx",
  "TaskInstanceLog": "This is running log..."
}
```

### Verification Steps

1. Check response contains `TaskInstanceLog` field
2. Log content is not empty or contains valid information

### Verification Command

```bash
# Get log and check length
aliyun dataworks-public get-task-instance-log \
  --region cn-hangzhou \
  --id <TASK_INSTANCE_ID> \
  --user-agent AlibabaCloud-Agent-Skills | jq '.TaskInstanceLog | length'
```

## Common Error Handling

| Error Code | Description | Resolution |
|-------|------|---------|
| `InvalidParameter` | Parameter error | Check required parameters are correct |
| `Forbidden` | Insufficient permissions | Check RAM permission configuration |
| `ProjectNotFound` | Workspace not found | Verify ProjectId is correct |
| `InstanceNotFound` | Instance not found | Verify instance ID is correct |
