# Acceptance Criteria: alibabacloud-finops-inspect

**Scenario**: Cost-oriented health inspection across all regions
**Purpose**: Skill testing acceptance criteria

---

## Correct Python SDK Code Patterns

### 1. Import Patterns

#### CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
from alibabacloud_rds20140815.client import Client as Rds20140815Client
from alibabacloud_vpc20160428.client import Client as Vpc20160428Client
from alibabacloud_slb20140515.client import Client as Slb20140515Client
from alibabacloud_alb20200616.client import Client as Alb20200616Client
from alibabacloud_nlb20220430.client import Client as Nlb20220430Client
from alibabacloud_cms20190101.client import Client as Cms20190101Client
```

#### INCORRECT
```python
from aliyunsdkcore.client import AcsClient  # Deprecated SDK
from alibabacloud_ecs.client import Client  # Wrong import path
```

### 2. Authentication — must use CredentialClient, never hardcode AK/SK

#### CORRECT
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
client = Ecs20140526Client(config)
```

#### INCORRECT
```python
# NEVER hardcode credentials
config = open_api_models.Config(
    access_key_id='LTAI...',
    access_key_secret='xxx...'
)
```

### 3. API Call Pattern — DescribeInstances with pagination

#### CORRECT
```python
from alibabacloud_ecs20140526 import models as ecs_models

def describe_instances(client, region_id):
    all_instances = []
    next_token = None
    while True:
        request = ecs_models.DescribeInstancesRequest(
            region_id=region_id,
            page_size=100,
            next_token=next_token
        )
        response = client.describe_instances(request)
        instances = response.body.instances.instance
        all_instances.extend(instances)
        next_token = response.body.next_token
        if not next_token:
            break
    return all_instances
```

### 4. CloudMonitor Metric Query Pattern

#### CORRECT
```python
from alibabacloud_cms20190101 import models as cms_models

def query_metric_last(client, namespace, metric_name, instance_id, days=7):
    request = cms_models.DescribeMetricLastRequest(
        namespace=namespace,
        metric_name=metric_name,
        dimensions=f'{{"instanceId":"{instance_id}"}}',
        period='86400'
    )
    response = client.describe_metric_last(request)
    return response.body
```

---

## CLI Command Patterns (for credential setup)

### 1. Verify CLI Configuration

#### CORRECT
```bash
aliyun configure list
```

#### INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID  # FORBIDDEN - never echo credentials
aliyun configure set --access-key-id "LTAI..."  # FORBIDDEN - never set literal values
```

---

## Judgment Logic Verification

### 1. ECS Utilization Judgment

| Condition | Severity | Priority |
|-----------|----------|----------|
| CPU < 5% AND Memory < 10% AND Network < 50 Kbps (7-day avg) | Critical Idle | P1 |
| CPU < 10% OR Memory < 20% (7-day avg) | Low Utilization | P2 |
| CPU >= 10% AND Memory >= 20% | Normal | - |
| Stopped + PrePaid | Stopped but billed | P1 |

### 2. Idle Resource Judgment

| Resource | Condition | Severity | Priority |
|----------|-----------|----------|----------|
| EIP | Status=Available | Unbound EIP | P0 |
| EIP | Status=InUse + zero 7-day traffic | Bound but zero traffic | P1 |
| Disk | Status=Available + DiskType=data + created > 30 days | Unmounted disk (old) | P0 |
| Disk | Status=Available + DiskType=data + created <= 30 days | Unmounted disk | P1 |
| CLB/ALB/NLB | No listeners | Idle LB | P0 |
| NAT | No EIP bound | Fully idle NAT | P0 |
| NAT | EIP bound + zero SNAT/DNAT rules | Configuration missing | P0 |

### 3. Observation Window Handling

| Condition | Action |
|-----------|--------|
| Resource created within last 7 days | Exclude from idle/low-utilization judgment, flag as "observation window" |
| RDS PayType=Serverless | Exclude from judgment, flag as "Serverless instance" |
| ECS without CloudMonitor agent | Flag as "memory data missing", judge on CPU only |

---

## Error Handling Patterns

### 1. Permission Error

#### CORRECT Behavior
- Detect error code containing `Forbidden` or `RAM` or `AccessDenied`
- Guide user to check RAM permissions. The skill requires read-only actions: `ecs:DescribeRegions`, `ecs:DescribeInstances`, `ecs:DescribeDisks`, `rds:DescribeDBInstances`, `vpc:DescribeEipAddresses`, `vpc:DescribeNatGateways`, `slb:DescribeLoadBalancers`, `alb:ListLoadBalancers`, `nlb:ListLoadBalancers`, `cms:DescribeMetricLast`, `cms:DescribeMetricList`
- Continue inspection for other resource types

#### INCORRECT Behavior
- Abort entire inspection on single permission error
- Ignore permission errors silently

### 2. Throttling Error

#### CORRECT Behavior
- Detect error code `Throttling` or `Throttling.User`
- Implement exponential backoff (1s -> 2s -> 4s)
- Retry up to 3 times
- Log throttling events in error summary

#### INCORRECT Behavior
- Immediately abort on throttling
- Retry without backoff

### 3. Network Timeout

#### CORRECT Behavior
- Detect connection timeout or read timeout
- Retry with increasing timeout (5s -> 10s -> 15s)
- Up to 2 retries

---

## Test Scenarios

| Test Case | Input | Expected Result |
|-----------|-------|-----------------|
| Full inspection | No parameters | Inspects all regions, all resource types |
| Region filter | --regions cn-hangzhou | Only inspects cn-hangzhou |
| Type filter | --types ecs,rds | Only inspects ECS and RDS |
| Custom thresholds | --cpu-threshold 15 --memory-threshold 25 | Uses custom thresholds |
| Idle only | --idle-only | Skips utilization analysis |
| Utilization only | --utilization-only | Skips idle resource detection |
| Invalid credentials | No credentials configured | Error message, stops execution |
| No instances | Valid credentials, empty account | Empty results, zero issues |
| Throttling simulation | Large account | Retries with backoff, completes with partial results |
| Permission denied | Missing RAM permissions | Error for specific resource type, continues others |
