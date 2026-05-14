# PAI (DLC Deep Learning Container) Reference

Script: `scripts/pai.py` | API style: ROA | Version: pai-dlc/2020-12-03

PAI-DLC is purpose-built for AI training/inference and supports distributed training frameworks such as PyTorch, TensorFlow, and MPI.

## End-to-End Workflow

```
1. Analyze task requirements (does it need a GPU?)
2. list_ecs_specs to query available specs -> pick the most suitable CPU/GPU spec
3. Cost confirmation
4. create_training_job (auto-resolves the image)
5. wait_job_complete (built-in ImagePullBackOff detection + auto log dump when stuck)
6. Inspect results
7. cleanup_jobs to clean up failed jobs when needed
```

**Key principle**: analyze first, query specs next, then choose on demand. Do not default to GPU. Simple scripts (shell, data processing, non-ML) only need a CPU spec.

PAI differs from ECS/FC/ACK: the script is passed directly into CreateJob via the `user_command` parameter, with no separate "run script" step.

## Step 1: Analyze the Task & Query Specs

### Decide Whether a GPU Is Needed

| Needs GPU | Does Not Need GPU |
|-----------|-------------------|
| PyTorch/TensorFlow model training | Shell scripts, data processing |
| CUDA compute workloads | CPU-bound compute |
| Large-model inference / fine-tuning | Simple test jobs |

### Query Available Specs

```python
from pai import list_ecs_specs

# Query CPU specs
cpu_specs = list_ecs_specs(accelerator_type="CPU")
for s in cpu_specs[:5]:
    print(f"{s['InstanceType']}: {s['Cpu']}C {s['Memory']}GB")

# Query GPU specs
gpu_specs = list_ecs_specs(accelerator_type="GPU")
for s in gpu_specs[:5]:
    print(f"{s['InstanceType']}: {s['Cpu']}C {s['Memory']}GB "
          f"{s['Gpu']}x{s.get('GpuType','')} {s.get('GpuMemory','')}GB")
```

Returned fields: `InstanceType, AcceleratorType, Cpu, Gpu, GpuType, Memory, GpuMemory, IsAvailable, SpotStockStatus, PaymentTypes`

### Spec Selection Guide

- **Simple scripts / tests**: CPU spec, e.g. `ecs.c6.large` (2C 4GB)
- **Data processing**: CPU spec, e.g. `ecs.c6.xlarge` (4C 8GB)
- **Small-model inference / fine-tuning**: `ecs.gn6i-c4g1.xlarge` (1x T4 16GB)
- **Mid-size model training**: `ecs.gn6v-c8g1.2xlarge` (1x V100 16GB)
- **Large-model fine-tuning**: `ecs.gn7i-c32g1.8xlarge` (4x A10 24GB)
- **Large-model pre-training**: `ecs.ebmgn7i.32xlarge` (8x A100 80GB)

## Step 2: Cost Confirmation (Mandatory)

**Before creating a training job you MUST estimate cost and confirm with the user. Do not call create_job / create_training_job without confirmation.**

PAI-DLC public resource groups are billed using ECS specs; estimate via the ECS `describe_price` API:

```python
from ecs import describe_price

result = describe_price(
    instance_type="ecs.c6.large",  # use the ecs_spec returned from list_ecs_specs
    price_unit="Hour",
    instance_charge_type="PostPaid",
    system_disk_category="cloud_essd",
    system_disk_size=120,
)
hourly_per_worker = result["PriceInfo"]["Price"]["TradePrice"]
total_hourly = hourly_per_worker * worker_count
```

Cost display template:
```
PAI-DLC cost estimate:
  Job type: PyTorchJob
  Spec: ecs.c6.large (2vCPU 4GB, CPU) x 1 Worker
  Per-worker price: CNY 0.17/hour
  Estimated runtime: ~2 minutes
  Estimated total cost: < CNY 0.01
  Billing: pay-as-you-go, billing stops automatically when the job finishes

Proceed with creation?
```

> Lingjun / resource-quota mode pricing depends on the specific quota plan; refer to the PAI console pricing page. For public resource groups, use the ECS price inquiry API.

## API Quick Reference

### list_ecs_specs(...) -> list[dict]

Query the ECS specs supported by PAI-DLC. **Always call this before creating a job to confirm available specs.**

```python
from pai import list_ecs_specs

# CPU specs only
specs = list_ecs_specs(accelerator_type="CPU")

# GPU specs only, sorted by GPU count
specs = list_ecs_specs(accelerator_type="GPU", sort_by="GPU", order="asc")

# All specs
specs = list_ecs_specs()
```

Parameters:
- `accelerator_type`: `"CPU"` | `"GPU"` | `None` (all)
- `sort_by`: `"CPU"` | `"GPU"` | `"Memory"` | `"GmtCreateTime"`
- `order`: `"asc"` | `"desc"`

### resolve_image(...) -> str

Dynamically resolve the best image URI. **You do not need to specify an image manually; it is queried automatically based on `job_type` and `chip_type`.**

```python
from pai import resolve_image

# CPU image
cpu_img = resolve_image("PyTorchJob", chip_type="CPU")

# GPU image
gpu_img = resolve_image("PyTorchJob", chip_type="GPU")
```

Parameters:
- `job_type`: `PyTorchJob` | `TFJob` | `MPIJob` | `XGBoostJob` | `RayJob`
- `chip_type`: `"GPU"` | `"CPU"`

Image selection strategy:
1. Query the aiworkspace ListImages API (`system.supported.dlc=true,system.chipType={chip_type}`)
2. Filter by framework name prefix (e.g. `pytorch:`)
3. Prefer standard images (exclude accl/ngc/deepEp variants)
4. For CPU prefer images whose tag contains "cpu"; for GPU prefer images whose tag contains "gpu"
5. Results are cached to avoid repeated queries

### Workspace Auto-Management

The `workspace_id` parameter is optional in every job-creation function:
- If omitted, `ListWorkspaces` is called automatically to detect existing workspaces
- If the account has no workspace at all, **a workspace named `alibabacloud_compute_default` is created automatically** (simple mode, production environment only)
- Results are cached so subsequent calls do not repeat the request

### create_training_job(...) -> dict

**Recommended entry point.** Creates a training job, automatically building the JobSpec and inferring the image from the spec. Returns `{JobId, RequestId}`.

```python
from pai import create_training_job

# CPU job (simple script)
result = create_training_job(
    display_name="test-script",
    user_command="bash /root/a.sh",
    job_type="PyTorchJob",
    ecs_spec="ecs.c6.large",        # CPU spec -> CPU image is selected automatically
    worker_count=1,
)

# GPU job (model training)
result = create_training_job(
    display_name="qwen-7b-finetune",
    user_command="python train.py",
    job_type="PyTorchJob",
    ecs_spec="ecs.gn6i-c4g1.xlarge", # GPU spec -> GPU image is selected automatically
    worker_count=1,
)
# result["JobId"] -> "dlc-xxx"
```

Image inference logic: detects whether `ecs_spec` contains `.gn` or `.ebmgn` to decide CPU vs GPU,
then calls `resolve_image()` to fetch a matching image. You can also override via the `image` parameter.

Parameters:
- `display_name`: job name (required)
- `user_command`: launch command (required)
- `job_type`: `PyTorchJob` | `TFJob` | `MPIJob` | `XGBoostJob` | `RayJob`
- `image`: Docker image (None means auto-resolve)
- `worker_count`: number of worker replicas
- `ecs_spec`: ECS spec (for public resource groups)
- `gpu/gpu_type/cpu/memory`: for resource-quota mode; pick either these or `ecs_spec`
- `workspace_id`: workspace ID (auto-detected)
- `resource_id`: resource group ID (empty = public resource pool)
- `envs`: dict of environment variables
- `thirdparty_libs`: list of pip packages

**Resource specification modes**:
- Public resource group: use `ecs_spec` to pick the ECS instance type
- Lingjun / resource quota: use a combination of `cpu`, `memory`, `gpu`, `gpu_type`

### create_pytorch_job(...) -> dict

PyTorch-specific convenience entry point. Same parameters as `create_training_job`, but `job_type` is fixed to `PyTorchJob`.

### create_job(...) -> dict

Low-level API. You must build `job_specs` manually. Prefer `create_training_job` instead.

```python
from pai import create_job, build_job_spec

specs = [build_job_spec(
    spec_type="Worker",
    image="...",   # obtain via resolve_image()
    pod_count=4,
    ecs_spec="ecs.gn6i-c4g1.xlarge",
)]

result = create_job(
    display_name="custom-job",
    job_type="PyTorchJob",
    user_command="torchrun --nproc_per_node=1 train.py",
    job_specs=specs,
)
```

### build_job_spec(...) -> dict

Builds a single JobSpec dict. `image` is required.

### get_job(job_id, region) -> dict

Fetch job details. Returned fields include: `JobId, Status, SubStatus, DisplayName, Duration, Pods, ReasonMessage, ...`

Status values: Creating, Queuing, Running, Succeeded, Failed, Stopped

### wait_job_complete(job_id, ...) -> dict

Wait for the job to complete. **Built-in safeguards:**

1. **Active ImagePullBackOff detection**: once an image-pull error is detected, the job is auto-terminated with an error after `image_pull_timeout` (default 300s)
2. **Stall auto-diagnosis**: if the job status does not change for more than `interval * 4` seconds, pod events and logs are fetched automatically to print diagnostics
3. **Timeout protection**: auto-terminate beyond `timeout` (default 7200s)
4. **Failure auto-diagnosis**: when the job is Failed/Stopped, pod logs and events are dumped automatically

```python
from pai import wait_job_complete

detail = wait_job_complete(
    "dlc-xxx",
    timeout=7200,
    interval=30,
    image_pull_timeout=300,
)
print(detail["Status"])  # Succeeded
```

### Logs and Events

```python
from pai import get_job_logs, get_pod_logs, get_pod_events

# Recommended: iterates over all pods automatically; no need to know the pod ID
all_logs = get_job_logs(job_id="dlc-xxx")
# Returns dict: {"dlc-xxx-master-0": ["line1", "line2", ...], ...}

# Fetch a single pod's logs (obtain the pod ID via get_job() first)
logs = get_pod_logs(job_id="dlc-xxx", pod_id="dlc-xxx-master-0")

# Fetch pod system events
events = get_pod_events(job_id="dlc-xxx", pod_id="dlc-xxx-master-0")
```

### Other APIs

- `list_jobs(workspace_id, display_name, status, page_number, page_size, region)` -> dict
- `stop_job(job_id, region)` -> dict (HTTP POST)
- `delete_job(job_id, region)` -> dict
- `list_images(labels, name, page_size, region)` -> list[dict]

### cleanup_jobs(...) -> list[str]

Clean up failed/abnormal jobs.

```python
from pai import cleanup_jobs

# Clean up all Failed jobs (only stops those still running)
affected = cleanup_jobs(status="Failed")

# Clean up and delete
affected = cleanup_jobs(status="Failed", delete=True)

# Clean up Stopped jobs
affected = cleanup_jobs(status="Stopped", delete=True)
```

## Error Handling

### Built-in Retries

The `_call` function automatically retries the following transient errors (up to 3 times, exponential backoff):
- Throttling (rate limiting)
- ServiceUnavailable
- InternalError
- OperationTimeout
- ETIMEDOUT / ConnectionReset

### Common Errors

| Error | Cause | Resolution |
|-------|-------|-----------|
| InvalidAction.NotFound (404) | Action name or HTTP method mismatch | Check the API docs |
| OperationForbidden (403) | Missing WorkspaceId | Code auto-detects; a workspace is created automatically when none exists |
| ImagePullBackOff | Image does not exist or is not accessible | Use resolve_image dynamic lookup to avoid this |
| Throttling | API call rate too high | Built-in automatic retry |

## Documentation Search

When uncertain about a parameter, encountering an unknown error code, or needing the latest API docs, use `scripts/doc_search.py` to search the Alibaba Cloud official documentation:

```python
from doc_search import search_and_format

print(search_and_format("CreateJob PyTorchJob parameters", product="pai"))
print(search_and_format("ListEcsSpecs instance specs", product="pai"))
print(search_and_format("DLC distributed training configuration", product="pai"))
```
