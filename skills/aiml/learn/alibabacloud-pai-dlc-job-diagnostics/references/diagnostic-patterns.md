# Failure Pattern Knowledge Base

Domain knowledge the agent consults during diagnosis — common failure
patterns, keyword signatures, and exit-code meanings. Match observed data
against these patterns; do not apply them mechanically.

---

## 1. Queuing-Stuck Patterns

### 1.1 Quota Exceeded

| Pattern | Signature | Root cause |
|---------|-----------|------------|
| `self_quota` Failed | `ExceedResources` contains GPU/CPU/Memory | This quota is full — free up usage or expand it |
| `ancestor_quota` Failed | Parent quota cap exhausted | Parent-quota bottleneck in nested-quota setups |
| `user_limit` Failed | Single user exceeds workspace cap | Admin set a per-user resource limit |
| `queue_strategy` Failed | Queue strategy blocking | FIFO mode — jobs ahead have not finished |

**Typical symptom**: job stays in `Queuing`, `get-job-events` shows no obvious
error, and the resource-diagnosis API returns a failed check.

### 1.2 Node Scheduling Failures

| Pattern | Signature | Root cause |
|---------|-----------|------------|
| All `OutOfGPU` | Every node has zero GPUs | Cluster fully loaded — wait or scale up |
| Some `NotEnoughGPU` | GPUs remain but insufficient per pod | Fragmentation — per-node residual GPU < per-pod demand |
| `AIMasterBlackList` | Node blocklisted | Fault-tolerance flagged the node — needs ops intervention |
| `GPUUnhealthy` | GPU health issue | Hardware fault — node auto-isolated |
| `NodeUnschedulable` | Manually cordoned | Ops marked the node unschedulable |
| `DriverVersionMismatch` | Driver version | Node GPU driver does not match the image requirement |

### 1.3 Hyper-Node Fragmentation (Lingjun)

| Pattern | Signature | Root cause |
|---------|-----------|------------|
| `NetworkTopologyNotSatisfied` | Hyper-node `AvailableNodeCount` < `MinAvailable` | Whole-group requirement, but pieces are already in use |
| `Unavailable` | All child nodes of a hyper-node unavailable | Entire group occupied or faulted |
| `PartiallyAvailable` | Partially available, below affinity-group minimum | Large job needs full topology; fragments insufficient |

### 1.4 Public Resource (EcsSpec) Queuing

No resource-diagnosis API available. Common causes:
- Instance inventory exhausted (events contain `resource type is not enough`)
- Spot bid too low (Spot scenarios)
- Zone-level capacity tight

---

## 2. Job Failure Patterns

### 2.1 Failure Classification (priority order)

| Priority | Category | Keywords / signatures |
|----------|----------|------------------------|
| 1 | **Network issue** | `ReadTimeoutError`, `Connection timeout`, `pip install` timeout, `NCCL timeout`, `Socket timeout`, `ErrImagePull` (network unreachable) |
| 2 | **Image issue** | `ErrImagePull`, `ImagePullBackOff`, `image not found`, `manifest unknown`, `unauthorized` |
| 3 | **Runtime error** | `ImportError`, `ModuleNotFoundError`, `SyntaxError`, `command not found`, `Permission denied`, Python tracebacks |
| 4 | **Resource shortage** | `ResourceAllocateFailed`, `resource type is not enough`, `Evicted`, spot reclamation |
| 5 | **Configuration error** | `Invalid argument`, missing env vars, unset API key, wrong parameter format |
| 6 | **System issue** | HTTP 503, `ServiceUnavailable`, internal errors, platform-side problems |

### 2.2 Exit-Code Meanings

| Exit code | Meaning | Typical scenario |
|-----------|---------|------------------|
| 0 | Normal exit | Completed successfully (Job overall may still fail if other pods failed) |
| 1 | Generic error | User-script exception, uncaught Python exception |
| 2 | Shell misuse | Command syntax error, file not found |
| 126 | No execute permission | Script lacks `+x` |
| 127 | Command not found | Not on `PATH` |
| 137 | SIGKILL (9) | OOM-Killed or external forced termination |
| 139 | SIGSEGV (11) | Segfault — usually a C/C++-level bug |
| 143 | SIGTERM (15) | Graceful termination (e.g. pod reclaimed) |
| 245 | NCCL timeout | Distributed-comm timeout — typically network issue or another-node failure |
| 255 | SSH error | MPI scenarios — SSH connection failed |

### 2.3 Fast Decision Path

```
get-job → ReasonCode non-empty?
├─ ResourceAllocateFailed → resource shortage (logs unnecessary)
├─ StoppedByUser → user-initiated stop (not a failure)
├─ Other ReasonCode → analyze together with ReasonMessage
└─ ReasonCode empty → inspect pod logs + events
    ├─ Pod never reached Running → startup-phase failure (check pod events)
    └─ Pod was Running → runtime-phase failure (check last lines of pod logs)
```

### 2.4 Log-Analysis Tips

- **Focus on the last 20-50 lines** — the real error usually sits at the tail
- **Ignore routine warnings** — `WARN: requirements.txt not found`, `Running pip as root`, `DeprecationWarning` are noise
- **Watch for keywords** — `ERROR`, `Exception`, `Fatal`, `Traceback`, `exit code`
- **Stack traces** — find the innermost `raise` or the bottom-most error line

---

## 3. Hang Patterns

### 3.1 Hang Criteria

| Condition | Verdict |
|-----------|---------|
| Log silent > 30 min + GPU utilization = 0 | High probability of hang |
| Log stuck on `NCCL INFO` lines | NCCL init stuck (network / node issue) |
| Log stuck on `Waiting for workers` | Distributed rendezvous wait |
| Log produces output but loss is flat | Possibly a training-logic bug (atypical hang) |
| Last line contains `All-reduce timeout` | Communication deadlock |

### 3.2 Common Causes of NCCL Init Hang

- One node has no network connectivity (RDMA config issue)
- Inter-node IB NIC fault
- Firewall rules blocking
- Container-network misconfiguration

### 3.3 Relation to Restarts

- When AIMaster fault tolerance is enabled, hangs beyond the `hang-interval` threshold auto-trigger a restart
- Restart records with no explicit pod-exit event → likely AIMaster hang-detection trigger

---

## 4. Restart-Anomaly Patterns

### 4.1 Restart-Trigger Classification

| Trigger | Signature | Meaning |
|---------|-----------|---------|
| Pod exit (explicit exit code) | Events show `exited with code X` | Clear root cause — analyze by exit code |
| AIMaster hang detection | No explicit exit event, fires on schedule | Training stall auto-detected |
| Hardware fault | SanityCheck on a node Failed | Triggers node replacement and restart |
| Preemption (Spot) | Pod `Evicted` | Spot instance reclaimed |

### 4.2 Fault-Tolerance Budget

- `max_restart`: total restart budget
- `current_restart / max_restart`: consumed fraction
- Consumed > 80% → warning (budget nearly exhausted)
- Consumed 100% → next failure pushes the Job to terminal Failed
