# Scaling: Resource Queue Management

## Decision Guidance

### When to Scale Up?

| Indicator | Scale-up Threshold | Description |
|-----------|-------------------|-------------|
| Jobs pending for long time | Frequent queuing | Resource queue CU insufficient, unable to allocate new jobs |
| Job runtime significantly increased | 2x+ normal time | Too many concurrent jobs, severe resource contention |
| Kyuubi query latency increased | P99 latency doubled | Interactive queries need more resources |

### When to Scale Down?

| Indicator | Scale-down Threshold | Description |
|-----------|---------------------|-------------|
| Resource queue long idle | No jobs running for 1+ hour | Reduce CU quota to lower costs |
| Business low-peak period | Nights, weekends | Regular scale-down to save resources |

### What Resources to Scale?

| Problem | Solution |
|---------|----------|
| Severe job queuing | Scale up resource queue CU |
| Single job memory insufficient | Adjust job Spark parameters (executor.memory) |
| Too many concurrent jobs | Scale up resource queue CU or create multiple queues |

## 1. View Resource Queues

### View Queue List

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/queues --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

Key information in the response:
- `queueName`: Queue name
- `queueStatus`: Queue status
- `maxResource`: Resource limit (CU)
- `usedResource`: Used resources (CU)

## 2. Modify Resource Queues

### Scale Up Resource Queue

Before scaling up, confirm:
1. Workspace ID
2. Queue name
3. Target CU quantity

> **Important Constraint**: The sum of CU across all queues in a workspace cannot exceed the workspace total CU limit. For example, if workspace has 8 CU and root_queue has 6 CU allocated, dev_queue can only have max 2 CU. To scale beyond the limit, first scale down other queues to free up space.

After confirming the operation, need user explicit confirmation before execution.

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/queues/action/edit?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"workspaceId":"w-xxx","workspaceQueueName":"dev_queue","resourceSpec":{"cu":64,"maxCu":128}}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Scale Down Resource Queue

> **Note**: Scaling down may increase wait time for queued jobs. If running jobs use resources exceeding the scaled-down quota, scaling down won't affect running jobs, but new jobs may need to wait.

```bash
aliyun emr-serverless-spark POST "/api/v1/workspaces/queues/action/edit?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{"workspaceId":"w-xxx","workspaceQueueName":"dev_queue","resourceSpec":{"cu":16}}' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Verify After Scaling

```bash
# View queue status to confirm change生效
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/queues --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

## Common Issues

### Scale-up Failed

| Error Code | Error Message | Cause | Solution |
|------------|---------------|-------|----------|
| InvalidParameter | CU quantity not in allowed range | CU quantity invalid | Check if CU quantity is valid |
| UnSupportedOperator | workspace rest cpu is not enough | Queue CU total exceeds workspace limit | Scale down other queues first, or increase workspace CU quota |
| OperationDenied | Operation not allowed | Workspace status abnormal or insufficient permissions | Check workspace status and permissions |
| QuotaExceeded | Quota exceeded | Exceeded account-level quota | Contact Alibaba Cloud to increase quota |

### Scale-down Considerations

- Scaling down won't abort running jobs
- After scaling down, newly submitted large-resource jobs may queue and wait
- Recommend executing scale-down operations during business low-peak periods

### Continuous Operation Considerations

- When modifying multiple queues continuously, need to wait for previous operation to complete before executing next, otherwise may report `Error.Internal: fail to update app instance queue`
- Recommend waiting 5-10 seconds after each queue change before executing next queue operation

## Related Documentation

- [Workspace Lifecycle](workspace-lifecycle.md) - Create, query, manage workspaces
- [Job Management](job-management.md) - Submit, monitor, diagnose Spark jobs
- [Kyuubi Service](kyuubi-service.md) - Interactive SQL gateway management
- [API Parameter Reference](api-reference.md) - Complete parameter documentation