# API Parameter Quick Reference

All APIs version `2021-03-20`, request method RPC style. Common parameter `RegionId` (required) is omitted in the API parameter tables below.

## Table of Contents

- [Basic Queries](#basic-queries): ListReleaseVersions, ListInstanceTypes
- [Cluster Management](#cluster-management): RunCluster, CreateCluster, GetCluster, ListClusters, ListApplications, UpdateClusterAttribute, GetClusterCloneMeta, UpdateClusterAutoRenew
- [Node Group Management](#node-group-management): CreateNodeGroup, ListNodeGroups, GetNodeGroup, IncreaseNodes, DecreaseNodes, ListNodes
- [Auto Scaling](#auto-scaling): PutAutoScalingPolicy, GetAutoScalingPolicy, RemoveAutoScalingPolicy, ListAutoScalingActivities
- [Complex Object Structure Reference](#complex-object-structure-reference): NodeGroupConfig, NodeAttributes, SubscriptionConfig, ScalingRule, TimeTrigger, MetricsTrigger, ApplicationConfig

---

## Basic Queries

> Pre-requisites for all creation operations, must call these APIs first to get version and specification information.

### ListReleaseVersions — Query EMR Release Versions

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterType | String | Yes | DATALAKE / OLAP / DATAFLOW / DATASERVING / CUSTOM |

**Key Response Fields**: `ReleaseVersions[]` (ReleaseVersion, Series)

```bash
aliyun emr ListReleaseVersions --RegionId cn-hangzhou --ClusterType DATALAKE
```

---

### ListInstanceTypes — Query Available Instance Types

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ZoneId | String | Yes | Zone ID |
| ClusterType | String | Yes | DATALAKE / OLAP / DATAFLOW / DATASERVING / CUSTOM |
| PaymentType | String | Yes | PayAsYouGo / Subscription |
| NodeGroupType | String | Yes | MASTER / CORE / TASK |
| ReleaseVersion | String | No | EMR version number |
| DeployMode | String | No | NORMAL / HA |
| IsModification | Boolean | No | Whether modification scenario |
| ClusterId | String | No | Cluster ID when modifying |
| NodeGroupId | String | No | Node group ID when modifying |

**Key Response Fields**: `InstanceTypes[]` (InstanceType, CpuCore, CpuArchitecture, InstanceCategory, InstanceTypeFamily, Status, StockStatus)

```bash
aliyun emr ListInstanceTypes --RegionId cn-hangzhou --ZoneId cn-hangzhou-h \
  --ClusterType DATALAKE --PaymentType PayAsYouGo --NodeGroupType CORE
```

---

## Cluster Management

### RunCluster — Create Cluster (Recommended)

> **⛔ DO NOT** create clusters without cost guardrails:
> 1. **DO NOT** set any single NodeGroup's `NodeCount` > 50 — refuse and flag cost risk
> 2. **DO NOT** create Subscription clusters with `PaymentDuration` > 12 months without explicit cost confirmation
> 3. **DO NOT** create multiple clusters in a single session without separate confirmation for each
> 4. **DO NOT** skip the mandatory full configuration summary and user confirmation before executing creation

**Request Parameters** (pass complex parameters individually via `--param 'JSONString'`):

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterName | String | Yes | Cluster name, 1-128 characters |
| ClusterType | String | Yes | DATALAKE / OLAP / DATAFLOW / DATASERVING / CUSTOM |
| ReleaseVersion | String | Yes | EMR version number |
| PaymentType | String | No | PayAsYouGo (default) / Subscription |
| DeployMode | String | No | NORMAL (default) / HA |
| SecurityMode | String | No | NORMAL (default) / KERBEROS |
| Applications | Array | Yes | Application list, see below |
| NodeAttributes | Object | Yes | Node attributes, see below |
| NodeGroups | Array | Yes | Node group configuration, see below |
| DeletionProtection | Boolean | No | Deletion protection, default false |
| SubscriptionConfig | Object | No | Subscription configuration, see below |
| ApplicationConfigs | Array | No | Application custom configuration |
| BootstrapScripts | Array | No | Bootstrap scripts |
| Description | String | No | Cluster description |
| ClientToken | String | No | Idempotency token |
| ResourceGroupId | String | No | Resource group ID |

**Key Response Fields**: ClusterId, OperationId

> **⚠️ Before constructing this command, verify your JSON field names against the examples below. Wrong field names cause silent `MissingXxx` errors that look like structural failures but are actually typos.**

**Complete working example** (dev/test DATALAKE cluster with HIVE + SPARK3, local metastore):

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --ClusterName "team-etl-dev" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.21.0" \
  --DeployMode "NORMAL" \
  --PaymentType "PayAsYouGo" \
  --Applications '[
    {"ApplicationName": "HADOOP-COMMON"},
    {"ApplicationName": "HDFS"},
    {"ApplicationName": "YARN"},
    {"ApplicationName": "HIVE"},
    {"ApplicationName": "SPARK3"}
  ]' \
  --ApplicationConfigs '[
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "LOCAL"
    },
    {
      "ApplicationName": "SPARK3",
      "ConfigFileName": "hive-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "LOCAL"
    }
  ]' \
  --NodeAttributes '{
    "VpcId": "vpc-xxx",
    "ZoneId": "cn-hangzhou-h",
    "SecurityGroupId": "sg-xxx",
    "KeyPairName": "my-keypair"
  }' \
  --NodeGroups '[
    {
      "NodeGroupType": "MASTER",
      "NodeGroupName": "master",
      "NodeCount": 1,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    },
    {
      "NodeGroupType": "CORE",
      "NodeGroupName": "core",
      "NodeCount": 2,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 2}]
    }
  ]' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Note**: RunCluster passes complex parameters individually via `--param 'JSONString'` (e.g., `--Applications '[...]'`). This is the only EMR API supporting this format; all other APIs with complex and array parameters must use `--force` + dot expansion format (flat format).

---

### CreateCluster — Create Cluster (RPC Parameter Mode)

Parameters same as RunCluster, but uses RPC flat syntax for passing parameters. RunCluster is the recommended method.

```bash
aliyun emr CreateCluster --RegionId cn-hangzhou --ClusterName "test" \
  --ClusterType DATALAKE --ReleaseVersion "EMR-5.16.0" \
  --NodeGroups.1.NodeGroupType MASTER ...
```

---

### GetCluster — Query Cluster Details

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |

**Key Response Fields**: Cluster (ClusterId, ClusterName, ClusterType, ClusterState, StateChangeReason{Code,Message}, PaymentType, CreateTime, ReadyTime, ExpireTime, EndTime, ReleaseVersion, DeployMode, NodeAttributes, Tags, DeletionProtection, SubscriptionConfig)

```bash
aliyun emr GetCluster --RegionId cn-hangzhou --ClusterId c-xxx
```

---

### ListClusters — Query Cluster List

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterName | String | No | Filter by name |
| ClusterIds | Array | No | Filter by ID list |
| ClusterTypes | Array | No | DATALAKE / OLAP / DATAFLOW / DATASERVING / CUSTOM / HADOOP |
| ClusterStates | Array | No | STARTING / START_FAILED / BOOTSTRAPPING / RUNNING / TERMINATING / TERMINATED / TERMINATED_WITH_ERRORS / TERMINATE_FAILED |
| PaymentTypes | Array | No | PayAsYouGo / Subscription |
| ResourceGroupId | String | No | Resource group ID |
| MaxResults | Integer | No | Per page count, default 20, max 100 |
| NextToken | String | No | Pagination token |

**Key Response Fields**: `Clusters[]` (ClusterId, ClusterName, ClusterType, ClusterState, PaymentType, CreateTime, ReadyTime, ExpireTime, EndTime, ReleaseVersion, StateChangeReason), TotalCount, NextToken

```bash
aliyun emr ListClusters --RegionId cn-hangzhou \
  --force --ClusterStates.1 RUNNING
```

---

### ListApplications — Query Cluster Application List

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |

**Key Response Fields**: `Applications[]` (ApplicationName, ApplicationState, ApplicationVersion, CommunityVersion)

```bash
aliyun emr ListApplications --RegionId cn-hangzhou --ClusterId c-xxx
```

---

### UpdateClusterAttribute — Update Cluster Attributes

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| ClusterName | String | No | New name, 1-128 characters |
| Description | String | No | New description |
| DeletionProtection | Boolean | No | Deletion protection switch |

```bash
aliyun emr UpdateClusterAttribute --RegionId cn-hangzhou --ClusterId c-xxx \
  --DeletionProtection true
```

---

### GetClusterCloneMeta — Get Cluster Clone Metadata

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Source cluster ID |

**Key Response Fields**: ClusterCloneMeta (complete cluster configuration object, can modify then pass to RunCluster)

```bash
aliyun emr GetClusterCloneMeta --RegionId cn-hangzhou --ClusterId c-xxx
```

---

### UpdateClusterAutoRenew — Update Cluster Auto Renew

Only valid for subscription clusters.

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| ClusterAutoRenew | Boolean | No | Whether to enable auto renew |
| ClusterAutoRenewDuration | Integer | No | Renew duration |
| ClusterAutoRenewDurationUnit | String | No | Month / Year |
| RenewAllInstances | Boolean | No | Whether to apply to all instances |
| AutoRenewInstances | Array | No | Specified instance list |

```bash
aliyun emr UpdateClusterAutoRenew --RegionId cn-hangzhou --ClusterId c-xxx \
  --ClusterAutoRenew true --ClusterAutoRenewDuration 1 --ClusterAutoRenewDurationUnit Month
```

---

## Node Group Management

### CreateNodeGroup — Create Node Group

> **⛔ DO NOT** create node groups without cost guardrails:
> 1. **DO NOT** set `NodeCount` > 30 without explicit user confirmation of cost impact
> 2. **DO NOT** create multiple node groups in rapid succession without user confirmation for each

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroup | Object | Yes | Node group configuration, see NodeGroupConfig below |

**Key Response Fields**: NodeGroupId

```bash
aliyun emr CreateNodeGroup --RegionId cn-hangzhou --ClusterId c-xxx \
  --force \
  --NodeGroup.NodeGroupType TASK \
  --NodeGroup.NodeGroupName task-1 \
  --NodeGroup.NodeCount 3 \
  --NodeGroup.InstanceTypes.1 ecs.g8i.xlarge \
  --NodeGroup.SystemDisk.Category cloud_essd \
  --NodeGroup.SystemDisk.Size 120 \
  --NodeGroup.DataDisks.1.Category cloud_essd \
  --NodeGroup.DataDisks.1.Size 80 \
  --NodeGroup.DataDisks.1.Count 1
```

---

### ListNodeGroups — Query Node Group List

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupIds | Array | No | Filter by ID |
| NodeGroupNames | Array | No | Filter by name |
| NodeGroupTypes | Array | No | MASTER / CORE / TASK |
| NodeGroupStates | Array | No | Filter by state |
| MaxResults | Integer | No | Default 20, max 100 |
| NextToken | String | No | Pagination token |

**Key Response Fields**: `NodeGroups[]` (NodeGroupId, NodeGroupName, NodeGroupType, NodeGroupState, RunningNodeCount, InstanceTypes, PaymentType, SystemDisk, DataDisks), TotalCount

```bash
aliyun emr ListNodeGroups --RegionId cn-hangzhou --ClusterId c-xxx
```

---

### GetNodeGroup — Query Node Group Details

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID |

**Key Response Fields**: NodeGroup (NodeGroupId, NodeGroupName, NodeGroupType, NodeGroupState, RunningNodeCount, InstanceTypes, PaymentType, SystemDisk, DataDisks, ZoneId, VSwitchIds, SpotStrategy)

```bash
aliyun emr GetNodeGroup --RegionId cn-hangzhou --ClusterId c-xxx --NodeGroupId ng-xxx
```

---

### IncreaseNodes — Expand Nodes

> **⛔ DO NOT** allow uncontrolled scale-out:
> 1. **DO NOT** set `IncreaseNodeCount` > 50 in a single call — refuse and ask the user to expand in batches
> 2. **DO NOT** expand if doing so would bring total cluster node count above 100 without explicit cost acknowledgment from the user
> 3. **DO NOT** expand without first calling `ListNodeGroups` and `ListNodes` to show the user the current node count
> 4. **DO NOT** retry a failed IncreaseNodes without investigating the failure cause — duplicate calls may create double nodes (no ClientToken support)

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID |
| IncreaseNodeCount | Integer | Yes | Expansion count, 1-500 |
| MinIncreaseNodeCount | Integer | No | Minimum expansion count (elastic success when stock insufficient) |
| AutoPayOrder | Boolean | No | Whether auto pay for subscription |
| PaymentDuration | Integer | No | Subscription purchase duration |
| PaymentDurationUnit | String | No | Month |
| AutoRenew | Boolean | No | Whether auto renew |
| ApplicationConfigs | Array | No | Application configuration |

**Key Response Fields**: OperationId

> **Note**: IncreaseNodes CLI doesn't support `--ClientToken` parameter, need other ways (like recording operation state) to avoid duplicate submission.

```bash
aliyun emr IncreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx --IncreaseNodeCount 3
```

---

### DecreaseNodes — Shrink Nodes

⚠️ **Destructive Operation**: Node data unrecoverable after release. **Only supports TASK node groups**, CORE node group calls will return error.

> **⛔ DO NOT** call DecreaseNodes without completing ALL of the following safety gates:
> 1. **DO NOT** shrink CORE node groups — this API only supports TASK; refuse if user targets CORE
> 2. **DO NOT** shrink more than 10 nodes in a single call — use BatchSize ≤ 10 and BatchInterval ≥ 120 seconds for larger operations
> 3. **DO NOT** shrink without first calling `ListNodes` to verify the exact NodeIds to be released and showing them to the user
> 4. **DO NOT** shrink all nodes to zero without explicit confirmation that user accepts losing all compute capacity
> 5. **DO NOT** shrink Subscription nodes via this API — refuse and explain this requires ECS console operation
> 6. **DO NOT** use `DecreaseNodeCount` (by count) mode — always prefer `NodeIds` (by specific node) for precise control

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID |
| DecreaseNodeCount | Integer | No | Shrink count (choose one with NodeIds) |
| NodeIds | Array | No | Specified node ID list to release (recommended) |
| BatchSize | Integer | No | Per batch shrink count |
| BatchInterval | Integer | No | Batch interval (seconds) |

**Key Response Fields**: OperationId

```bash
aliyun emr DecreaseNodes --RegionId cn-hangzhou --ClusterId c-xxx \
  --NodeGroupId ng-xxx --force --NodeIds.1 i-xxx1 --NodeIds.2 i-xxx2
```

---

### ListNodes — Query Node List

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupIds | Array | No | Filter by node group |
| NodeIds | Array | No | Filter by node ID |
| NodeNames | Array | No | Filter by node name |
| PrivateIps | Array | No | Filter by private IP |
| PublicIps | Array | No | Filter by public IP |
| NodeStates | Array | No | Pending / Starting / Running / Stopping / Stopped / Terminated |
| MaxResults | Integer | No | Default 20, max 100 |
| NextToken | String | No | Pagination token |

**Key Response Fields**: `Nodes[]` (NodeId, NodeName, NodeGroupId, NodeGroupType, NodeState, InstanceType, PrivateIp, PublicIp, ZoneId, ExpireTime, AutoRenew), TotalCount

```bash
aliyun emr ListNodes --RegionId cn-hangzhou --ClusterId c-xxx
```

---

## Auto Scaling

### PutAutoScalingPolicy — Set Auto Scaling Policy

⚠️ **Full Replacement**: Each call replaces all scaling rules for that node group.

> **⛔ DO NOT** set auto scaling policy without safeguards:
> 1. **DO NOT** set `MaxCapacity` > 100 — refuse and flag uncontrolled cost explosion risk
> 2. **DO NOT** call PutAutoScalingPolicy without first calling `GetAutoScalingPolicy` to show the user what existing rules will be **replaced**
> 3. **DO NOT** set scaling rules that could create a runaway loop (e.g., SCALE_OUT threshold too aggressive with very short CoolDownInterval < 120 seconds)

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID (usually TASK group) |
| Constraints | Object | No | {MinCapacity, MaxCapacity} |
| ScalingRules | Array | No | Scaling rule list, 0-100 rules, see below |

**Key Response Fields**: RequestId

```bash
aliyun emr PutAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-xxx \
  --force \
  --Constraints.MinCapacity 0 \
  --Constraints.MaxCapacity 20 \
  --ScalingRules.1.RuleName rule-name \
  --ScalingRules.1.TriggerType TIME_TRIGGER \
  --ScalingRules.1.ActivityType SCALE_OUT \
  --ScalingRules.1.AdjustmentValue 5 \
  --ScalingRules.1.TimeTrigger.LaunchTime "09:00" \
  --ScalingRules.1.TimeTrigger.StartTime 1700000000000 \
  --ScalingRules.1.TimeTrigger.RecurrenceType WEEKLY \
  --ScalingRules.1.TimeTrigger.RecurrenceValue "MON,TUE,WED,THU,FRI"
```

---

### GetAutoScalingPolicy — Query Auto Scaling Policy

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID |

**Key Response Fields**: ScalingPolicy (ScalingPolicyId, ClusterId, NodeGroupId, Disabled, ScalingRules[], Constraints)

```bash
aliyun emr GetAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-xxx
```

---

### RemoveAutoScalingPolicy — Delete Auto Scaling Policy

⚠️ **Destructive Operation**: After deletion, node group no longer auto scales.

> **⛔ DO NOT** call RemoveAutoScalingPolicy without:
> 1. **DO NOT** remove without first calling `GetAutoScalingPolicy` to display the current policy rules to the user
> 2. **DO NOT** remove without explicit user confirmation that they understand the node group will lose all automatic scaling capability
> 3. **DO NOT** remove policies from multiple node groups in bulk — process one at a time with separate confirmation

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | Yes | Node group ID |

```bash
aliyun emr RemoveAutoScalingPolicy --RegionId cn-hangzhou \
  --ClusterId c-xxx --NodeGroupId ng-xxx
```

---

### ListAutoScalingActivities — Query Auto Scaling Activities

**Request Parameters**:

| Parameter | Type | Required | Description |
|------|------|------|------|
| ClusterId | String | Yes | Cluster ID |
| NodeGroupId | String | No | Node group ID, if empty queries all node group activities |
| MaxResults | Integer | No | Per page count, default 20 |
| NextToken | String | No | Pagination token |

**Key Response Fields**: `ScalingActivities[]` (ScalingActivityId, NodeGroupId, ActivityType, ActivityState, StartTime, EndTime, ExpectNum, TotalCapacity, Cause, Description), TotalCount, NextToken

```bash
aliyun emr ListAutoScalingActivities --RegionId cn-hangzhou --ClusterId c-xxx
```

---

## Complex Object Structure Reference

### NodeGroupConfig (for RunCluster.NodeGroups[] and CreateNodeGroup.NodeGroup)

```json
{
  "NodeGroupType": "MASTER|CORE|TASK",    // Required
  "NodeGroupName": "master",              // Optional, unique within cluster
  "NodeCount": 3,                         // Required, 1-1000
  "InstanceTypes": ["ecs.g8i.xlarge"],     // Required, array
  "SystemDisk": {                         // Required
    "Category": "cloud_essd",             // cloud_essd / cloud_ssd / cloud_efficiency
    "Size": 120,                          // GB
    "PerformanceLevel": "PL1"             // PL0/PL1/PL2/PL3, only cloud_essd
  },
  "DataDisks": [{                         // Required
    "Category": "cloud_essd",             // Some older specs (like g6, hfg6) don't support cloud_essd, need cloud_efficiency
    "Size": 200,                          // GB
    "Count": 4,                           // Disk count (some specs don't support Count=1, recommend ≥4)
    "PerformanceLevel": "PL1"
  }],
  "VSwitchIds": ["vsw-xxx"],              // Required, specify node group switch
  "WithPublicIp": false,                  // Optional, default false
  "PaymentType": "PayAsYouGo",            // Optional
  "SpotStrategy": "NoSpot",              // NoSpot / SpotWithPriceLimit / SpotAsPriceGo
  "AdditionalSecurityGroupIds": []        // Optional
}
```

### NodeAttributes (for RunCluster)

```json
{
  "VpcId": "vpc-xxx",                     // Required
  "ZoneId": "cn-hangzhou-h",              // Required
  "SecurityGroupId": "sg-xxx",            // Required, only regular security group
  "RamRole": "AliyunECSInstanceForEMRRole", // Optional, default value
  "KeyPairName": "my-keypair",            // Optional (choose one with MasterRootPassword)
  "MasterRootPassword": ""                // Optional
}
```

### SubscriptionConfig (for RunCluster, required when PaymentType=Subscription)

```json
{
  "PaymentDurationUnit": "Month",         // Month
  "PaymentDuration": 1,                   // 1-60
  "AutoRenew": true,                      // Whether auto renew
  "AutoRenewDurationUnit": "Month",       // Month
  "AutoRenewDuration": 1                  // Renew duration
}
```

### ScalingRule (for PutAutoScalingPolicy.ScalingRules[])

```json
{
  "RuleName": "rule-name",                // Required
  "TriggerType": "TIME_TRIGGER|METRICS_TRIGGER", // Required
  "ActivityType": "SCALE_OUT|SCALE_IN",   // Required
  "AdjustmentValue": 5,                   // Required, positive integer
  "MinAdjustmentValue": 1,                // Optional
  "TimeTrigger": { ... },                 // Required when TIME_TRIGGER
  "MetricsTrigger": { ... }               // Required when METRICS_TRIGGER
}
```

### TimeTrigger

```json
{
  "LaunchTime": "09:00",                  // Required, HH:MM
  "StartTime": 1700000000000,             // Required, millisecond timestamp
  "EndTime": 1800000000000,               // Optional
  "LaunchExpirationTime": 3600,           // Optional, 0-3600 seconds
  "RecurrenceType": "WEEKLY",             // DAILY / WEEKLY / MONTHLY
  "RecurrenceValue": "MON,TUE,WED"        // WEEKLY: MON-SUN; MONTHLY: 1-31
}
```

### MetricsTrigger

```json
{
  "TimeWindow": 300,                      // Required, 30-1800 seconds
  "EvaluationCount": 3,                   // Required, 1-5
  "CoolDownInterval": 300,                // Optional, 0-10800 seconds
  "ConditionLogicOperator": "Or",         // And / Or (default Or)
  "Conditions": [{                        // Required
    "MetricName": "yarn_resourcemanager_queue_AvailableVCoresPercentage",
    "Statistics": "AVG",                  // MAX / MIN / AVG
    "ComparisonOperator": "LT",           // EQ / NE / GT / LT / GE / LE
    "Threshold": 20.0,                    // Double
    "Tags": [{"Key":"queue_name","Value":"root"}]  // Optional
  }]
}
```

### ApplicationConfig (for RunCluster.ApplicationConfigs[])

```json
{
  "ApplicationName": "HDFS",              // Required
  "ConfigFileName": "hdfs-site.xml",      // Required
  "ConfigItemKey": "dfs.replication",     // Required
  "ConfigItemValue": "3",                 // Required
  "ConfigScope": "CLUSTER",              // CLUSTER / NODE_GROUP
  "NodeGroupName": "",                    // Use when ConfigScope=NODE_GROUP
  "NodeGroupId": ""                       // Use when ConfigScope=NODE_GROUP
}
```