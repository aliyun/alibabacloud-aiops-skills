# API Calling Patterns: Python SDK

This document provides code patterns for calling Alibaba Cloud APIs using the Python Common SDK.

---

## Client Initialization Pattern

```python
import os
import uuid
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models

SKILL_NAME = 'alibabacloud-finops-inspect'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '') or str(uuid.uuid4())

def _build_user_agent() -> str:
    """Build user agent string for observability.

    Format: AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{session-id}

    The SESSION_ID is injected by the Agent via inline env var:
        SKILL_SESSION_ID=xxx python3 src/main.py

    If SKILL_SESSION_ID is not set, a UUID4 is auto-generated as fallback.
    The UA always contains the full three-segment format.
    """
    return f'AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{SESSION_ID}'

def create_client(endpoint: str) -> OpenApiClient:
    """Create an API client with automatic credential loading."""
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=endpoint,
        user_agent=_build_user_agent()
    )
    return OpenApiClient(config)
```

---

## Product Client Creation

```python
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_rds20140815.client import Client as RdsClient
from alibabacloud_vpc20160428.client import Client as VpcClient
from alibabacloud_slb20140515.client import Client as SlbClient
from alibabacloud_alb20200616.client import Client as AlbClient
from alibabacloud_nlb20220430.client import Client as NlbClient
from alibabacloud_cms20190101.client import Client as CmsClient

def create_ecs_client(region_id: str) -> EcsClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'ecs.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return EcsClient(config)

def create_rds_client(region_id: str) -> RdsClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'rds.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return RdsClient(config)

def create_vpc_client(region_id: str) -> VpcClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'vpc.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return VpcClient(config)

def create_slb_client(region_id: str) -> SlbClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'slb.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return SlbClient(config)

def create_alb_client(region_id: str) -> AlbClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'alb.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return AlbClient(config)

def create_nlb_client(region_id: str) -> NlbClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'nlb.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return NlbClient(config)

def create_cms_client(region_id: str) -> CmsClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f'metrics.{region_id}.aliyuncs.com',
        user_agent=_build_user_agent()
    )
    return CmsClient(config)
```

---

## Retry and Throttling Pattern

```python
import time
import logging
from functools import wraps
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retrying API calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    # Handle throttling
                    if 'Throttling' in error_msg or 'Throttling.User' in error_msg:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Throttled on attempt {attempt+1}/{max_retries}, "
                                      f"retrying in {delay}s...")
                        time.sleep(delay)
                    # Handle network timeout
                    elif 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                        delay = (attempt + 1) * 5
                        logger.warning(f"Timeout on attempt {attempt+1}/{max_retries}, "
                                      f"retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        # Non-retryable error
                        raise
            raise last_error
        return wrapper
    return decorator
```

---

## Pagination Pattern

### ECS / VPC / RDS (NextToken-based)

```python
def paginate_describe_instances(client, region_id):
    """Paginate through all ECS instances in a region."""
    all_instances = []
    next_token = None

    while True:
        from alibabacloud_ecs20140526 import models as ecs_models
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

### ALB / NLB (NextToken-based)

```python
def paginate_alb_load_balancers(client):
    """Paginate through all ALB instances."""
    all_lbs = []
    next_token = None

    while True:
        from alibabacloud_alb20200616 import models as alb_models
        request = alb_models.ListLoadBalancersRequest(
            max_results=100,
            next_token=next_token
        )
        response = client.list_load_balancers(request)
        lbs = response.body.load_balancers
        if lbs:
            all_lbs.extend(lbs)
        next_token = response.body.next_token
        if not next_token:
            break

    return all_lbs
```

### RDS (PageNumber-based)

```python
def paginate_rds_instances(client, region_id):
    """Paginate through all RDS instances in a region."""
    all_instances = []
    page_number = 1

    while True:
        from alibabacloud_rds20140815 import models as rds_models
        request = rds_models.DescribeDBInstancesRequest(
            region_id=region_id,
            page_size=100,
            page_number=page_number
        )
        response = client.describe_dbinstances(request)
        instances = response.body.items.dbinstance
        all_instances.extend(instances)

        total_count = response.body.total_record_count or 0
        if len(all_instances) >= total_count or not instances:
            break
        page_number += 1

    return all_instances
```

---

## CloudMonitor Metric Query Pattern

```python
import json
from alibabacloud_cms20190101 import models as cms_models

def query_metric_last(client, namespace, metric_name, resource_id, period=86400):
    """Query the latest metric value from CloudMonitor.

    Args:
        client: CMS client instance
        namespace: Metric namespace (e.g., acs_ecs_dashboard)
        metric_name: Metric name (e.g., CPUUtilization)
        resource_id: Resource identifier (e.g., instance ID)
        period: Aggregation period in seconds (default: 86400 = daily)

    Returns:
        Parsed datapoints or None if query fails
    """
    dimensions = json.dumps({"instanceId": resource_id})
    request = cms_models.DescribeMetricLastRequest(
        namespace=namespace,
        metric_name=metric_name,
        dimensions=dimensions,
        period=str(period)
    )
    response = client.describe_metric_last(request)

    if response.body.code == '200' and response.body.datapoints:
        datapoints = json.loads(response.body.datapoints)
        return datapoints
    return None

def compute_average(datapoints, key='Average'):
    """Compute average from a list of CloudMonitor datapoints.

    Args:
        datapoints: List of datapoint dicts
        key: The field to average (default: 'Average')

    Returns:
        Average value or None if no valid data
    """
    if not datapoints:
        return None

    values = []
    for dp in datapoints:
        if key in dp and dp[key] is not None:
            values.append(dp[key])

    if not values:
        return None

    return sum(values) / len(values)
```

---

## Concurrency Pattern (Multi-Region)

```python
import concurrent.futures
import threading
from typing import List, Callable, Any

def concurrent_execute(
    func: Callable,
    items: List[Any],
    max_workers: int = 5
) -> List[Any]:
    """Execute a function concurrently across multiple items.

    Args:
        func: Function to execute
        items: List of items to process
        max_workers: Maximum number of concurrent workers

    Returns:
        List of results
    """
    results = []
    lock = threading.Lock()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): item for item in items}
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                with lock:
                    if result:
                        results.extend(result)
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                with lock:
                    results.append({'error': str(e), 'item': str(item)})

    return results
```

---

## User-Agent and Session ID Pattern

```python
import os
import uuid

SKILL_NAME = 'alibabacloud-finops-inspect'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '') or str(uuid.uuid4())

def _build_user_agent() -> str:
    """Build user agent string for observability.

    Format: AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{session-id}

    The SESSION_ID is injected by the Agent via inline env var:
        SKILL_SESSION_ID=xxx python3 src/main.py

    If SKILL_SESSION_ID is not set, a UUID4 is auto-generated as fallback.
    The UA always contains the full three-segment format.
    """
    return f'AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{SESSION_ID}'
```
