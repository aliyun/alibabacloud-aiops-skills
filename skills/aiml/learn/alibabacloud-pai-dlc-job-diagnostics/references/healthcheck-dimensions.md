# Health-Inspection Dimensions and Interpretation Rules

Optional dimensions the agent can choose from during health inspection. Pick
inspection depth based on job scale and the user's focus.

---

## Dimension 1: Resource Utilization (GPU / VRAM / Memory)

> **Note**: Resource utilization metrics (GPU core, GPU memory, CPU, network,
> disk) are NOT available via this skill's CLI commands. Direct the user to
> the **PAI console monitoring dashboard** for real-time data. The console
> link is generated in the health-inspection execution steps.

---

## Dimension 2: Training Throughput

**Data source**: structured training metrics extracted from `get-pod-logs`.

**Pod selection**: target the **master (rank=0) pod** first, as master typically
prints aggregated metrics (loss/step/epoch). Worker pod logs serve as
supplementary reference only when master logs are incomplete or unavailable.

**Common log formats**:
```
[iter 15000] loss=2.31, dur=2.3s, mfu=0.45, lr=1e-4
step 15000: loss 2.31, time 2300ms
Epoch 3/10, iter 15000, loss=2.31
```

**Extractable metrics**:
- `iter` / `step`: current iteration count
- `loss`: training loss
- `dur` / `time`: per-step duration (s/step)
- `mfu`: Model FLOPs Utilization
- `epoch`: current epoch
- `lr`: learning rate

**Interpretation rules**:
- Loss steadily decreasing → training converging normally
- Loss flat → may have entered a plateau
- Loss rising → training may be unstable
- `dur` suddenly increases → possible node straggler or I/O bottleneck

**Note**: log formats vary widely across training frameworks — extraction is
not guaranteed. When no structured metrics are detected, simply annotate
"no standard training-metric output detected in logs".

---

## Dimension 3: Hang Detection

**Data source**: `get-pod-logs --max-lines 50` (latest log slice).

**Logic**:
1. Read the timestamp of the latest log line
2. Compute the gap to current time
3. Combine with log content pattern for a final verdict

**Criteria**:
- Logs flowing continuously (< 5 min gap) → normal
- Logs stuck on NCCL Init lines (10-30 min) → suspected NCCL-init hang
- Logs silent > 30 min → suspected hang

**Typical NCCL-init-phase logs**:
```
NCCL INFO Bootstrap: Using ...
NCCL INFO Channel ...
NCCL INFO NET/...
```

---

## Dimension 4: Hardware Health (Sanity Check)

**Data source**: `list-job-sanity-check-results` / `get-job-sanity-check-result`.

**Precondition**: `Settings.EnableSanityCheck = true` must be set for data to exist.

**Check items**:
- `gemm_*`: GPU compute baseline (TFLOP/s)
- `allreduce_*`: collective-comm bandwidth (GB/s)
- `alltoall_*`: all-to-all comm bandwidth (GB/s)
- `mini_gpt`: single-node mini-model training validation (loss consistency)
- `network_connectivity`: network reachability
- `nic_status`: NIC status

**Interpretation rules**:
- Deviation from mean > 5% → outlier node, raise a warning
- Deviation > 10% → significant anomaly, may slow overall training
- A node Failed → that node likely has a hardware issue

**Note**: even when all checks PASSED, surface the baseline numbers so the
user can gauge the cluster's compute level.

---

## Dimension 5: Restart Stability

**Data source**: `get-job` (RestartCount, Settings) + `get-job-events` (exit events).

**Key fields**:
- From `get-job`: current restart count
- From `Settings` or `ElasticSpec`: `max-restart` configuration
- From `Events`: trigger reason of each restart

**Assessment rules**:
- Fault-tolerance budget consumed < 20% → healthy
- Consumed 20-80% → normal consumption
- Consumed > 80% → budget critical, needs attention
- Frequent restarts in a short window → possible persistent fault

---

## Choosing Inspection Depth

The agent may decide depth based on the following signals:

| Signal | Recommended depth |
|--------|-------------------|
| Kilo-card+ job (`PodCount > 100`) | All dimensions; focus on hang + SanityCheck + restarts |
| Medium scale (10-100 cards) | Training throughput + hang + restarts |
| Small job (< 10 cards) | Training throughput + basic status |
| User explicitly asks "is it stuck?" | Hang detection first |
| User asks "is it running well?" | Training throughput + hang detection first |
| Job has a restart history | Restart analysis + fault-tolerance budget first |
