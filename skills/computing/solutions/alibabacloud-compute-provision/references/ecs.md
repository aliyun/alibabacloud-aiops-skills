# ECS Reference

Script: `scripts/ecs.py` | API style: RPC | Version: ecs/2014-05-26

ECS is the most general-purpose compute resource, suitable for all scenarios, and is the default choice.

## Region Selection Guidance

**If the task involves installing external dependencies (pip install, apt-get install, npm install, downloading GitHub assets via curl, etc.), prefer overseas regions** to avoid connectivity issues when accessing overseas sources from mainland China.

| Scenario | Recommended Region | Notes |
|----------|--------------------|-------|
| External dependencies required | `ap-southeast-1` (Singapore) | Smooth network; access to PyPI/npm/GitHub/Docker Hub works without issue |
| No external dependencies | `cn-hangzhou` (Hangzhou) and other mainland regions | Low latency, lower price |
| User-specified region | Per user request | — |

> When using an overseas region, the VPC/VSwitch must also be created in the same region (`ensure_vpc_and_vswitch(region="ap-southeast-1", zone_id=...)`).
> A public IP must also be allocated (`internet_max_bandwidth_out > 0`); otherwise the instance cannot reach external networks.

## Full Workflow

```
1. Spec recommendation/lookup -> 2. Inventory check -> 3. Price quote -> 4. Network preparation -> 5. Security group -> 6. Image lookup -> 7. Create instance -> 8. Run script -> 9. Resource cleanup
```

## API Quick Reference

### 1. Spec Recommendation / Lookup

#### describe_recommend_instance_type(...) -> dict

**Recommended entry point**. Recommends instance specs based on requirements (vCPU/memory), with results sorted by inventory, price, or newest products. Avoids manually filtering through a large set of specs.

```python
from ecs import describe_recommend_instance_type

result = describe_recommend_instance_type(
    cores=2,                              # vCPU count (used together with memory)
    memory=4.0,                           # Memory in GiB (used together with cores)
    # instance_type="ecs.g7.large",       # Or specify a spec to find alternatives (mutually exclusive with cores/memory)
    instance_family_level=None,           # EntryLevel | EnterpriseLevel | CreditEntryLevel
    instance_charge_type="PostPaid",      # PostPaid | PrePaid
    priority_strategy="InventoryFirst",   # InventoryFirst | PriceFirst | NewProductFirst
    zone_id=None,                         # Restrict to a specific zone
    system_disk_category="cloud_essd",    # Disk type filter
    max_price=None,                       # Maximum hourly unit price (spot only)
    instance_type_family=None,            # Restrict to instance families, e.g. ["ecs.g7", "ecs.c7"]
    region=None,
)
# result["Data"]["RecommendInstanceType"] -> [{InstanceType: {InstanceType, Cores, Memory, MemoryGB, ...}, ZoneId, Priority, ...}]
# Note: Memory is originally in MB; the function automatically adds a MemoryGB field (converted to GB). Use MemoryGB when displaying.
```

#### describe_instance_types(...) -> dict

Filters instance spec details by CPU/memory/GPU. Use this when you need to inspect CPU, memory, and GPU information for specific specs.

```python
from ecs import describe_instance_types

result = describe_instance_types(
    instance_type_family=None,   # Instance family, e.g. "ecs.g7"
    instance_types=None,         # Exact spec list, e.g. ["ecs.g7.xlarge"]
    min_cpu=8,                   # Minimum vCPU
    max_cpu=32,                  # Maximum vCPU
    min_memory=None,             # Minimum memory (GB)
    max_memory=None,             # Maximum memory (GB)
    gpu_amount=None,             # Number of GPU cards, e.g. 1
    region=None,
)
# result["InstanceTypes"]["InstanceType"] -> [{InstanceTypeId, CpuCoreCount, MemorySize, GPUAmount, ...}]
```

#### describe_instance_type_families(generation, region) -> dict

Lists instance families (e.g. ecs.g7 general-purpose, ecs.c7 compute-optimized). Returns `InstanceTypeFamilies.InstanceTypeFamily[]`.

### 2. Inventory Check

#### describe_regions(region) -> dict

Returns the list of all available regions.

#### describe_zones(region) -> dict

Returns the list of all available zones in the current region.

#### describe_available_resource(...) -> dict

Queries purchasable resources (specs/disk types/etc.) within a zone. **After picking a spec, you must call this to confirm inventory.**

```python
from ecs import describe_available_resource

result = describe_available_resource(
    destination_resource="InstanceType",  # InstanceType | SystemDisk | DataDisk | Network
    zone_id="cn-hangzhou-h",              # Optional, specifies a zone
    instance_type="ecs.g7.2xlarge",       # Optional, filters a specific spec
    instance_charge_type="PostPaid",      # PostPaid (pay-as-you-go) | PrePaid (subscription)
    io_optimized="optimized",             # Defaults to optimized
    region=None,
)
# result["AvailableZones"]["AvailableZone"] -> available resources grouped by zone
```

### 3. Price Quote and Cost Confirmation

#### describe_price(...) -> dict

Queries the real-time price of an instance configuration. **Must be called before creating an instance; show the cost to the user and obtain confirmation before proceeding.**

```python
from ecs import describe_price

result = describe_price(
    instance_type="ecs.g7.2xlarge",       # Required
    period=1,                             # Billing period
    price_unit="Hour",                    # Hour | Month | Year
    instance_charge_type="PostPaid",      # PostPaid | PrePaid
    system_disk_category="cloud_essd",    # System disk type
    system_disk_size=40,                  # System disk size (GB)
    internet_max_bandwidth_out=0,         # Public bandwidth (Mbps); 0 = no public IP, >0 = allocate public IP
    amount=1,                             # Number of instances
    region=None,
    zone_id=None,
)
# result["PriceInfo"]["Price"] -> {TradePrice, OriginalPrice, DiscountPrice, Currency}
```

#### Cost Confirmation Flow (Mandatory)

After getting a quote, follow the steps below; **do not call run_instances without user confirmation**:

1. Call `describe_price` to obtain the real-time unit price
2. Estimate the runtime based on task type
3. Compute estimated total cost = unit price * estimated runtime * number of instances
4. Present the cost breakdown to the user and wait for confirmation

```
ECS Cost Estimate:
  Spec: ecs.t6-c1m2.large (2 vCPU, 4 GB)
  Image: Ubuntu 24.04
  System disk: cloud_essd 40 GB
  Unit price: CNY 0.017/hour (trade price)
  Estimated runtime: ~5 minutes
  Estimated total cost: CNY 0.002
  Billing: pay-as-you-go (PostPaid), released after completion

Proceed with creation?
```

Runtime estimation reference:
- Simple shell commands (echo/ls/curl): < 1 minute
- Data processing/compilation: 5-30 minutes
- Model training: 1-24 hours
- Long-running services (Web/API): runs continuously, quoted hourly

### 4. Network Preparation

You must prepare a VPC and VSwitch first (see the network preparation steps in SKILL.md). Once you have `vpc_id` and `vsw_id`, proceed to the next step.

### 5. Security Group

#### setup_security_group(vpc_id, sg_name, ingress_rules, region) -> str

**Recommended entry point**. Creates a security group, opens inbound ports per application requirements, and applies a full-egress rule in one step. Returns `security_group_id`.

> WARNING: **Inbound rules must be set based on the application actually being deployed**: open 80/443 for websites; for management ports such as SSH, restrict `source_cidr_ip` to the operator's public IP (e.g. `1.2.3.4/32`); never expose database ports to `0.0.0.0/0`. When external access is not needed, pass `None` or `[]`.

```python
from ecs import setup_security_group

# Public website
sg_id = setup_security_group(vpc_id="vpc-xxx", ingress_rules=[
    {"port_range": "80/80"},
    {"port_range": "443/443"},
])

# Website + SSH only from the operator's IP
sg_id = setup_security_group(vpc_id="vpc-xxx", ingress_rules=[
    {"port_range": "80/80"},
    {"port_range": "443/443"},
    {"port_range": "22/22", "source_cidr_ip": "203.0.113.5/32"},
])

# Internal-only worker, no inbound traffic
sg_id = setup_security_group(vpc_id="vpc-xxx", ingress_rules=None)
```

Per-rule fields: `port_range` (required, e.g. `"80/80"`), `source_cidr_ip` (defaults to `0.0.0.0/0`), `ip_protocol` (defaults to `tcp`).

For finer-grained control, call the steps separately:
- `create_security_group(vpc_id, sg_name, description, region)` -> str (sg_id)
- `authorize_security_group(sg_id, ip_protocol, port_range, source_cidr_ip, region)` - inbound rule
- `authorize_security_group_egress(sg_id, ip_protocol, port_range, dest_cidr_ip, region)` - outbound rule

### 6. Image Lookup

#### describe_images(...) -> dict

```python
from ecs import describe_images

result = describe_images(
    image_name=None,                      # Exact image name
    os_type=None,                         # linux | windows
    image_family=None,                    # e.g. "acs:ubuntu_24_04_x64"
    instance_type=None,                   # Filter compatible images by spec
    region=None,
    page_size=20,
)
# result["Images"]["Image"] -> [{ImageId, ImageName, OSName, ...}]
```

**Prefer using image_family to retrieve the latest image precisely** - it returns a single image that is the latest version in that family.

Common image families (official names):

| OS | image_family |
|----|--------------|
| Alibaba Cloud Linux 3 LTS 64-bit (recommended) | `acs:alibaba_cloud_linux_3_2104_lts_x64` |
| Ubuntu 24.04 LTS 64-bit | `acs:ubuntu_24_04_x64` |
| Ubuntu 22.04 LTS 64-bit | `acs:ubuntu_22_04_x64` |
| Ubuntu 20.04 LTS 64-bit | `acs:ubuntu_20_04_x64` |
| CentOS 7.9 64-bit | `acs:centos_7_9_x64` |
| Anolis OS 8.10 ANCK 64-bit | `acs:anolis_8_10_anck_x64` |
| Debian 12 64-bit | `acs:debian_12_x64` |

> Note: image_family follows the format `acs:<os>_<version>_<arch>[_<variant>]`, and does not include suffixes such as `20G_alibase`.

### 7. Create Instance

#### Recommended two-step flow: find → confirm → create

**Step A: find_available_instance_type(...)** — searches across regions/zones to find an instance type with stock AND returns its pricing. Call this BEFORE cost confirmation.

```python
from ecs import find_available_instance_type

spec = find_available_instance_type(
    cores=2,
    memory=4,
    regions=["cn-hangzhou", "cn-shanghai", "cn-beijing"],
    # instance_type="ecs.c7.large",   # Optional: check a specific type
)
# spec = {
#   "instance_type": "ecs.c7.large",
#   "region": "cn-shanghai",
#   "zone_id": "cn-shanghai-b",
#   "cores": 2, "memory": 4.0,
#   "price_per_hour": 0.17, "currency": "CNY"
# }
```

**→ Now present the cost to the user and wait for confirmation (see Cost Confirmation rule).**

**Step B: create_instance_with_infra(...)** — creates VPC/VSwitch/SecurityGroup/Image and the instance. Call this AFTER user confirms the cost.

```python
from ecs import create_instance_with_infra

result = create_instance_with_infra(
    instance_type=spec["instance_type"],   # From step A
    zone_id=spec["zone_id"],               # From step A
    region=spec["region"],                 # From step A
    image_family="acs:alibaba_cloud_linux_3_2104_lts_x64",
    internet_max_bandwidth_out=5,          # 0=no public IP, >0=with public IP
)
# result keys: instance_id, region, zone_id, instance_type,
#              vpc_id, vswitch_id, security_group_id, image_id,
#              vpc_is_new, vswitch_is_new
```

> When using these two functions, you do NOT need to manually call `ensure_vpc_and_vswitch`, `create_security_group`, `describe_images`, or `run_instances` — they are all handled internally by `create_instance_with_infra`.
>
> **⛔ Do NOT pass `image_id`/`ImageId` or `UserData`** to `create_instance_with_infra()` — these are managed internally and will raise `ValueError` if passed. Use `image_family` to select the OS, and `run_command()`/`run_command_and_wait()` for script execution after creation.

#### run_instances(...) -> dict (low-level)

Creates an ECS instance and waits until it reaches Running. Requires VPC, VSwitch, SecurityGroup, and ImageId to be prepared in advance. Use the two-step flow above instead unless you need fine-grained control.

> **⛔ UserData is forbidden**: `run_instances()` will raise `ValueError` if `UserData` is passed. To execute scripts on the instance, create the instance first, then use `run_command()` or `run_command_and_wait()` (see Section 8). This ensures script execution is observable and retriable.

```python
from ecs import run_instances

result = run_instances(
    instance_type="ecs.g7.2xlarge",       # Required
    vswitch_id="vsw-xxx",                 # Required
    security_group_id="sg-xxx",           # Required
    image_id="aliyun_3_x64_20G_alibase_xxx",  # Required
    instance_name="acf-instance",         # Instance name
    system_disk_category="cloud_essd",    # System disk type
    system_disk_size=40,                  # System disk size (GB)
    internet_max_bandwidth_out=0,         # Public bandwidth (Mbps); see note below
    instance_charge_type="PostPaid",      # PostPaid | PrePaid
    amount=1,                             # Number of instances
    region=None,
    # **extra_params accepts any additional RunInstances parameters (except UserData)
)
# result["InstanceIdSets"]["InstanceIdSet"] -> ["i-xxx"]
```

**Public IP allocation rules** (`internet_max_bandwidth_out` parameter):

| Value | Effect | Use case |
|-------|--------|----------|
| `0` (default) | **No public IP allocated** | Pure internal tasks, no external access required |
| `1~100` | **Public IP allocated automatically**, with the value as outbound bandwidth (Mbps) | Scenarios that require public network access |

Typical scenarios that require a public IP:
- Deploying a website / Web service (external users need access)
- Scripts that need `apt-get install`, `pip install`, or `curl` to download external resources
- The user wants to SSH directly to the instance

> Once a public IP is allocated, bandwidth is billed by traffic (`PayByTraffic`), based on actual usage.

#### describe_instances(instance_ids, instance_name, status, region, page_size) -> dict

Queries instance information. Returns `Instances.Instance[]`.

### 8. Run Script

#### run_command_and_cleanup(...) -> dict (ONE-SHOT TASKS)

**For one-shot tasks (run script then release).** Runs the script, collects output, then automatically releases the instance + security group. VSwitch and VPC are only deleted if they were freshly created (not shared/reused). Cleanup errors are logged but do not raise — the command result is always returned.

**Preferred usage** — pass the `infra` dict returned by `create_instance_with_infra()`:

```python
from ecs import run_command_and_cleanup

result = run_command_and_cleanup(
    instance_id=infra["instance_id"],
    command_content="#!/bin/bash\necho hello && date",
    # script_path="/path/to/a.sh",       # Alternative: read from local file
    timeout=600,
    infra=infra,                          # From create_instance_with_infra(); handles cleanup scope automatically
)
# result -> {ExitCode, DecodedOutput, ...}
# Instance + SG released; VPC/VSwitch released only if they were newly created
```

When `infra` is provided, the function reads `vpc_is_new` / `vswitch_is_new` flags to decide cleanup scope — reused VPC/VSwitch are preserved. You can also pass individual IDs manually if needed.

> **⛔ You MUST use this function for one-shot ECS tasks.** Using `run_command_and_wait()` for one-shot tasks will leave the instance running and incurring charges.

#### run_command_and_wait(instance_id, ...) -> dict (LONG-RUNNING SERVICES)

**For long-running services (keep the instance alive).** Runs the script and returns output, but does NOT release the instance. Use this only when the user needs the instance to keep running (e.g. web server, API service).

```python
from ecs import run_command_and_wait

result = run_command_and_wait(
    instance_id="i-xxx",
    script_path="/path/to/a.sh",          # Local script file path
    command_type="RunShellScript",
    timeout=600,
    region=None,
)
# result -> {ExitCode, Output(Base64), DecodedOutput, ErrorInfo, ...}
```

> When the user provides a script file (e.g. `a.sh`), prefer `script_path` to read the file content; do not manually hard-code the file content into `command_content`.

Cloud Assistant InvocationStatus state transitions: `Pending -> Running -> Success/Failed/Stopped`

For asynchronous execution, call the steps separately:
- `run_command(instance_id, command_content, command_type, timeout, region, script_path)` -> str (invoke_id)
- `describe_invocations(invoke_id, region)` -> dict - query execution status
- `describe_invocation_results(invoke_id, instance_id, region)` -> dict - retrieve output

### 9. Resource Cleanup

#### Cleanup Strategy (Decide by Scenario)

| Scenario | Strategy | Examples |
|----------|----------|----------|
| One-shot script | **Automatically release all resources** after execution | `echo hello`, data processing scripts, batch compute |
| Long-running service | **Do not release**; report the resource list and cost to the user | Web servers, API services, databases |
| Unclear scenario | **Ask the user** whether to release | Dev/test environments, debugging tasks |

Decision logic:
1. Does the script start a persistent process (e.g. `nohup`, `systemctl`, `docker run -d`, a Web framework `serve`)? -> Long-running, do not release
2. The user explicitly says "release after execution" or the script is a one-shot command -> Auto-release
3. Otherwise -> Ask the user

#### Cleanup Order (Reverse of Creation Order)

```
ECS instance -> Security group -> VSwitch -> VPC
```

For each step, describe to confirm resource state, delete, then describe again to verify deletion:

```python
from ecs import describe_instances, delete_instances, delete_security_group

# 1. Confirm the instance exists and check its state, then release
instances = describe_instances(instance_ids=["i-xxx"])
# Release (built-in retry; automatically handles states such as IncorrectInstanceStatus.Initializing)
delete_instances(instance_ids=["i-xxx"], force=True)
# Verify the release completed (instance disappears or state becomes Deleted)
describe_instances(instance_ids=["i-xxx"])

# 2. Delete the security group (only possible after instances are released)
delete_security_group(security_group_id="sg-xxx")

# 3. Delete the VSwitch / VPC (see the network cleanup steps in SKILL.md)
```

> **Do not delete reused resources**: `create_instance_with_infra()` returns `vpc_is_new` / `vswitch_is_new` flags. Only delete resources where the flag is `True`. If using `run_command_and_cleanup()` with the `infra` parameter, this is handled automatically.
> **Handling delete failures**: if a delete call fails (e.g. resources still have dependencies), use describe to inspect the relationships, resolve the dependencies, then retry.

#### Resource Summary

Regardless of whether resources are released, output a resource list to the user after the script finishes:

```
Created resources:
  - ECS: i-xxx (ecs.t6-c1m2.large, PostPaid ~CNY 0.017/h) [released/running]
  - SecurityGroup: sg-xxx [released/retained]
  - VSwitch: vsw-xxx [released/retained (reused)]
  - VPC: vpc-xxx [released/retained (reused)]
```

## Spec Lookup Strategy Selection

| Scenario | Recommended API | Notes |
|----------|-----------------|-------|
| Known requirements (vCPU + memory) | `describe_recommend_instance_type(cores, memory)` | Auto-recommends and sorts |
| Pick the cheapest by price | `describe_recommend_instance_type(priority_strategy="PriceFirst")` | Sorted by per-vCPU hourly price |
| Find which zones have stock for a given spec | `describe_available_resource(instance_type=...)` | Inventory grouped by zone |
| Inspect detailed spec parameters | `describe_instance_types(instance_types=[...])` | View CPU/memory/GPU details |

## Instance Family Quick Reference

| Family | Ratio | Suitable For |
|--------|-------|--------------|
| g (general) | 1:4 (vCPU:memory) | Web, middleware |
| c (compute) | 1:2 | Batch compute, high concurrency |
| r (memory) | 1:8 | Databases, big data |
| t (burstable) | Baseline + credits | Dev/test |
| gn (GPU) | Includes GPU | AI inference/training |

## Documentation Search

When you encounter uncertain parameters, unknown error codes, or need to consult the latest API docs, use `scripts/doc_search.py` to search the official Alibaba Cloud documentation:

```python
from doc_search import search_and_format

# Search ECS-related docs
print(search_and_format("RunInstances parameter reference", product="ecs"))
print(search_and_format("DescribeImages ImageFamily", product="ecs"))
print(search_and_format("Cloud Assistant InvocationStatus states", product="ecs"))

# Search by error code
print(search_and_format("OperationDenied.NoStock", product="ecs"))
```

Search results return titles, summaries, and links; use the web_fetch tool to inspect the full document content.

## Common Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| OperationDenied.NoStock | Insufficient inventory | Switch to another zone or spec; use describe_recommend_instance_type to find alternatives |
| InvalidInstanceType.NotSupported | The zone does not support this spec | Confirm with describe_available_resource |
| QuotaExceed | Quota exceeded | Prompt the user to request a quota increase |
| InvalidSystemDiskCategory.NotSupported | The disk type is unavailable | Switch to cloud_essd or cloud_ssd |
