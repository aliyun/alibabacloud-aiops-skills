# RAM permission list

Minimum read-only RAM permissions required for this skill (no write actions):

## Alibaba Cloud Elasticsearch OpenAPI

- `elasticsearch:DescribeInstance` — Instance details (including clusterTasks)
- `elasticsearch:ListInstance` — List instances
- `elasticsearch:ListSearchLog` — Instance runtime logs
- `elasticsearch:ListActionRecords` — Instance change / action records
- `elasticsearch:ListAllNode` — Cluster node information

## Cloud Monitor (CMS)

- `cms:DescribeMetricList` — Time-series metrics (CPU, memory, disk, load, cluster health)
- `cms:DescribeSystemEventAttribute` — System events (control-plane changes, restarts, etc.)
- `cms:DescribeMetricMetaList` — Metric metadata (available metric catalog)

## Optional but recommended

- `sts:GetCallerIdentity` — Validate the CLI profile (`aliyun sts get-caller-identity`)

## Runtime dependencies

```
aliyun CLI >= 3.3.1
curl
```
