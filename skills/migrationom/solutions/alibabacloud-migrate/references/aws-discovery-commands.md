# AWS Resource Discovery (Script-First)

Migration assessment requires a reproducible inventory. All discovery that involves looping over resources or making multiple API calls is encapsulated in scripts. This document explains **how to run the scripts**, **required permissions**, and **fallback options** — it does not list per-service AWS CLI commands.

---

## Quick Start

Two steps for a complete discovery:

```bash
# Step 1: Broad scan — one list/describe per service category, ~30–60 seconds
./scripts/aws-scan-region.sh <region>

# Step 2: Deep scan — loops over each main resource to fetch per-resource details
./scripts/aws-scan-enrich.sh <region> aws-scan-<region>-<timestamp>
```

- Step 1 output: `aws-scan-<region>-<timestamp>/inventory.md`
- Step 2 writes `inventory-deep.md` into the same directory; omitting the second argument creates a new directory.

### Environment Variables (both scripts)

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_SCAN_CMD_TIMEOUT` | `120` | Per-command timeout in seconds; requires GNU `timeout` |
| `AWS_SCAN_REDACT` | `1` | When `1`, redacts IPs, resource IDs, and account numbers in output |
| `AWS_MAX_ATTEMPTS` / `AWS_RETRY_MODE` | CLI standard | Passed to AWS CLI to prevent slow APIs from stalling the scan |

---

## Prerequisites

- **AWS CLI v2** installed and configured via `aws configure` (or equivalent credential environment variables).
- Verify access: `aws sts get-caller-identity`

### IAM Recommendations

Attach the **`ReadOnlyAccess`** managed policy when possible. For least-privilege, the minimum permissions must cover all `Describe*` / `List*` / `Get*` calls in the scripts, plus:

`lambda:GetPolicy` · `apigateway:GET` · `events:ListEventBuses` · `events:ListRules` · `events:ListTargetsByRule` · `s3:GetBucket*` · `sns:ListSubscriptionsByTopic` · `iam:GetRolePolicy` · `ecr:DescribeRepositories` · `kinesis:ListStreams` · `wafv2:ListWebACLs` · `directconnect:Describe*` · `elasticache:DescribeReplicationGroups` · `elasticache:DescribeCacheParameters` · `kafka:DescribeCluster` · `cognito-idp:DescribeUserPool` · `cognito-idp:ListUserPoolClients` · `elasticfilesystem:DescribeMountTargets` · `elasticfilesystem:DescribeAccessPoints`

---

## Script Responsibilities

| Discovery requirement | Covered by |
|-----------------------|------------|
| Whether main resources exist per service (EC2, Lambda, S3, SNS, EventBridge buses, ECR, Kinesis, WAF, VPN, Direct Connect, EMR, etc.) | `aws-scan-region.sh` |
| EventBridge rules **and** `list-targets-by-rule` per rule, on every event bus | `aws-scan-enrich.sh` |
| S3 per-bucket lifecycle rules + bucket policy | `aws-scan-enrich.sh` |
| SNS per-topic subscriptions | `aws-scan-enrich.sh` |
| IAM inline policy content per role | `aws-scan-enrich.sh` |
| Lambda `get-policy` per function (invoke permissions / push triggers) | `aws-scan-enrich.sh` |
| API Gateway REST: `get-resources` + `get-stages` per API; HTTP v2: routes + stages | `aws-scan-enrich.sh` |
| ECS per-cluster services + task definitions | `aws-scan-enrich.sh` |
| EKS per-cluster describe + addons | `aws-scan-enrich.sh` |
| ELB v2 per-LB listeners + target groups | `aws-scan-enrich.sh` |
| Route53 per-zone record sets | `aws-scan-enrich.sh` |
| CloudFront per-distribution origins + cache behaviors + SSL | `aws-scan-enrich.sh` |
| DynamoDB per-table capacity, GSI/LSI, streams | `aws-scan-enrich.sh` |
| SQS per-queue attributes (DLQ, encryption, FIFO) | `aws-scan-enrich.sh` |
| RDS subnet groups + user-modified parameter groups | `aws-scan-enrich.sh` |
| Step Functions per-state-machine definition + logging | `aws-scan-enrich.sh` |
| ElastiCache replication groups + user-modified parameters | `aws-scan-enrich.sh` |
| MSK (Kafka) per-cluster broker config and version | `aws-scan-enrich.sh` |
| Cognito per-user-pool config + app clients | `aws-scan-enrich.sh` |
| EFS per-file-system mount targets + access points | `aws-scan-enrich.sh` |

---

## Optional: Resource Explorer Overview

If **Resource Explorer** is already enabled in the account, a single query gives a high-level resource count across all types (does not replace the per-field detail from the scripts):

```bash
aws resourcegroupstaggingapi get-resources --region <resource-explorer-aggregation-region>
```

Refer to current AWS documentation for the aggregation region and enablement steps.

---

## No CLI or Insufficient Permissions

- Export or screenshot resource lists from the AWS Console per region, then fill in the resource table in `migration-assessment-report.md` manually.
- Both scripts annotate `AccessDenied` and timeout conditions inside each output block, making it easy to distinguish "no resources" from "no permission".
