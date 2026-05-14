#!/usr/bin/env python3
"""Alibaba Cloud ACK (Container Service Kubernetes) management.

Capabilities:
  - describe_regions / describe_clusters  (query)
  - create_cluster / ensure_cluster       (create or reuse a cluster)
  - wait_cluster_running / wait_cluster_deleted  (wait for state)
  - run_script_as_job                     (submit a Job via the Kubernetes SDK)
  - delete_cluster / cleanup_resources    (reverse-order cleanup)
  - create_and_run                        (convenience entry, auto cleanup)

ACK uses ROA-style API (version=2015-12-15).
Endpoint: cs.{region}.aliyuncs.com

Job execution uses the ``kubernetes`` Python SDK (no kubectl dependency).
"""

from __future__ import annotations

import base64
import json
import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from common import call_roa_api, get_default_region, wait_until, pp

VERSION = "2015-12-15"


def _get_endpoint(region: str | None = None) -> str:
    r = region or get_default_region()
    return f"cs.{r}.aliyuncs.com"


def _call(
    pathname: str,
    method: str = "GET",
    query: dict | None = None,
    body: dict | None = None,
    region: str | None = None,
    action: str = "anonymous",
) -> dict | str:
    ep = _get_endpoint(region)
    return call_roa_api(
        version=VERSION,
        pathname=pathname,
        method=method,
        query=query,
        body=body,
        region=region,
        endpoint=ep,
        action=action,
    )


# ---------------------------------------------------------------------------
# Region query
# ---------------------------------------------------------------------------

def describe_regions(region: str | None = None) -> dict:
    """List ACK available regions."""
    return _call("/regions", region=region, action="DescribeRegions")


# ---------------------------------------------------------------------------
# Cluster query
# ---------------------------------------------------------------------------

def describe_clusters(
    name: str | None = None,
    cluster_type: str | None = None,
    region: str | None = None,
    page_size: int = 50,
    page_number: int = 1,
) -> list[dict]:
    """List ACK clusters with optional filters.

    Args:
        name: Filter by cluster name (exact match).
        cluster_type: Filter by type (ManagedKubernetes, etc.).

    Returns:
        List of cluster info dicts.
    """
    query: dict[str, Any] = {
        "page_size": str(page_size),
        "page_number": str(page_number),
    }
    if name:
        query["name"] = name
    if cluster_type:
        query["cluster_type"] = cluster_type

    result = _call(
        "/api/v1/clusters",
        query=query,
        region=region,
        action="DescribeClustersV1",
    )
    return result.get("clusters", [])


_K8S_PROBE_TIMEOUT = 3
_PROBE_CONCURRENCY = 10
_PROBE_MAX_CANDIDATES = 100


def _check_cluster_rbac(cluster_id: str, region: str | None = None) -> bool:
    """Verify that the current account has batch/jobs RBAC permission on the cluster."""
    try:
        batch_v1, _, _ = _build_k8s_clients(cluster_id, region)
        batch_v1.list_namespaced_job("default", _request_timeout=_K8S_PROBE_TIMEOUT)
        return True
    except Exception as e:
        err_msg = str(e)
        if "forbidden" in err_msg.lower() or "RBAC" in err_msg:
            print(f"  RBAC check failed for {cluster_id}: {e}")
        else:
            print(f"  Cannot reach cluster {cluster_id}: {e}")
        return False


def _probe_cluster(cluster_id: str, name: str, region: str | None) -> str | None:
    """Check if a single cluster is reusable (nodes ready + RBAC). Returns cluster_id or None."""
    try:
        batch_v1, core_v1, _ = _build_k8s_clients(cluster_id, region)
        nodes = core_v1.list_node(_request_timeout=_K8S_PROBE_TIMEOUT)
        ready = sum(
            1 for n in nodes.items
            for cond in (n.status.conditions or [])
            if cond.type == "Ready" and cond.status == "True"
        )
        if ready <= 0:
            return None
        batch_v1.list_namespaced_job("default", _request_timeout=_K8S_PROBE_TIMEOUT)
        print(f"Found reusable cluster: {cluster_id} ({name}), {ready} ready node(s)")
        return cluster_id
    except Exception as e:
        print(f"  Cluster {cluster_id} ({name}) not reusable: {e}")
        return None


def _find_reusable_cluster(
    cluster_type: str = "ManagedKubernetes",
    region: str | None = None,
    name_prefix: str = "acf-",
) -> str | None:
    """Find any running cluster with ready nodes, checked concurrently.

    Only considers clusters whose name starts with *name_prefix*.
    At most ``_PROBE_MAX_CANDIDATES`` clusters are checked, with
    ``_PROBE_CONCURRENCY`` probes running in parallel.

    Returns cluster_id if a suitable cluster is found, None otherwise.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_clusters = describe_clusters(cluster_type=cluster_type, region=region)
    candidates = [
        c for c in all_clusters
        if c.get("state") == "running"
        and int(c.get("size", 0)) > 0
        and c.get("name", "").startswith(name_prefix)
    ][:_PROBE_MAX_CANDIDATES]
    if not candidates:
        return None

    with ThreadPoolExecutor(max_workers=_PROBE_CONCURRENCY) as pool:
        futures = {
            pool.submit(_probe_cluster, c["cluster_id"], c.get("name", "?"), region): c
            for c in candidates
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                for f in futures:
                    f.cancel()
                return result
    return None


def ensure_cluster(
    cluster_name: str = "acf-cluster",
    cluster_type: str = "ManagedKubernetes",
    vpcid: str | None = None,
    vswitch_ids: list[str] | None = None,
    worker_instance_types: list[str] | None = None,
    num_of_nodes: int = 1,
    worker_system_disk_category: str = "cloud_essd",
    worker_system_disk_size: int = 120,
    region: str | None = None,
    reuse_any: bool = False,
    **extra,
) -> str:
    """Find an existing running cluster or create a new one.

    Search order:
    1. Exact name match (running or initializing)
    2. Any ``acf-`` prefixed running cluster with ready nodes (if reuse_any=True)
    3. Create a new cluster

    Returns the cluster_id of a running cluster with ready nodes.
    """
    # 1. Exact name match
    clusters = describe_clusters(name=cluster_name, cluster_type=cluster_type, region=region)
    for c in clusters:
        if c.get("state") == "running" and c.get("name") == cluster_name:
            cluster_id = c["cluster_id"]
            if _check_cluster_rbac(cluster_id, region):
                print(f"Reusing existing cluster (name match): {cluster_id} ({cluster_name})")
                return cluster_id
            print(f"  Cluster {cluster_id} ({cluster_name}) matched by name but lacks RBAC permissions, skipping")
        if c.get("state") == "initial" and c.get("name") == cluster_name:
            cluster_id = c["cluster_id"]
            print(f"Found initializing cluster: {cluster_id}, waiting...")
            wait_cluster_running(cluster_id, region)
            wait_nodes_ready(cluster_id, min_nodes=1, region=region)
            return cluster_id

    # 2. Any acf- prefixed running cluster with ready nodes
    if reuse_any:
        reused = _find_reusable_cluster(cluster_type=cluster_type, region=region)
        if reused:
            return reused

    # 3. Create new cluster
    result = create_cluster(
        cluster_name=cluster_name,
        cluster_type=cluster_type,
        vpcid=vpcid,
        vswitch_ids=vswitch_ids,
        worker_instance_types=worker_instance_types or ["ecs.g7.xlarge"],
        num_of_nodes=num_of_nodes,
        worker_system_disk_category=worker_system_disk_category,
        worker_system_disk_size=worker_system_disk_size,
        region=region,
        **extra,
    )
    cluster_id = result["cluster_id"]
    wait_cluster_running(cluster_id, region)
    wait_nodes_ready(cluster_id, min_nodes=max(1, num_of_nodes), region=region)
    return cluster_id


# ---------------------------------------------------------------------------
# Cluster management
# ---------------------------------------------------------------------------

def create_cluster(
    cluster_name: str,
    cluster_type: str = "ManagedKubernetes",
    kubernetes_version: str | None = None,
    vpcid: str | None = None,
    vswitch_ids: list[str] | None = None,
    container_cidr: str = "172.20.0.0/16",
    service_cidr: str = "172.21.0.0/20",
    worker_instance_types: list[str] | None = None,
    num_of_nodes: int = 2,
    worker_system_disk_category: str = "cloud_essd",
    worker_system_disk_size: int = 120,
    security_group_id: str | None = None,
    login_password: str | None = None,
    key_pair: str | None = None,
    endpoint_public_access: bool = False,
    region: str | None = None,
    **extra,
) -> dict:
    """Create an ACK managed cluster.

    If neither security_group_id, login_password, nor key_pair is provided,
    they are auto-generated (enterprise SG, random password).

    Args:
        endpoint_public_access: Whether the API server has a public endpoint.
            Defaults to False (private only). Set to True if the orchestrator
            runs outside the cluster VPC and needs to reach the API server.

    Returns:
        Dict with cluster_id, task_id, etc.
    """
    import secrets
    import string

    r = region or get_default_region()

    if not login_password and not key_pair:
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        login_password = (
            secrets.choice(string.ascii_uppercase)
            + secrets.choice(string.ascii_lowercase)
            + secrets.choice(string.digits)
            + secrets.choice("!@#$%")
            + "".join(secrets.choice(alphabet) for _ in range(12))
        )

    body: dict[str, Any] = {
        "name": cluster_name,
        "region_id": r,
        "cluster_type": cluster_type,
        "container_cidr": container_cidr,
        "service_cidr": service_cidr,
        "num_of_nodes": num_of_nodes,
        "worker_system_disk_category": worker_system_disk_category,
        "worker_system_disk_size": worker_system_disk_size,
        "snat_entry": True,
        "endpoint_public_access": endpoint_public_access,
    }

    if login_password:
        body["login_password"] = login_password
    if key_pair:
        body["key_pair"] = key_pair

    if security_group_id:
        body["security_group_id"] = security_group_id
    else:
        body["is_enterprise_security_group"] = True

    if kubernetes_version:
        body["kubernetes_version"] = kubernetes_version
    if vpcid:
        body["vpcid"] = vpcid
    if vswitch_ids:
        body["vswitch_ids"] = vswitch_ids
        body["worker_vswitch_ids"] = vswitch_ids
    if worker_instance_types:
        body["worker_instance_types"] = worker_instance_types

    body.update(extra)

    result = _call("/clusters", method="POST", body=body, region=region, action="CreateCluster")
    cluster_id = result.get("cluster_id", "")
    print(f"Cluster creation started: {cluster_id}")
    return result


def describe_cluster_detail(cluster_id: str, region: str | None = None) -> dict:
    """Get cluster detail. state: initial, running, failed, deleted, deleting."""
    return _call(f"/clusters/{cluster_id}", region=region, action="DescribeClusterDetail")


def wait_cluster_running(cluster_id: str, region: str | None = None, timeout: int = 900) -> dict:
    """Wait until cluster reaches 'running' state (default 15 min)."""
    def _check():
        detail = describe_cluster_detail(cluster_id, region)
        return {"Status": detail.get("state", "unknown"), **detail}

    result = wait_until(
        _check,
        target_statuses={"running"},
        fail_statuses={"failed", "deleted", "delete_failed"},
        interval=30,
        timeout=timeout,
        status_key="Status",
    )
    print(f"Cluster {cluster_id} is running")
    return result


def wait_nodes_ready(
    cluster_id: str,
    min_nodes: int = 1,
    region: str | None = None,
    timeout: int = 300,
    interval: int = 15,
) -> int:
    """Wait until at least *min_nodes* K8s nodes are Ready.

    Uses the Kubernetes Python SDK (no kubectl needed).
    Returns the number of ready nodes.
    """
    batch_v1, core_v1, api_client = _build_k8s_clients(cluster_id, region)
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            nodes = core_v1.list_node()
        except Exception as e:
            remaining = int(deadline - time.time())
            print(f"  [{remaining}s left] K8s API not reachable yet: {e}")
            time.sleep(interval)
            continue

        ready_count = 0
        for node in nodes.items:
            for cond in (node.status.conditions or []):
                if cond.type == "Ready" and cond.status == "True":
                    ready_count += 1
                    break

        remaining = int(deadline - time.time())
        if ready_count >= min_nodes:
            print(f"Nodes ready: {ready_count}/{len(nodes.items)}")
            return ready_count

        print(f"  [{remaining}s left] ready={ready_count}/{len(nodes.items)}, need {min_nodes}")
        time.sleep(interval)

    raise TimeoutError(
        f"Only {ready_count} of {min_nodes} required nodes ready after {timeout}s"
    )


def delete_cluster(cluster_id: str, region: str | None = None) -> dict:
    """Submit cluster deletion (async). Use wait_cluster_deleted to block."""
    return _call(f"/clusters/{cluster_id}", method="DELETE", region=region, action="DeleteCluster")


def wait_cluster_deleted(cluster_id: str, region: str | None = None, timeout: int = 600) -> None:
    """Wait until cluster is fully deleted."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            detail = describe_cluster_detail(cluster_id, region)
            state = detail.get("state", "unknown")
        except Exception as e:
            err = str(e)
            if "NotFound" in err or "404" in err or "ErrorClusterNotFound" in err:
                print(f"Cluster {cluster_id} deleted")
                return
            raise
        if state in ("deleted",):
            print(f"Cluster {cluster_id} deleted")
            return
        if state in ("delete_failed",):
            raise RuntimeError(f"Cluster {cluster_id} deletion failed")
        print(f"  Cluster state: {state}, waiting 15s...")
        time.sleep(15)
    raise TimeoutError(f"Cluster {cluster_id} deletion timed out after {timeout}s")


def cleanup_resources(
    cluster_id: str,
    security_group_id: str | None = None,
    region: str | None = None,
    delete_timeout: int = 600,
) -> None:
    """Reverse-order resource cleanup: cluster → wait → optional SG.

    If security_group_id is None (cluster auto-created SG), the SG is
    automatically released with the cluster — no manual cleanup needed.
    """
    print(f"Deleting cluster {cluster_id}...")
    delete_cluster(cluster_id, region)
    wait_cluster_deleted(cluster_id, region, timeout=delete_timeout)

    if security_group_id:
        try:
            from ecs import delete_security_group
            print(f"Deleting security group {security_group_id}...")
            delete_security_group(security_group_id, region)
            print(f"Security group {security_group_id} deleted")
        except Exception as e:
            print(f"Warning: SG cleanup failed (may already be deleted): {e}")


# ---------------------------------------------------------------------------
# Node pool management
# ---------------------------------------------------------------------------

def create_cluster_node_pool(
    cluster_id: str,
    nodepool_name: str = "acf-nodepool",
    instance_types: list[str] | None = None,
    vswitch_ids: list[str] | None = None,
    desired_size: int = 2,
    system_disk_category: str = "cloud_essd",
    system_disk_size: int = 120,
    region: str | None = None,
    **extra,
) -> dict:
    """Create a node pool in an existing cluster."""
    body: dict[str, Any] = {
        "nodepool_info": {"name": nodepool_name},
        "scaling_group": {
            "instance_types": instance_types or ["ecs.g7.xlarge"],
            "vswitch_ids": vswitch_ids or [],
            "system_disk_category": system_disk_category,
            "system_disk_size": system_disk_size,
            "desired_size": desired_size,
        },
    }
    body.update(extra)

    result = _call(
        f"/clusters/{cluster_id}/nodepools",
        method="POST",
        body=body,
        region=region,
        action="CreateClusterNodePool",
    )
    nodepool_id = result.get("nodepool_id", "")
    print(f"NodePool created: {nodepool_id}")
    return result


def describe_cluster_node_pools(cluster_id: str, region: str | None = None) -> dict:
    """List node pools in a cluster."""
    return _call(f"/clusters/{cluster_id}/nodepools", region=region, action="DescribeClusterNodePools")


# ---------------------------------------------------------------------------
# Kubeconfig & Kubernetes SDK helpers
# ---------------------------------------------------------------------------

def get_cluster_kubeconfig(cluster_id: str, region: str | None = None, private: bool = False) -> str:
    """Get kubeconfig YAML string for a cluster.

    Args:
        private: If True, return private (VPC-internal) endpoint kubeconfig.
                 If False (default), return public endpoint kubeconfig.
    """
    result = _call(
        f"/k8s/{cluster_id}/user_config",
        query={"PrivateIpAddress": "true" if private else "false"},
        region=region,
        action="DescribeClusterUserKubeconfig",
    )
    return result.get("config", "")


def _build_k8s_clients(cluster_id: str, region: str | None = None):
    """Build Kubernetes API clients from cluster kubeconfig.

    Returns (BatchV1Api, CoreV1Api, api_client).
    """
    import yaml
    from kubernetes import client as k8s_client, config as k8s_config

    kubeconfig_str = get_cluster_kubeconfig(cluster_id, region)
    kubeconfig_dict = yaml.safe_load(kubeconfig_str)

    api_client = k8s_config.new_client_from_config_dict(kubeconfig_dict)
    batch_v1 = k8s_client.BatchV1Api(api_client)
    core_v1 = k8s_client.CoreV1Api(api_client)
    return batch_v1, core_v1, api_client


def _resolve_image(
    core_v1,
    script_type: str = "shell",
    explicit_image: str | None = None,
) -> str:
    """Dynamically resolve a container image from the cluster's own registry.

    Queries kube-system pods to extract the registry prefix that is
    guaranteed to be accessible from within the cluster, then maps
    script_type to a suitable base image.

    Falls back to Docker Hub images if registry detection fails
    (e.g. for overseas clusters that can access Docker Hub directly).
    """
    if explicit_image:
        return explicit_image

    image_map = {"shell": "acs/busybox:v1.29.2", "python": "acs/python:3.10-slim"}
    fallback_map = {"shell": "busybox:1.36", "python": "python:3.10-slim"}

    try:
        pods = core_v1.list_namespaced_pod("kube-system", limit=10)
        for pod in pods.items:
            for container in pod.spec.containers:
                img = container.image or ""
                if "/acs/" in img:
                    registry_prefix = img.split("/acs/")[0]
                    resolved = f"{registry_prefix}/{image_map.get(script_type, image_map['shell'])}"
                    print(f"Resolved image from cluster registry: {resolved}")
                    return resolved
    except Exception as e:
        print(f"Warning: failed to detect cluster registry, using fallback: {e}")

    return fallback_map.get(script_type, fallback_map["shell"])


# ---------------------------------------------------------------------------
# Script execution (via Kubernetes SDK)
# ---------------------------------------------------------------------------

_FATAL_POD_REASONS = {
    "ImagePullBackOff", "ErrImagePull", "InvalidImageName",
    "CreateContainerConfigError", "CrashLoopBackOff",
    "RunContainerError", "ErrImageNeverPull",
}


def _check_pod_fatal_errors(core_v1, job_name: str, namespace: str) -> str | None:
    """Check if any pod of the Job has a fatal container error.

    Returns an error description string, or None if no fatal errors.
    """
    pods = core_v1.list_namespaced_pod(
        namespace, label_selector=f"job-name={job_name}",
    )
    for pod in pods.items:
        for cs in (pod.status.container_statuses or []):
            if cs.state and cs.state.waiting:
                reason = cs.state.waiting.reason or ""
                if reason in _FATAL_POD_REASONS:
                    msg = cs.state.waiting.message or ""
                    return f"Pod {pod.metadata.name}: {reason} — {msg[:300]}"
    return None


def run_script_as_job(
    cluster_id: str,
    script_content: str,
    job_name: str = "acf-job",
    image: str | None = None,
    script_type: str = "shell",
    namespace: str = "default",
    region: str | None = None,
    poll_interval: int = 10,
    timeout: int = 600,
) -> str:
    """Execute a script as a K8s Job using the Kubernetes Python SDK.

    Dynamically resolves container image from cluster registry.
    Polls pod status; raises immediately on fatal errors
    (ImagePullBackOff, CrashLoopBackOff, etc.).

    Args:
        cluster_id: ACK cluster ID.
        script_content: Script content to execute.
        job_name: Kubernetes Job name.
        image: Container image override. Auto-resolved if None.
        script_type: "shell" or "python".
        namespace: Kubernetes namespace.
        region: Alibaba Cloud region.
        poll_interval: Seconds between status checks.
        timeout: Max seconds to wait.

    Returns:
        Job logs output string.
    """
    from kubernetes import client as k8s_client
    from kubernetes.client.rest import ApiException

    batch_v1, core_v1, api_client = _build_k8s_clients(cluster_id, region)

    resolved_image = _resolve_image(core_v1, script_type, image)
    interpreter = "/bin/sh" if script_type == "shell" else "python3"
    encoded_script = base64.b64encode(script_content.encode()).decode()

    job = k8s_client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=k8s_client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=k8s_client.V1JobSpec(
            backoff_limit=3,
            ttl_seconds_after_finished=300,
            template=k8s_client.V1PodTemplateSpec(
                spec=k8s_client.V1PodSpec(
                    restart_policy="Never",
                    containers=[k8s_client.V1Container(
                        name="runner",
                        image=resolved_image,
                        command=["/bin/sh", "-c",
                                 f"echo '{encoded_script}' | base64 -d | {interpreter}"],
                    )],
                ),
            ),
        ),
    )

    try:
        batch_v1.delete_namespaced_job(
            job_name, namespace, propagation_policy="Background",
        )
        time.sleep(3)
        print(f"Cleaned up previous Job '{job_name}'")
    except ApiException as e:
        if e.status != 404:
            raise

    print(f"Creating Job '{job_name}' (image: {resolved_image})...")
    batch_v1.create_namespaced_job(namespace, job)

    print(f"Polling Job status (interval={poll_interval}s, timeout={timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        job_status = batch_v1.read_namespaced_job_status(job_name, namespace)
        conditions = job_status.status.conditions or []

        for cond in conditions:
            if cond.type == "Complete" and cond.status == "True":
                print(f"Job '{job_name}' completed successfully.")
                return _collect_job_logs(core_v1, job_name, namespace)
            if cond.type == "Failed" and cond.status == "True":
                logs = _collect_job_logs(core_v1, job_name, namespace)
                raise RuntimeError(f"Job '{job_name}' failed.\nLogs:\n{logs}")

        fatal = _check_pod_fatal_errors(core_v1, job_name, namespace)
        if fatal:
            raise RuntimeError(f"Job '{job_name}' fatal error: {fatal}")

        active = job_status.status.active or 0
        succeeded = job_status.status.succeeded or 0
        failed = job_status.status.failed or 0
        remaining = int(deadline - time.time())
        print(f"  [{remaining}s left] active={active} succeeded={succeeded} failed={failed}")
        time.sleep(poll_interval)

    raise TimeoutError(f"Job '{job_name}' timed out after {timeout}s")


def _collect_job_logs(core_v1, job_name: str, namespace: str) -> str:
    """Collect logs from all pods belonging to a Job."""
    pods = core_v1.list_namespaced_pod(
        namespace, label_selector=f"job-name={job_name}",
    )
    logs_parts = []
    for pod in pods.items:
        try:
            log = core_v1.read_namespaced_pod_log(
                pod.metadata.name, namespace, tail_lines=200,
            )
            logs_parts.append(log)
        except Exception:
            pass

    output = "\n".join(logs_parts)
    print(f"Job '{job_name}' output:\n{output}")
    return output


# ---------------------------------------------------------------------------
# Convenience entry
# ---------------------------------------------------------------------------

def create_and_run(
    script_content: str,
    cluster_name: str = "acf-cluster",
    vpcid: str | None = None,
    vswitch_ids: list[str] | None = None,
    zone_id: str | None = None,
    worker_instance_types: list[str] | None = None,
    num_of_nodes: int = 1,
    image: str | None = None,
    script_type: str = "shell",
    auto_cleanup: bool = True,
    endpoint_public_access: bool = False,
    region: str | None = None,
) -> dict:
    """Convenience: ensure cluster → run script → optional cleanup.

    If vpcid/vswitch_ids are not provided but zone_id is, automatically
    creates network resources via vpc.ensure_vpc_and_vswitch.

    Security group is auto-created by ACK (enterprise SG) and released
    with the cluster — no manual SG management needed.

    Args:
        script_content: Script to execute.
        cluster_name: Cluster name (used for reuse detection).
        vpcid: VPC ID. Auto-created if None and zone_id is given.
        vswitch_ids: VSwitch IDs.
        zone_id: Used to auto-create VPC/VSwitch if vpcid is None.
        worker_instance_types: ECS instance types for worker nodes.
        num_of_nodes: Number of worker nodes.
        image: Container image override.
        script_type: "shell" or "python".
        auto_cleanup: Delete cluster after execution.
        endpoint_public_access: Whether the cluster API server has a public
            endpoint. Defaults to False; pass True when the orchestrator runs
            outside the cluster VPC.
        region: Alibaba Cloud region.

    Returns:
        Dict with cluster_id and job_output.
    """
    if not vpcid and zone_id:
        from vpc import ensure_vpc_and_vswitch
        vpcid, vsw_id, _, _ = ensure_vpc_and_vswitch(zone_id=zone_id, region=region)
        vswitch_ids = [vsw_id]

    cluster_id = ensure_cluster(
        cluster_name=cluster_name,
        vpcid=vpcid,
        vswitch_ids=vswitch_ids,
        worker_instance_types=worker_instance_types,
        num_of_nodes=num_of_nodes,
        region=region,
        endpoint_public_access=endpoint_public_access,
    )

    try:
        job_output = run_script_as_job(
            cluster_id, script_content,
            image=image, script_type=script_type, region=region,
        )
        return {"cluster_id": cluster_id, "job_output": job_output}
    finally:
        if auto_cleanup:
            try:
                cleanup_resources(cluster_id, region=region)
            except Exception as e:
                print(f"Warning: cleanup failed: {e}")
