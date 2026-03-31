# Verification Method

## Step 1: Verify Forward Path Analysis

Run a forward path analysis between two known-reachable resources (e.g., two ECS instances in the same VPC):

```bash
aliyun nis create-and-analyze-network-path \
  --source-id <SourceEcsId> \
  --source-type ecs \
  --target-id <TargetEcsId> \
  --target-type ecs \
  --protocol tcp \
  --target-port 80 \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: Returns `NetworkReachableAnalysisId`.

## Step 2: Poll for Result

```bash
aliyun nis get-network-reachable-analysis \
  --network-reachable-analysis-id <AnalysisId> \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: `NetworkReachableAnalysisStatus` transitions from `init` to `finish`. `Reachable` is `true` for known-reachable paths.

## Step 3: Verify Reverse Path Analysis

Swap source and target, swap ports:

```bash
aliyun nis create-and-analyze-network-path \
  --source-id <TargetEcsId> \
  --source-type ecs \
  --target-id <SourceEcsId> \
  --target-type ecs \
  --protocol tcp \
  --source-port 80 \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: Returns a new `NetworkReachableAnalysisId` for the reverse path.

## Step 4: Verify Monitoring Data Query

```bash
aliyun cms DescribeMetricData \
  --Namespace acs_ecs_dashboard \
  --MetricName CPUUtilization \
  --Dimensions '[{"instanceId":"<EcsInstanceId>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: Returns monitoring data points with timestamps and values.

## Step 5: Verify Mermaid Topology Output

After obtaining `topologyData.positive` from `GetNetworkReachableAnalysis`, verify:
- `nodeList` contains source, destination, and intermediate nodes
- `linkList` contains directional connections
- Generated Mermaid `graph LR` diagram renders correctly
