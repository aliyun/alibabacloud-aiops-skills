---
name: alibabacloud-cadt-probe
description: |
  Use CADT probe service to discover cloud resources under an Alibaba Cloud account. Use this skill when users need to:
  (1) Discover existing cloud resources via CADT probe
  (2) Inventory existing resource list
  (3) Export resource list for CADT architecture import
  (4) Understand resource distribution within an account
  (5) Query related/associated resources for a specific resource (e.g., find security groups and vswitches linked to an ECS instance)
  
  Trigger words: resource probe, CADT probe, probe, resource inventory, list resources, view cloud resources, related resources, associated resources, resource relationships
---

# CADT Alibaba Cloud Resource Probe

Use the CADT probe service (BPStudio API) to discover cloud resources under an Alibaba Cloud account.

## Quick Start

### Prerequisites

```bash
pip install alibabacloud_bpstudio20210931==8.1.1 alibabacloud_credentials==1.0.5
```

Configure credentials using the Alibaba Cloud default credential chain. Choose one of the following methods:

- Run `aliyun configure` to set up a credential profile
- Set environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (auto-detected by the default chain)
- Use an ECS instance RAM role (when running on ECS)
- Configure `~/.alibabacloud/credentials` file

### Pre-conditions

The **Cloud Config** service must be enabled in the Alibaba Cloud console, as CADT probe relies on resource data provided by Cloud Config:
- Enable at: https://config.console.aliyun.com/
- Monitoring scope must be set to "All resources in account"
- After initial activation, wait 30-60 minutes for the initial scan to complete

## RAM Policy

This skill requires the following RAM permissions to execute BPStudio probe operations and discover cloud resources across 20+ Alibaba Cloud services.

For the complete permission list including a least-privilege RAM policy JSON, see [references/ram-policies.md](references/ram-policies.md).

**Key permissions:**

| Service | Action | Purpose |
|---------|--------|---------|
| BPStudio | `bpstudio:ExecuteOperation` | Execute all probe sync operations (CreateOneClickJob, GetOneClickStatus, GetProbeResourceSummary, GetProbeRelatedItems, GetLastProbeTime, GetProbeRegions, GetProbeResult) |
| Config | `config:ListDiscoveredResources` + 5 others | Resource discovery via Cloud Config |
| VPC / SLB / ALB / NLB / ACK / ... | Various Describe/List actions | Product-specific resource discovery and relation queries |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

### Run Probe

```bash
python scripts/probe.py
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--regions` | No | Comma-separated list of regions to probe and filter results (e.g., cn-hangzhou,cn-beijing). Probes all regions when not specified |
| `--output` | No | Output JSON file path. Prints to console only when not specified |
| `--list-types` | No | Comma-separated resource type filter list (serviceTypes) for GetProbeResult / GetProbeResourceSummary; empty means no filter |
| `--skip-probe` | No | Skip task creation and polling, directly pull existing probe results (suitable for previously probed scenarios) |
| `-q`, `--quiet` | No | Quiet mode: suppress console decorative output, only output pure JSON to stdout (suitable for Agent/script calls). [debug] output is disabled by default in this mode |
| `--debug` | No | Enable debug output: print [debug] details of API responses (with full response body) to stderr. Disabled by default in quiet mode (-q) |
| `--summary` | No | Summary mode: only output aggregated statistics (skip GetProbeResult detailed resource list), significantly reducing output size |
| `--keep-attributes` | No | Retain the original attributes field for each resource (stripped by default to reduce output size) |
| `--related-resource-id` | No | Resource ID for querying related resources (GetProbeRelatedItems). When specified, skips full probe and only queries related resources for this resource (e.g., `i-xxx` for ECS, `sg-xxx` for security group, `vpc-xxx` for VPC) |
| `--related-types` | No | Comma-separated resource type filter for `--related-resource-id` (e.g., `security_group,vswitch`). Empty means return all related resource types |

## Usage Examples

### 1. Basic Probe

```bash
python scripts/probe.py
```

### 2. Export JSON Results

```bash
python scripts/probe.py --output probe_result.json
```

### 3. Skip Probe and Pull Existing Results

If you have previously probed (resource data is cached on the server side), you can directly pull existing results without creating a new task:

```bash
python scripts/probe.py --skip-probe
python scripts/probe.py --skip-probe --output result.json
python scripts/probe.py --skip-probe --list-types ecs,vpc
```

### 4. Agent Mode (Quiet Mode)

Use the `-q` flag to suppress all human-readable output, printing only pure JSON to stdout for easy Agent or script parsing. By default, the `attributes` field of each resource is stripped to reduce output size:

```bash
python scripts/probe.py -q
python scripts/probe.py -q --output result.json
python scripts/probe.py -q --regions cn-hangzhou --list-types ecs,vpc
```

To retain full attributes, use `--keep-attributes`:

```bash
python scripts/probe.py -q --keep-attributes
```

#### Output Auto-Degradation (Agent Mode)

When the JSON output is large (e.g., 127 security groups with Permissions arrays + 100 vswitches), the script automatically degrades output to prevent terminal truncation:

| Output Size | Behavior |
|-------------|----------|
| ≤ 50KB | Normal JSON (with indentation) to stdout |
| 50KB ~ 200KB | Compact JSON (no indentation) to stdout, warning on stderr |
| > 200KB | Full data written to file, stdout outputs a summary JSON only |

When output exceeds 200KB, stdout returns a summary like:

```json
{
  "status": "output_too_large",
  "output_file": "/path/to/file.json",
  "total_resources": 246,
  "by_type": {"security_group": 127, "vswitch": 100, "ecs": 19},
  "hint": "Read the output file for full results"
}
```

**Recommendation:** Always use `--output` to write full results to a file, then read the file for parsing. This avoids any output size issues:

```bash
python scripts/probe.py -q --output result.json
```

### 5. Summary Mode (Aggregated Statistics Only)

When there are many resources, use `--summary` to skip the detailed resource list and only output aggregated statistics by region/type, suitable for dashboard analysis:

```bash
python scripts/probe.py --summary
python scripts/probe.py -q --summary
python scripts/probe.py --summary --output summary.json
```

### 6. Query Related Resources for a Specific Resource

Query all resources related to a specific resource (e.g., ECS instance's security groups, vswitches, etc.):

```bash
python scripts/probe.py --related-resource-id i-xxx --related-types security_group,vswitch --output related_items_ecs.json
```

This calls the `GetProbeRelatedItems` API, which returns all resources topologically related to the specified resource in the probe results. It does NOT create a new probe task. The `attributes` field of each related resource is stripped by default (same as probe results), which significantly reduces output size for resources like security groups that contain large Permissions arrays.

**Two-step workflow** (get a resource ID first, then query its related resources):

```bash
# Step 1: Get resource list (use --skip-probe if already probed, -q for machine-readable output)
python scripts/probe.py --skip-probe -q --list-types ecs --regions cn-hangzhou

# Step 2: Pick any instance ID from Step 1 output, then query its related resources
python scripts/probe.py --related-resource-id i-bp1xxxxx --related-types security_group,vswitch --output related_items_ecs.json
```

**Supported `--related-types` values** (same as `--list-types` resource type keys):
- `security_group` — Security Group
- `vswitch` — VSwitch
- `vpc` — Virtual Private Cloud
- `disk` — Cloud Disk
- `eni` — Elastic Network Interface
- `eip` — Elastic IP Address
- ... (any resource type key listed in the supported resource types)

Leave `--related-types` empty to return all related resource types:

```bash
python scripts/probe.py --related-resource-id i-xxx --output all_related.json
```

**Output format** (when using `--related-resource-id`):

```json
{
  "mode": "related-items",
  "query_time": "2025-04-17 16:00:00",
  "resourceId": "i-bp1xxxxx",
  "serviceTypes": ["security_group", "vswitch"],
  "related_items": { ... }
}
```

## How It Works

The script implements resource probing through a two-phase flow using the BPStudio SDK:

### Phase 1: Submit Probe Task

Call `ExecuteOperationSync` API:
- `ServiceType` = `probe`
- `Operation` = `CreateOneClickJob`
- `Attributes` = `{"regions": [...]}`

The API returns an `operation_id` (task ID).

### Phase 2: Poll for Results

Call `ExecuteOperationSync` API:
- `ServiceType` = `probe`
- `Operation` = `GetOneClickStatus`
- `Attributes` = `{"jobId": <jobId>}`
- Poll every 10 seconds, timeout after 30 minutes, until the task completes
- When `status == "SUCCESS"`, the `arguments` field contains the probed resource data (JSON)
- When `status == "FAILURE"`, the `message` field contains the error information

### Execution Modes

- **Default (full probe):** `CreateOneClickJob` → poll `GetOneClickStatus` (every 10s, timeout 30min) until SUCCESS → `GetProbeResourceSummary` → `GetProbeResult` → `GetLastProbeTime` + `GetProbeRegions` (cache validation) → output
- **--skip-probe:** Skip CreateOneClickJob and polling, directly pull cached results via `GetProbeResourceSummary` → `GetProbeResult` → cache validation (`cache_info` included in output)
- **--related-resource-id:** Skip full probe, directly call `GetProbeRelatedItems` with `resourceId` and optional `serviceTypes` filter → output. Requires a prior probe run; empty result if no probe data exists.

### Cache Validation (All Modes)

After fetching results, the script always calls `GetLastProbeTime` and `GetProbeRegions` to validate the cache state:

- **`cache_info`** (only in `--skip-probe` mode): Contains `last_probe_minutes_ago` (minutes since last probe, -1 if no valid job) and `cached_regions` (list of region IDs in cache)
- **`cache_warnings`** (all modes): Array of warning strings when:
  - No valid probe job exists (`lastTime == -1`)
  - `--regions` includes regions not present in the cache → results for those regions will be empty

## Output Description

### Console Output

```
======================================================================
CADT Resource Probe (BPStudio)
======================================================================
  Probe time:   2025-04-17 15:30:00
======================================================================

Submitting probe task...
  Task ID: op-xxxxxxxxxxxxx
  Waiting for probe to complete...
  Current status: Running (elapsed 5s)
  Current status: SUCCESS (elapsed 15s)
  Probe complete!

======================================================================
Probe Results
======================================================================
<Resource list details>
======================================================================
```

### JSON Output

When using the `--output` flag, a full JSON file is written:

```json
{
  "regions": ["cn-hangzhou", "cn-beijing"],
  "probe_time": "2025-04-17 15:30:00",
  "job_id": "12345",
  "progress": {"status": "SUCCESS"},
  "summary": { ... },
  "probe_result": { ... },
  "probe_result_filter": {
    "regions": "all",
    "serviceType": "all"
  }
}
```

#### --skip-probe Output (with cache_info)

When using `--skip-probe`, the output includes a `cache_info` field:

```json
{
  "regions": ["cn-hangzhou"],
  "probe_time": "2025-04-17 16:00:00",
  "job_id": "",
  "progress": {},
  "cache_info": {
    "last_probe_minutes_ago": 45,
    "cached_regions": ["cn-hangzhou", "cn-beijing"]
  },
  "summary": { ... },
  "probe_result": { ... },
  "probe_result_filter": { ... }
}
```

#### --related-resource-id Output

When using `--related-resource-id`, the output structure is different from the full probe output:

```json
{
  "mode": "related-items",
  "query_time": "2025-04-17 16:00:00",
  "resourceId": "i-bp1xxxxx",
  "serviceTypes": ["security_group", "vswitch"],
  "related_items": {
    "list": [
      { "resourceId": "sg-xxx", "resourceType": "security_group", ... },
      { "resourceId": "vsw-xxx", "resourceType": "vswitch", ... }
    ]
  }
}
```

Key fields:
- `mode`: Always `"related-items"` for this query type
- `resourceId`: The resource ID that was queried
- `serviceTypes`: The type filters applied (empty list means no filter)
- `related_items`: Raw response from `GetProbeRelatedItems`, containing a `list` of related resources

#### _relationships (Auto-extracted Relationship IDs)

Each resource in `probe_result.list` and `related_items.list` automatically includes a `_relationships` field (when applicable) that extracts cross-resource reference IDs from the nested `attributes` JSON. This field is added **before** attributes are stripped, so it is always available even without `--keep-attributes`.

Example — an ECS instance resource:

```json
{
  "resourceId": "i-bp1xxxxx",
  "resourceType": "ecs",
  "_relationships": {
    "security_group_ids": ["sg-abc", "sg-def"],
    "vswitch_id": "vsw-123",
    "vpc_id": "vpc-456"
  }
}
```

Supported resource types and extracted relationships:

| Resource Type | Extracted Fields |
|--------------|-----------------|
| `ecs` | `security_group_ids`, `vswitch_id`, `vpc_id` |
| `eni` | `security_group_ids`, `vswitch_id`, `vpc_id` |
| `rds`, `polardb`, `dds`, `kvstore`, `tair` | `vpc_id`, `vswitch_id` |
| `clb`, `slb`, `alb`, `nlb` | `vpc_id`, `vswitch_id` (where applicable) |
| `nat`, `vpn` | `vpc_id`, `vswitch_id` (where applicable) |
| `nas`, `hbase`, `clickhouse`, `lindorm`, `adb` | `vpc_id`, `vswitch_id` |
| `elasticsearch`, `kafka`, `emr`, `mse` | `vpc_id`, `vswitch_id` (where applicable) |
| `disk` | `instance_id` (references ECS) |
| `eip` | `instance_id` (bound resource) |

If a resource type is not in the table or no relationship fields are found, `_relationships` is omitted.

#### cache_warnings

When cache issues are detected, a `cache_warnings` array is added to the output (in all modes):

```json
{
  "cache_warnings": [
    "Requested region(s) cn-shenzhen not in probe cache — results for these regions will be empty. Cached regions: cn-hangzhou, cn-beijing"
  ]
}
```

## Observability

### User-Agent

All Alibaba Cloud API calls made by this skill (SDK and CLI) include a custom User-Agent:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-probe/{session-id}
```

**Rule:** Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag above.
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

### Session ID

- Source: environment variable `SKILL_SESSION_ID`
- Fallback: if `SKILL_SESSION_ID` is not set, a random 32-character hex UUID is generated
- Scope: one session ID per invocation (created when the BPStudio client is initialized)

## Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| `0` | Success |
| `1` | Failure (credentials not configured, probe task submission failed, API error, etc.) |
| `2` | Region cache miss — `--regions` includes regions not present in the probe cache. Results are still output, but the Agent should be aware that those regions returned empty data due to cache gaps, not because the regions have no resources. |

## Error Handling

### Credentials Not Configured

```
Error: Unable to get credential. Please configure the default credential chain.
```

### Probe Task Submission Failed

Check:
- Whether credentials are correct
- Whether the account has BPStudio operation permissions (see [references/ram-policies.md](references/ram-policies.md) for the full permission list)
- Whether the Cloud Config service has been enabled

If the error is a permission error, follow the **Permission Failure Handling** process described in the RAM Policy section above.

### Probe Task Timeout

Default timeout is 30 minutes (1800 seconds). If it times out, the script outputs the current status and task ID, which can be used to query later.

### Cache Warnings (stderr)

Cache warnings are printed to stderr and included in the JSON output as `cache_warnings`:
- `No valid probe job found in cache — results may be empty or stale`
- `Requested region(s) <regions> not in probe cache — results for these regions will be empty. Cached regions: <cached>`

## Supported Resource Types

CADT probe supports 60+ Alibaba Cloud resource types. See [resource_types.md](references/resource_types.md) for the full list.

## File Structure

```
alibabacloud-cadt-probe/
├── SKILL.md                    # This file
├── references/
│   ├── ram-policies.md         # Required RAM permissions
│   └── resource_types.md       # Supported resource types reference
└── scripts/
    └── probe.py                # Core probe script
```

## Dependencies

```
alibabacloud_bpstudio20210931==8.1.1
alibabacloud_credentials==1.0.5
```
