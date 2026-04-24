# Daily Operations: Inspection, Renewal, Troubleshooting

## Table of Contents

- [1. Cluster Inspection](#1-cluster-inspection): Quick inspection checklist, abnormal cluster discovery, expiration check
- [2. Renewal Management](#2-renewal-management): Expiration time, auto renewal settings
- [3. Troubleshooting](#3-troubleshooting): START_FAILED, TERMINATED_WITH_ERRORS, node abnormality, throttling

## 1. Cluster Inspection

### Quick Inspection Checklist

```bash
# 1. View all cluster statuses (focus on non-RUNNING states)
aliyun emr list-clusters --biz-region-id cn-hangzhou \
  --cluster-states RUNNING

# 2. View cluster details (focus on ClusterState, ExpireTime)
aliyun emr get-cluster --biz-region-id cn-hangzhou --cluster-id c-xxx

# 3. Check node group health
aliyun emr list-node-groups --biz-region-id cn-hangzhou --cluster-id c-xxx

# 4. Check abnormal nodes
aliyun emr list-nodes --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --node-states Stopped Terminated

# 5. Check all node running status
aliyun emr list-nodes --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --node-states Running
```

### Discover Abnormal Clusters

```bash
# Find all abnormal state clusters
aliyun emr list-clusters --biz-region-id cn-hangzhou \
  --cluster-states START_FAILED TERMINATED_WITH_ERRORS TERMINATE_FAILED
```

### Check Expiring Clusters

```bash
# View subscription clusters (check ExpireTime field)
aliyun emr list-clusters --biz-region-id cn-hangzhou \
  --payment-types Subscription
```

> **Timestamp Note**: ExpireTime, CreateTime etc. returned by API are all millisecond timestamps, need to convert to readable format when displaying.

## 2. Renewal Management

### View Expiration Time

```bash
# View subscription cluster expiration time
aliyun emr get-cluster --biz-region-id cn-hangzhou --cluster-id c-xxx
# Focus on ExpireTime field in response (millisecond timestamp)
```

### Set Auto Renewal

```bash
# Enable auto renewal (renew 1 month each time)
aliyun emr update-cluster-auto-renew --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --cluster-auto-renew true --cluster-auto-renew-duration 1 --cluster-auto-renew-duration-unit Month

# Enable auto renewal for all instances
aliyun emr update-cluster-auto-renew --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --cluster-auto-renew true --cluster-auto-renew-duration 1 --cluster-auto-renew-duration-unit Month \
  --renew-all-instances true
```

### Disable Auto Renewal

```bash
aliyun emr update-cluster-auto-renew --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --cluster-auto-renew false
```

## 3. Troubleshooting

### START_FAILED (Cluster Creation Failed)

```bash
# View failure reason
aliyun emr get-cluster --biz-region-id cn-hangzhou --cluster-id c-xxx
# Focus on Code and Message in StateChangeReason
```

| Common Cause | Diagnosis Method |
|---------|---------|
| VPC/VSwitch doesn't exist or not in same zone | `aliyun vpc describe-vswitches --vpc-id vpc-xxx` |
| Security group type error (enterprise security group) | `aliyun ecs describe-security-groups --security-group-id sg-xxx`, confirm Type=normal |
| Instance type stock insufficient | Change zone or spec, `aliyun emr list-instance-types ...` |
| RAM role missing | Check if AliyunECSInstanceForEMRRole exists |
| Key pair doesn't exist | `aliyun ecs describe-key-pairs --biz-key-pair-name my-keypair` |
| Account balance insufficient | Recharge then retry |

### TERMINATED_WITH_ERRORS (Cluster Abnormal Termination)

```bash
aliyun emr get-cluster --biz-region-id cn-hangzhou --cluster-id c-xxx
# Check StateChangeReason
```

| Common Cause | Description |
|---------|------|
| Account arrears | Pay-as-you-go clusters will be automatically released when in arrears |
| Disk full | System disk or data disk insufficient space causes service abnormality |
| OOM | Node memory insufficient, consider upgrading spec or expanding |

### Node Abnormality

```bash
# Find abnormal nodes
aliyun emr list-nodes --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --node-states Stopped Terminated

# View node group for specific node
aliyun emr get-node-group --biz-region-id cn-hangzhou --cluster-id c-xxx \
  --node-group-id ng-xxx
```

### Operation Denied

| Error | Cause | Solution |
|------|------|---------|
| `OperationDenied.ClusterStatus` | Cluster state doesn't allow current operation | Wait for cluster to become RUNNING then retry |

### API Throttling

| Error | Description | Solution |
|------|------|---------|
| `Throttling` | Request rate exceeded | Wait a few seconds then retry |

## Related Documentation

- When need to switch to other scenarios, please return to intent routing table in `SKILL.md` to select the appropriate reference document.