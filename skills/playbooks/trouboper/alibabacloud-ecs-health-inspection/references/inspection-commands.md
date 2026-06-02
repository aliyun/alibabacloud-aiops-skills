# Inspection Commands Reference

All aliyun CLI commands used in each step of the ECS inspection workflow.

> **Unified Plugin Mode**: every `aliyun` CLI invocation in this skill uses **plugin-mode kebab-case** (lowercase-hyphenated actions and parameters). The CMS product requires the dedicated plugin `aliyun-cli-cms` 0.3.0+; the `aliyun configure set --auto-plugin-install true` + `aliyun plugin update` commands in the Installation section of SKILL.md handle this automatically.

---

## Step 0: Enable AI-Mode (Skill Entry)

**[MUST]** Run before any CLI call. Older CLI versions that do not support these subcommands are silently ignored by `|| true`.

```bash
aliyun configure ai-mode enable 2>/dev/null || true
aliyun configure ai-mode set-user-agent \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-health-inspection" 2>/dev/null || true
```

> AI-mode only serves Agent Skill calls. It must be disabled at the end of the inspection (see Step 7).

---

## Step 1: Confirm Instance Information

```bash
aliyun ecs describe-instances \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-ids '["<INSTANCE_ID>"]'
```

**Response fields to extract:** `Status` (must be Running) / `InstanceName` / `OSType` (linux|windows) / `InstanceType` / `CPU` / `Memory` / `InstanceNetworkType` / `GPUAmount` / `GPUSpec`.

---

## Step 2: Check CloudMonitor Agent Status

```bash
aliyun cms describe-monitoring-agent-statuses \
  --region <REGION_ID> \
  --instance-ids <INSTANCE_ID>
```

> `--instance-ids` accepts a comma-separated list (`i-xxx,i-yyy`). **Do NOT** use a JSON array here — its accepted format differs from the `--instance-ids` parameter of the ECS `describe-instances` command.

**Decision:**
- `Status=running` → Step 3A (CloudMonitor path)
- `Status=stopped` / empty response / error / `InvalidOperation.NoPermission` → Step 3B (ECS API fallback)

---

## Step 3A: CloudMonitor Path — Metric Queries

### Common Command Template

3A.1–3A.9 all share the same template; only `<METRIC_NAME>` changes:

```bash
aliyun cms describe-metric-last \
  --region <REGION_ID> \
  --namespace acs_ecs_dashboard \
  --metric-name <METRIC_NAME> \
  --dimensions '{"instanceId":"<INSTANCE_ID>"}' \
  --period 60
```

> **Convention:** every CMS command and parameter is kebab-case (`--namespace` / `--metric-name` / `--dimensions` / `--period`). This requires the `aliyun-cli-cms` plugin (the SKILL.md Installation step has already enabled `auto-plugin-install`, so usually no manual action is needed).

### 3A.1–3A.7 Standard Metric Matrix

| Sub  | MetricName(s)                                | Description           | Unit    | Extraction rule                                |
|------|----------------------------------------------|-----------------------|---------|------------------------------------------------|
| 3A.1 | `CPUUtilization`                             | CPU utilization       | %       | latest + window avg + window max               |
| 3A.2 | `load_1m`, `load_5m`, `load_15m`             | System load           | —       | each takes the latest                          |
| 3A.3 | `memory_usedutilization`                     | Memory utilization    | %       | latest                                         |
| 3A.4 | `DiskReadBPS`, `DiskWriteBPS`                | Disk IO throughput    | bytes/s | latest                                         |
| 3A.5 | `DiskReadIOPS`, `DiskWriteIOPS`              | Disk IOPS             | count/s | latest                                         |
| 3A.6 | `networkin_rate`, `networkout_rate`          | Network traffic       | bits/s  | latest                                         |
| 3A.7 | `diskusage_utilization`                      | Disk-usage percentage | %       | latest per mount point                         |

> **Note:** the `MetricName` value is the OpenAPI business literal — **not** a CLI parameter style. Some are PascalCase (`CPUUtilization` / `DiskReadBPS`), others are snake_case (`load_1m` / `memory_usedutilization` / `networkin_rate`). Pass the literals as listed; do not normalize them.

> Any metric returning empty data → mark it as `"N/A"` in the report. Memory and disk metrics are unavailable on certain instance families.

### 3A — Parallel Batch Execution

Pack the 3A.1–3A.7 metric queries plus the Step 4 `describe-disks` call (and 3A.9 for GPU instances) into a single shell command. Bash background jobs `&` + `wait` give true parallelism:

```bash
# Store instance ID and region in variables for reuse
IID="i-xxxxx"
RGN="cn-xxxxx"

# 3A.1 CPU
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name CPUUtilization --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_cpu.json 2>&1 &

# 3A.2 Load (3 metrics in parallel)
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name load_1m --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_load1m.json 2>&1 &
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name load_5m --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_load5m.json 2>&1 &
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name load_15m --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_load15m.json 2>&1 &

# 3A.3 Memory
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name memory_usedutilization --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_mem.json 2>&1 &

# 3A.4 Disk BPS (read + write)
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name DiskReadBPS --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_diskrbps.json 2>&1 &
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name DiskWriteBPS --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_diskwbps.json 2>&1 &

# 3A.5 Disk IOPS (read + write)
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name DiskReadIOPS --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_diskriops.json 2>&1 &
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name DiskWriteIOPS --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_diskwiops.json 2>&1 &

# 3A.6 Network (in + out)
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name networkin_rate --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_netin.json 2>&1 &
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name networkout_rate --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_netout.json 2>&1 &

# 3A.7 Disk Usage
aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name diskusage_utilization --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_diskusage.json 2>&1 &

# Step 4: Disk Capacity
aliyun ecs describe-disks --biz-region-id $RGN --region $RGN --instance-id $IID > /tmp/ecs_inspect_disks.json 2>&1 &

# 3A.9 GPU metrics — only for GPU instances (Step 1 detected GPUAmount > 0 or InstanceType matches a GPU prefix)
# aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name instance_gpu_gpu_temperature --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_gputemp.json 2>&1 &
# aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name instance_gpu_gpu_usedutilization --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_gpuutil.json 2>&1 &
# aliyun cms describe-metric-last --region $RGN --namespace acs_ecs_dashboard --metric-name instance_gpu_memory_usedutilization --dimensions "{\"instanceId\":\"$IID\"}" --period 60 > /tmp/ecs_inspect_gpumem.json 2>&1 &

# Wait for ALL background jobs to complete
wait

# Print all results sequentially for parsing
for k in cpu load1m load5m load15m mem diskrbps diskwbps diskriops diskwiops netin netout diskusage disks; do
  echo "=== ${k} ===" && cat /tmp/ecs_inspect_${k}.json
done
```

> **Conditional Batch 2**: only when the output above shows CPU > 80% or Memory > 80% should you fire [§ 3A.8](#3a8-process-monitoring-conditional).

### 3A.8 Process Monitoring (Conditional)

> **Trigger**: only when CPU > 80% or Memory > 80%; skip otherwise to save API calls.

Use the [Common Command Template](#common-command-template) with `metric-name` set to `process.cpu` and `process.memory` to retrieve the Top-5 CPU / memory processes.

**Response fields** (each datapoint is one process): `name` / `pid` / `user` / `Average` (CPU% or Mem%).

> The memory metric may be empty on some instance families → mark as `"N/A"`.

### 3A.9 GPU Monitoring (Conditional)

> **Trigger**: only when the instance is a **GPU instance** (Step 1 detected `GPUAmount > 0` or `InstanceType` matches a GPU prefix); otherwise skip the entire section.

Use the [Common Command Template](#common-command-template) with `metric-name` set to the following three (instance-level aggregates):

| MetricName                              | Description           | Unit |
|-----------------------------------------|-----------------------|------|
| `instance_gpu_gpu_temperature`          | GPU temperature       | °C   |
| `instance_gpu_gpu_usedutilization`      | GPU utilization       | %    |
| `instance_gpu_memory_usedutilization`   | GPU memory utilization| %    |

> Empty result → mark as `"N/A"`. GPU metrics require the CloudMonitor agent's GPU monitoring plugin to be installed.

---

## Step 3B: ECS API Fallback Path

### 3B.1 Time Range Calculation

```bash
# Linux / macOS compatible
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
START_TIME=$(date -u -d '15 minutes ago' +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-15M +"%Y-%m-%dT%H:%M:%SZ")
```

### 3B.2 Instance Monitor Data (CPU / Memory / Network / IO)

```bash
aliyun ecs describe-instance-monitor-data \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID> \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60
```

**Response fields**:

| Field | Description | Unit |
|-------|-------------|------|
| `CPU` | CPU utilization | % |
| `Memory` | Memory utilization (limited instance families) | % |
| `IntranetRX` / `IntranetTX` | Intranet traffic | bytes/s |
| `InternetRX` / `InternetTX` | Internet traffic | bytes/s |
| `IOPSRead` / `IOPSWrite` | Disk IOPS | count/s |
| `BPSRead` / `BPSWrite` | Disk BPS | bytes/s |

**Processing**: compute avg + max within the window per metric.

### 3B.3 Disk Monitor Data

First call [Step 4](#step-4-disk-capacity) to get the disk list, then query per disk:

```bash
aliyun ecs describe-disk-monitor-data \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --disk-id <DISK_ID> \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60
```

**Response fields**: `BPSRead` / `BPSWrite` / `IOPSRead` / `IOPSWrite` / `LatencyRead` / `LatencyWrite`.

### Fallback-Path Metric Availability

| Metric | Availability | Source |
|--------|:--:|--------|
| CPU usage | ✓ | describe-instance-monitor-data |
| Memory usage | ⚠️ | Limited instance families; empty → `"N/A"` |
| Disk IO BPS / IOPS | ✓ | describe-instance-monitor-data / describe-disk-monitor-data |
| Disk latency | ✓ | describe-disk-monitor-data |
| Network traffic | ✓ | describe-instance-monitor-data |
| System load | ✗ | Not available |
| Disk usage % | ✗ | Not available |

---

## Step 4: Disk Capacity

```bash
aliyun ecs describe-disks \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID>
```

**Response fields per disk**: `DiskId` / `Size` (GB) / `Category` (cloud_essd|cloud_ssd|...) / `Type` (system|data) / `Device` (/dev/vda...) / `Status` (In_use|Available).

---

## Step 7: Cleanup & AI-Mode Disable (Skill Exit — every exit point)

**[MUST]** Run at every exit point (success / failure / exception / cancellation):

```bash
# Disable AI-mode
aliyun configure ai-mode disable 2>/dev/null || true

# Remove temporary JSON files generated during inspection
rm -f /tmp/ecs_inspect_*.json
```

> AI-mode must not leak across sessions. Whether or not the inspection completed, this step is mandatory.
