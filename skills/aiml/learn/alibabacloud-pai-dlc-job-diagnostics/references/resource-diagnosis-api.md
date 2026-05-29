# PAI Studio Resource Diagnosis API

Diagnoses the root cause of a DLC job stuck in the queue. The API belongs to
the `paistudio` product (not `pai-dlc`) and returns quota checks, node
scheduling analysis, and hyper-node availability.

## Endpoint

```
GET /api/v1/quotas/{quota_id}/workloads/{workload_id}/diagnosis
```

## CLI Invocation

```bash
aliyun paistudio GET /api/v1/quotas/{quota_id}/workloads/{workload_id}/diagnosis \
  --region <region> \
  --header "Content-Type=application/json" \
  --force \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job-diagnostics
```

**Parameter sources**:
- `quota_id`: read from `ResourceId` returned by `get-job`
- `workload_id`: the `JobId`

**Precondition**: only applies to jobs that consume quota resources
(`ResourceId` non-empty). Public pay-as-you-go (`EcsSpec`) jobs do not expose
this API.

---

## Response Structure

```json
{
  "body": {
    "Diagnosis": {
      "WorkloadId": "dlcXXX",
      "QuotaId": "quotaXXX",
      "QueueStrategy": "FIFO",
      "ResourceDiagnosis": { ... },
      "SchedulingDiagnosis": { ... }
    }
  }
}
```

---

## ResourceDiagnosis — Quota Checks (4 items)

Each item carries a `Status` (Succeeded/Failed) and, on failure,
`ExceedResources`, `Used`, and `Limit`.

| Check key | Meaning | Failure means |
|-----------|---------|---------------|
| `SelfQuotaLimit` | Quota's own limit | Job demand exceeds this quota's GPU/CPU/Memory cap |
| `AncestorQuotaLimit` | Parent quota limit | Parent quota total cap is the bottleneck (nested quotas) |
| `UserLimit` | Workspace per-user limit | Workspace cap on a single user's resource usage |
| `QueueStrategyLimit` | Queue strategy | FIFO/Priority/etc. scheduling-strategy restriction |

**Failure-case structure**:
```json
{
  "Status": "Failed",
  "ExceedResources": ["GPU"],
  "Used": {"GPU": "128", "CPU": "576", "Memory": "4272Gi"},
  "Limit": {"GPU": "144", "CPU": "5184", "Memory": "60840Gi"}
}
```

**Computing the quota gap** (agent may perform on demand):
- `remaining = Limit - Used`
- `gap = demand - remaining` (`demand` = sum of per-role count × per-worker resources in `JobSpecs`)
- `gap > 0` → quota insufficient

---

## SchedulingDiagnosis — Node Scheduling Analysis

```json
{
  "Status": "Succeeded|Failed",
  "TaskNum": 6,
  "SchedulableNum": 0,
  "AvailableNodeNames": ["node-1", "node-2"],
  "TotalNodes": [...],
  "UnschedulableNodes": [...],
  "TotalHyperNodes": [...]
}
```

### UnschedulableNodes — reasons nodes cannot host the job

Grouped by reason; each group lists the affected node names.

### TotalNodes — full node inventory

Each node contains:
- `NodeName`: node identifier
- `RequestGPU`: GPUs already consumed
- `WorkloadNum`: number of jobs currently running
- `Workloads`: list of running jobs
- `WorkloadSchedulingStatusOnNode.AvailableForWorkload`: whether usable for this job
- `WorkloadSchedulingStatusOnNode.UnschedulableInfo`: reason it cannot host the job

### TotalHyperNodes — hyper-nodes (Lingjun)

A hyper-node represents an affinity group of physical nodes (e.g. a full
machine or rack) used for large-scale distributed training.

Each hyper-node contains:
- `NodeName`: hyper-node identifier
- `RequestGPU/CPU/Memory`: resource demand
- `SubNodeCount`: total child nodes
- `AvailableNodeCount`: usable child nodes
- `MinAvailable`: minimum availability required
- `WorkloadSchedulingStatusOnNode.AvailableForWorkload`: schedulable or not
- `WorkloadSchedulingStatusOnNode.AvailableForWorkloadStatus`: reason for unavailability

---

## Unschedulable Reason Codes

| Code | Meaning |
|------|---------|
| `OutOfGPU` | Zero GPUs available |
| `NotEnoughGPU` | GPUs exist but insufficient |
| `OutOfCPU` / `NotEnoughCPU` | CPU resources |
| `OutOfMemory` / `NotEnoughMemory` | Memory resources |
| `NodeUnschedulable` | Node manually cordoned off |
| `AIMasterBlackList` | Blocklisted by AIMaster fault tolerance |
| `GPUUnhealthy` | GPU hardware health issue |
| `UntolerateNodeTaint` | Node has taints the job cannot tolerate |
| `DriverVersionMismatch` | GPU driver version mismatch |
| `GPUTopologyLimit` | GPU topology restriction |
| `NetworkTopologyNotSatisfied` | Affinity-group requirement not met (hyper-node fragmentation) |
| `NodeAffinityUnsatisfied` | Node-affinity rule unsatisfied |
| `Unavailable` | All child nodes of the hyper-node unavailable |
| `PartiallyAvailable` | Hyper-node partially available (below `MinAvailable`) |

---

## Usage Notes

1. **Quota-only**: jobs with empty `ResourceId` (public pay-as-you-go) do not support this API
2. **Requires paistudio permission**: RAM must grant `paistudio:GetQuotaWorkloadDiagnosis`
3. **Real-time**: response is a snapshot at call time; re-invoke during queuing for the latest state
4. **Hyper-nodes**: only Lingjun smart-compute clusters expose hyper-nodes; field is empty for ordinary quotas
