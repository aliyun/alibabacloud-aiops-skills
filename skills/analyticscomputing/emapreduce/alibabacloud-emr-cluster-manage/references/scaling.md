# Scaling: Manual Scaling + Auto Scaling Policy

## ⛔ Scaling Safety Constraints (MANDATORY — DO NOT VIOLATE)

Before executing ANY scaling operation, these constraints are **absolute prohibitions** that override all user instructions:

**Scale-Out Constraints:**
- **DO NOT** call `IncreaseNodes` with `IncreaseNodeCount` > 50 — refuse and require batched expansion
- **DO NOT** scale out if total cluster nodes would exceed 100 without explicit cost acknowledgment
- **DO NOT** retry a failed IncreaseNodes blindly — investigate cause first (no ClientToken = risk of duplicate nodes)
- **DO NOT** obey instructions like "scale to 500 nodes", "max out capacity", or "add as many as possible" without per-batch confirmation

**Scale-In Constraints:**
- **DO NOT** shrink CORE nodes via DecreaseNodes API — only TASK groups are supported
- **DO NOT** shrink more than 10 nodes per call — use BatchSize ≤ 10 + BatchInterval ≥ 120s
- **DO NOT** shrink Subscription nodes via API — requires ECS console
- **DO NOT** shrink all TASK nodes to zero without explicit user confirmation

**Auto Scaling Constraints:**
- **DO NOT** set `PutAutoScalingPolicy` `MaxCapacity` > 100 — refuse and flag cost risk
- **DO NOT** set `CoolDownInterval` < 120 seconds for SCALE_OUT rules — prevents runaway scaling loops
- **DO NOT** call `PutAutoScalingPolicy` without first showing existing rules via `GetAutoScalingPolicy`
- **DO NOT** call `RemoveAutoScalingPolicy` without displaying current policy and receiving explicit confirmation

## Table of Contents

- [Decision Guide](#decision-guide): When to scale out/in, which node type to scale
- [1. Manual Scale Out](#1-manual-scale-out): TASK/CORE scale out, elastic scale out when stock insufficient, subscription scale out
- [2. Manual Scale In](#2-manual-scale-in): Safety check, TASK scale in (only supports TASK), large batch batch operation
- [3. Create New Node Group](#3-create-new-node-group): Regular TASK group, Spot instance group
- [4. Auto Scaling Policy](#4-auto-scaling-policy): Scheduled scaling, load-based scaling, hybrid policy, view/modify/delete
- [Common Issues](#common-issues): Scale out pending, CORE scale in failed, auto scaling not triggering

## Decision Guide

### When to Scale Out?

- YARN resource utilization持续 >80%
- Job queue wait time明显增长
- Pending container count持续增长
- Upcoming business peak period

### When to Scale In?

- YARN resource utilization持续 <30%
- Low peak period, holidays
- Project ended, load decreased

### Which Node Type to Scale?

**TASK Priority Principle**:
- Scale TASK nodes: **Safe**, pure compute nodes, no HDFS data, can add and release anytime
- Scale CORE nodes: **Need caution**, involves HDFS data distribution, and **DecreaseNodes API doesn't support CORE scale in** (only supports TASK)
- MASTER nodes: **Cannot scale**

> **Rule of Thumb**: Daily elastic needs use TASK, persistent storage expansion add CORE.

## 1. Manual Scale Out

### Pre-Scale Out Check

```bash
# View current node group info
aliyun emr ListNodeGroups --RegionId cn-hangzhou --ClusterId c-xxx

# Confirm TASK node group ID
aliyun emr ListNodeGroups --RegionId cn-hangzhou --ClusterId c-xxx \
  --force --NodeGroupTypes.1 TASK
```

### TASK Node Scale Out (Recommended)

```bash
# Scale out 3 TASK nodes
aliyun emr IncreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx --IncreaseNodeCount 3
```

### CORE Node Scale Out (Need Caution)

```bash
# Scale out 2 CORE nodes (will trigger HDFS rebalance)
aliyun emr IncreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-core-xxx --IncreaseNodeCount 2
```

> **Note**: After CORE scale out, HDFS will automatically perform data rebalancing, IO load will increase during this period.

### Elastic Scale Out When Stock Insufficient

When target spec stock insufficient, use `MinIncreaseNodeCount` to allow partial success:

```bash
# Expect 5 nodes, at least 2 nodes
aliyun emr IncreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx --IncreaseNodeCount 5 --MinIncreaseNodeCount 2
```

### Subscription Scale Out

```bash
aliyun emr IncreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx --IncreaseNodeCount 2 \
  --PaymentDuration 1 --PaymentDurationUnit Month --AutoPayOrder true --AutoRenew true
```

### Verify Scale Out Result

```bash
# After scale out completes, check node status
aliyun emr ListNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --force --NodeGroupIds.1 ng-xxx --NodeStates.1 Running
```

## 2. Manual Scale In

### Safety Checklist

1. **Confirm Payment Type**: Subscription nodes don't support scale in via EMR API (DecreaseNodes), need to go to ECS console to unsubscribe or wait for expiration without renewal
2. **Confirm TASK Node Group**: DecreaseNodes API **only supports TASK node groups**, CORE node groups don't support scale in via API
3. Confirm no critical tasks running on target nodes
4. Large batch scale in use batch operation

### TASK Node Scale In

```bash
# First view TASK node list, select nodes to release
aliyun emr ListNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --force --NodeGroupIds.1 ng-task-xxx --NodeStates.1 Running

# ⚠️ Scale in by node ID precisely (recommended)
aliyun emr DecreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-task-xxx --force --NodeIds.1 i-xxx1 --NodeIds.2 i-xxx2
```

> **Important**: DecreaseNodes only supports TASK node groups. To reduce CORE nodes, need to operate in ECS console or contact technical support.

### Large Batch Scale In: Use BatchSize + BatchInterval

Avoid taking大量 nodes offline at once causing cluster instability:

```bash
# Scale in 2 nodes per batch, batch interval 300 seconds
aliyun emr DecreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx \
  --force --NodeIds.1 i-xxx1 --NodeIds.2 i-xxx2 --NodeIds.3 i-xxx3 --NodeIds.4 i-xxx4 \
  --BatchSize 2 --BatchInterval 300
```

## 3. Create New Node Group

### When Need New Node Group?

- No TASK node group when cluster created
- Need different spec compute nodes (e.g., GPU instances)
- Need Spot instance node group to reduce cost
- Need independent auto scaling policy

### Create Regular TASK Node Group

```bash
aliyun emr CreateNodeGroup --RegionId cn-hangzhou --ClusterId c-xxx \
  --force \
  --NodeGroup.NodeGroupType TASK \
  --NodeGroup.NodeGroupName task-compute \
  --NodeGroup.NodeCount 3 \
  --NodeGroup.InstanceTypes.1 ecs.g8i.2xlarge \
  --NodeGroup.SystemDisk.Category cloud_essd \
  --NodeGroup.SystemDisk.Size 120 \
  --NodeGroup.DataDisks.1.Category cloud_essd \
  --NodeGroup.DataDisks.1.Size 80 \
  --NodeGroup.DataDisks.1.Count 1
```

### Create Spot Instance TASK Node Group

```bash
# Multi-spec disaster tolerance, improve Spot availability
aliyun emr CreateNodeGroup --RegionId cn-hangzhou --ClusterId c-xxx \
  --force \
  --NodeGroup.NodeGroupType TASK \
  --NodeGroup.NodeGroupName task-spot \
  --NodeGroup.NodeCount 5 \
  --NodeGroup.InstanceTypes.1 ecs.g8i.2xlarge \
  --NodeGroup.InstanceTypes.2 ecs.g8i.xlarge \
  --NodeGroup.InstanceTypes.3 ecs.c8i.2xlarge \
  --NodeGroup.SystemDisk.Category cloud_essd \
  --NodeGroup.SystemDisk.Size 120 \
  --NodeGroup.DataDisks.1.Category cloud_essd \
  --NodeGroup.DataDisks.1.Size 80 \
  --NodeGroup.DataDisks.1.Count 1 \
  --NodeGroup.SpotStrategy SpotAsPriceGo
```

> **Spot Best Practice**: Configure 3+ InstanceTypes to improve availability. TASK nodes have no HDFS data, Spot being reclaimed doesn't affect data.

### Spot Instance Bidding Strategy

| SpotStrategy | Description |
|-------------|------|
| `SpotAsPriceGo` (recommended) | Follow market price, won't be reclaimed due to price fluctuation, but may be reclaimed due to stock shortage |
| `SpotWithPriceLimit` | Set price cap, reclaimed when price exceeds cap or stock insufficient. Need to set cap price for each spec via `SpotBidPrices` |

**SpotWithPriceLimit Example**:

```json
"SpotStrategy": "SpotWithPriceLimit",
"SpotBidPrices": [
  {"InstanceType": "ecs.g8i.2xlarge", "BidPrice": 0.5},
  {"InstanceType": "ecs.g8i.xlarge", "BidPrice": 0.25}
]
```

> Generally recommend `SpotAsPriceGo`, worry-free and longer holding time. `SpotWithPriceLimit` suitable for scenarios with strict cost cap requirements.

### TASK Node Group Advanced Configuration

The following parameters can be configured when creating TASK node group via CreateNodeGroup or RunCluster:

**Graceful Shutdown (GracefulShutdown)**

Only supported for clusters with YARN service deployed. When enabled, during scale in will wait for tasks on node to complete (or exceed timeout) before releasing node, avoiding running jobs being interrupted.

```json
"GracefulShutdown": true
```

> Timeout configured via YARN parameter `yarn.resourcemanager.nodemanager-graceful-decommission-timeout-secs`.

**Auto Compensation (SpotInstanceRemedy / CompensateWithOnDemand)**

Only TASK node groups support. When enabled, EMR automatically monitors node running status, releases abnormal nodes and expands same count nodes when异常 detected. `CompensateWithOnDemand` allows automatically using pay-as-you-go instances to compensate when Spot instances unavailable.

```json
"SpotInstanceRemedy": true,
"CompensateWithOnDemand": true
```

**Scale Policy (NodeResizeStrategy)**

Only supports preemptible instances (Spot) TASK node groups.

| Policy | Description |
|------|------|
| `PRIORITY` (default) | Try purchasing in InstanceTypes list order |
| `COST_OPTIMIZED` | When scaling out, create by vCPU unit price low to high; when scaling in, remove by vCPU unit price high to low. Prioritize Spot instances, automatically try pay-as-you-go when stock insufficient |

```json
"NodeResizeStrategy": "COST_OPTIMIZED"
```

**Resource Reservation Strategy (PrivatePoolOptions)**

Only supports TASK node groups + pay-as-you-go. Can associate ECS private pool, prioritize using pre-allocated resources.

| Policy | Description |
|------|------|
| Public pool only (default) | Use public resource pool |
| Private pool priority | Prioritize from specified private pool, automatically use public resource pool when insufficient |
| Specified private pool | Only use specified private pool |

**Complete Example: Spot TASK Node Group with Advanced Configuration**

```bash
aliyun emr CreateNodeGroup --RegionId cn-hangzhou --ClusterId c-xxx \
  --force \
  --NodeGroup.NodeGroupType TASK \
  --NodeGroup.NodeGroupName task-spot-advanced \
  --NodeGroup.NodeCount 5 \
  --NodeGroup.InstanceTypes.1 ecs.g8i.2xlarge \
  --NodeGroup.InstanceTypes.2 ecs.g8i.xlarge \
  --NodeGroup.InstanceTypes.3 ecs.c8i.2xlarge \
  --NodeGroup.SystemDisk.Category cloud_essd \
  --NodeGroup.SystemDisk.Size 120 \
  --NodeGroup.DataDisks.1.Category cloud_essd \
  --NodeGroup.DataDisks.1.Size 80 \
  --NodeGroup.DataDisks.1.Count 1 \
  --NodeGroup.SpotStrategy SpotAsPriceGo \
  --NodeGroup.NodeResizeStrategy COST_OPTIMIZED \
  --NodeGroup.SpotInstanceRemedy true \
  --NodeGroup.CompensateWithOnDemand true \
  --NodeGroup.GracefulShutdown true
```

## 4. Auto Scaling Policy

Auto scaling is only configured on **TASK node groups**, automatically scales based on rules. Divided into **managed policy** and **custom policy** two modes, when switching modes original rules will失效.

### Managed Auto Scaling (Recommended for Simple Scenarios)

EMR automatically adjusts TASK node count based on YARN load and historical job patterns, users only need to set min/max node count:

| Parameter | Description |
|------|------|
| Min Task Node Count | Minimum nodes preserved when scaling in |
| Max Task Node Count | Maximum nodes allowed when scaling out |
| Max Pay-as-you-go Task Node Count | Control ratio of pay-as-you-go vs preemptible instances |

> **Limitation**: Only supports clusters with YARN deployed; effect not guaranteed when containing Trino, Presto, StarRocks, Impala or ClickHouse services. TASK node group needs to be pay-as-you-go or preemptible instances.

### Custom Auto Scaling

Configure精细 scheduled/load rules via PutAutoScalingPolicy API.

> **Important**: PutAutoScalingPolicy is **full replacement** operation, each call replaces all scaling rules for that node group. Before modifying, first use GetAutoScalingPolicy to query current policy. When multiple rules trigger simultaneously, **scale out prioritizes over scale in**.

### Rule Type Comparison

| Type | Trigger Method | Use Case | Advantages | Disadvantages |
|------|---------|---------|------|------|
| **TIME_TRIGGER** (Scheduled Scaling) | By time schedule | Predictable periodic load | Prepare in advance, no delay | Cannot handle突发 |
| **METRICS_TRIGGER** (Load-based Scaling) | By YARN metrics | Unpredictable load changes | Adaptive | Has delay |

### Scheduled Scaling Configuration

Weekday 9:00 scale out, 20:00 scale back:

```bash
aliyun emr PutAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-task-xxx \
  --force \
  --Constraints.MinCapacity 0 \
  --Constraints.MaxCapacity 20 \
  --ScalingRules.1.RuleName workday-scaleout \
  --ScalingRules.1.TriggerType TIME_TRIGGER \
  --ScalingRules.1.ActivityType SCALE_OUT \
  --ScalingRules.1.AdjustmentValue 5 \
  --ScalingRules.1.TimeTrigger.LaunchTime "09:00" \
  --ScalingRules.1.TimeTrigger.StartTime 1700000000000 \
  --ScalingRules.1.TimeTrigger.RecurrenceType WEEKLY \
  --ScalingRules.1.TimeTrigger.RecurrenceValue "MON,TUE,WED,THU,FRI" \
  --ScalingRules.2.RuleName workday-scalein \
  --ScalingRules.2.TriggerType TIME_TRIGGER \
  --ScalingRules.2.ActivityType SCALE_IN \
  --ScalingRules.2.AdjustmentValue 5 \
  --ScalingRules.2.TimeTrigger.LaunchTime "20:00" \
  --ScalingRules.2.TimeTrigger.StartTime 1700000000000 \
  --ScalingRules.2.TimeTrigger.RecurrenceType WEEKLY \
  --ScalingRules.2.TimeTrigger.RecurrenceValue "MON,TUE,WED,THU,FRI"
```

**TimeTrigger Parameter Description**:
- `LaunchTime`: Trigger time, HH:MM format
- `StartTime`: Policy effective start timestamp (milliseconds)
- `RecurrenceType`: Repeat type DAILY / WEEKLY / MONTHLY
- `RecurrenceValue`: DAILY leave empty, WEEKLY fill weekday like `MON,TUE`, MONTHLY fill date like `1,15`

### Load-based Scaling Configuration

Auto scale based on YARN available VCore percentage:

```bash
aliyun emr PutAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-task-xxx \
  --force \
  --Constraints.MinCapacity 2 \
  --Constraints.MaxCapacity 50 \
  --ScalingRules.1.RuleName yarn-vcore-scaleout \
  --ScalingRules.1.TriggerType METRICS_TRIGGER \
  --ScalingRules.1.ActivityType SCALE_OUT \
  --ScalingRules.1.AdjustmentValue 3 \
  --ScalingRules.1.MetricsTrigger.TimeWindow 300 \
  --ScalingRules.1.MetricsTrigger.EvaluationCount 3 \
  --ScalingRules.1.MetricsTrigger.CoolDownInterval 300 \
  --ScalingRules.1.MetricsTrigger.Conditions.1.MetricName yarn_resourcemanager_queue_AvailableVCoresPercentage \
  --ScalingRules.1.MetricsTrigger.Conditions.1.Statistics AVG \
  --ScalingRules.1.MetricsTrigger.Conditions.1.ComparisonOperator LT \
  --ScalingRules.1.MetricsTrigger.Conditions.1.Threshold 20.0 \
  --ScalingRules.1.MetricsTrigger.Conditions.1.Tags.1.Key queue_name \
  --ScalingRules.1.MetricsTrigger.Conditions.1.Tags.1.Value root \
  --ScalingRules.2.RuleName yarn-vcore-scalein \
  --ScalingRules.2.TriggerType METRICS_TRIGGER \
  --ScalingRules.2.ActivityType SCALE_IN \
  --ScalingRules.2.AdjustmentValue 2 \
  --ScalingRules.2.MetricsTrigger.TimeWindow 300 \
  --ScalingRules.2.MetricsTrigger.EvaluationCount 5 \
  --ScalingRules.2.MetricsTrigger.CoolDownInterval 600 \
  --ScalingRules.2.MetricsTrigger.Conditions.1.MetricName yarn_resourcemanager_queue_AvailableVCoresPercentage \
  --ScalingRules.2.MetricsTrigger.Conditions.1.Statistics AVG \
  --ScalingRules.2.MetricsTrigger.Conditions.1.ComparisonOperator GT \
  --ScalingRules.2.MetricsTrigger.Conditions.1.Threshold 80.0 \
  --ScalingRules.2.MetricsTrigger.Conditions.1.Tags.1.Key queue_name \
  --ScalingRules.2.MetricsTrigger.Conditions.1.Tags.1.Value root
```

**Common YARN Metrics and Recommended Thresholds**:

| Metric | Meaning | Scale Out Threshold | Scale In Threshold |
|------|------|---------|---------|
| `yarn_resourcemanager_queue_AvailableVCoresPercentage` | Available VCore percentage | < 20% | > 80% |
| `yarn_resourcemanager_queue_AvailableMemoryPercentage` | Available memory percentage | < 20% | > 80% |
| `yarn_resourcemanager_queue_PendingVCores` | Pending VCore count | > 100 | < 10 |
| `yarn_resourcemanager_queue_PendingMB` | Pending memory (MB) | As needed | As needed |
| `yarn_resourcemanager_queue_PendingContainers` | Pending container count | > 50 | < 5 |
| `yarn_resourcemanager_queue_AllocatedVCores` | Allocated VCore count | As needed | As needed |
| `yarn_resourcemanager_queue_AllocatedMB` | Allocated memory (MB) | As needed | As needed |
| `yarn_resourcemanager_queue_AppsRunning` | Running application count | As needed | As needed |
| `yarn_resourcemanager_queue_AppsPending` | Pending application count | > 10 | = 0 |

> Full support for 23 YARN metrics, including VCore/memory/container/application dimensions for allocation, pending, reserved, etc. Specify queue via `queue_name` in Tags (e.g., `root`).

**MetricsTrigger Parameter Description**:
- `TimeWindow`: Monitoring window (seconds), 30-1800, recommend 300
- `EvaluationCount`: Consecutive满足 count, 1-5, scale out recommend 3, scale in recommend 5
- `CoolDownInterval`: Cooldown time (seconds), 0-10800, prevent frequent scaling
- `ConditionLogicOperator`: Multi-condition relationship, And / Or (default Or)
- `Conditions`: Metric condition list

### Hybrid Policy (Recommended)

Scheduled scaling provides baseline + load-based scaling handles bursts:

```bash
aliyun emr PutAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-task-xxx \
  --force \
  --Constraints.MinCapacity 0 \
  --Constraints.MaxCapacity 30 \
  --ScalingRules.1.RuleName workday-baseline \
  --ScalingRules.1.TriggerType TIME_TRIGGER \
  --ScalingRules.1.ActivityType SCALE_OUT \
  --ScalingRules.1.AdjustmentValue 5 \
  --ScalingRules.1.TimeTrigger.LaunchTime "08:30" \
  --ScalingRules.1.TimeTrigger.StartTime 1700000000000 \
  --ScalingRules.1.TimeTrigger.RecurrenceType WEEKLY \
  --ScalingRules.1.TimeTrigger.RecurrenceValue "MON,TUE,WED,THU,FRI" \
  --ScalingRules.2.RuleName evening-shrink \
  --ScalingRules.2.TriggerType TIME_TRIGGER \
  --ScalingRules.2.ActivityType SCALE_IN \
  --ScalingRules.2.AdjustmentValue 5 \
  --ScalingRules.2.TimeTrigger.LaunchTime "21:00" \
  --ScalingRules.2.TimeTrigger.StartTime 1700000000000 \
  --ScalingRules.2.TimeTrigger.RecurrenceType WEEKLY \
  --ScalingRules.2.TimeTrigger.RecurrenceValue "MON,TUE,WED,THU,FRI" \
  --ScalingRules.3.RuleName burst-scaleout \
  --ScalingRules.3.TriggerType METRICS_TRIGGER \
  --ScalingRules.3.ActivityType SCALE_OUT \
  --ScalingRules.3.AdjustmentValue 3 \
  --ScalingRules.3.MetricsTrigger.TimeWindow 300 \
  --ScalingRules.3.MetricsTrigger.EvaluationCount 2 \
  --ScalingRules.3.MetricsTrigger.CoolDownInterval 300 \
  --ScalingRules.3.MetricsTrigger.Conditions.1.MetricName yarn_resourcemanager_queue_AvailableVCoresPercentage \
  --ScalingRules.3.MetricsTrigger.Conditions.1.Statistics AVG \
  --ScalingRules.3.MetricsTrigger.Conditions.1.ComparisonOperator LT \
  --ScalingRules.3.MetricsTrigger.Conditions.1.Threshold 15.0 \
  --ScalingRules.3.MetricsTrigger.Conditions.1.Tags.1.Key queue_name \
  --ScalingRules.3.MetricsTrigger.Conditions.1.Tags.1.Value root \
  --ScalingRules.4.RuleName idle-scalein \
  --ScalingRules.4.TriggerType METRICS_TRIGGER \
  --ScalingRules.4.ActivityType SCALE_IN \
  --ScalingRules.4.AdjustmentValue 2 \
  --ScalingRules.4.MetricsTrigger.TimeWindow 300 \
  --ScalingRules.4.MetricsTrigger.EvaluationCount 5 \
  --ScalingRules.4.MetricsTrigger.CoolDownInterval 600 \
  --ScalingRules.4.MetricsTrigger.Conditions.1.MetricName yarn_resourcemanager_queue_AvailableVCoresPercentage \
  --ScalingRules.4.MetricsTrigger.Conditions.1.Statistics AVG \
  --ScalingRules.4.MetricsTrigger.Conditions.1.ComparisonOperator GT \
  --ScalingRules.4.MetricsTrigger.Conditions.1.Threshold 80.0 \
  --ScalingRules.4.MetricsTrigger.Conditions.1.Tags.1.Key queue_name \
  --ScalingRules.4.MetricsTrigger.Conditions.1.Tags.1.Value root
```

### View Current Policy

```bash
aliyun emr GetAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-task-xxx
```

Check returned `Disabled` field to confirm if policy is effective.

### Modify Policy

Simply use PutAutoScalingPolicy to resubmit complete rules (full replacement).

### Delete Policy

```bash
# ⚠️ After deletion, node group no longer auto scales
aliyun emr RemoveAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-task-xxx
```

## Common Issues

| Issue | Cause | Solution |
|------|------|---------|
| Scaled out nodes keep Pending | Instance spec stock insufficient | Use MinIncreaseNodeCount to allow partial success, or change spec |
| CORE scale in failed | DecreaseNodes API only supports TASK node groups | CORE nodes don't support API scale in, need to operate in ECS console |
| Auto scaling not triggering | Policy Disabled or metrics未达 threshold | Use GetAutoScalingPolicy to check policy status and threshold settings |
| Node group长时间 INCREASING after scale out | Nodes已 Running but node group state transitions slowly (可达 15+ minutes) | This is normal behavior, wait for state to return to RUNNING before executing next scaling operation. Other scaling operations during INCREASING will report ConcurrentModification |
| Immediately scale back after scale out | CoolDownInterval set too short | Increase cooldown time, scale in recommend 600+ seconds |
| Spot instance reclaimed | Normal behavior, market price fluctuation | Configure multi-spec disaster tolerance, ensure core data not on TASK nodes |
| Subscription node scale in failed | DecreaseNodes doesn't support subscription nodes | Go to ECS console to unsubscribe, or wait for expiration without renewal |

## Related Documentation

- When need to switch to other scenarios, please return to intent routing table in `SKILL.md` to select the appropriate reference document.