#!/usr/bin/env python3
"""Alibaba Cloud PAI-DLC (Deep Learning Containers) management.

Capabilities:
  - create_job / get_job / list_jobs  (create / query jobs)
  - stop_job / delete_job  (manage jobs)

PAI-DLC uses ROA-style API (version=2020-12-03).
Endpoint: pai-dlc.{region}.aliyuncs.com
"""

from __future__ import annotations

import json
import re
import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from common import call_roa_api, get_default_region, wait_until, pp

VERSION = "2020-12-03"

_cached_workspace_id: str | None = None


def _get_endpoint(region: str | None = None) -> str:
    r = region or get_default_region()
    return f"pai-dlc.{r}.aliyuncs.com"


def _call(
    pathname: str,
    method: str = "GET",
    query: dict | None = None,
    body: dict | None = None,
    region: str | None = None,
    action: str = "anonymous",
    max_retries: int = 3,
) -> dict | str:
    ep = _get_endpoint(region)
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
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
        except Exception as e:
            last_err = e
            err_str = str(e)
            retryable = any(k in err_str for k in (
                "Throttling", "ServiceUnavailable", "InternalError",
                "OperationTimeout", "ETIMEDOUT", "ConnectionReset",
            ))
            if retryable and attempt < max_retries:
                wait = 2 ** attempt
                print(f"  Retryable error (attempt {attempt}/{max_retries}), "
                      f"retrying in {wait}s: {err_str[:120]}")
                time.sleep(wait)
            else:
                raise
    raise last_err  # unreachable but keeps type checker happy


def _aiworkspace_call(
    pathname: str,
    method: str = "GET",
    query: dict | None = None,
    body: dict | None = None,
    action: str = "anonymous",
    region: str | None = None,
) -> dict | str:
    r = region or get_default_region()
    ep = f"aiworkspace.{r}.aliyuncs.com"
    return call_roa_api(
        version="2021-02-04",
        pathname=pathname,
        method=method,
        query=query,
        body=body,
        region=r,
        endpoint=ep,
        action=action,
    )


def _get_workspace_id(region: str | None = None) -> str:
    """Auto-detect or auto-create a PAI workspace."""
    global _cached_workspace_id
    if _cached_workspace_id:
        return _cached_workspace_id

    result = _aiworkspace_call(
        "/api/v1/workspaces",
        query={"PageSize": "10", "PageNumber": "1"},
        action="ListWorkspaces",
        region=region,
    )
    workspaces = result.get("Workspaces", [])
    if workspaces:
        _cached_workspace_id = workspaces[0]["WorkspaceId"]
        print(f"PAI workspace auto-detected: {_cached_workspace_id} "
              f"({workspaces[0].get('DisplayName', '')})")
        return _cached_workspace_id

    return _create_workspace(region=region)


def _create_workspace(
    name: str = "alibabacloud_compute_default",
    description: str = "Auto-created by Alibaba Cloud Compute Provision skill",
    region: str | None = None,
) -> str:
    """Create a PAI workspace and cache the ID."""
    global _cached_workspace_id
    print(f"No PAI workspace found, creating '{name}'...")
    result = _aiworkspace_call(
        "/api/v1/workspaces",
        method="POST",
        body={
            "WorkspaceName": name,
            "Description": description,
            "DisplayName": name,
            "EnvTypes": ["prod"],
        },
        action="CreateWorkspace",
        region=region,
    )
    ws_id = result.get("WorkspaceId", "")
    if not ws_id:
        raise RuntimeError(f"CreateWorkspace returned no WorkspaceId: {result}")
    _cached_workspace_id = ws_id
    print(f"PAI workspace created: {ws_id} ({name})")
    return ws_id


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------

def create_job(
    display_name: str,
    job_type: str,
    user_command: str,
    job_specs: list[dict[str, Any]],
    workspace_id: str | None = None,
    resource_id: str | None = None,
    user_vpc: dict | None = None,
    data_sources: list[dict] | None = None,
    code_source: dict | None = None,
    thirdparty_libs: list[str] | None = None,
    thirdparty_lib_dir: str | None = None,
    envs: dict[str, str] | None = None,
    priority: int = 1,
    job_max_running_time_minutes: int | None = None,
    region: str | None = None,
) -> dict:
    """Create a PAI-DLC job.

    Args:
        display_name: Job display name.
        job_type: TFJob | PyTorchJob | MPIJob | XGBoostJob | OneFlowJob | RayJob
        user_command: Launch command (e.g. 'python train.py').
        job_specs: List of JobSpec dicts defining nodes. Each should have:
            - Type: Worker/Chief/PS/Evaluator
            - Image: Docker image
            - PodCount: Number of replicas
            - EcsSpec: ECS instance type (e.g. 'ecs.gn6i-c4g1.xlarge')
            - ResourceConfig: {CPU, Memory, GPU, GPUType, SharedMemory}
        workspace_id: PAI workspace ID.
        resource_id: Resource group ID (empty = public resource pool).
        user_vpc: {VpcId, SwitchId, SecurityGroupId}.
        data_sources: List of {DataSourceId, MountPath, Uri}.
        code_source: {CodeSourceId, Branch, Commit, MountPath}.
        thirdparty_libs: List of pip packages, e.g. ['torch==2.1.0'].
        envs: Environment variables.
        priority: 1 (lowest) to 9 (highest).
        job_max_running_time_minutes: Max run time in minutes.

    Returns:
        Dict with JobId, RequestId.
    """
    body: dict[str, Any] = {
        "DisplayName": display_name,
        "JobType": job_type,
        "UserCommand": user_command,
        "JobSpecs": job_specs,
        "Priority": priority,
    }

    body["WorkspaceId"] = workspace_id or _get_workspace_id(region)
    if resource_id:
        body["ResourceId"] = resource_id
    if user_vpc:
        body["UserVpc"] = user_vpc
    if data_sources:
        body["DataSources"] = data_sources
    if code_source:
        body["CodeSource"] = code_source
    if thirdparty_libs:
        body["ThirdpartyLibs"] = thirdparty_libs
    if thirdparty_lib_dir:
        body["ThirdpartyLibDir"] = thirdparty_lib_dir
    if envs:
        body["Envs"] = envs
    if job_max_running_time_minutes:
        body["JobMaxRunningTimeMinutes"] = job_max_running_time_minutes

    result = _call("/api/v1/jobs", method="POST", body=body, region=region, action="CreateJob")
    job_id = result.get("JobId", "")
    print(f"DLC Job created: {job_id}")
    return result


def get_job(job_id: str, region: str | None = None) -> dict:
    """Get job details and runtime status."""
    return _call(f"/api/v1/jobs/{job_id}", region=region, action="GetJob")


def list_jobs(
    workspace_id: str | None = None,
    display_name: str | None = None,
    status: str | None = None,
    page_number: int = 1,
    page_size: int = 50,
    region: str | None = None,
) -> dict:
    """List DLC jobs."""
    query: dict[str, Any] = {
        "PageNumber": page_number,
        "PageSize": page_size,
    }
    if workspace_id:
        query["WorkspaceId"] = workspace_id
    if display_name:
        query["DisplayName"] = display_name
    if status:
        query["Status"] = status
    return _call("/api/v1/jobs", query=query, region=region, action="ListJobs")


def stop_job(job_id: str, region: str | None = None) -> dict:
    """Stop a running job."""
    return _call(
        f"/api/v1/jobs/{job_id}/stop",
        method="POST",
        region=region,
        action="StopJob",
    )


def delete_job(job_id: str, region: str | None = None) -> dict:
    """Delete a job."""
    return _call(
        f"/api/v1/jobs/{job_id}",
        method="DELETE",
        region=region,
        action="DeleteJob",
    )


def list_ecs_specs(
    accelerator_type: str | None = None,
    sort_by: str = "Cpu",
    order: str = "asc",
    page_size: int = 100,
    region: str | None = None,
) -> list[dict]:
    """List ECS specs supported by PAI-DLC.

    Args:
        accelerator_type: "CPU" | "GPU" | None (all).
        sort_by: CPU | GPU | Memory | GmtCreateTime.
        order: asc | desc.

    Returns:
        List of spec dicts with InstanceType, AcceleratorType, Cpu, Gpu,
        GpuType, Memory, GpuMemory, IsAvailable, etc.
    """
    query: dict[str, Any] = {
        "SortBy": sort_by,
        "Order": order,
        "PageSize": page_size,
        "PageNumber": 1,
        "ResourceType": "ECS",
    }
    if accelerator_type:
        query["AcceleratorType"] = accelerator_type
    result = _call("/api/v1/ecsspecs", query=query, region=region, action="ListEcsSpecs")
    specs = result.get("EcsSpecs", [])
    available = [s for s in specs if s.get("IsAvailable")]
    print(f"Found {len(available)} available specs "
          f"(total {len(specs)}, type={accelerator_type or 'all'})")
    return available


def get_pod_logs(
    job_id: str,
    pod_id: str,
    max_lines: int = 2000,
    region: str | None = None,
) -> list[str]:
    """Get logs from a job pod (stdout/stderr)."""
    query: dict[str, Any] = {"MaxLines": max_lines}
    result = _call(
        f"/api/v1/jobs/{job_id}/pods/{pod_id}/logs",
        query=query,
        region=region,
        action="GetPodLogs",
    )
    logs = result.get("Logs", [])
    for line in logs:
        print(line)
    return logs


def get_job_logs(
    job_id: str,
    max_lines: int = 2000,
    region: str | None = None,
) -> dict[str, list[str]]:
    """Get logs from all pods of a job.

    Automatically fetches the pod list via get_job(), then retrieves logs
    for each pod. No need to know pod IDs in advance.

    Returns:
        Dict mapping pod_id -> list of log lines.
    """
    detail = get_job(job_id, region)
    pods = detail.get("Pods", [])
    if not pods:
        print(f"No pods found for job {job_id}")
        return {}

    all_logs: dict[str, list[str]] = {}
    for pod in pods:
        pod_id = pod.get("PodId", "")
        if not pod_id:
            continue
        pod_status = pod.get("Status", "Unknown")
        print(f"--- Pod {pod_id} (status={pod_status}) ---")
        try:
            logs = get_pod_logs(job_id, pod_id, max_lines=max_lines, region=region)
            all_logs[pod_id] = logs
            if not logs:
                print("  (no logs)")
        except Exception as e:
            print(f"  Could not fetch logs: {e}")
            all_logs[pod_id] = []
    return all_logs


def get_pod_events(
    job_id: str,
    pod_id: str,
    max_events_num: int = 100,
    region: str | None = None,
) -> list[str]:
    """Get system events from a job pod."""
    query: dict[str, Any] = {"MaxEventsNum": max_events_num}
    result = _call(
        f"/api/v1/jobs/{job_id}/pods/{pod_id}/events",
        query=query,
        region=region,
        action="GetPodEvents",
    )
    events = result.get("Events", [])
    for event in events:
        print(event)
    return events


def wait_job_complete(
    job_id: str,
    region: str | None = None,
    timeout: int = 7200,
    interval: int = 30,
    image_pull_timeout: int = 300,
) -> dict:
    """Wait for a DLC job to complete.

    Terminal statuses: Succeeded, Failed, Stopped.
    Proactively detects ImagePullBackOff and queries pod logs/events when
    the job appears stuck.

    Args:
        image_pull_timeout: Seconds to tolerate ImagePulling before raising
            an error (default 5 minutes).
    """
    _WARMUP_STATUSES = {"Creating", "Queuing", "Waiting", "EnvPreparing"}
    _IMAGE_ERROR_KEYWORDS = {"ImagePullBackOff", "ErrImagePull", "ImageInspectError"}
    _WARMUP_PATIENCE = 180  # seconds — env prep & image pull are expected to take 1-3 min

    last_status = ""
    last_sub_status = ""
    stuck_since: float | None = None
    image_pull_since: float | None = None
    log_checked = False

    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            _dump_diagnostics(job_id, region)
            raise TimeoutError(
                f"Job {job_id} timed out after {timeout}s (last status: {last_status})"
            )

        detail = get_job(job_id, region)
        status = detail.get("Status", "Unknown")
        sub_status = detail.get("SubStatus", "")
        pods = detail.get("Pods", [])

        status_changed = status != last_status or sub_status != last_sub_status
        if status_changed:
            print(f"  [{int(elapsed)}s] Job {job_id}: {status}"
                  + (f" ({sub_status})" if sub_status else ""))
            last_status = status
            last_sub_status = sub_status
            stuck_since = None
            log_checked = False

        if status == "Succeeded":
            print(f"Job {job_id} completed successfully.")
            return detail
        if status in ("Failed", "Stopped"):
            _dump_diagnostics(job_id, region)
            raise RuntimeError(
                f"Job {job_id} {status}. Reason: {detail.get('ReasonMessage', 'unknown')}"
            )

        pod_events_text = " ".join(
            str(p.get("SubStatus", "")) + str(p.get("Reason", ""))
            for p in pods
        )
        has_image_error = any(k in pod_events_text for k in _IMAGE_ERROR_KEYWORDS)

        if has_image_error:
            if image_pull_since is None:
                image_pull_since = time.time()
                print(f"  WARNING: ImagePull error detected, "
                      f"will abort after {image_pull_timeout}s")
            elif time.time() - image_pull_since > image_pull_timeout:
                _dump_diagnostics(job_id, region)
                raise RuntimeError(
                    f"Job {job_id} stuck in ImagePullBackOff for "
                    f">{image_pull_timeout}s. Image may be invalid."
                )

        is_warmup = status in _WARMUP_STATUSES or sub_status in ("Preparing",)
        patience = _WARMUP_PATIENCE if is_warmup else interval * 4

        if stuck_since is None:
            stuck_since = time.time()
        stuck_duration = time.time() - stuck_since
        if stuck_duration > patience and not log_checked:
            print(f"  Job appears stuck ({int(stuck_duration)}s in {status}), "
                  f"fetching diagnostics...")
            _dump_diagnostics(job_id, region)
            log_checked = True

        time.sleep(interval)


def _dump_diagnostics(job_id: str, region: str | None = None) -> None:
    """Fetch pod logs and events for diagnostic output."""
    try:
        detail = get_job(job_id, region)
        pods = detail.get("Pods", [])
        for pod in pods[:3]:
            pod_id = pod.get("PodId", "")
            if not pod_id:
                continue
            print(f"\n--- Pod {pod_id} (status={pod.get('Status')}, "
                  f"sub={pod.get('SubStatus')}) ---")
            try:
                events = get_pod_events(job_id, pod_id, max_events_num=20, region=region)
                if events:
                    print(f"  Events ({len(events)}):")
                    for e in events[-5:]:
                        print(f"    {e}")
            except Exception as e:
                print(f"  Could not fetch events: {e}")
            try:
                logs = get_pod_logs(job_id, pod_id, max_lines=30, region=region)
                if logs:
                    print(f"  Logs (last {len(logs)} lines):")
                    for line in logs[-10:]:
                        print(f"    {line}")
            except Exception as e:
                print(f"  Could not fetch logs: {e}")
    except Exception as e:
        print(f"  Diagnostics failed: {e}")


# ---------------------------------------------------------------------------
# Image query
# ---------------------------------------------------------------------------

_JOB_TYPE_TO_IMAGE_NAME = {
    "PyTorchJob": "pytorch",
    "TFJob": "tensorflow",
    "MPIJob": "pytorch",
    "XGBoostJob": "xgboost",
    "RayJob": "ray",
}

_image_cache: dict[str, str] = {}


def list_images(
    labels: str = "system.supported.dlc=true",
    name: str | None = None,
    page_size: int = 100,
    region: str | None = None,
) -> list[dict]:
    """List available PAI images via aiworkspace API.

    Args:
        labels: Label filter string (e.g. "system.supported.dlc=true,system.chipType=GPU").
        name: Image name search (fuzzy).
        page_size: Max results per page.

    Returns:
        List of image dicts with Name, ImageUri, Labels, etc.
    """
    query: dict[str, Any] = {
        "PageSize": str(page_size),
        "PageNumber": "1",
        "Labels": labels,
        "Verbose": "true",
    }
    if name:
        query["Name"] = name

    result = _aiworkspace_call(
        "/api/v1/images",
        query=query,
        action="ListImages",
        region=region,
    )
    images = result.get("Images", [])
    print(f"Found {len(images)} images (total {result.get('TotalCount', 0)})"
          f" for labels={labels}, name={name}")
    return images


def resolve_image(
    job_type: str = "PyTorchJob",
    chip_type: str = "GPU",
    region: str | None = None,
) -> str:
    """Dynamically resolve the best available image for a given job type.

    Args:
        job_type: PyTorchJob | TFJob | MPIJob | XGBoostJob | RayJob.
        chip_type: "GPU" or "CPU". Determines whether to use GPU or CPU images.
        region: Alibaba Cloud region.

    Selection strategy:
        1. Query aiworkspace ListImages filtered by DLC support + chip_type.
        2. Filter by framework name prefix (e.g. "pytorch:").
        3. Score candidates: prefer standard (non-accl/ngc/deepEp) > latest.
        4. For CPU chip_type, prefer images with "cpu" in tag name.
    """
    cache_key = f"{job_type}:{chip_type}:{region}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    image_name = _JOB_TYPE_TO_IMAGE_NAME.get(job_type, "pytorch")
    prefixes = [f"{image_name}:", f"{image_name}-training:"]
    labels = f"system.supported.dlc=true,system.chipType={chip_type}"
    images = list_images(labels=labels, name=image_name, region=region)

    candidates = []
    for img in images:
        name = img.get("Name", "")
        uri = img.get("ImageUri", "")
        if not uri or not any(name.startswith(p) for p in prefixes):
            continue
        candidates.append(img)

    if not candidates:
        raise RuntimeError(
            f"No {chip_type} images found for {job_type} "
            f"(searched prefixes={prefixes}). "
            "Check PAI console for available images."
        )

    def _score(img: dict) -> tuple:
        name = img.get("Name", "")
        is_standard = "-accl" not in name and "-ngc" not in name and "-deepEp" not in name
        tag = name.split(":", 1)[-1] if ":" in name else ""
        chip_match = (
            ("cpu" in tag.lower()) if chip_type == "CPU"
            else ("gpu" in tag.lower())
        )
        created = img.get("GmtCreateTime", "")
        return (is_standard, chip_match, created)

    candidates.sort(key=_score, reverse=True)
    chosen = candidates[0]
    uri = chosen["ImageUri"]
    _image_cache[cache_key] = uri
    print(f"Resolved {chip_type} image for {job_type}: {chosen.get('Name', '')} -> {uri}")
    return uri


def _resolve_lightweight_image(
    chip_type: str = "CPU",
    region: str | None = None,
) -> str:
    """Resolve a lightweight base image (python) for simple shell scripts.

    Prefers the latest python image matching the chip_type, avoiding heavy
    ML framework images when only running basic commands.
    """
    cache_key = f"_lightweight:{chip_type}:{region}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    labels = f"system.supported.dlc=true,system.chipType={chip_type}"
    images = list_images(labels=labels, name="python", region=region)

    candidates = [
        img for img in images
        if img.get("ImageUri") and img.get("Name", "").startswith("python:")
    ]
    if not candidates:
        print("No lightweight python image found, falling back to framework image")
        return resolve_image("PyTorchJob", chip_type=chip_type, region=region)

    candidates.sort(key=lambda img: img.get("GmtCreateTime", ""), reverse=True)
    chosen = candidates[0]
    uri = chosen["ImageUri"]
    _image_cache[cache_key] = uri
    print(f"Using lightweight image for simple script: {chosen.get('Name', '')} -> {uri}")
    return uri


# ---------------------------------------------------------------------------
# Convenience helper: create a training job
# ---------------------------------------------------------------------------

def build_job_spec(
    spec_type: str = "Worker",
    image: str | None = None,
    pod_count: int = 1,
    ecs_spec: str | None = None,
    cpu: int | None = None,
    memory: int | None = None,
    gpu: int | None = None,
    gpu_type: str | None = None,
    shared_memory: int | None = None,
) -> dict:
    """Build a single JobSpec dict.

    Use ecs_spec for public resource group, or cpu/memory/gpu for resource quota.

    Args:
        spec_type: Worker | Chief | PS | Evaluator | Master
        image: Docker image URL. If None, must be set before submitting.
        pod_count: Number of replicas.
        ecs_spec: ECS instance type (for public resource group).
        cpu/memory/gpu/gpu_type/shared_memory: Resource config (for resource quota).
    """
    if not image:
        raise ValueError("image is required — use resolve_image() to get a valid one")
    spec: dict[str, Any] = {
        "Type": spec_type,
        "Image": image,
        "PodCount": pod_count,
    }

    if ecs_spec:
        spec["EcsSpec"] = ecs_spec
    elif cpu or memory or gpu:
        resource_config: dict[str, Any] = {}
        if cpu:
            resource_config["CPU"] = str(cpu)
        if memory:
            resource_config["Memory"] = str(memory)
        if gpu:
            resource_config["GPU"] = str(gpu)
        if gpu_type:
            resource_config["GPUType"] = gpu_type
        if shared_memory:
            resource_config["SharedMemory"] = str(shared_memory)
        spec["ResourceConfig"] = resource_config

    return spec


def _infer_chip_type(ecs_spec: str | None, gpu: int | None) -> str:
    """Infer chip type from ecs_spec or explicit gpu parameter."""
    if gpu and gpu > 0:
        return "GPU"
    if ecs_spec:
        return "GPU" if ".gn" in ecs_spec or ".ebmgn" in ecs_spec else "CPU"
    return "CPU"


_FRAMEWORK_KEYWORDS = re.compile(
    r"\bpython\s|\.py\b|import\s|torch|tensorflow|tf\.|keras|"
    r"xgboost|transformers|accelerate|deepspeed|ray\b",
    re.IGNORECASE,
)


def _needs_framework_image(user_command: str) -> bool:
    """Return True if user_command appears to need a ML framework image."""
    return bool(_FRAMEWORK_KEYWORDS.search(user_command))


def create_pytorch_job(
    display_name: str,
    user_command: str,
    image: str | None = None,
    worker_count: int = 1,
    ecs_spec: str = "ecs.gn6i-c4g1.xlarge",
    workspace_id: str | None = None,
    resource_id: str | None = None,
    user_vpc: dict | None = None,
    envs: dict[str, str] | None = None,
    thirdparty_libs: list[str] | None = None,
    region: str | None = None,
) -> dict:
    """Convenience: create a PyTorch training job.

    For multi-node distributed training, set worker_count > 1.
    """
    chip = _infer_chip_type(ecs_spec, None)
    img = image or resolve_image("PyTorchJob", chip_type=chip, region=region)
    specs = [build_job_spec(
        spec_type="Worker",
        image=img,
        pod_count=worker_count,
        ecs_spec=ecs_spec,
    )]
    return create_job(
        display_name=display_name,
        job_type="PyTorchJob",
        user_command=user_command,
        job_specs=specs,
        workspace_id=workspace_id,
        resource_id=resource_id,
        user_vpc=user_vpc,
        envs=envs,
        thirdparty_libs=thirdparty_libs,
        region=region,
    )


def create_training_job(
    display_name: str,
    user_command: str,
    job_type: str = "PyTorchJob",
    image: str | None = None,
    worker_count: int = 1,
    ecs_spec: str | None = None,
    gpu: int | None = None,
    gpu_type: str | None = None,
    cpu: int | None = None,
    memory: int | None = None,
    workspace_id: str | None = None,
    resource_id: str | None = None,
    user_vpc: dict | None = None,
    envs: dict[str, str] | None = None,
    thirdparty_libs: list[str] | None = None,
    region: str | None = None,
) -> dict:
    """General-purpose training job creation.

    Supports TFJob, PyTorchJob, MPIJob, etc.
    Provide either ecs_spec (public pool) or cpu/memory/gpu (resource quota).
    Image is resolved dynamically based on chip type (CPU/GPU) inferred from
    the chosen ecs_spec.

    For simple shell commands (no Python/ML framework keywords detected),
    a lightweight base image is used instead of a heavy framework image.
    """
    chip = _infer_chip_type(ecs_spec, gpu)

    if image:
        img = image
    elif chip == "CPU" and not _needs_framework_image(user_command):
        img = _resolve_lightweight_image(chip_type=chip, region=region)
    else:
        img = resolve_image(job_type, chip_type=chip, region=region)

    specs = [build_job_spec(
        spec_type="Worker",
        image=img,
        pod_count=worker_count,
        ecs_spec=ecs_spec,
        cpu=cpu,
        memory=memory,
        gpu=gpu,
        gpu_type=gpu_type,
    )]
    return create_job(
        display_name=display_name,
        job_type=job_type,
        user_command=user_command,
        job_specs=specs,
        workspace_id=workspace_id,
        resource_id=resource_id,
        user_vpc=user_vpc,
        envs=envs,
        thirdparty_libs=thirdparty_libs,
        region=region,
    )


# ---------------------------------------------------------------------------
# Clean up failed jobs
# ---------------------------------------------------------------------------

def cleanup_jobs(
    status: str = "Failed",
    workspace_id: str | None = None,
    delete: bool = False,
    region: str | None = None,
) -> list[str]:
    """Stop and optionally delete jobs matching the given status.

    Args:
        status: Job status to match ("Failed", "Stopped", etc.).
        workspace_id: Workspace filter (auto-detected if None).
        delete: If True, delete the jobs; otherwise just stop running ones.

    Returns:
        List of affected job IDs.
    """
    ws = workspace_id or _get_workspace_id(region)
    result = list_jobs(workspace_id=ws, status=status, page_size=100, region=region)
    jobs = result.get("Jobs", [])
    affected: list[str] = []
    for job in jobs:
        jid = job.get("JobId", "")
        jstatus = job.get("Status", "")
        if not jid:
            continue
        try:
            if jstatus in ("Running", "Queuing", "Waiting", "Creating"):
                stop_job(jid, region)
                print(f"  Stopped: {jid}")
            if delete:
                delete_job(jid, region)
                print(f"  Deleted: {jid}")
            affected.append(jid)
        except Exception as e:
            print(f"  Cleanup error for {jid}: {e}")
    print(f"Cleaned up {len(affected)} {status} jobs (delete={delete})")
    return affected
