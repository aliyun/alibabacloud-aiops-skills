# ACK (Container Service for Kubernetes) Reference

Script: `scripts/ack.py` | API style: ROA | Version: CS/2015-12-15

ACK is suited for containerized workloads and Kubernetes orchestration scenarios. Cluster creation takes a long time (5-15 minutes), so **prefer reusing existing clusters**.

Dependency: `pip install kubernetes` (Job execution uses the K8s Python SDK; no local kubectl install required).

## End-to-end workflow

```
1. Decide node specs
→ 2. Cost confirmation (ECS price query + Pro edition management fee)
→ 3. Network preparation (VPC)
→ 4. ensure_cluster (name match → reuse any available cluster → create + wait_nodes_ready)
→ 5. run_script_as_job (submit Job via K8s SDK, dynamic image resolution)
→ 6. cleanup_resources (reverse order: cluster → wait → SG)
```

> `create_and_run` wraps steps 3-6 to complete the full flow in a single call.
>
> **Key**: step 4 not only waits for the cluster to be running, it also waits for nodes to become Ready, so Jobs can actually be scheduled.

## Cost confirmation (mandatory)

**Before creating a cluster you must estimate the cost and confirm with the user. Do not call create_cluster without confirmation.**

ACK itself **has no price-query API**. ACK cost = cluster management fee + Worker node ECS cost:
- Managed basic edition (ManagedKubernetes): cluster management fee is **free**
- Managed Pro edition: cluster management fee ~CNY 0.64/hour
- Worker node cost: estimate via ECS `describe_price`

```python
# Use the ECS pricing helper (see SKILL.md)

result = describe_price(
    instance_type="ecs.g7.xlarge",       # Worker node spec
    price_unit="Hour",
    instance_charge_type="PostPaid",
    system_disk_category="cloud_essd",
    system_disk_size=120,
)
hourly_per_node = result["PriceInfo"]["Price"]["TradePrice"]
total_hourly = hourly_per_node * num_of_nodes
```

**Determining cluster edition**: when reusing an existing cluster, check the `profile` field returned by `describe_cluster_detail`:
- `profile="Default"` → basic edition (management fee is free)
- `profile="XEnhance"` or user explicitly requests Pro → Pro edition (CNY 0.64/hour)

Cost display template (basic edition):
```
ACK cost estimate:
  Cluster type: ManagedKubernetes (managed basic edition, management fee free)
  Worker spec: ecs.g7.xlarge (4vCPU, 16GB) x 2 nodes
  Per-node price: CNY 0.84/hour
  Total node cost: CNY 1.68/hour
  System disk: cloud_essd 120GB x 2
  Estimated runtime: ~1 hour
  Estimated total cost: CNY 1.68
  Billing method: pay-as-you-go (PostPaid)

Proceed with creation?
```

Cost display template (Pro edition):
```
ACK cost estimate:
  Cluster type: ManagedKubernetes Pro (managed Pro edition)
  Cluster management fee: CNY 0.64/hour
  Worker spec: ecs.g7.xlarge (4vCPU, 16GB) x 2 nodes
  Per-node price: CNY 0.84/hour
  Total node cost: CNY 1.68/hour
  System disk: cloud_essd 120GB x 2
  Estimated runtime: ~1 hour
  Estimated total cost: CNY 2.32 (management CNY 0.64 + nodes CNY 1.68)
  Billing method: pay-as-you-go (PostPaid)

Proceed with creation?
```

## API quick reference

### ensure_cluster(...) -> str

**Recommended entry point**. Three-tier lookup: name match → `acf-` prefix cluster → create new. Returns cluster_id and **guarantees nodes are Ready**.

```python
from ack import ensure_cluster

cluster_id = ensure_cluster(
    cluster_name="acf-cluster",                   # used for name matching
    vpcid="vpc-xxx",                               # VPC ID (used when creating)
    vswitch_ids=["vsw-xxx"],                       # VSwitch ID list (used when creating)
    worker_instance_types=["ecs.g7.xlarge"],       # Worker node ECS spec
    num_of_nodes=1,                                # Worker node count
    reuse_any=False,                               # whether to search for available acf- prefixed clusters (default False)
    region=None,
)
# cluster_id -> "c-xxx" (may be a reused existing cluster)
```

Logic:
1. `describe_clusters(name=cluster_name)` looks up clusters with the same name
2. Same-name + running -> reuse directly after RBAC check passes
3. Same-name + initial -> `wait_cluster_running` + `wait_nodes_ready`
4. No same-name + `reuse_any=True` -> search running clusters with `acf-` prefix (concurrent probing, 3s timeout); reuse any cluster that has Ready nodes and RBAC permission via the K8s API
5. None of the above -> `create_cluster` + `wait_cluster_running` + `wait_nodes_ready`

> **Note**: `reuse_any` defaults to `False`, only same-name clusters are reused. Other `acf-` prefixed clusters are only searched when the user explicitly sets `reuse_any=True`. Clusters whose names do not start with `acf-` are never reused.

### wait_nodes_ready(cluster_id, min_nodes, region, timeout) -> int

Polls node Ready status via the K8s API. Returns the count of Ready nodes.

```python
from ack import wait_nodes_ready

ready_count = wait_nodes_ready(
    cluster_id="c-xxx",
    min_nodes=1,                                   # minimum number of Ready nodes required
    timeout=300,                                   # timeout in seconds
)
```

> `ensure_cluster` calls `wait_nodes_ready` internally, so manual invocation is usually unnecessary.

### describe_clusters(name, cluster_type, region) -> list[dict]

Lists clusters. Calls the `DescribeClustersV1` API (`GET /api/v1/clusters`).

```python
from ack import describe_clusters

clusters = describe_clusters(name="acf-cluster")
for c in clusters:
    print(f"{c['cluster_id']}: {c['name']} ({c['state']})")
```

### create_cluster(...) -> dict

Creates a managed ACK cluster. Returns `{cluster_id, task_id, request_id}`.

```python
from ack import create_cluster

result = create_cluster(
    cluster_name="acf-cluster",                   # required
    cluster_type="ManagedKubernetes",             # managed edition (recommended)
    vpcid="vpc-xxx",                               # required
    vswitch_ids=["vsw-xxx"],                       # required
    container_cidr="172.20.0.0/16",                # Pod CIDR
    service_cidr="172.21.0.0/20",                  # Service CIDR
    worker_instance_types=["ecs.g7.xlarge"],       # Worker ECS spec
    num_of_nodes=2,                                # node count
    worker_system_disk_category="cloud_essd",
    worker_system_disk_size=120,
    # security_group_id=None -> auto-create an enterprise security group, released with the cluster
    # login_password=None    -> auto-generate a random password
    region=None,
)
```

> **Security group**: when `security_group_id` is omitted an enterprise security group is auto-created (`is_enterprise_security_group=True`) and released automatically when the cluster is deleted, no manual cleanup needed.

> **Login credentials**: when neither `login_password` nor `key_pair` is provided, a 16-character random password is generated.

### wait_cluster_running(cluster_id, region, timeout=900) -> dict

Waits for the cluster to become ready. Default timeout is 15 minutes.

### describe_cluster_detail(cluster_id, region) -> dict

Returns cluster details. State values: `initial`, `running`, `failed`, `deleted`, `deleting`.

### run_script_as_job(...) -> str

**Runs a script in the cluster via the Kubernetes Python SDK**. Automatically resolves the in-cluster image registry, polls Pod status, and raises on errors.

```python
from ack import run_script_as_job

output = run_script_as_job(
    cluster_id="c-xxx",                            # required
    script_content="echo hello",                   # script content
    job_name="acf-job",                            # Job name
    script_type="shell",                           # "shell" or "python"
    # image=None -> dynamically resolve the image registry prefix from kube-system pods
    poll_interval=10,                              # status polling interval (seconds)
    timeout=600,                                   # maximum wait time (seconds)
    region=None,
)
# output -> "hello\n" (Job stdout)
```

Key features:
- **Dynamic image resolution**: extracts the in-cluster registry prefix from kube-system pods (e.g. `registry-cn-hangzhou-vpc.ack.aliyuncs.com/acs/`), guaranteeing the image is pullable from inside the cluster
- **Polling-based status checks**: checks every `poll_interval` seconds; raises immediately on fatal errors such as `ImagePullBackOff` or `CrashLoopBackOff`
- **Auto cleanup of stale Jobs**: if a Job with the same name exists, it is deleted and recreated
- **Auto Job reclamation**: sets `ttlSecondsAfterFinished=300`, so completed Jobs are cleaned up 5 minutes after completion

### delete_cluster(cluster_id, region) -> dict

Submits a cluster delete request (asynchronous). Use together with `wait_cluster_deleted`.

### wait_cluster_deleted(cluster_id, region, timeout=600) -> None

Waits for the cluster to be fully deleted. Polls until the state is `deleted` or the API returns 404.

### cleanup_resources(cluster_id, security_group_id, region) -> None

**Reverse-order resource cleanup**: delete cluster -> wait for deletion -> optionally delete security group.

```python
from ack import cleanup_resources

# Auto-created security groups need no manual cleanup (released with the cluster)
cleanup_resources(cluster_id="c-xxx")

# Externally provided security groups must be specified explicitly
cleanup_resources(cluster_id="c-xxx", security_group_id="sg-xxx")
```

### create_and_run(...) -> dict

**One-stop convenience entry point**. Runs the full flow automatically: VPC preparation -> cluster reuse/creation -> script execution -> auto cleanup.

```python
from ack import create_and_run

# Option 1: auto-create network (specify zone_id)
result = create_and_run(
    script_content="echo hello",
    cluster_name="acf-cluster",
    zone_id="cn-hangzhou-h",                       # auto-create VPC/VSwitch
    worker_instance_types=["ecs.t6-c1m2.large"],
    num_of_nodes=1,
    script_type="shell",
    auto_cleanup=True,                             # delete the cluster automatically after execution
)

# Option 2: use existing network
result = create_and_run(
    script_content="print('hello')",
    vpcid="vpc-xxx",
    vswitch_ids=["vsw-xxx"],
    script_type="python",
    auto_cleanup=False,                            # keep the cluster for later use
)
# result -> {"cluster_id": "c-xxx", "job_output": "hello\n"}
```

Key features:
- **Cluster reuse**: looks up an existing running cluster by name to avoid redundant creation
- **Automatic network preparation**: when `zone_id` is provided, the network is created automatically via the network preparation helpers (see SKILL.md)
- **Hands-off security group**: when no SG is provided, ACK auto-creates an enterprise security group that is released with the cluster
- **try/finally auto cleanup**: cleans up the cluster even if script execution fails (when `auto_cleanup=True`)

### Other APIs

- `describe_regions(region)` -> dict — query available regions
- `get_cluster_kubeconfig(cluster_id, region)` -> str — fetch kubeconfig YAML
- `create_cluster_node_pool(cluster_id, ...)` -> dict — create a node pool
- `describe_cluster_node_pools(cluster_id, region)` -> dict — list node pools

## Documentation search

When uncertain about parameters, encountering unknown error codes, or needing the latest API docs:

```python
from doc_search import search_and_format

print(search_and_format("CreateCluster managed cluster parameters", product="ack"))
print(search_and_format("node pool GPU scheduling", product="ack"))
```

ACK API reference: https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-overview

## Notes

- Cluster creation takes 5-15 minutes; prefer `ensure_cluster` to reuse same-name clusters; pass `reuse_any=True` explicitly to search other clusters
- When `reuse_any=True`, only `acf-` prefixed clusters are searched; clusters whose names do not start with `acf-` are never auto-reused
- Cluster probing uses a 3-second timeout, concurrency of 10, and inspects up to 100 candidates while validating RBAC permissions (batch/jobs)
- After the cluster is running, `ensure_cluster` calls `wait_nodes_ready` automatically and only returns once nodes are schedulable
- container_cidr and service_cidr must not overlap with the VPC CIDR
- When `security_group_id` is omitted, ACK auto-creates an enterprise security group that is released with the cluster
- Cluster cost mainly comes from Worker node ECS instances and is billed continuously even with no workload; the Pro edition adds a CNY 0.64/hour management fee
- Images are resolved dynamically from kube-system pods, no manual registry configuration needed
- When reusing an existing cluster, set `auto_cleanup=False` to avoid deleting a cluster that was not created by this run
