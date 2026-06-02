# Degradation Paths and JSON Validation

> This document collects the full mandatory rules referenced by SKILL.md Step 2 / Step 3A / Step 3B / Step 6.1.
> The main SKILL.md keeps only the core directives and links here.

---

## 1. Step 2 — Mandatory Execution Sequence on Permission Failures

**Scope:** the agent-status query returns `403`, `InvalidAuthorization`, or `Forbidden`.

> **Never jump straight to Step 3B.** The execution must follow this order:

1. **Record the permission interception** — flag the CMS Agent status as permission-restricted.
2. **Still fire all 3A.1–3A.7 `describe-metric-last` requests in parallel (plus 3A.9 for GPU instances)**, because some metrics may have independent RAM grants and must be probed individually. MetricName list:
   - `CPUUtilization` (3A.1)
   - `load_1m` / `load_5m` / `load_15m` (3A.2)
   - `memory_usedutilization` (3A.3)
   - `DiskReadBPS` / `DiskWriteBPS` (3A.4)
   - `DiskReadIOPS` / `DiskWriteIOPS` (3A.5)
   - `networkin_rate` / `networkout_rate` (3A.6)
   - `diskusage_utilization` (3A.7)
   - GPU instances additionally include the 3A.9 `instance_gpu_*` metrics
3. **Execution checkpoint** — before invoking any 3B API, the output must explicitly record "All 3A.x requests have been fired; results: XX succeeded / YY returned 403 or empty". Without this checkpoint, or if any 3A request was not fired, entering 3B is forbidden.
4. **Count successes** — successfully retrieved metrics are folded into the report as usual.
5. **Only when every 3A request returns 403 or empty data** is the Step 3B `describe-instance-monitor-data` fallback allowed.
6. **Report declaration** — in the JSON `narrative`, state: "Some metrics were automatically switched to the ECS Monitor API fallback path due to RAM permission restrictions."

> The `→ Step 3B` arrow in the decision table only means "may eventually downgrade", not "skip all 3A queries immediately".

---

## 2. Step 3A — Error Handling Rules

### 2.1 3A.8 Mandatory Trigger (independent conditional branch)

3A.8 is an independent conditional branch and is **unaffected by failures in 3A.1–3A.7**. Whenever Batch 1's `CPUUtilization` or `memory_usedutilization` exceeds 80%, the 3A.8 query must be fired immediately. Even when the overall path has been downgraded to 3B, 3A.8 must still run first; skipping or deferring it because of 403s on other metrics is forbidden.

### 2.2 3A.8 Process-Level Query Tolerance

If the process-level metrics return 403 or empty, the report should explain "Process-level metric queries are restricted; manually run `top -bn1 | head -15`" and continue the workflow. Aborting the workflow is forbidden.

### 2.3 3A.9 GPU Metric Batch Tolerance

`instance_gpu_gpu_temperature` / `instance_gpu_gpu_usedutilization` / `instance_gpu_memory_usedutilization` **must all be fired**. On partial failure:
- Record each failed item and the cause in `dimensions[]`.
- A single failure must NOT cause the rest of the GPU queries to be cancelled.
- Successful items are added to the report normally; failed items are labelled `"N/A — query restricted"`.

### 2.4 MetricName is Locked, Byte-for-Byte

For every `cms describe-metric-last` call (3A.1–3A.9), use the **literal** `MetricName` as listed in SKILL.md Step 3A and in this document. The following are forbidden:
- Changing the case (e.g. `GPUUtilization` instead of `instance_gpu_gpu_usedutilization`).
- Adding prefixes / suffixes (e.g. `acs_ecs_dashboard.cpu_total`, `gpu_temperature_celsius`).
- Replacing dots with underscores or vice versa (e.g. `instance.gpu.temp`).
- Switching to alternative namespaces (e.g. `acs_gpu_monitoring`).

If the **first** attempt with the canonical name returns `400 metric not exist` / `404`, **stop immediately**. The metric does not exist for this instance / region / agent state. Do NOT loop with name variants. Mark the entry as `"N/A — query restricted"` in `dimensions[]` and continue with the remaining batch.

---

## 3. Step 3B — Mandatory Call List for the Fallback Path

### 3.1 Hard Stop on Entering 3B

The moment Step 3B is selected, **abort every `cms describe-metric-last` call** that is still running or queued. CloudMonitor is unreachable on this path; re-issuing any `cms` command inside 3B is forbidden and will be flagged as a Skill failure. The path switch is one-way: 3A → 3B, never back.

### 3.2 Three Mandatory ECS API Calls (one single shell invocation)

When taking the 3B path, the following three calls **must all run in parallel inside one single shell invocation** (bash `&` + `wait`). Splitting the batch across multiple sequential tool calls is forbidden. Fetching only the capacity while skipping the performance monitoring is forbidden:

1. `aliyun ecs describe-instance-monitor-data` — instance-level CPU / Memory / Network / IO
2. `aliyun ecs describe-disks` — disk list + capacity
3. `aliyun ecs describe-disk-monitor-data` — **per-disk BPS / IOPS / Latency**, called once per `DiskId`

```bash
aliyun ecs describe-instance-monitor-data --region-id $REGION --instance-id $INSTANCE_ID \
  --start-time $START --end-time $END --period 60 \
  > /tmp/ecs_3b_imd.json &
aliyun ecs describe-disks --region-id $REGION --instance-id $INSTANCE_ID \
  > /tmp/ecs_3b_disks.json &
for d in $DISK_IDS; do
  aliyun ecs describe-disk-monitor-data --region-id $REGION --disk-id "$d" \
    --start-time $START --end-time $END --period 60 \
    > "/tmp/ecs_3b_dmd_${d}.json" &
done
wait
```

**Self-check after `wait`**: `/tmp/ecs_3b_imd.json`, `/tmp/ecs_3b_disks.json`, **and at least one `/tmp/ecs_3b_dmd_*.json`** must all be present and non-empty. If any of the three commands is missing from the executed shell history, abort the run as a Skill failure.

### 3.3 Metric-Loss Declaration

Metrics that cannot be obtained must be declared explicitly in the JSON:
- The `value` of the corresponding entry in `dimensions[]` is set to `"N/A — fallback path triggered by permission limit"`.
- For process-level metrics, add a hint to `anomalies[]` or `recommendations.immediate[]`: "Manually run `top` or `ps aux --sort=-%cpu | head -10`".
- For GPU instances on the 3B path, **the 3A.9 GPU `describe-metric-last` queries must still be attempted** (GPU metrics may have a permission grant independent of the agent status). Only when CMS is fully unreachable do you label them `"GPU metrics require a running CloudMonitor agent and are currently unavailable"`.
- **Never silently omit unavailable metrics** — every dimension must be reflected in the report.

---

## 4. Step 6.1 — JSON Pre-Validation Checklist

### 4.1 General Rules

1. **Required fields cannot be empty** — `dimensions[].value` / `anomalies[].detail` / `narrative` must not be empty strings.
2. **Field naming must match the schema exactly** — do not invent field names; `python3 scripts/render_report.py --schema` is the source of truth.
3. **Empty data is uniformly `"N/A"`** — no blanks, no `null`.
4. **`disks[]` must cover every disk discovered in Step 4** — none may be omitted.
5. **Data-loss guard** — before serializing the JSON, traverse every API response file you produced (`/tmp/ecs_3b_*.json`, `cms describe-metric-last` payloads, etc.). If a metric carries a valid numeric value in the raw response, surface it in both `metrics.*` and the corresponding `dimensions[]` row. Silently overwriting an available value with `null` or `"N/A"` is a Skill failure. The only legitimate triggers for `"N/A"` are: (a) API returned empty `Datapoints` / empty array, (b) HTTP `403` / `404` / `InvalidAuthorization`, or (c) the metric appears on the Step 3B unavailable list. Common pitfalls observed in evaluations: 3A.2 system-load values being lost between collection and serialization, and 3A.7 disk-usage values being downgraded to `"N/A"` even though the response contained valid numbers.

### 4.2 Hard Type Constraints

`dimensions[].value` / `dimensions[].current` must be **a plain number or `"N/A"`**:
- Range strings such as `"99-100%"`, `"around 50%"` are forbidden.
- Range / fluctuation information belongs in independent fields like `min` / `max` / `avg`, or in the prose.

### 4.3 Unit Enforcement (disk latency)

The `Latency` value returned by the API is in microseconds (`μs`); **it must NOT be converted to `ms`**.

The following situations are hard-blocked and must be fixed before rendering:
- The field carries an `ms` suffix.
- The numeric value is less than 1 (likely accidentally divided by 1000).

If a unit suffix or `unit` field is needed, it must be `"μs"` — never `"ms"`.

Other units: network traffic in `bits/s`; IO throughput in `bytes/s`.

### 4.4 Grade Mapping

`grade` / `grade_label` must follow `health_score` strictly:

| Score range | grade | grade_label |
|-------------|:-----:|-------------|
| `>= 90` | A | Excellent |
| `[75, 89]` | B | Good |
| `[60, 74]` | C | Fair, needs attention |
| `[40, 59]` | D | WARNING |
| `< 40` | F | CRITICAL |

**A low score combined with `one_liner` text such as "everything is fine" or "no anomalies" is forbidden.**

### 4.5 Auto Validation (mandatory)

Before rendering, always run:

```bash
python3 scripts/render_report.py --validate --input /tmp/ecs_inspect_data.json
```

The validator covers required fields, the `grade` ↔ `health_score` match, the consistency between grade and `one_liner`, range expressions in `dimensions[].current`, the `disk_latency` unit, and a non-empty `disks[]`.

**Non-zero exit code → fix the JSON and re-run until it passes; rendering broken data is forbidden.**
