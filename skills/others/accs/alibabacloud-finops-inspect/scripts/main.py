#!/usr/bin/env python3
"""
Alibaba Cloud FinOps Resource Inspection Tool

Performs cost-oriented health inspection across all regions of an Alibaba Cloud account.
Scans ECS, RDS, EIP, Cloud Disks, Load Balancers (CLB/ALB/NLB), and NAT Gateways
to identify underutilized and idle resources.

Usage:
    python3 src/main.py                          # Full inspection
    python3 src/main.py --regions cn-hangzhou     # Specific regions
    python3 src/main.py --types ecs,rds,eip       # Specific resource types
    python3 src/main.py --cpu-threshold 15        # Custom thresholds
    python3 src/main.py --idle-only               # Idle resources only
    python3 src/main.py --utilization-only        # Utilization only
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# --- Alibaba Cloud SDK imports ---
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models

from alibabacloud_rds20140815.client import Client as RdsClient
from alibabacloud_rds20140815 import models as rds_models

from alibabacloud_vpc20160428.client import Client as VpcClient
from alibabacloud_vpc20160428 import models as vpc_models

from alibabacloud_slb20140515.client import Client as SlbClient
from alibabacloud_slb20140515 import models as slb_models

from alibabacloud_alb20200616.client import Client as AlbClient
from alibabacloud_alb20200616 import models as alb_models

from alibabacloud_nlb20220430.client import Client as NlbClient
from alibabacloud_nlb20220430 import models as nlb_models

from alibabacloud_cms20190101.client import Client as CmsClient
from alibabacloud_cms20190101 import models as cms_models

# --- Constants ---

SKILL_NAME = 'alibabacloud-finops-inspect'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '') or uuid.uuid4().hex

ALL_RESOURCE_TYPES = ['ecs', 'rds', 'eip', 'disk', 'clb', 'alb', 'nlb', 'nat']

# CloudMonitor namespaces
CMS_NAMESPACE_ECS = 'acs_ecs_dashboard'
CMS_NAMESPACE_RDS = 'acs_rds_dashboard'
CMS_NAMESPACE_EIP = 'acs_vpc_eip'

# Default thresholds
DEFAULT_CPU_THRESHOLD = 10
DEFAULT_MEMORY_THRESHOLD = 20
DEFAULT_DAYS = 7
DEFAULT_PAGE_SIZE = 100
MAX_CONCURRENT_REGIONS = 5
TOTAL_TIMEOUT_SECONDS = 600  # 10 minutes

# --- Logging ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# --- Enums and Data Classes ---

class Severity(str, Enum):
    P0 = "P0 - Act Now"
    P1 = "P1 - Recommended"
    P2 = "P2 - Observe"
    NORMAL = "Normal"
    OBSERVATION_WINDOW = "Observation Window"


class ResourceType(str, Enum):
    ECS = "ecs"
    RDS = "rds"
    EIP = "eip"
    DISK = "disk"
    CLB = "clb"
    ALB = "alb"
    NLB = "nlb"
    NAT = "nat"


@dataclass
class InspectionResult:
    """Holds the result of inspecting a single resource."""
    resource_type: str
    resource_id: str
    resource_name: str
    region_id: str
    status: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    monthly_cost_estimate: str = ""


@dataclass
class InspectionReport:
    """Aggregated inspection report."""
    start_time: str = ""
    end_time: str = ""
    regions: List[str] = field(default_factory=list)
    resource_counts: Dict[str, int] = field(default_factory=dict)
    issue_counts: Dict[str, int] = field(default_factory=dict)
    results: List[InspectionResult] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)


# --- Utility Functions ---

def _build_user_agent() -> str:
    """Build the complete three-segment User-Agent string."""
    return f'AlibabaCloud-Agent-Skills/{SKILL_NAME}/{SESSION_ID}'


def create_client_config(endpoint: str) -> open_api_models.Config:
    """Create an API client config with automatic credential loading."""
    credential = CredentialClient()
    return open_api_models.Config(
        credential=credential,
        endpoint=endpoint,
        user_agent=_build_user_agent()
    )


def create_runtime_options(connect_timeout: int = 5000, read_timeout: int = 10000) -> util_models.RuntimeOptions:
    """Create runtime options with configurable timeouts."""
    return util_models.RuntimeOptions(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout
    )


def is_within_observation_window(creation_time_str: str, days: int = 7) -> bool:
    """Check if a resource was created within the observation window.

    Args:
        creation_time_str: Creation time in ISO format (e.g., '2024-01-15T10:30:00Z')
        days: Number of days for the observation window

    Returns:
        True if the resource is within the observation window
    """
    try:
        # Handle various ISO formats
        creation_time_str = creation_time_str.replace('Z', '+00:00')
        if '+' not in creation_time_str and '-' not in creation_time_str[10:]:
            creation_time_str += '+00:00'
        creation_time = datetime.fromisoformat(creation_time_str)
        cutoff = datetime.now(creation_time.tzinfo) - timedelta(days=days)
        return creation_time > cutoff
    except (ValueError, AttributeError):
        return False


def parse_datetime_safe(time_str: str) -> Optional[datetime]:
    """Safely parse datetime string in various formats."""
    if not time_str:
        return None
    try:
        time_str = time_str.replace('Z', '+00:00')
        if '+' not in time_str and '-' not in time_str[10:]:
            time_str += '+00:00'
        return datetime.fromisoformat(time_str)
    except (ValueError, AttributeError):
        return None


def days_since_creation(creation_time_str: str) -> float:
    """Calculate days since resource creation."""
    creation_time = parse_datetime_safe(creation_time_str)
    if not creation_time:
        return 0
    now = datetime.now(creation_time.tzinfo) if creation_time.tzinfo else datetime.now()
    delta = now - creation_time
    return delta.total_seconds() / 86400


# --- Retry Decorator ---

def with_retry(max_retries: int = 3, base_delay: float = 1.0, label: str = ""):
    """Decorator for retrying API calls with exponential backoff."""
    def decorator(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    retry_label = f" [{label}]" if label else ""

                    if 'Throttling' in error_msg or 'Throttling.User' in error_msg:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Throttled{retry_label} on attempt {attempt+1}/{max_retries}, retrying in {delay}s...")
                        time.sleep(delay)
                    elif 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                        delay = (attempt + 1) * 5
                        logger.warning(f"Timeout{retry_label} on attempt {attempt+1}/{max_retries}, retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


# --- Client Factory ---

class ClientFactory:
    """Factory for creating Alibaba Cloud API clients."""

    @staticmethod
    def create_ecs_client(region_id: str) -> EcsClient:
        config = create_client_config(f'ecs.{region_id}.aliyuncs.com')
        return EcsClient(config)

    @staticmethod
    def create_rds_client(region_id: str) -> RdsClient:
        config = create_client_config(f'rds.{region_id}.aliyuncs.com')
        return RdsClient(config)

    @staticmethod
    def create_vpc_client(region_id: str) -> VpcClient:
        config = create_client_config(f'vpc.{region_id}.aliyuncs.com')
        return VpcClient(config)

    @staticmethod
    def create_slb_client(region_id: str) -> SlbClient:
        config = create_client_config(f'slb.{region_id}.aliyuncs.com')
        return SlbClient(config)

    @staticmethod
    def create_alb_client(region_id: str) -> AlbClient:
        config = create_client_config(f'alb.{region_id}.aliyuncs.com')
        return AlbClient(config)

    @staticmethod
    def create_nlb_client(region_id: str) -> NlbClient:
        config = create_client_config(f'nlb.{region_id}.aliyuncs.com')
        return NlbClient(config)

    @staticmethod
    def create_cms_client(region_id: str) -> CmsClient:
        config = create_client_config(f'metrics.{region_id}.aliyuncs.com')
        return CmsClient(config)


# --- Region Discovery ---

def discover_regions() -> List[str]:
    """Discover all enabled regions under the account using ECS DescribeRegions.

    Returns:
        List of region IDs
    """
    logger.info("Discovering enabled regions...")
    # Use cn-hangzhou as the default endpoint for region discovery
    client = ClientFactory.create_ecs_client('cn-hangzhou')

    try:
        request = ecs_models.DescribeRegionsRequest(
            instance_charge_type='PostPaid'
        )
        runtime = create_runtime_options()
        response = client.describe_regions_with_options(request, runtime)

        regions = []
        if response.body and response.body.regions and response.body.regions.region:
            for region in response.body.regions.region:
                if region.region_id:
                    regions.append(region.region_id)
                    logger.info(f"  Found region: {region.region_id} ({region.local_name or ''})")

        if not regions:
            logger.warning("No regions discovered. Check account and credentials.")
        return regions

    except Exception as e:
        logger.error(f"Failed to discover regions: {e}")
        raise


# --- CloudMonitor Query ---

def query_cms_metric(client: CmsClient, namespace: str, metric_name: str,
                     dimensions: str, period: str = '86400') -> Optional[List[Dict]]:
    """Query a CloudMonitor metric.

    Args:
        client: CMS client instance
        namespace: Metric namespace
        metric_name: Metric name
        dimensions: JSON dimensions string
        period: Aggregation period in seconds

    Returns:
        List of datapoints or None
    """

    @with_retry(max_retries=3, base_delay=1.0, label=f"CMS:{metric_name}")
    def _do_query():
        request = cms_models.DescribeMetricLastRequest(
            namespace=namespace,
            metric_name=metric_name,
            dimensions=dimensions,
            period=period
        )
        runtime = create_runtime_options(read_timeout=15000)
        response = client.describe_metric_last_with_options(request, runtime)

        if response.body and response.body.code == '200' and response.body.datapoints:
            return json.loads(response.body.datapoints)
        return None

    try:
        return _do_query()
    except Exception as e:
        logger.debug(f"CMS query failed for {metric_name}: {e}")
        return None


def compute_average(datapoints: Optional[List[Dict]], key: str = 'Average') -> Optional[float]:
    """Compute average from CloudMonitor datapoints.

    Args:
        datapoints: List of datapoint dicts
        key: The field to average

    Returns:
        Average value or None
    """
    if not datapoints:
        return None

    values = []
    for dp in datapoints:
        if key in dp and dp[key] is not None:
            try:
                values.append(float(dp[key]))
            except (ValueError, TypeError):
                continue

    if not values:
        return None

    return sum(values) / len(values)


def compute_max(datapoints: Optional[List[Dict]], key: str = 'Maximum') -> Optional[float]:
    """Compute maximum from CloudMonitor datapoints."""
    if not datapoints:
        return None

    values = []
    for dp in datapoints:
        if key in dp and dp[key] is not None:
            try:
                values.append(float(dp[key]))
            except (ValueError, TypeError):
                continue

    if not values:
        return None

    return max(values)


# --- ECS Inspector ---

def inspect_ecs_instances(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect ECS instances in a region.

    Returns:
        Tuple of (results, errors)
    """
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting ECS instances...")

    client = ClientFactory.create_ecs_client(region_id)
    cms_client = ClientFactory.create_cms_client(region_id)

    # Paginate through all instances
    all_instances = []
    next_token = None

    @with_retry(max_retries=3, base_delay=0.5, label=f"ECS:DescribeInstances:{region_id}")
    def _describe_instances(token=None):
        request = ecs_models.DescribeInstancesRequest(
            region_id=region_id,
            page_size=DEFAULT_PAGE_SIZE,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.describe_instances_with_options(request, runtime)

    try:
        while True:
            response = _describe_instances(next_token)
            if response.body and response.body.instances and response.body.instances.instance:
                all_instances.extend(response.body.instances.instance)
            next_token = response.body.next_token if response.body else None
            if not next_token:
                break
    except Exception as e:
        errors.append({
            'api': 'DescribeInstances',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe ECS instances: {e}")
        return results, errors

    logger.info(f"[{region_id}] Found {len(all_instances)} ECS instances")

    for instance in all_instances:
        instance_id = instance.instance_id or 'unknown'
        instance_name = instance.instance_name or instance_id
        status = instance.status or 'unknown'
        charge_type = instance.instance_charge_type or 'unknown'
        creation_time = instance.creation_time or ''
        instance_type = instance.instance_type or ''

        resource_details = {
            'instance_type': instance_type,
            'charge_type': charge_type,
            'status': status,
            'creation_time': creation_time,
        }

        # Check for stopped but billed prepaid instances
        if status == 'Stopped' and charge_type == 'PrePaid':
            results.append(InspectionResult(
                resource_type='ecs',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.P1.value,
                details=resource_details,
                recommendation=(
                    f"PREPAID instance {instance_id} is stopped but still billed. "
                    f"Consider releasing if no longer needed. [Please confirm before acting]"
                )
            ))
            continue

        # Skip non-running instances for utilization analysis
        if status != 'Running':
            continue

        # Skip if utilization-only mode is not set and we only want idle resources
        if config.idle_only:
            continue

        # Check observation window
        if is_within_observation_window(creation_time, config.days):
            results.append(InspectionResult(
                resource_type='ecs',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.OBSERVATION_WINDOW.value,
                details=resource_details,
                recommendation=(
                    f"Instance {instance_id} was created recently (within {config.days} days). "
                    f"Monitoring data collected but not judged for optimization. [Observe]"
                )
            ))
            continue

        # Query CloudMonitor metrics
        dimensions = json.dumps({"instanceId": instance_id})

        cpu_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'CPUUtilization', dimensions))
        memory_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'memory_usedutilization', dimensions))
        disk_read_iops = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'DiskReadIOPS', dimensions, 'Average'))
        disk_write_iops = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'DiskWriteIOPS', dimensions, 'Average'))
        net_in = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'IntranetInRate', dimensions))
        net_out = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_ECS, 'IntranetOutRate', dimensions))

        memory_missing = memory_avg is None
        total_iops = (disk_read_iops or 0) + (disk_write_iops or 0)
        max_network = max(net_in or 0, net_out or 0)

        resource_details.update({
            'cpu_avg': round(cpu_avg, 2) if cpu_avg is not None else 'N/A',
            'memory_avg': round(memory_avg, 2) if memory_avg is not None else 'N/A (no agent)',
            'total_iops': round(total_iops, 2),
            'max_network_kbps': round(max_network, 2),
        })

        # Judgment logic
        is_critical_idle = False
        is_low_util = False

        if not memory_missing:
            is_critical_idle = (
                (cpu_avg is not None and cpu_avg < 5) and
                (memory_avg is not None and memory_avg < 10) and
                max_network < 50
            )
            is_low_util = (
                (cpu_avg is not None and cpu_avg < config.cpu_threshold) or
                (memory_avg is not None and memory_avg < config.memory_threshold)
            )
        else:
            # Without memory data, judge on CPU only
            is_critical_idle = (cpu_avg is not None and cpu_avg < 5) and max_network < 50
            is_low_util = cpu_avg is not None and cpu_avg < config.cpu_threshold

        if is_critical_idle:
            results.append(InspectionResult(
                resource_type='ecs',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.P1.value,
                details=resource_details,
                recommendation=(
                    f"CRITICAL IDLE: CPU={cpu_avg:.1f}%, Memory={memory_avg:.1f}%, "
                    f"Network={max_network:.1f} Kbps (7-day avg). "
                    f"Consider releasing or downsizing. [Please confirm before acting]"
                )
            ))
        elif is_low_util:
            results.append(InspectionResult(
                resource_type='ecs',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.P2.value,
                details=resource_details,
                recommendation=(
                    f"LOW UTILIZATION: CPU={cpu_avg:.1f}%, Memory={memory_avg:.1f}%. "
                    f"Consider downsizing instance type. [Please confirm before acting]"
                )
            ))
        else:
            # Billing optimization: long-running PostPaid instances should switch to PrePaid
            if charge_type == 'PostPaid':
                age_days = days_since_creation(creation_time)
                if age_days > 30:
                    results.append(InspectionResult(
                        resource_type='ecs',
                        resource_id=instance_id,
                        resource_name=instance_name,
                        region_id=region_id,
                        status=status,
                        severity=Severity.P2.value,
                        details={**resource_details, 'running_days': round(age_days, 1)},
                        recommendation=(
                            f"BILLING OPTIMIZATION: PostPaid instance {instance_id} has been "
                            f"running for {age_days:.0f} days (>30 days). Consider switching "
                            f"to PrePaid (subscription) billing for approximately 30%-50% "
                            f"cost savings. [Please confirm before acting]"
                        )
                    ))

    return results, errors


# --- RDS Inspector ---

def inspect_rds_instances(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect RDS instances in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting RDS instances...")

    client = ClientFactory.create_rds_client(region_id)
    cms_client = ClientFactory.create_cms_client(region_id)

    all_instances = []
    page_number = 1

    @with_retry(max_retries=3, base_delay=0.5, label=f"RDS:DescribeDBInstances:{region_id}")
    def _describe_dbinstances(page_num):
        request = rds_models.DescribeDBInstancesRequest(
            region_id=region_id,
            page_size=DEFAULT_PAGE_SIZE,
            page_number=page_num
        )
        runtime = create_runtime_options()
        return client.describe_dbinstances_with_options(request, runtime)

    try:
        while True:
            response = _describe_dbinstances(page_number)
            if response.body and response.body.items and response.body.items.dbinstance:
                all_instances.extend(response.body.items.dbinstance)
            total_count = response.body.total_record_count or 0
            if len(all_instances) >= total_count or not (response.body.items and response.body.items.dbinstance):
                break
            page_number += 1
    except Exception as e:
        errors.append({
            'api': 'DescribeDBInstances',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe RDS instances: {e}")
        return results, errors

    logger.info(f"[{region_id}] Found {len(all_instances)} RDS instances")

    for instance in all_instances:
        instance_id = instance.d_binstance_id or 'unknown'
        instance_name = instance.d_binstance_description or instance_id
        status = instance.d_binstance_status or 'unknown'
        pay_type = instance.pay_type or 'unknown'
        engine = instance.engine or 'unknown'
        engine_version = instance.engine_version or ''
        creation_time = instance.creation_time or ''

        resource_details = {
            'engine': f"{engine}/{engine_version}",
            'db_instance_class': instance.d_binstance_class or '',
            'pay_type': pay_type,
            'status': status,
            'creation_time': creation_time,
        }

        if status != 'Running':
            continue

        # Serverless instances auto-scale to zero, normal behavior
        # Must be checked before idle_only gate to ensure proper handling in all modes
        if pay_type == 'Serverless':
            results.append(InspectionResult(
                resource_type='rds',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.OBSERVATION_WINDOW.value,
                details=resource_details,
                recommendation=(
                    f"Serverless instance {instance_id}. Auto-scaling to zero is normal behavior. "
                    f"No optimization needed. [Observe]"
                )
            ))
            continue

        # Check observation window
        if is_within_observation_window(creation_time, config.days):
            results.append(InspectionResult(
                resource_type='rds',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.OBSERVATION_WINDOW.value,
                details=resource_details,
                recommendation=(
                    f"RDS instance {instance_id} was created recently (within {config.days} days). "
                    f"Monitoring data collected but not judged. [Observe]"
                )
            ))
            continue

        # Query CloudMonitor metrics
        dimensions = json.dumps({"instanceId": instance_id})

        cpu_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_RDS, 'CpuUsage', dimensions))
        memory_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_RDS, 'MemoryUsage', dimensions))
        iops_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_RDS, 'IOPSUsage', dimensions))
        conn_avg = compute_average(
            query_cms_metric(cms_client, CMS_NAMESPACE_RDS, 'ConnectionUsage', dimensions))

        resource_details.update({
            'cpu_avg': round(cpu_avg, 2) if cpu_avg is not None else 'N/A',
            'memory_avg': round(memory_avg, 2) if memory_avg is not None else 'N/A',
            'iops_avg': round(iops_avg, 2) if iops_avg is not None else 'N/A',
            'connection_avg': round(conn_avg, 2) if conn_avg is not None else 'N/A',
        })

        # Judgment: zero connections = idle, low CPU = underutilized
        is_idle = conn_avg is not None and conn_avg < 1
        is_low_util = (
            (cpu_avg is not None and cpu_avg < config.cpu_threshold) or
            (memory_avg is not None and memory_avg < config.memory_threshold)
        )

        if is_idle:
            results.append(InspectionResult(
                resource_type='rds',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.P1.value,
                details=resource_details,
                recommendation=(
                    f"IDLE: Connection usage={conn_avg:.1f}%. "
                    f"Consider releasing or converting to Serverless. [Please confirm before acting]"
                )
            ))
        elif not config.idle_only and is_low_util:
            # Low utilization check only runs in non-idle-only mode
            results.append(InspectionResult(
                resource_type='rds',
                resource_id=instance_id,
                resource_name=instance_name,
                region_id=region_id,
                status=status,
                severity=Severity.P2.value,
                details=resource_details,
                recommendation=(
                    f"LOW UTILIZATION: CPU={cpu_avg:.1f}%, Memory={memory_avg:.1f}%. "
                    f"Consider downsizing instance class. [Please confirm before acting]"
                )
            ))
        elif not config.idle_only:
            # Billing optimization: long-running PostPaid RDS instances should switch to PrePaid
            if pay_type == 'Postpaid':
                age_days = days_since_creation(creation_time)
                if age_days > 30:
                    results.append(InspectionResult(
                        resource_type='rds',
                        resource_id=instance_id,
                        resource_name=instance_name,
                        region_id=region_id,
                        status=status,
                        severity=Severity.P2.value,
                        details={**resource_details, 'running_days': round(age_days, 1)},
                        recommendation=(
                            f"BILLING OPTIMIZATION: PostPaid RDS instance {instance_id} has been "
                            f"running for {age_days:.0f} days (>30 days). Consider switching "
                            f"to PrePaid (subscription) billing for approximately 30%-50% "
                            f"cost savings. [Please confirm before acting]"
                        )
                    ))

    return results, errors


# --- EIP Inspector ---

def inspect_eips(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect EIPs in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting EIPs...")

    client = ClientFactory.create_vpc_client(region_id)
    cms_client = ClientFactory.create_cms_client(region_id)

    all_eips = []
    page_number = 1

    @with_retry(max_retries=3, base_delay=0.5, label=f"VPC:DescribeEipAddresses:{region_id}")
    def _describe_eips(page_num):
        request = vpc_models.DescribeEipAddressesRequest(
            region_id=region_id,
            page_size=50,
            page_number=page_num
        )
        runtime = create_runtime_options()
        return client.describe_eip_addresses_with_options(request, runtime)

    try:
        while True:
            response = _describe_eips(page_number)
            if response.body and response.body.eip_addresses and response.body.eip_addresses.eip_address:
                all_eips.extend(response.body.eip_addresses.eip_address)
            total_count = response.body.total_count or 0
            if len(all_eips) >= total_count or not (response.body.eip_addresses and response.body.eip_addresses.eip_address):
                break
            page_number += 1
    except Exception as e:
        errors.append({
            'api': 'DescribeEipAddresses',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe EIPs: {e}")
        return results, errors

    logger.info(f"[{region_id}] Found {len(all_eips)} EIPs")

    for eip in all_eips:
        allocation_id = eip.allocation_id or 'unknown'
        ip_address = eip.ip_address or ''
        eip_name = eip.name or allocation_id
        eip_status = eip.status or 'unknown'
        instance_id = eip.instance_id or ''
        bandwidth = eip.bandwidth or 0

        resource_details = {
            'ip_address': ip_address,
            'status': eip_status,
            'bound_instance': instance_id,
            'bandwidth_mbps': bandwidth,
        }

        if eip_status == 'Available':
            # Unbound EIP - P0
            results.append(InspectionResult(
                resource_type='eip',
                resource_id=allocation_id,
                resource_name=eip_name,
                region_id=region_id,
                status=eip_status,
                severity=Severity.P0.value,
                details=resource_details,
                recommendation=(
                    f"UNBOUND EIP: {ip_address} ({allocation_id}) is not bound to any resource. "
                    f"Consider releasing if not needed. [Please confirm before acting]"
                )
            ))
        elif eip_status == 'InUse':
            if config.idle_only:
                # Check traffic for bound EIP
                dimensions = json.dumps({"instanceId": allocation_id})
                net_rx = compute_average(
                    query_cms_metric(cms_client, CMS_NAMESPACE_EIP, 'net_rx.rate', dimensions))
                net_tx = compute_average(
                    query_cms_metric(cms_client, CMS_NAMESPACE_EIP, 'net_tx.rate', dimensions))

                max_traffic = max(net_rx or 0, net_tx or 0)
                resource_details.update({
                    'net_rx_bps': round(net_rx, 2) if net_rx is not None else 'N/A',
                    'net_tx_bps': round(net_tx, 2) if net_tx is not None else 'N/A',
                })

                if max_traffic < 100:  # Less than 100 bytes/s average
                    results.append(InspectionResult(
                        resource_type='eip',
                        resource_id=allocation_id,
                        resource_name=eip_name,
                        region_id=region_id,
                        status=eip_status,
                        severity=Severity.P1.value,
                        details=resource_details,
                        recommendation=(
                            f"ZERO TRAFFIC EIP: {ip_address} is bound but has near-zero traffic "
                            f"(RX={net_rx:.0f}, TX={net_tx:.0f} bytes/s 7-day avg). "
                            f"Consider releasing if not needed. [Please confirm before acting]"
                        )
                    ))

    return results, errors


# --- Disk Inspector ---

def inspect_disks(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect unmounted data disks in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting unmounted disks...")

    client = ClientFactory.create_ecs_client(region_id)

    all_disks = []
    next_token = None

    @with_retry(max_retries=3, base_delay=0.5, label=f"ECS:DescribeDisks:{region_id}")
    def _describe_disks(token=None):
        request = ecs_models.DescribeDisksRequest(
            region_id=region_id,
            status='Available',
            disk_type='data',
            page_size=DEFAULT_PAGE_SIZE,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.describe_disks_with_options(request, runtime)

    try:
        while True:
            response = _describe_disks(next_token)
            if response.body and response.body.disks and response.body.disks.disk:
                all_disks.extend(response.body.disks.disk)
            next_token = response.body.next_token if response.body else None
            if not next_token:
                break
    except Exception as e:
        errors.append({
            'api': 'DescribeDisks',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe disks: {e}")
        return results, errors

    logger.info(f"[{region_id}] Found {len(all_disks)} unmounted data disks")

    for disk in all_disks:
        disk_id = disk.disk_id or 'unknown'
        disk_name = disk.disk_name or disk_id
        disk_status = disk.status or 'unknown'
        disk_category = disk.category or ''
        disk_size = disk.size or 0
        creation_time = disk.creation_time or ''

        resource_details = {
            'category': disk_category,
            'size_gb': disk_size,
            'status': disk_status,
            'creation_time': creation_time,
        }

        age_days = days_since_creation(creation_time)

        # Disks created > 30 days ago are P0, otherwise P1
        if age_days > 30:
            severity = Severity.P0.value
            recommendation = (
                f"UNMOUNTED DISK (OLD): {disk_id} ({disk_category}, {disk_size}GB) has been "
                f"unmounted for {age_days:.0f} days (>30 days). "
                f"Consider creating a snapshot and releasing. [Please confirm before acting]"
            )
        else:
            severity = Severity.P1.value
            recommendation = (
                f"UNMOUNTED DISK: {disk_id} ({disk_category}, {disk_size}GB) has been "
                f"unmounted for {age_days:.0f} days. "
                f"Consider attaching or releasing. [Please confirm before acting]"
            )

        results.append(InspectionResult(
            resource_type='disk',
            resource_id=disk_id,
            resource_name=disk_name,
            region_id=region_id,
            status=disk_status,
            severity=severity,
            details=resource_details,
            recommendation=recommendation
        ))

    return results, errors


# --- CLB Inspector ---

def inspect_clb(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect CLB instances in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting CLB instances...")

    client = ClientFactory.create_slb_client(region_id)

    @with_retry(max_retries=3, base_delay=0.5, label=f"SLB:DescribeLoadBalancers:{region_id}")
    def _describe_lbs():
        request = slb_models.DescribeLoadBalancersRequest(
            region_id=region_id
        )
        runtime = create_runtime_options()
        return client.describe_load_balancers_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"SLB:DescribeListeners:{region_id}")
    def _describe_listeners(lb_id):
        request = slb_models.DescribeLoadBalancerListenersRequest(
            region_id=region_id,
            load_balancer_id=lb_id
        )
        runtime = create_runtime_options()
        return client.describe_load_balancer_listeners_with_options(request, runtime)

    try:
        response = _describe_lbs()
        if not response.body or not response.body.load_balancers or not response.body.load_balancers.load_balancer:
            return results, errors

        for lb in response.body.load_balancers.load_balancer:
            lb_id = lb.load_balancer_id or 'unknown'
            lb_name = lb.load_balancer_name or lb_id
            lb_status = lb.status or 'unknown'
            address = lb.address or ''

            resource_details = {
                'address': address,
                'status': lb_status,
                'pay_type': getattr(lb, 'pay_type', '') or '',
            }

            # Check listeners
            is_idle = True
            try:
                listener_response = _describe_listeners(lb_id)
                if listener_response.body and listener_response.body.listeners:
                    listeners = listener_response.body.listeners.listener
                    if listeners:
                        # Check if any listener has backend servers with non-zero weight
                        for listener in listeners:
                            if hasattr(listener, 'backend_servers') and listener.backend_servers:
                                backends = listener.backend_servers.backend_server
                                if backends:
                                    for backend in backends:
                                        if getattr(backend, 'weight', 0) > 0:
                                            is_idle = False
                                            break
                            if not is_idle:
                                break
            except Exception as e:
                logger.debug(f"[{region_id}] Failed to describe CLB listeners for {lb_id}: {e}")

            if is_idle:
                results.append(InspectionResult(
                    resource_type='clb',
                    resource_id=lb_id,
                    resource_name=lb_name,
                    region_id=region_id,
                    status=lb_status,
                    severity=Severity.P0.value,
                    details=resource_details,
                    recommendation=(
                        f"IDLE CLB: {lb_id} has no listeners or all listeners have zero backend weights. "
                        f"Consider releasing if not needed. [Please confirm before acting]"
                    )
                ))

    except Exception as e:
        errors.append({
            'api': 'DescribeLoadBalancers',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe CLB instances: {e}")

    return results, errors


# --- ALB Inspector ---

def inspect_alb(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect ALB instances in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting ALB instances...")

    client = ClientFactory.create_alb_client(region_id)

    @with_retry(max_retries=3, base_delay=0.5, label=f"ALB:ListLoadBalancers:{region_id}")
    def _list_lbs(token=None):
        request = alb_models.ListLoadBalancersRequest(
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_load_balancers_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"ALB:ListListeners:{region_id}")
    def _list_listeners(lb_id, token=None):
        request = alb_models.ListListenersRequest(
            load_balancer_id=lb_id,
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_listeners_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"ALB:ListServerGroups:{region_id}")
    def _list_server_groups(token=None):
        request = alb_models.ListServerGroupsRequest(
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_server_groups_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"ALB:ListServerGroupServers:{region_id}")
    def _list_sg_servers(sg_id):
        request = alb_models.ListServerGroupServersRequest(
            server_group_id=sg_id
        )
        runtime = create_runtime_options()
        return client.list_server_group_servers_with_options(request, runtime)

    try:
        # Get all ALBs
        all_lbs = []
        next_token = None
        while True:
            response = _list_lbs(next_token)
            if response.body and response.body.load_balancers:
                all_lbs.extend(response.body.load_balancers)
            next_token = response.body.next_token if response.body else None
            if not next_token:
                break

        for lb in all_lbs:
            lb_id = lb.load_balancer_id or 'unknown'
            lb_name = lb.load_balancer_name or lb_id
            lb_status = lb.load_balancer_status or 'unknown'
            address_type = lb.address_type or ''

            resource_details = {
                'address_type': address_type,
                'status': lb_status,
            }

            # Check listeners
            is_idle = True
            listeners = []
            try:
                next_token = None
                while True:
                    response = _list_listeners(lb_id, next_token)
                    if response.body and response.body.listeners:
                        listeners.extend(response.body.listeners)
                    next_token = response.body.next_token if response.body else None
                    if not next_token:
                        break
            except Exception as e:
                logger.debug(f"[{region_id}] Failed to list ALB listeners for {lb_id}: {e}")

            if not listeners:
                is_idle = True
            else:
                # Check if listeners are bound to server groups with servers
                for listener in listeners:
                    sg_id = getattr(listener, 'server_group_id', '')
                    if not sg_id:
                        continue
                    # Check server group for servers
                    try:
                        sg_response = _list_sg_servers(sg_id)
                        if sg_response.body and sg_response.body.servers:
                            if sg_response.body.servers:
                                is_idle = False
                                break
                    except Exception:
                        pass

            if is_idle:
                results.append(InspectionResult(
                    resource_type='alb',
                    resource_id=lb_id,
                    resource_name=lb_name,
                    region_id=region_id,
                    status=lb_status,
                    severity=Severity.P0.value,
                    details=resource_details,
                    recommendation=(
                        f"IDLE ALB: {lb_id} has no listeners or listeners without backend servers. "
                        f"Consider releasing if not needed. [Please confirm before acting]"
                    )
                ))

    except Exception as e:
        errors.append({
            'api': 'ListLoadBalancers',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe ALB instances: {e}")

    return results, errors


# --- NLB Inspector ---

def inspect_nlb(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect NLB instances in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting NLB instances...")

    client = ClientFactory.create_nlb_client(region_id)

    @with_retry(max_retries=3, base_delay=0.5, label=f"NLB:ListLoadBalancers:{region_id}")
    def _list_lbs(token=None):
        request = nlb_models.ListLoadBalancersRequest(
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_load_balancers_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"NLB:ListListeners:{region_id}")
    def _list_listeners(lb_id, token=None):
        request = nlb_models.ListListenersRequest(
            load_balancer_id=lb_id,
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_listeners_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"NLB:ListServerGroups:{region_id}")
    def _list_server_groups(lb_id=None, token=None):
        request = nlb_models.ListServerGroupsRequest(
            load_balancer_id=lb_id,
            max_results=100,
            next_token=token
        )
        runtime = create_runtime_options()
        return client.list_server_groups_with_options(request, runtime)

    try:
        # Get all NLBs
        all_lbs = []
        next_token = None
        while True:
            response = _list_lbs(next_token)
            if response.body and response.body.load_balancers:
                all_lbs.extend(response.body.load_balancers)
            next_token = response.body.next_token if response.body else None
            if not next_token:
                break

        for lb in all_lbs:
            lb_id = lb.load_balancer_id or 'unknown'
            lb_name = lb.load_balancer_name or lb_id
            lb_status = lb.load_balancer_status or 'unknown'
            address_type = lb.address_type or ''

            resource_details = {
                'address_type': address_type,
                'status': lb_status,
            }

            # Check listeners
            is_idle = True
            try:
                next_token = None
                while True:
                    response = _list_listeners(lb_id, next_token)
                    if response.body and response.body.listeners:
                        for listener in response.body.listeners:
                            sg_id = getattr(listener, 'server_group_id', '')
                            if sg_id:
                                is_idle = False
                                break
                    if is_idle:
                        next_token = response.body.next_token if response.body else None
                        if not next_token:
                            break
                    else:
                        break
            except Exception as e:
                logger.debug(f"[{region_id}] Failed to list NLB listeners for {lb_id}: {e}")

            if is_idle:
                results.append(InspectionResult(
                    resource_type='nlb',
                    resource_id=lb_id,
                    resource_name=lb_name,
                    region_id=region_id,
                    status=lb_status,
                    severity=Severity.P0.value,
                    details=resource_details,
                    recommendation=(
                        f"IDLE NLB: {lb_id} has no listeners or listeners without backend server groups. "
                        f"Consider releasing if not needed. [Please confirm before acting]"
                    )
                ))

    except Exception as e:
        errors.append({
            'api': 'ListLoadBalancers',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe NLB instances: {e}")

    return results, errors


# --- NAT Gateway Inspector ---

def inspect_nat_gateways(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict]]:
    """Inspect NAT gateways in a region."""
    results = []
    errors = []
    logger.info(f"[{region_id}] Inspecting NAT gateways...")

    client = ClientFactory.create_vpc_client(region_id)

    @with_retry(max_retries=3, base_delay=0.5, label=f"VPC:DescribeNatGateways:{region_id}")
    def _describe_nats(page_num):
        request = vpc_models.DescribeNatGatewaysRequest(
            region_id=region_id,
            network_type='internet',
            page_size=50,
            page_number=page_num
        )
        runtime = create_runtime_options()
        return client.describe_nat_gateways_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"VPC:DescribeSnatTableEntries:{region_id}")
    def _describe_snat(nat_id):
        request = vpc_models.DescribeSnatTableEntriesRequest(
            region_id=region_id,
            nat_gateway_id=nat_id
        )
        runtime = create_runtime_options()
        return client.describe_snat_table_entries_with_options(request, runtime)

    @with_retry(max_retries=3, base_delay=0.5, label=f"VPC:DescribeForwardTableEntries:{region_id}")
    def _describe_dnat(fwd_table_id):
        request = vpc_models.DescribeForwardTableEntriesRequest(
            region_id=region_id,
            forward_table_id=fwd_table_id
        )
        runtime = create_runtime_options()
        return client.describe_forward_table_entries_with_options(request, runtime)

    try:
        all_nats = []
        page_number = 1
        while True:
            response = _describe_nats(page_number)
            if response.body and response.body.nat_gateways and response.body.nat_gateways.nat_gateway:
                all_nats.extend(response.body.nat_gateways.nat_gateway)
            total_count = response.body.total_count or 0
            if len(all_nats) >= total_count or not (response.body.nat_gateways and response.body.nat_gateways.nat_gateway):
                break
            page_number += 1
    except Exception as e:
        errors.append({
            'api': 'DescribeNatGateways',
            'region': region_id,
            'error': str(e)
        })
        logger.error(f"[{region_id}] Failed to describe NAT gateways: {e}")
        return results, errors

    logger.info(f"[{region_id}] Found {len(all_nats)} public NAT gateways")

    for nat in all_nats:
        nat_id = nat.nat_gateway_id or 'unknown'
        nat_name = nat.name or nat_id
        nat_status = nat.status or 'unknown'
        vpc_id = nat.vpc_id or ''

        # Check for bound EIPs
        has_eip = False
        eip_count = 0

        # Check bandwidth package IPs
        if nat.bandwidth_package_ids:
            eip_count += 1
            has_eip = True

        # Check NAT gateway private info IP lists
        if hasattr(nat, 'nat_gateway_private_info') and nat.nat_gateway_private_info:
            ip_lists = nat.nat_gateway_private_info.ip_lists
            if ip_lists and ip_lists.ip_list_item:
                eip_count = len(ip_lists.ip_list_item)
                has_eip = eip_count > 0

        resource_details = {
            'vpc_id': vpc_id,
            'status': nat_status,
            'has_eip': has_eip,
            'eip_count': eip_count,
        }

        if not has_eip:
            # No EIP bound - fully idle
            results.append(InspectionResult(
                resource_type='nat',
                resource_id=nat_id,
                resource_name=nat_name,
                region_id=region_id,
                status=nat_status,
                severity=Severity.P0.value,
                details=resource_details,
                recommendation=(
                    f"IDLE NAT: {nat_id} has no EIP bound. "
                    f"Consider releasing if not needed. [Please confirm before acting]"
                )
            ))
        else:
            # Check SNAT and DNAT rules
            snat_count = 0
            dnat_count = 0

            try:
                snat_response = _describe_snat(nat_id)
                if snat_response.body and snat_response.body.snat_table_entries:
                    entries = snat_response.body.snat_table_entries.snat_table_entry
                    if entries:
                        snat_count = len(entries)
            except Exception as e:
                logger.debug(f"[{region_id}] Failed to describe SNAT entries for {nat_id}: {e}")

            # Get forward table ID from NAT gateway
            forward_table_id = ''
            if hasattr(nat, 'forward_table_ids') and nat.forward_table_ids:
                if hasattr(nat.forward_table_ids, 'forward_table_id') and nat.forward_table_ids.forward_table_id:
                    fwd_ids = nat.forward_table_ids.forward_table_id
                    if isinstance(fwd_ids, list) and fwd_ids:
                        forward_table_id = fwd_ids[0]
                    elif isinstance(fwd_ids, str):
                        forward_table_id = fwd_ids

            if forward_table_id:
                try:
                    dnat_response = _describe_dnat(forward_table_id)
                    if dnat_response.body and dnat_response.body.forward_table_entries:
                        entries = dnat_response.body.forward_table_entries.forward_table_entry
                        if entries:
                            dnat_count = len(entries)
                except Exception as e:
                    logger.debug(f"[{region_id}] Failed to describe DNAT entries for {nat_id}: {e}")

            resource_details.update({
                'snat_rules': snat_count,
                'dnat_rules': dnat_count,
            })

            if snat_count == 0 and dnat_count == 0:
                results.append(InspectionResult(
                    resource_type='nat',
                    resource_id=nat_id,
                    resource_name=nat_name,
                    region_id=region_id,
                    status=nat_status,
                    severity=Severity.P0.value,
                    details=resource_details,
                    recommendation=(
                        f"CONFIGURATION MISSING: {nat_id} has EIP bound but zero SNAT/DNAT rules. "
                        f"Consider releasing or configuring rules. [Please confirm before acting]"
                    )
                ))

    return results, errors


# --- Report Generator ---

def generate_report(report: InspectionReport) -> str:
    """Generate a structured text report."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("ALIBABA CLOUD FINOPS RESOURCE INSPECTION REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {report.end_time}")
    lines.append(f"Inspection Period: {report.start_time} - {report.end_time}")
    lines.append(f"Regions Scanned: {', '.join(report.regions) if report.regions else 'N/A'}")
    lines.append("")

    # Summary
    lines.append("-" * 80)
    lines.append("INSPECTION SUMMARY")
    lines.append("-" * 80)

    total_resources = sum(report.resource_counts.values())
    total_issues = sum(report.issue_counts.values())

    lines.append(f"Total Resources Scanned: {total_resources}")
    lines.append(f"Total Issues Found: {total_issues}")
    lines.append("")

    lines.append("Resource Counts:")
    for rtype, count in sorted(report.resource_counts.items()):
        lines.append(f"  {rtype.upper()}: {count}")
    lines.append("")

    if report.issue_counts:
        lines.append("Issue Counts by Severity:")
        # Sort by priority: P0 -> P1 -> P2
        priority_order = {Severity.P0.value: 0, Severity.P1.value: 1, Severity.P2.value: 2}
        sorted_issues = sorted(
            report.issue_counts.items(),
            key=lambda x: priority_order.get(x[0], 99)
        )
        for severity, count in sorted_issues:
            lines.append(f"  {severity}: {count}")
        lines.append("")

    # Per-Resource Detail Tables
    for rtype in ['ecs', 'rds', 'eip', 'disk', 'clb', 'alb', 'nlb', 'nat']:
        rtype_results = [r for r in report.results if r.resource_type == rtype]

        lines.append("-" * 80)
        lines.append(f"{rtype.upper()} DETAILS")
        lines.append("-" * 80)

        if not rtype_results:
            lines.append("No issues found.")
            lines.append("")
            continue

        # Table header
        lines.append(f"{'Resource ID':<25} {'Region':<15} {'Severity':<20} {'Status':<12}")
        lines.append("-" * 72)

        for r in rtype_results:
            lines.append(
                f"{r.resource_id:<25} {r.region_id:<15} {r.severity:<20} {r.status:<12}"
            )
        lines.append("")

        # Detail entries
        for r in rtype_results:
            lines.append(f"  Resource: {r.resource_id} ({r.resource_name})")
            lines.append(f"  Severity: {r.severity}")
            for key, value in r.details.items():
                lines.append(f"    {key}: {value}")
            if r.recommendation:
                lines.append(f"  Recommendation: {r.recommendation}")
            lines.append("")

    # Recommendation Summary
    lines.append("-" * 80)
    lines.append("RECOMMENDATION SUMMARY")
    lines.append("-" * 80)

    # Group by priority
    priority_order = {Severity.P0.value: 0, Severity.P1.value: 1, Severity.P2.value: 2}
    sorted_results = sorted(
        report.results,
        key=lambda x: priority_order.get(x.severity, 99)
    )

    for r in sorted_results:
        if not r.recommendation:
            continue
        lines.append(f"[{r.severity}] {r.resource_type.upper()} - {r.resource_id}")
        lines.append(f"  {r.recommendation}")
        lines.append("")

    # Error Summary
    if report.errors:
        lines.append("-" * 80)
        lines.append("ERROR SUMMARY")
        lines.append("-" * 80)

        for error in report.errors:
            lines.append(f"  API: {error.get('api', 'unknown')}")
            lines.append(f"  Region: {error.get('region', 'unknown')}")
            lines.append(f"  Error: {error.get('error', 'unknown')}")
            lines.append("")

    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


# --- Main Entry Point ---

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Alibaba Cloud FinOps Resource Inspection Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/main.py                              # Full inspection
  python3 src/main.py --regions cn-hangzhou        # Specific regions
  python3 src/main.py --types ecs,rds,eip          # Specific resource types
  python3 src/main.py --cpu-threshold 15           # Custom CPU threshold
  python3 src/main.py --idle-only                  # Idle resources only
  python3 src/main.py --utilization-only           # Utilization only
        """
    )

    parser.add_argument(
        '--regions',
        type=str,
        default=None,
        help='Comma-separated Region IDs (e.g., cn-hangzhou,cn-shanghai). Default: all enabled regions'
    )
    parser.add_argument(
        '--types',
        type=str,
        default=None,
        help=f'Comma-separated resource types. Options: {",".join(ALL_RESOURCE_TYPES)}. Default: all types'
    )
    parser.add_argument(
        '--cpu-threshold',
        type=float,
        default=DEFAULT_CPU_THRESHOLD,
        help=f'CPU low-utilization threshold (%%). Default: {DEFAULT_CPU_THRESHOLD}'
    )
    parser.add_argument(
        '--memory-threshold',
        type=float,
        default=DEFAULT_MEMORY_THRESHOLD,
        help=f'Memory low-utilization threshold (%%). Default: {DEFAULT_MEMORY_THRESHOLD}'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_DAYS,
        help=f'Monitoring lookback days. Default: {DEFAULT_DAYS}'
    )
    parser.add_argument(
        '--idle-only',
        action='store_true',
        default=False,
        help='Only inspect idle resources (skip utilization analysis)'
    )
    parser.add_argument(
        '--utilization-only',
        action='store_true',
        default=False,
        help='Only inspect utilization (skip idle resource detection)'
    )

    return parser.parse_args()


def inspect_region(region_id: str, config: argparse.Namespace) -> Tuple[List[InspectionResult], List[Dict], Dict[str, int]]:
    """Run all inspectors for a single region.

    Returns:
        Tuple of (results, errors, resource_counts)
    """
    results = []
    errors = []
    resource_counts = {}

    # Map resource types to inspector functions
    inspectors = {
        'ecs': inspect_ecs_instances,
        'rds': inspect_rds_instances,
        'eip': inspect_eips,
        'disk': inspect_disks,
        'clb': inspect_clb,
        'alb': inspect_alb,
        'nlb': inspect_nlb,
        'nat': inspect_nat_gateways,
    }

    for rtype in config.types:
        if rtype not in inspectors:
            logger.warning(f"Unknown resource type: {rtype}")
            continue

        inspector_func = inspectors[rtype]
        try:
            r_results, r_errors = inspector_func(region_id, config)
            results.extend(r_results)
            errors.extend(r_errors)

            # Count resources (approximate from results + errors)
            if rtype == 'ecs':
                # Count from ECS instances (includes normal ones)
                resource_counts['ecs'] = len([r for r in r_results if r.resource_type == 'ecs'])
            elif rtype == 'rds':
                resource_counts['rds'] = len([r for r in r_results if r.resource_type == 'rds'])
            elif rtype == 'eip':
                resource_counts['eip'] = len([r for r in r_results if r.resource_type == 'eip'])
            elif rtype == 'disk':
                resource_counts['disk'] = len([r for r in r_results if r.resource_type == 'disk'])
            elif rtype == 'clb':
                resource_counts['clb'] = len([r for r in r_results if r.resource_type == 'clb'])
            elif rtype == 'alb':
                resource_counts['alb'] = len([r for r in r_results if r.resource_type == 'alb'])
            elif rtype == 'nlb':
                resource_counts['nlb'] = len([r for r in r_results if r.resource_type == 'nlb'])
            elif rtype == 'nat':
                resource_counts['nat'] = len([r for r in r_results if r.resource_type == 'nat'])

        except Exception as e:
            errors.append({
                'api': rtype,
                'region': region_id,
                'error': str(e)
            })
            logger.error(f"[{region_id}] Inspector {rtype} failed: {e}")

    return results, errors, resource_counts


def main():
    """Main entry point."""
    config = parse_args()
    start_time = datetime.now().isoformat()
    has_errors = False

    print("=" * 80)
    print("ALIBABA CLOUD FINOPS RESOURCE INSPECTION")
    print("=" * 80)
    print(f"Start Time: {start_time}")
    print(f"Skill: {SKILL_NAME}")
    if SESSION_ID:
        print(f"Session: {SESSION_ID}")
    print()

    # Parse regions
    if config.regions:
        regions = [r.strip() for r in config.regions.split(',') if r.strip()]
        logger.info(f"Using user-specified regions: {regions}")
    else:
        try:
            regions = discover_regions()
        except Exception as e:
            logger.error(f"Failed to discover regions: {e}")
            print("ERROR: Could not discover regions. Check credentials and network.")
            sys.exit(1)

    if not regions:
        logger.error("No regions found. Exiting.")
        sys.exit(1)

    # Parse resource types
    if config.types:
        types = [t.strip().lower() for t in config.types.split(',') if t.strip()]
        for t in types:
            if t not in ALL_RESOURCE_TYPES:
                logger.error(f"Invalid resource type: {t}. Valid types: {ALL_RESOURCE_TYPES}")
                sys.exit(1)
    else:
        types = ALL_RESOURCE_TYPES

    config.types = types

    logger.info(f"Resource types to inspect: {types}")
    logger.info(f"Regions to scan: {regions}")
    logger.info(f"CPU threshold: {config.cpu_threshold}%")
    logger.info(f"Memory threshold: {config.memory_threshold}%")
    logger.info(f"Lookback days: {config.days}")
    logger.info(f"Idle only: {config.idle_only}")
    logger.info(f"Utilization only: {config.utilization_only}")
    print()

    # Initialize report
    report = InspectionReport(
        start_time=start_time,
        regions=regions,
    )

    # Run inspections with concurrency across regions
    all_results = []
    all_errors = []
    all_resource_counts = {}

    def _inspect_single_region(region_id):
        return inspect_region(region_id, config)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REGIONS) as executor:
        future_to_region = {
            executor.submit(_inspect_single_region, region_id): region_id
            for region_id in regions
        }

        for future in concurrent.futures.as_completed(future_to_region):
            region_id = future_to_region[future]
            try:
                r_results, r_errors, r_counts = future.result()
                all_results.extend(r_results)
                all_errors.extend(r_errors)
                for k, v in r_counts.items():
                    all_resource_counts[k] = all_resource_counts.get(k, 0) + v
            except Exception as e:
                logger.error(f"Region {region_id} inspection failed: {e}")
                all_errors.append({
                    'api': 'region_inspection',
                    'region': region_id,
                    'error': str(e)
                })
                has_errors = True

    # Build report
    report.end_time = datetime.now().isoformat()
    report.results = all_results
    report.errors = all_errors
    report.resource_counts = all_resource_counts

    # Count issues by severity
    severity_counts = {}
    for r in all_results:
        if r.severity and r.severity != Severity.NORMAL.value and r.severity != Severity.OBSERVATION_WINDOW.value:
            severity_counts[r.severity] = severity_counts.get(r.severity, 0) + 1
    report.issue_counts = severity_counts

    # Generate and print report
    report_text = generate_report(report)
    print(report_text)

    # Exit code
    if has_errors and not all_results:
        sys.exit(2)  # Partial completion
    elif has_errors:
        sys.exit(2)  # Partial completion
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
