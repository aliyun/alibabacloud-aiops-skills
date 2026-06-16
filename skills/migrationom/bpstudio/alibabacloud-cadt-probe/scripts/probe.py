#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CADT Alibaba Cloud Resource Probe Script

Use the CADT probe service (BPStudio ExecuteOperationSync) to discover cloud resources.

Usage:
    python probe.py
    python probe.py --regions cn-hangzhou,cn-beijing
    python probe.py --regions cn-hangzhou --output result.json
    python probe.py -q --output result.json    # Quiet mode, suitable for Agent calls
    python probe.py --regions cn-beijing --list-types ecs,vpc
    python probe.py --skip-probe
    python probe.py --related-resource-id i-2ze2efazdozp5htaptaz
    python probe.py --related-resource-id i-xxx --related-types security_group,vswitch
"""

import argparse
import json
import os
import sys
import time
import uuid
from typing import Dict, Any, List, Callable, Optional

from alibabacloud_bpstudio20210931.client import Client as BPStudio20210931Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_bpstudio20210931 import models as bpstudio_20210931_models
from alibabacloud_tea_util import models as util_models


ENDPOINT = "bpstudio.cn-hangzhou.aliyuncs.com"

SERVICE_TYPE = "probe"
OPERATION = "CreateOneClickJob"

POLL_INTERVAL = 10
POLL_TIMEOUT = 30 * 60

RESOURCE_TYPE_EN: Dict[str, str] = {
    "ecs": "Elastic Compute Service",
    "ddh": "Dedicated Host",
    "ess": "Elastic Resource Group",
    "fc": "Function Compute",
    "ack": "Container Service (Dedicated)",
    "ack_managed": "Container Service (Managed)",
    "ask": "Container Service (Serverless)",
    "acr": "Container Registry",
    "vpc": "Virtual Private Cloud",
    "eip": "Elastic IP Address",
    "nat": "NAT Gateway",
    "clb": "Classic Load Balancer",
    "alb": "Application Load Balancer",
    "nlb": "Network Load Balancer",
    "vpn": "VPN Gateway",
    "vbr": "Virtual Border Router",
    "cbn": "Cloud Enterprise Network",
    "cbwp": "Common Bandwidth Package",
    "eni": "Elastic Network Interface",
    "security_group": "Security Group",
    "oss": "Object Storage Service",
    "nas": "File Storage",
    "nas_treme": "Extreme File Storage",
    "cpfs": "Cloud Parallel File Storage",
    "disk": "Cloud Disk",
    "rds": "ApsaraDB RDS",
    "polardb": "PolarDB",
    "dds": "ApsaraDB for MongoDB",
    "ddssharding": "ApsaraDB for MongoDB (Sharded Cluster)",
    "kvstore": "ApsaraDB for Redis (Tair Compatible)",
    "tair": "ApsaraDB for Tair",
    "hbase": "ApsaraDB for HBase",
    "clickhouse": "ApsaraDB for ClickHouse",
    "lindorm": "Lindorm (Multi-model Database)",
    "selectdb": "ApsaraDB for SelectDB",
    "gdb": "Graph Database",
    "drds": "PolarDB Distributed Edition",
    "mybase": "ApsaraDB Dedicated Cluster (MyBase)",
    "adb": "AnalyticDB",
    "hologres": "Hologres (Real-time Data Warehouse)",
    "odps": "MaxCompute",
    "emr": "E-MapReduce",
    "datahub": "DataHub",
    "dla": "Data Lake Analytics",
    "flink": "Realtime Compute for Apache Flink",
    "dide": "DataWorks",
    "kafka": "Message Queue for Apache Kafka",
    "rocketmq": "Message Queue (RocketMQ)",
    "onsproxy": "Message Queue for RabbitMQ",
    "elasticsearch": "Elasticsearch",
    "mse": "Microservices Engine",
    "apigateway": "API Gateway",
    "waf": "Web Application Firewall",
    "ddoscoo": "Anti-DDoS",
    "bastionhost": "Bastion Host",
    "dbaudit": "Database Audit",
    "actiontrail": "ActionTrail",
    "dns": "Alibaba Cloud DNS",
    "cbs": "Cloud Backup Service",
    "ots": "Tablestore",
    "pai": "Platform for AI",
    "airec": "AI Recommendation",
    "hcs_sgw": "Cloud Storage Gateway",
    "slb_vservergroup": "SLB VServer Group",
    "slb": "Classic Load Balancer",
    "sls": "Simple Log Service (SLS)",
    "vswitch": "VSwitch",
    "alb_servergroup": "ALB Server Group",
    "dataworks_space": "DataWorks Workspace",
    "dide_exresourcemixed_public": "DataWorks Mixed Resources",
    "kafka_severless": "Message Queue for Apache Kafka (Serverless)",
    "kvstore_prepaid_public_cn": "ApsaraDB for Redis (Subscription)",
}


def _resolve_resource_type_en(key: str) -> str:
    """Look up English description by resource type key, return empty string if not found"""
    if not key:
        return ""
    return RESOURCE_TYPE_EN.get(str(key).lower(), "")


REGION_EN: Dict[str, str] = {
    "cn-qingdao": "China North 1 (Qingdao)",
    "cn-beijing": "China North 2 (Beijing)",
    "cn-zhangjiakou": "China North 3 (Zhangjiakou)",
    "cn-huhehaote": "China North 5 (Hohhot)",
    "cn-wulanchabu": "China North 6 (Ulanqab)",
    "cn-hangzhou": "China East 1 (Hangzhou)",
    "cn-shanghai": "China East 2 (Shanghai)",
    "cn-nanjing": "China East 5 (Nanjing)",
    "cn-fuzhou": "China East 6 (Fuzhou)",
    "cn-shenzhen": "China South 1 (Shenzhen)",
    "cn-heyuan": "China South 2 (Heyuan)",
    "cn-guangzhou": "China South 3 (Guangzhou)",
    "cn-chengdu": "China Southwest 1 (Chengdu)",
    "cn-wuhan-lr": "China Central (Wuhan LR)",
    "cn-zhengzhou-jva": "China Central (Zhengzhou JVA)",
    "cn-hongkong": "China (Hong Kong)",
    "cn-wulanchabu-acdr-1": "Ulanqab ACDR 1",
    "cn-wulanchabu-gic-1": "Ulanqab GIC 1",
    "cn-heyuan-acdr-1": "Heyuan ACDR 1",
    "cn-zhangjiakou-spe": "Zhangjiakou SPE",
    "cn-shanghai-finance-1": "Shanghai Finance Cloud",
    "cn-beijing-finance-1": "Beijing Finance Cloud",
    "cn-shenzhen-finance-1": "Shenzhen Finance Cloud",
    "cn-hangzhou-finance": "Hangzhou Finance Cloud",
    "cn-north-2-gov-1": "China North 2 Gov Cloud 1",
    "cn-shanghai-cloudspe": "Shanghai CloudSPE",
    "cn-haidian-cm12-c01": "Haidian CM12",
    "cn-hangzhou-dg-a01": "Hangzhou DG A01",
    "cn-hzfinance": "Hangzhou Finance",
    "ens_cn-zhangjiakou": "ENS Zhangjiakou",
    "ap-northeast-1": "Asia Pacific NE 1 (Tokyo)",
    "ap-northeast-2": "Asia Pacific NE 2 (Seoul)",
    "ap-southeast-1": "Asia Pacific SE 1 (Singapore)",
    "ap-southeast-2": "Asia Pacific SE 2 (Sydney)",
    "ap-southeast-3": "Asia Pacific SE 3 (Kuala Lumpur)",
    "ap-southeast-5": "Asia Pacific SE 5 (Jakarta)",
    "ap-southeast-6": "Asia Pacific SE 6 (Manila)",
    "ap-southeast-7": "Asia Pacific SE 7 (Bangkok)",
    "ap-southeast-8": "Asia Pacific SE 8",
    "ap-south-1": "Asia Pacific South 1 (Mumbai)",
    "us-east-1": "US East 1 (Virginia)",
    "us-west-1": "US West 1 (Silicon Valley)",
    "us-west-1-pop": "US West 1 POP",
    "us-southeast-1": "US SE 1",
    "na-south-1": "North America South 1",
    "eu-central-1": "EU Central 1 (Frankfurt)",
    "eu-central-1-pop": "EU Central 1 POP",
    "eu-west-1": "EU West 1 (London)",
    "me-east-1": "Middle East 1 (Dubai)",
    "me-central-1": "Middle East Central 1",
    "global": "Global",
    "acc_m2m": "M2M",
}


def _resolve_region_en(key: str) -> str:
    """Look up English description by regionId, return empty string if not found"""
    if not key:
        return ""
    return REGION_EN.get(str(key).lower(), "")


ATTR_RELATIONSHIP_PATHS: Dict[str, List[Dict[str, Any]]] = {
    "ecs": [
        {"field": "security_group_ids", "path": ["SecurityGroupIds", "SecurityGroupId"], "ref_type": "security_group", "is_list": True},
        {"field": "vswitch_id", "path": ["VpcAttributes", "VSwitchId"], "ref_type": "vswitch"},
        {"field": "vpc_id", "path": ["VpcAttributes", "VpcId"], "ref_type": "vpc"},
    ],
    "rds": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "polardb": [
        {"field": "vpc_id", "path": ["VPCId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "dds": [
        {"field": "vpc_id", "path": ["VPCId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "kvstore": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "tair": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "clb": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "slb": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "alb": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
    ],
    "nlb": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
    ],
    "nat": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["NatGatewayPrivateInfo", "VswitchId"], "ref_type": "vswitch"},
    ],
    "vpn": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
    ],
    "eni": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
        {"field": "security_group_ids", "path": ["SecurityGroupIds", "SecurityGroupId"], "ref_type": "security_group", "is_list": True},
    ],
    "eip": [
        {"field": "instance_id", "path": ["InstanceId"], "ref_type": "auto"},
    ],
    "disk": [
        {"field": "instance_id", "path": ["InstanceId"], "ref_type": "ecs"},
    ],
    "nas": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "hbase": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "clickhouse": [
        {"field": "vpc_id", "path": ["VPCId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "lindorm": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "adb": [
        {"field": "vpc_id", "path": ["VPCId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "elasticsearch": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "kafka": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
    "emr": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
    ],
    "mse": [
        {"field": "vpc_id", "path": ["VpcId"], "ref_type": "vpc"},
        {"field": "vswitch_id", "path": ["VSwitchId"], "ref_type": "vswitch"},
    ],
}


def _parse_attributes(attrs: Any) -> Optional[Dict[str, Any]]:
    """Parse attributes field which may be a JSON string or dict"""
    if attrs is None:
        return None
    if isinstance(attrs, dict):
        return attrs
    if isinstance(attrs, str) and attrs.strip() not in ("", "{}"):
        try:
            parsed = json.loads(attrs)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _resolve_path(data: Dict[str, Any], path: List[str]) -> Any:
    """Navigate nested dict using a list of keys"""
    current: Any = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def _extract_relationships(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relationship IDs from a resource's attributes field.

    Returns a dict mapping relationship field names to their values:
    - Single string for scalar fields (e.g., "vpc_id": "vpc-xxx")
    - List of strings for list fields (e.g., "security_group_ids": ["sg-xxx"])
    """
    attrs = _parse_attributes(resource.get("attributes"))
    if not attrs:
        return {}

    resource_type = str(resource.get("resourceType", "")).lower()
    paths = ATTR_RELATIONSHIP_PATHS.get(resource_type)
    if not paths:
        return {}

    relationships: Dict[str, Any] = {}
    for spec in paths:
        value = _resolve_path(attrs, spec["path"])
        if value is None:
            continue
        field = spec["field"]
        if spec.get("is_list"):
            if isinstance(value, list):
                clean = [str(v) for v in value if v]
                if clean:
                    relationships[field] = clean
            elif isinstance(value, str) and value:
                relationships[field] = [value]
        else:
            if isinstance(value, str) and value:
                relationships[field] = value
            elif isinstance(value, list) and len(value) == 1:
                relationships[field] = str(value[0])

    return relationships


THRESHOLD_COMPACT = 50_000
THRESHOLD_FILE = 200_000


def _build_stdout_summary(output: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "status": "output_too_large",
        "output_file": file_path,
        "hint": "Read the output file for full results",
    }
    mode = output.get("mode")
    if mode == "related-items":
        items = output.get("related_items", {})
        items_list = items.get("list", []) if isinstance(items, dict) else []
        by_type: Dict[str, int] = {}
        if isinstance(items_list, list):
            for item in items_list:
                if isinstance(item, dict):
                    rt = str(item.get("resourceType", "unknown"))
                    by_type[rt] = by_type.get(rt, 0) + 1
        summary["total_related_items"] = len(items_list)
        summary["by_type"] = by_type
    else:
        probe_result = output.get("probe_result", {})
        resource_list = probe_result.get("list", []) if isinstance(probe_result, dict) else []
        by_type = {}
        if isinstance(resource_list, list):
            for r in resource_list:
                if isinstance(r, dict):
                    rt = str(r.get("resourceType", "unknown"))
                    by_type[rt] = by_type.get(rt, 0) + 1
        summary["total_resources"] = len(resource_list)
        summary["by_type"] = by_type
        s = output.get("summary")
        if isinstance(s, dict):
            summary["summary"] = s
    return summary


def _error_exit(message: str, error: str, exit_code: int, quiet: bool) -> None:
    print(f"\n{message}", file=sys.stderr)
    if quiet:
        print(json.dumps({"status": "error", "error": error, "message": message, "exit_code": exit_code}, ensure_ascii=False))
    sys.exit(exit_code)


def _smart_output_json(
    output: Dict[str, Any],
    quiet: bool,
    output_path: Optional[str],
    display_target: str = "probe_result",
) -> None:
    if not quiet:
        target = output.get(display_target)
        if target:
            print("\n" + "=" * 70)
            if display_target == "related_items":
                print("GetProbeRelatedItems Response Details (arguments)")
            else:
                print("GetProbeResult Response Details (arguments)")
            print("=" * 70)
            txt = json.dumps(target, ensure_ascii=False, indent=2, default=str)
            if len(txt) > 5000:
                print(txt[:5000])
                print(f"... (truncated, total {len(txt)} chars, see --output file for full content)")
            else:
                print(txt)
        return

    if output_path:
        summary = {"status": "ok", "output_file": output_path}
        print(json.dumps(summary, ensure_ascii=False, default=str))
        return

    txt = json.dumps(output, ensure_ascii=False, default=str)
    if len(txt) <= THRESHOLD_COMPACT:
        print(txt)
        return

    txt_compact = json.dumps(output, ensure_ascii=False, separators=(',', ':'), default=str)
    if len(txt_compact) <= THRESHOLD_FILE:
        print(f"[output] Auto-switched to compact JSON ({len(txt_compact)} chars)", file=sys.stderr)
        print(txt_compact)
        return

    actual_file = output_path
    if not actual_file:
        import tempfile
        fd, actual_file = tempfile.mkstemp(suffix='.json', prefix='probe_')
        os.close(fd)
        with open(actual_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        print(f"[output] Output too large ({len(txt_compact)} chars), saved to: {actual_file}", file=sys.stderr)

    summary = _build_stdout_summary(output, actual_file)
    print(json.dumps(summary, ensure_ascii=False, default=str))


class CADTProber:
    """CADT Resource Prober

    Submits a probe task (CreateOneClickJob) via the BPStudio ExecuteOperationSync API,
    then polls probe progress via GetOneClickStatus until completion.
    """

    def __init__(self, regions: List[str], list_types: Optional[List[str]] = None, skip_probe: bool = False, quiet: bool = False, job_id: Optional[str] = None, summary_only: bool = False, keep_attributes: bool = False, debug: bool = False):
        self.regions = regions
        self.list_types = list(list_types or [])
        self.skip_probe = skip_probe
        self.quiet = quiet
        self.job_id = job_id
        self.summary_only = summary_only
        self.keep_attributes = keep_attributes
        self.debug = debug
        self.client = self._create_client()

    def _print(self, *args, file=None, **kwargs):
        """Conditional print: in quiet mode only output to stderr, otherwise print normally"""
        if file is not None:
            print(*args, file=file, **kwargs)
        elif not self.quiet:
            print(*args, **kwargs)

    def _enrich_resources_with_relationships(self, resource_list: List[Dict[str, Any]], label: str = "") -> int:
        """Extract relationship IDs from attributes and add as top-level _relationships field.

        Must be called BEFORE attributes are stripped.
        Returns the number of resources enriched.
        """
        if not isinstance(resource_list, list):
            return 0
        enriched = 0
        for r in resource_list:
            if not isinstance(r, dict):
                continue
            rels = _extract_relationships(r)
            if rels:
                r["_relationships"] = rels
                enriched += 1
        if enriched > 0:
            self._print(
                f"\n  [Relationship extraction] Extracted relationship IDs from {enriched} resources{f' ({label})' if label else ''}",
                flush=True,
            )
        return enriched

    def _create_client(self) -> BPStudio20210931Client:
        """Create BPStudio client"""
        credentials_client = CredentialClient()

        session_id = os.environ.get("SKILL_SESSION_ID") or uuid.uuid4().hex
        skill_name = "alibabacloud-cadt-probe"
        user_agent = f"AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

        config = open_api_models.Config(
            credential=credentials_client,
            endpoint=ENDPOINT,
            user_agent=user_agent,
        )
        return BPStudio20210931Client(config)

    def _create_runtime(self) -> util_models.RuntimeOptions:
        """Create RuntimeOptions with timeout configuration"""
        runtime = util_models.RuntimeOptions()
        runtime.connect_timeout = 10000
        runtime.read_timeout = 30000
        return runtime

    def start_probe_job(self) -> str:
        """Submit probe task, return jobId

        On successful CreateOneClickJob, the value field in arguments is the jobId.
        If there is a currently running task, it will be automatically retried.
        """
        self._print("Submitting probe task...", flush=True)
        if self.regions:
            self._print(f"  Probe regions: {', '.join(self.regions)}", flush=True)
        else:
            self._print("  Probe regions: All supported regions", flush=True)

        max_retries = 5
        retry_interval = 30

        for attempt in range(max_retries):
            try:
                attributes: Dict[str, Any] = {}
                if self.regions:
                    attributes["regions"] = self.regions
                request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
                    service_type=SERVICE_TYPE,
                    operation=OPERATION,
                    attributes=attributes,
                    client_token=str(uuid.uuid4())
                )
                resp = self.client.execute_operation_sync_with_options(
                    request, self._create_runtime()
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Submission exception: {str(e)}, retrying in {retry_interval}s...",
                          file=sys.stderr)
                    time.sleep(retry_interval)
                    self.client = self._create_client()
                    continue
                raise RuntimeError(f"Probe task submission exception: {str(e)}")

            if not resp.body:
                raise RuntimeError("Probe task submission failed: empty response body")

            if str(resp.body.code) != "200":
                raise RuntimeError(
                    f"Probe task submission failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
                )

            data = resp.body.data
            if not data:
                raise RuntimeError("Probe task submission failed: empty response data")

            if data.status == "FAILURE" and data.message and "running" in data.message.lower():
                if attempt < max_retries - 1:
                    self._print(f"  {data.message} Retrying in {retry_interval}s...",
                          file=sys.stderr)
                    time.sleep(retry_interval)
                    self.client = self._create_client()
                    continue
                raise RuntimeError(f"Probe task submission failed: {data.message}")

            if data.status != "SUCCESS":
                raise RuntimeError(
                    f"Probe task submission failed: {data.message or 'Unknown error'} (status={data.status})"
                )

            arguments_str = data.arguments
            job_id = None
            if arguments_str:
                try:
                    if isinstance(arguments_str, dict):
                        args_dict = arguments_str
                    elif isinstance(arguments_str, str):
                        args_dict = json.loads(arguments_str)
                    else:
                        args_dict = {}
                    if isinstance(args_dict, dict):
                        job_id = str(args_dict.get("value", ""))
                except (json.JSONDecodeError, TypeError):
                    pass

            if not job_id:
                raise RuntimeError(
                    f"Probe task submission failed: no jobId returned (arguments={arguments_str})"
                )

            self._print(f"  JobId: {job_id}", flush=True)
            return job_id

        raise RuntimeError("Probe task submission failed: max retries exceeded")

    def get_probe_progress(self, job_id: str) -> Dict[str, Any]:
        """Query probe task progress

        Calls GetOneClickStatus via ExecuteOperationSync,
        passing jobId to get probe progress.

        Returns:
            dict containing progress information
        """
        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetOneClickStatus",
            attributes={"jobId": job_id},
            client_token=str(uuid.uuid4())
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"Probe progress query exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("Probe progress query failed: empty response body")

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"Probe progress query failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        result = {
            "status": resp.body.data.status if resp.body.data else None,
            "message": resp.body.data.message if resp.body.data else None,
            "operation_id": resp.body.data.operation_id if resp.body.data else None,
        }

        arguments_str = resp.body.data.arguments if resp.body.data else None
        if arguments_str:
            if isinstance(arguments_str, dict):
                result["arguments"] = arguments_str
            elif isinstance(arguments_str, str) and arguments_str.strip() not in ("", "{}"):
                try:
                    result["arguments"] = json.loads(arguments_str)
                except json.JSONDecodeError:
                    result["arguments_raw"] = arguments_str
            else:
                result["arguments"] = {}
        else:
            result["arguments"] = {}

        return result

    def poll_progress(self, job_id: str) -> Dict[str, Any]:
        """Poll probe progress until task completes or times out

        GetOneClickStatus arguments contains:
        - status: Probe status (Running/Completed/Failed etc.)
        - progressPercentage: Progress percentage
        - progressMessage: Current progress description
        - currentStep: Currently probed resource type

        Returns:
            Final progress information dict
        """
        self._print("  Waiting for probe to complete...", flush=True)

        start_time = time.time()
        last_pct = -1

        while True:
            elapsed = time.time() - start_time
            if elapsed > POLL_TIMEOUT:
                raise TimeoutError(
                    f"Probe task timed out ({POLL_TIMEOUT}s), jobId: {job_id}"
                )

            try:
                progress = self.get_probe_progress(job_id)
            except Exception as e:
                print(f"  Progress query exception: {str(e)}, retrying in {POLL_INTERVAL}s...", file=sys.stderr)
                self.client = self._create_client()
                time.sleep(POLL_INTERVAL)
                continue

            arguments = progress.get("arguments", {})

            one_click = arguments.get("OneClick") if isinstance(arguments, dict) else None
            if isinstance(one_click, dict):
                probe_status = one_click.get("status", "") or arguments.get("status", "")
                err_message = one_click.get("message", "") or arguments.get("message", "")
            else:
                probe_status = arguments.get("status", "")
                err_message = arguments.get("message", "")

            pct = arguments.get("progressPercentage", 0)
            msg = arguments.get("progressMessage", "")
            step = arguments.get("currentStep", "")

            self._print(f"  [{pct}%] {msg} | currentStep: {step} | status: {probe_status} (elapsed {int(elapsed)}s)", flush=True)

            if probe_status in ("Completed", "completed", "COMPLETED",
                                "Finish", "finish", "FINISH") or pct >= 100:
                self._print("  Probe complete!", flush=True)
                return arguments

            if probe_status in ("Fail", "fail", "FAIL", "Failed", "failed", "FAILED"):
                raise RuntimeError(
                    f"Probe task failed (status={probe_status}): "
                    f"{err_message or msg or 'Unknown error'}"
                )

            time.sleep(POLL_INTERVAL)

    def _print_summary(self, summary: Dict[str, Any]):
        """Print probe resource summary to console

        GetProbeResourceSummary returns:
        {
            "resourceInRegions": [{"key": "<regionId>", "count": <int>}, ...],
            "resourceOfType":    [{"key": "<resourceType>", "count": <int>}, ...]
        }
        """
        self._print("\n" + "=" * 70)
        self._print("Probe Resource Summary (GetProbeResourceSummary)")
        self._print("=" * 70)

        if not summary:
            self._print("  (No summary information)")
            return

        if isinstance(summary, dict) and "raw" in summary:
            self._print(summary["raw"])
            return

        if not isinstance(summary, dict):
            self._print(f"  {json.dumps(summary, ensure_ascii=False, indent=2)}")
            return

        regions_list = summary.get("resourceInRegions") or []
        types_list = summary.get("resourceOfType") or []

        def _print_kv_table(
            title: str,
            items: List[Dict[str, Any]],
            key_label: str,
            en_resolver: Optional[Callable[[str], str]] = None,
        ):
            self._print(f"\n  [{title}] {len(items)} items")
            if not items:
                self._print("    (empty)")
                return 0
            key_w, cnt_w = 48, 8
            line_w = key_w + 1 + cnt_w
            self._print("  " + "-" * line_w)
            self._print(f"  {key_label:<{key_w}} {'Count':>{cnt_w}}")
            self._print("  " + "-" * line_w)
            total = 0
            sorted_items = sorted(
                items,
                key=lambda x: int(x.get("count") or 0) if isinstance(x, dict) else 0,
                reverse=True,
            )
            for item in sorted_items:
                if not isinstance(item, dict):
                    self._print(f"  {item}")
                    continue
                k = str(item.get("key", ""))
                c = item.get("count", 0)
                try:
                    total += int(c)
                except (ValueError, TypeError):
                    pass
                if en_resolver is not None:
                    en = en_resolver(k)
                    display_key = f"{k} ({en})" if en else k
                else:
                    display_key = k
                self._print(f"  {display_key:<{key_w}} {str(c):>{cnt_w}}")
            self._print("  " + "-" * line_w)
            self._print(f"  {'Total':<{key_w}} {total:>{cnt_w}}")
            return total

        regions_total = _print_kv_table(
            "By Region (resourceInRegions)", regions_list, "Region (regionId)",
            en_resolver=_resolve_region_en,
        )
        types_total = _print_kv_table(
            "By Resource Type (resourceOfType)", types_list, "Resource Type (resourceType)",
            en_resolver=_resolve_resource_type_en,
        )

        self._print()
        if regions_total == types_total:
            self._print(f"  Total resources: {regions_total}")
        else:
            self._print(f"  Warning: Resource totals mismatch between dimensions: "
                  f"resourceInRegions={regions_total}, resourceOfType={types_total}")

    def get_probe_resource_summary(
        self,
        regions: Optional[List[str]] = None,
        service_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get probe resource summary

        Calls GetProbeResourceSummary via ExecuteOperationSync,
        which returns resource summary for the account associated with the current credentials.

        Args:
            regions: Region filter list, None/empty list means no filter (server returns all regions)
            service_types: Resource type filter list (serviceTypes), None/empty list means no filter

        Returns:
            Resource summary dict containing resourceInRegions / resourceOfType
        """
        self._print("\nFetching probe resource summary...", flush=True)
        if regions:
            self._print(f"  Region filter: {', '.join(regions)}", flush=True)
        else:
            self._print("  Region filter: All regions", flush=True)
        if service_types:
            self._print(f"  Resource type filter: {', '.join(service_types)}", flush=True)
        else:
            self._print("  Resource type filter: All types", flush=True)

        attributes: Dict[str, Any] = {}
        if regions:
            attributes["regions"] = list(regions)
        if service_types:
            attributes["serviceTypes"] = list(service_types)

        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetProbeResourceSummary",
            attributes=attributes,
            client_token=str(uuid.uuid4())
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"Resource summary fetch exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("Resource summary fetch failed: empty response body")

        try:
            body_dict = resp.body.to_map() if hasattr(resp.body, "to_map") else None
        except Exception:
            body_dict = None
        if self.debug and body_dict is not None:
            raw = json.dumps(body_dict, ensure_ascii=False)
            print(f"  [debug] code={resp.body.code} requestId={getattr(resp.body, 'request_id', '')}", file=sys.stderr, flush=True)
            print(f"  [debug] body={raw[:1500]}{'...(truncated)' if len(raw) > 1500 else ''}", file=sys.stderr, flush=True)

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"Resource summary fetch failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        data = resp.body.data
        if data is not None:
            data_status = getattr(data, "status", None)
            data_message = getattr(data, "message", None)
            if data_status and str(data_status).upper() not in ("SUCCESS", "FINISH"):
                raise RuntimeError(
                    f"Resource summary business failure: {data_message or 'Unknown error'} (status={data_status})"
                )

        arguments = resp.body.data.arguments if resp.body.data else None
        if arguments:
            if isinstance(arguments, dict):
                return arguments
            elif isinstance(arguments, str) and arguments.strip() not in ("", "{}"):
                try:
                    return json.loads(arguments)
                except json.JSONDecodeError:
                    return {"raw": arguments}
        return {}

    def get_probe_related_items(
        self,
        resource_id: str,
        service_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Call probe.GetProbeRelatedItems to get all related resources for a given resource

        Args:
            resource_id: Resource instance ID (e.g., i-xxx, sg-xxx, vpc-xxx)
            service_types: Resource type filter list (serviceTypes).
                None/empty list means return all related resources;
                when specified, only return related resources of these types.

        Returns:
            Related resource details dict (raw arguments)
        """
        if not resource_id:
            raise ValueError("resource_id cannot be empty")

        self._print("\nFetching related items (GetProbeRelatedItems)...", flush=True)
        self._print(f"  Resource ID: {resource_id}", flush=True)
        if service_types:
            self._print(f"  Type filter: {', '.join(service_types)}", flush=True)
        else:
            self._print("  Type filter: No filter (return all related resources)", flush=True)

        attributes: Dict[str, Any] = {"resourceId": resource_id}
        if service_types:
            attributes["serviceTypes"] = list(service_types)

        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetProbeRelatedItems",
            attributes=attributes,
            client_token=str(uuid.uuid4()),
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"Related items fetch exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("Related items fetch failed: empty response body")

        try:
            body_dict = resp.body.to_map() if hasattr(resp.body, "to_map") else None
        except Exception:
            body_dict = None
        if self.debug and body_dict is not None:
            raw = json.dumps(body_dict, ensure_ascii=False)
            print(
                f"  [debug] code={resp.body.code} requestId={getattr(resp.body, 'request_id', '')}",
                file=sys.stderr,
                flush=True,
            )
            print(
                f"  [debug] body={raw[:1500]}{'...(truncated)' if len(raw) > 1500 else ''}",
                file=sys.stderr,
                flush=True,
            )

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"Related items fetch failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        data = resp.body.data
        if data is not None:
            data_status = getattr(data, "status", None)
            data_message = getattr(data, "message", None)
            if data_status and str(data_status).upper() not in ("SUCCESS", "FINISH"):
                raise RuntimeError(
                    f"Related items business failure: {data_message or 'Unknown error'} (status={data_status})"
                )

        arguments = resp.body.data.arguments if resp.body.data else None
        if arguments:
            if isinstance(arguments, dict):
                return arguments
            elif isinstance(arguments, str) and arguments.strip() not in ("", "{}"):
                try:
                    return json.loads(arguments)
                except json.JSONDecodeError:
                    return {"raw": arguments}
        return {}

    def get_last_probe_time(self) -> Dict[str, Any]:
        """Call probe.GetLastProbeTime to get last probe task info

        Returns:
            Dict with 'lastTime' key: minutes since last probe, -1 if no valid job
        """
        self._print("\nFetching last probe time (GetLastProbeTime)...", flush=True)

        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetLastProbeTime",
            attributes={},
            client_token=str(uuid.uuid4()),
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"GetLastProbeTime exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("GetLastProbeTime failed: empty response body")

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"GetLastProbeTime failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        data = resp.body.data
        if data is not None:
            data_status = getattr(data, "status", None)
            data_message = getattr(data, "message", None)
            if data_status and str(data_status).upper() not in ("SUCCESS", "FINISH"):
                raise RuntimeError(
                    f"GetLastProbeTime business failure: {data_message or 'Unknown error'} (status={data_status})"
                )

        arguments = resp.body.data.arguments if resp.body.data else None
        if arguments:
            if isinstance(arguments, dict):
                args_dict = arguments
            elif isinstance(arguments, str):
                try:
                    args_dict = json.loads(arguments)
                except json.JSONDecodeError:
                    args_dict = {}
            else:
                args_dict = {}

            last_time = args_dict.get("lastTime", -1)
            result = {"lastTime": int(last_time) if last_time is not None else -1}
            self._print(f"  Last probe: {result['lastTime']} minutes ago" if result['lastTime'] >= 0 else "  Last probe: no valid probe job found", flush=True)
            return result

        return {"lastTime": -1}

    def get_probe_regions(self) -> List[str]:
        """Call probe.GetProbeRegions to get cached region list

        Returns:
            List of cached region IDs
        """
        self._print("\nFetching cached probe regions (GetProbeRegions)...", flush=True)

        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetProbeRegions",
            attributes={},
            client_token=str(uuid.uuid4()),
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"GetProbeRegions exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("GetProbeRegions failed: empty response body")

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"GetProbeRegions failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        data = resp.body.data
        if data is not None:
            data_status = getattr(data, "status", None)
            data_message = getattr(data, "message", None)
            if data_status and str(data_status).upper() not in ("SUCCESS", "FINISH"):
                raise RuntimeError(
                    f"GetProbeRegions business failure: {data_message or 'Unknown error'} (status={data_status})"
                )

        arguments = resp.body.data.arguments if resp.body.data else None
        if arguments:
            if isinstance(arguments, list):
                regions = [str(r) for r in arguments]
            elif isinstance(arguments, dict):
                regions = arguments.get("regions", arguments.get("list", []))
                if isinstance(regions, list):
                    regions = [str(r) for r in regions]
                else:
                    regions = []
            elif isinstance(arguments, str):
                try:
                    parsed = json.loads(arguments)
                    if isinstance(parsed, list):
                        regions = [str(r) for r in parsed]
                    elif isinstance(parsed, dict):
                        regions = parsed.get("regions", parsed.get("list", []))
                        if isinstance(regions, list):
                            regions = [str(r) for r in regions]
                        else:
                            regions = []
                    else:
                        regions = []
                except json.JSONDecodeError:
                    regions = []
            else:
                regions = []
        else:
            regions = []

        self._print(f"  Cached regions: {', '.join(regions) if regions else 'none'}", flush=True)
        return regions

    def get_probe_result(
        self,
        regions: Optional[List[str]] = None,
        service_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Call probe.GetProbeResult to get detailed probe results

        Args:
            regions: Region filter list, None/empty list means no filter (server returns all regions)
            service_types: Resource type filter list (serviceType), None/empty list means no filter

        Returns:
            Detailed probe results dict (raw arguments)
        """
        self._print("\nFetching detailed probe results (GetProbeResult)...", flush=True)
        if regions:
            self._print(f"  Region filter: {', '.join(regions)}", flush=True)
        else:
            self._print("  Region filter: All regions", flush=True)
        if service_types:
            self._print(f"  Resource type filter: {', '.join(service_types)}", flush=True)
        else:
            self._print("  Resource type filter: All types", flush=True)

        attributes: Dict[str, Any] = {}
        if regions:
            attributes["regions"] = list(regions)
        if service_types:
            attributes["serviceTypes"] = list(service_types)

        request = bpstudio_20210931_models.ExecuteOperationSyncRequest(
            service_type=SERVICE_TYPE,
            operation="GetProbeResult",
            attributes=attributes,
            client_token=str(uuid.uuid4()),
        )

        try:
            resp = self.client.execute_operation_sync_with_options(
                request, self._create_runtime()
            )
        except Exception as e:
            raise RuntimeError(f"Detailed probe results fetch exception: {str(e)}")

        if not resp.body:
            raise RuntimeError("Detailed probe results fetch failed: empty response body")

        try:
            body_dict = resp.body.to_map() if hasattr(resp.body, "to_map") else None
        except Exception:
            body_dict = None
        if self.debug and body_dict is not None:
            raw = json.dumps(body_dict, ensure_ascii=False)
            print(
                f"  [debug] code={resp.body.code} requestId={getattr(resp.body, 'request_id', '')}",
                file=sys.stderr,
                flush=True,
            )
            print(
                f"  [debug] body={raw[:1500]}{'...(truncated)' if len(raw) > 1500 else ''}",
                file=sys.stderr,
                flush=True,
            )

        if str(resp.body.code) != "200":
            raise RuntimeError(
                f"Detailed probe results fetch failed: {resp.body.message or 'Unknown error'} (code={resp.body.code})"
            )

        data = resp.body.data
        if data is not None:
            data_status = getattr(data, "status", None)
            data_message = getattr(data, "message", None)
            if data_status and str(data_status).upper() not in ("SUCCESS", "FINISH"):
                raise RuntimeError(
                    f"Detailed probe results business failure: {data_message or 'Unknown error'} (status={data_status})"
                )

        arguments = resp.body.data.arguments if resp.body.data else None
        if arguments:
            if isinstance(arguments, dict):
                return arguments
            elif isinstance(arguments, str) and arguments.strip() not in ("", "{}"):
                try:
                    return json.loads(arguments)
                except json.JSONDecodeError:
                    return {"raw": arguments}
        return {}

    def probe(self) -> Dict[str, Any]:
        """Execute the complete probe workflow"""
        self._print("=" * 70)
        self._print("CADT Resource Probe (BPStudio)")
        self._print("=" * 70)
        self._print(f"  Probe regions:   {', '.join(self.regions) if self.regions else 'All supported regions'}")
        self._print(f"  Probe time:      {time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.skip_probe:
            self._print("  Probe mode:      Skip task creation (pull existing results)")
        elif self.job_id:
            self._print(f"  Probe mode:      Resume existing task (JobId: {self.job_id})")
        self._print("=" * 70)
        self._print()

        if self.skip_probe:
            job_id = ""
            progress: Dict[str, Any] = {}
        elif self.job_id:
            self._print(f"  Using existing JobId: {self.job_id}", flush=True)
            job_id = self.job_id
            progress = self.poll_progress(job_id)
        else:
            job_id = self.start_probe_job()
            progress = self.poll_progress(job_id)

        summary = self.get_probe_resource_summary(
            regions=self.regions,
            service_types=self.list_types,
        )

        self._print_summary(summary)

        probe_result: Optional[Dict[str, Any]] = None
        probe_result_error: Optional[str] = None
        if self.summary_only:
            self._print("\n  Skipping detailed results fetch (--summary mode)", flush=True)
        else:
            try:
                probe_result = self.get_probe_result(
                    regions=self.regions,
                    service_types=self.list_types,
                )
            except (RuntimeError, TimeoutError) as e:
                probe_result_error = str(e)
                self._print(f"\nGetProbeResult failed: {probe_result_error}", file=sys.stderr)

        if self.list_types and isinstance(probe_result, dict) and "list" in probe_result:
            resource_list = probe_result["list"]
            if isinstance(resource_list, list):
                allowed = {t.lower() for t in self.list_types}
                original_count = len(resource_list)
                filtered = [
                    r for r in resource_list
                    if isinstance(r, dict) and str(r.get("resourceType", "")).lower() in allowed
                ]
                probe_result["list"] = filtered
                self._print(
                    f"\n  [Client filter] --list-types={','.join(self.list_types)}: "
                    f"{original_count} -> {len(filtered)} items "
                    f"(filtered out {original_count - len(filtered)} items)",
                    flush=True,
                )

        if isinstance(probe_result, dict) and "list" in probe_result:
            self._enrich_resources_with_relationships(probe_result["list"], label="probe_result")

        if not self.keep_attributes and isinstance(probe_result, dict) and "list" in probe_result:
            resource_list = probe_result["list"]
            if isinstance(resource_list, list):
                stripped = 0
                for r in resource_list:
                    if isinstance(r, dict) and "attributes" in r:
                        del r["attributes"]
                        stripped += 1
                if stripped > 0:
                    self._print(
                        f"\n  [Output optimization] Stripped attributes from {stripped} resources "
                        f"(use --keep-attributes to retain original data)",
                        flush=True,
                    )

        cache_info: Optional[Dict[str, Any]] = None
        cache_warnings: List[str] = []
        try:
            last_probe_info = self.get_last_probe_time()
            cached_regions = self.get_probe_regions()

            if self.skip_probe:
                last_minutes = last_probe_info.get("lastTime", -1)
                if last_minutes >= 0:
                    probe_ts = time.time() - last_minutes * 60
                    probe_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(probe_ts))
                else:
                    probe_time_str = "unknown"
                cache_info = {
                    "cached_regions": cached_regions,
                    "probe_time": probe_time_str,
                    "last_probe_minutes_ago": last_minutes,
                }

            if last_probe_info.get("lastTime", -1) == -1:
                w = "No valid probe job found in cache — results may be empty or stale"
                cache_warnings.append(w)
                self._print(f"\n  [cache warning] {w}", file=sys.stderr, flush=True)

            if cached_regions and self.regions:
                cached_set = {r.lower() for r in cached_regions}
                missing = [r for r in self.regions if r.lower() not in cached_set]
                if missing:
                    w = (
                        f"Requested region(s) {', '.join(missing)} not in probe cache — "
                        f"results for these regions will be empty. "
                        f"Cached regions: {', '.join(cached_regions)}"
                    )
                    cache_warnings.append(w)
                    self._print(f"\n  [cache warning] {w}", file=sys.stderr, flush=True)
        except RuntimeError as e:
            self._print(f"\n  [cache check] Failed to fetch cache metadata: {e}", file=sys.stderr, flush=True)

        self._print("\n" + "=" * 70)

        output: Dict[str, Any] = {
            "regions": self.regions,
            "probe_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "job_id": job_id,
            "progress": progress,
            "summary": summary,
            "probe_result": probe_result,
            "probe_result_filter": {
                "regions": list(self.regions) if self.regions else "all",
                "serviceType": list(self.list_types) if self.list_types else "all",
            },
        }
        if cache_info is not None:
            output["cache_info"] = cache_info
        if cache_warnings:
            output["cache_warnings"] = cache_warnings
        if probe_result_error:
            output["probe_result_error"] = probe_result_error
        return output


def main():
    parser = argparse.ArgumentParser(
        description="CADT Alibaba Cloud Resource Probe Script - Use CADT probe service to discover cloud resources"
    )
    parser.add_argument(
        "--regions",
        required=False,
        default="",
        help="Comma-separated region list (e.g., cn-hangzhou,cn-beijing). Controls both probe scope and result filtering. Probes all supported regions when not specified"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (optional, prints to console only when not specified)"
    )
    parser.add_argument(
        "--list-types",
        default="",
        help="Comma-separated resource type filter list (serviceTypes) for GetProbeResult / GetProbeResourceSummary; empty means no filter (query all types)"
    )
    parser.add_argument(
        "--related-resource-id",
        default="",
        help="Resource ID for GetProbeRelatedItems. When specified, skips OneClick probe and only queries related resources for this resource"
    )
    parser.add_argument(
        "--related-types",
        default="",
        help="Comma-separated resource type filter list (serviceTypes) for GetProbeRelatedItems; empty means no filter (return all related resources)"
    )
    parser.add_argument(
        "--skip-probe",
        action="store_true",
        default=False,
        help="Skip task creation and polling, directly pull existing probe results (suitable for previously probed scenarios)"
    )
    parser.add_argument(
        "--job-id",
        help="Specify an existing jobId to resume querying, skipping task creation and directly polling progress (suitable for mid-probe failures, network timeouts, etc.)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=False,
        help="Quiet mode: suppress console decorative output, only output pure JSON to stdout (suitable for Agent/script calls)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Summary mode: only output aggregated statistics (skip GetProbeResult detailed resource list), reducing output size"
    )
    parser.add_argument(
        "--keep-attributes",
        action="store_true",
        default=False,
        help="Retain the original attributes field for each resource (stripped by default to reduce output size)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug output: print [debug] details of API responses (with full response body) to stderr. Disabled by default in quiet mode (-q)"
    )

    args = parser.parse_args()

    regions = [r.strip() for r in (args.regions or "").split(",") if r.strip()]
    list_types = [t.strip() for t in (args.list_types or "").split(",") if t.strip()]

    prober = CADTProber(
        regions=regions,
        list_types=list_types,
        skip_probe=args.skip_probe,
        quiet=args.quiet,
        job_id=args.job_id,
        summary_only=args.summary,
        keep_attributes=args.keep_attributes,
        debug=args.debug,
    )

    related_resource_id = (args.related_resource_id or "").strip()
    related_types = [t.strip() for t in (args.related_types or "").split(",") if t.strip()]

    if related_resource_id:
        prober._print("=" * 70)
        prober._print("CADT Related Items Query (GetProbeRelatedItems)")
        prober._print("=" * 70)
        prober._print(f"  Resource ID:    {related_resource_id}")
        prober._print(f"  Type filter:    {', '.join(related_types) if related_types else 'No filter'}")
        prober._print(f"  Query time:     {time.strftime('%Y-%m-%d %H:%M:%S')}")
        prober._print("=" * 70)
        try:
            related = prober.get_probe_related_items(related_resource_id, related_types)
        except (RuntimeError, ValueError) as e:
            _error_exit(f"Failed to fetch related resources: {str(e)}", "related_items_failed", 1, args.quiet)

        if isinstance(related, dict) and "list" in related:
            prober._enrich_resources_with_relationships(related["list"], label="related_items")

        if not args.keep_attributes and isinstance(related, dict) and "list" in related:
            resource_list = related["list"]
            if isinstance(resource_list, list):
                stripped = 0
                for r in resource_list:
                    if isinstance(r, dict) and "attributes" in r:
                        del r["attributes"]
                        stripped += 1
                if stripped > 0 and not args.quiet:
                    prober._print(
                        f"\n  [Output optimization] Stripped attributes from {stripped} related resources "
                        f"(use --keep-attributes to retain original data)",
                        flush=True,
                    )

        output = {
            "mode": "related-items",
            "query_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "resourceId": related_resource_id,
            "serviceTypes": related_types,
            "related_items": related,
        }

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2, default=str)
            if not args.quiet:
                prober._print(f"\nResults saved to: {args.output}")

        _smart_output_json(output, args.quiet, args.output, display_target="related_items")
        return

    try:
        output = prober.probe()
    except (RuntimeError, TimeoutError) as e:
        _error_exit(f"Probe failed: {str(e)}", "probe_task_failed", 1, args.quiet)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        if not args.quiet:
            print(f"\nResults saved to: {args.output}")

    _smart_output_json(output, args.quiet, args.output, display_target="probe_result")

    has_region_cache_miss = any(
        "not in probe cache" in w for w in output.get("cache_warnings", [])
    )
    if has_region_cache_miss:
        sys.exit(2)


if __name__ == '__main__':
    main()
