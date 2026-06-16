# RAM Policies for alibabacloud-flink-knowledge Skill

This document declares the RAM (Resource Access Management) permissions required when this Skill invokes `aliyun` CLI to call Alibaba Cloud services. All permissions follow the principle of least privilege — only the specific Actions necessary to complete each task are requested.

## Prerequisites

The RAM account executing this Skill must have the following permissions for `aliyun` CLI to successfully perform the corresponding operations.

## Core Permissions — Realtime Compute for Apache Flink (Read-Only)

These permissions are required for parameter queries, version queries, billing queries, diagnostic troubleshooting, and SQL-related queries:

- `realtime-compute:GetDeployment` — Query deployment details
- `realtime-compute:ListDeployments` — List all deployments
- `realtime-compute:GetJob` — Query job execution details
- `realtime-compute:ListJobs` — List all jobs
- `realtime-compute:GetDeploymentTarget` — Query deployment target configuration
- `realtime-compute:ListDeploymentTargets` — List deployment targets
- `realtime-compute:GetSavepointInfo` — Query savepoint information
- `realtime-compute:ListSavepoints` — List savepoints
- `realtime-compute:GetCheckpointInfo` — Query checkpoint information
- `realtime-compute:ListResourceQueues` — List resource queues
- `realtime-compute:GetWorkspace` — Query workspace details
- `realtime-compute:ListWorkspaces` — List workspaces
- `flink:GetDeployment` — Query deployment (Serverless API)
- `flink:ListDeployments` — List deployments (Serverless API)
- `flink:GetJob` — Query job (Serverless API)
- `flink:ListJobs` — List jobs (Serverless API)
- `flink:GetSavepoint` — Query savepoint (Serverless API)
- `flink:ListSavepoints` — List savepoints (Serverless API)
- `flink:GetDeploymentTarget` — Query deployment target (Serverless API)
- `flink:ListDeploymentTargets` — List deployment targets (Serverless API)

## Read-Only Permissions for Dependent Services

When this Skill diagnoses issues or generates cross-service SQL (e.g. Kafka → Hologres, CDC → Paimon), the following read-only permissions are required:

- `vpc:DescribeVpcs` — Query VPC list for network topology diagnosis
- `vpc:DescribeVSwitches` — Query vSwitch list for network topology diagnosis
- `vpc:DescribeSecurityGroups` — Query security groups for network topology diagnosis
- `rds:DescribeDBInstances` — List RDS instances for CDC source table schema retrieval
- `rds:DescribeDBInstanceAttribute` — Query RDS instance details for CDC source table schema retrieval
- `alikafka:GetInstanceList` — List Kafka instances for connectivity check
- `alikafka:GetTopicStatus` — Query Kafka topic status for connectivity check
- `hologram:ListInstances` — List Hologres instances for sink configuration validation
- `hologram:GetInstance` — Query Hologres instance details for sink configuration validation
- `dla:GetCatalog` — Query data lake catalog for Paimon sink access
- `dla:ListDatabases` — List data lake databases for Paimon sink access
- `log:GetProject` — Query SLS project for log-based troubleshooting
- `log:ListLogStores` — List SLS logstores for log-based troubleshooting
- `log:GetLogs` — Query SLS logs for log-based troubleshooting
- `oss:GetBucketInfo` — Query OSS bucket info for artifact storage access
- `oss:ListObjects` — List OSS objects for artifact storage access
- `bssopenapi:QueryProductList` — Query product list for billing queries
- `bssopenapi:QueryInstanceBill` — Query instance bill for billing queries
- `bssopenapi:GetSubscriptionPrice` — Query subscription price for billing queries

## Usage Recommendations

1. **Production Environment**: Grant only the "Core Permissions" section above. Extend with "Additional Permissions" only when SQL generation / job management features are needed.
2. **Billing Query Scenarios**: `bssopenapi:QueryProductList`, `bssopenapi:QueryInstanceBill`, and `bssopenapi:GetSubscriptionPrice` must be granted; otherwise `aliyun bss` commands will report insufficient permissions.
3. **CDC Multi-Table Sync**: `rds:DescribeDBInstances` is required for retrieving source table schemas. Note: actual deployment creation requires additional write permissions (`flink:CreateDeployment`) that are beyond this Skill's read-only scope — users should configure those separately in their deployment pipeline if needed.

## Permission Verification Commands

After configuring RAM permissions, verify with the following commands (using plugin mode + User-Agent declaration):

```bash
# Ensure the plugin is updated to the latest version
aliyun plugin update

# Verify Realtime Compute access
aliyun realtime-compute list-regions --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-flink-knowledge/{session-id}"

# Verify billing access
aliyun bssopenapi query-product-list --product-code=sc --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-flink-knowledge/{session-id}"

# Verify VPC access
aliyun vpc describe-vpcs --region-id=cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-flink-knowledge/{session-id}"
```
