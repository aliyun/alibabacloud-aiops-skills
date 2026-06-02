---
name: alibabacloud-ecs-health-inspection
description: ECS Health Inspection - Perform comprehensive health inspection on Alibaba Cloud ECS instances. Checks CPU usage, system load, memory usage, disk IO (BPS and IOPS), network traffic, disk capacity, and GPU metrics (when applicable). Generates a structured HTML inspection report with findings and recommendations. Use when users request ECS health inspection, instance health check, performance inspection, resource usage report, or system health status of an ECS instance.
metadata:
  pattern: pipeline
  steps: "8"
  required_params: "instance_id, region_id"
  domain: aiops
  owner: ecs-team
  contact: ecs-agent@alibaba-inc.com
---

# ECS Health Inspection

Performs a full-dimension read-only inspection on a single ECS instance, automatically selecting the optimal data source (CloudMonitor preferred, ECS Monitor API as fallback) and producing a structured HTML report.

## Architecture

`ECS Instance + CloudMonitor (acs_ecs_dashboard) + ECS Monitor API (DescribeInstanceMonitorData / DescribeDiskMonitorData) + Local Python Renderer (render_report.py)`

Read-only path. Zero resource creation or mutation.

---

## Installation

### Pre-check: Aliyun CLI >= 3.3.3 required

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low, install via the following secure flow (download → verify → install). **Do NOT use `curl ... | bash` to pipe a remote script directly into the shell** — this avoids supply-chain risks.
>
> **Step 1: Download the installer and the setup script:**
> ```bash
> # Choose the tarball that matches your architecture (amd64 / arm64) and OS
> curl -fsSL -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-arm64.tgz
> curl -fsSL -o setup.sh    https://aliyuncli.alicdn.com/setup.sh
> ```
>
> **Step 2: Inspect the script manually before executing:**
> ```bash
> less setup.sh           # Read the script and confirm there is nothing suspicious
> shasum -a 256 aliyun-cli.tgz setup.sh   # Record hashes; cross-check with the official channel
> bash ./setup.sh         # Execute only after the review passes
> aliyun version          # Verify >= 3.3.3
> ```
>
> Additional installation methods: https://help.aliyun.com/zh/cli/install-cli-on-macos-or-linux

### Pre-check: Aliyun CLI plugin update required

> [MUST] Enable plugin auto-install and refresh existing plugins (CMS uses plugin-mode kebab-case via `aliyun-cli-cms` 0.3.0+):
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```
> Verify the cms plugin is active (optional): `aliyun cms --help | head -3` should print `Note: The help information for product 'cms' is provided by the installed plugin 'aliyun-cli-cms'`.

### Python Runtime (HTML rendering dependency)

This skill ships one script — [scripts/render_report.py](scripts/render_report.py) — and explicitly declares its dependencies in **two synchronized locations**:

1. **Inline declaration** — top docstring of [scripts/render_report.py](scripts/render_report.py) (the `Dependencies` block).
2. **Standalone declaration** — [scripts/requirements.txt](scripts/requirements.txt) (canonical pip-compatible file).

| Layer | Requirement | Notes |
|-------|-------------|-------|
| Runtime | **Python >= 3.8** | Required |
| Third-party packages | **(none)** | The script is intentionally stdlib-only; no `pip install` needed |
| Standard library | `argparse`, `html`, `json`, `sys`, `typing`, `__future__` | All shipped with CPython |

Verify the runtime: `python3 --version`.

Install (a no-op today, kept for future-proofing CI/containers):

```bash
python3 -m pip install -r scripts/requirements.txt
```

> **Upgrade policy:** introducing any third-party dependency (e.g. Jinja2, pydantic, lxml) requires updating **both** the inline `Dependencies` block in `render_report.py` **and** `scripts/requirements.txt`, plus a one-line note in this section.

---

## Environment Variables

This skill does not require any extra environment variables. Credentials should be configured beforehand (outside the session) via `aliyun configure`.

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_PROFILE` | Optional | Select a specific aliyun profile |
| `ALIBABA_CLOUD_REGION_ID` | Optional | Default region (commands still need an explicit `--region`) |

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

Full permission list and a custom policy example: **[references/ram-policies.md](references/ram-policies.md)**.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

Minimum-permission summary (all read-only): `ecs:DescribeInstances`, `ecs:DescribeInstanceMonitorData`, `ecs:DescribeDiskMonitorData`, `ecs:DescribeDisks`, `cms:DescribeMonitoringAgentStatuses`, `cms:DescribeMetricLast`.

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|:----------------:|-------------|---------|
| `INSTANCE_ID` | **Required** | ECS instance ID | — |
| `REGION_ID` | **Required** | Region ID (e.g. `cn-hangzhou`) | — |
| `TIME_RANGE` | Optional | Data query window (minutes) | `15` |

**If any required parameter is missing, ask the user first — never guess.**

---

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

> **Commands Reference**: All `aliyun` CLI commands are recorded in **[references/inspection-commands.md](references/inspection-commands.md)**. Read the matching subsection before executing each step.

### Mandatory Rules

1. **Parameters first** — Instance ID and Region ID must be confirmed by the user; if missing, stop and ask.
2. **Maximize parallelism** — Independent queries MUST be batched into **one single shell invocation** (i.e. one `run_shell_command` / one `bash -c` call) using `&` + `wait`. Splitting a parallel batch into multiple sequential tool calls is forbidden — the evaluator counts each batch as one shell command, and serialized calls fail the parallelism check.
3. **CloudMonitor preferred** — Check Agent status first; `running` → 3A, otherwise → 3B.
4. **Conclusions must be based on real data** — No fabrication, speculation, or assumption. **CLI error handling:** if `aliyun` returns a parameter-missing or format error, NEVER pad with mock data; parse the error log, complete the parameters, and retry. After two consecutive failures, report the error code to the user and terminate the workflow.
5. **Unified plugin-mode kebab-case** — Both ECS and CMS (via the `aliyun-cli-cms` plugin) use lowercase-hyphenated actions and parameters.
6. **If a metric is unavailable, drop the section** — Do not emit `N/A` placeholder rows (e.g. there is no `load` on Windows).
7. **Read-only** — No step is allowed to modify the instance configuration.
8. **CPU/Memory > 80% triggers process-level inspection** — see Step 3A.8.

### Step 0: Enable AI-Mode ([MUST] skill entry)

> [MUST] Run **before any CLI call**:
> ```bash
> aliyun configure ai-mode enable 2>/dev/null || true
> aliyun configure ai-mode set-user-agent \
>   --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-health-inspection" 2>/dev/null || true
> ```
> AI-mode only serves Agent Skill calls; the matching `disable` in Step 7 must be executed at every exit point (success/failure/cancel).

### Step 1: Confirm Instance Information

Read **[inspection-commands.md § Step 1](references/inspection-commands.md#step-1-confirm-instance-information)**.

Extract: `Status` (must be Running) / `InstanceName` / `OSType` / `InstanceType` / `CPU` / `Memory` / `InstanceNetworkType` / `GPUAmount` / `GPUSpec`.

- **GPU detection**: `GPUAmount > 0`, or `InstanceType` matches the prefixes `ecs.gn` / `ecs.ga` / `ecs.ebmgn` / `ecs.vgn` → enable Step 3A.9.
- Instance does not exist → notify the user and run **Step 7** to exit.

### Step 2: CloudMonitor Agent Status

Read **[inspection-commands.md § Step 2](references/inspection-commands.md#step-2-check-cloudmonitor-agent-status)**.

| Agent Status | Path |
|--------------|------|
| `running` | → Step 3A |
| `stopped` / empty / `InvalidOperation.NoPermission` / `403` / `InvalidAuthorization` | → Step 3B |

> **[MUST] A permission error is NOT a direct jump to 3B.** When the agent-status query returns `403` / `InvalidAuthorization` / `Forbidden`, you **still must fire all 3A.1–3A.7 `describe-metric-last` requests in parallel (plus 3A.9 for GPU instances)** and record an execution checkpoint such as "XX succeeded / YY returned 403". **Only when every 3A request fails** are you allowed to enter 3B; declare the fallback in `narrative`.
>
> **[IMPORTANT] Before deciding to enter 3B, independently check the 3A.8 trigger:** if either `CPUUtilization` or `memory_usedutilization` from Batch 1 exceeds 80%, **immediately fire 3A.8 process-level queries in parallel**. This is independent of any 403 on the other 3A metrics, and must NOT be deferred until the fallback decision.
>
> Full execution sequence and MetricName retry list: **[references/degradation-and-validation.md § 1](references/degradation-and-validation.md#1-step-2--mandatory-execution-sequence-on-permission-failures)**.

### Step 3A: CloudMonitor Path

Read **[inspection-commands.md § 3A — Parallel Batch Execution](references/inspection-commands.md#3a--parallel-batch-execution)** and bundle 3A.1–3A.7 + Step 4 (+ 3A.9 for GPU instances) into a single parallel batch.

| Sub | MetricName | Description | Unit |
|-----|-----------|-------------|------|
| 3A.1 | `CPUUtilization` | CPU utilization | % |
| 3A.2 | `load_1m`, `load_5m`, `load_15m` | System load | — |
| 3A.3 | `memory_usedutilization` | Memory utilization | % |
| 3A.4 | `DiskReadBPS`, `DiskWriteBPS` | Disk IO throughput | bytes/s |
| 3A.5 | `DiskReadIOPS`, `DiskWriteIOPS` | Disk IOPS | count/s |
| 3A.6 | `networkin_rate`, `networkout_rate` | Network traffic | bits/s |
| 3A.7 | `diskusage_utilization` | Disk-usage percentage | % |
| 3A.9 | `instance_gpu_*` | GPU temperature / utilization / memory | °C / % / % |

**Batch 2 (conditional)** — fired when Batch 1 shows CPU > 80% or Memory > 80%:

| Sub | MetricName | Description | Unit |
|-----|-----------|-------------|------|
| 3A.8 | `process.cpu`, `process.memory` | Top 5 CPU / memory processes | % |

> **[MUST] 3A error handling and mandatory rules:**
> - **3A.8 is an independent conditional branch, unaffected by 3A.1–3A.7 failures**: if CPU or Memory exceeds 80%, it must be fired immediately and must NOT be skipped or deferred because of 403s on other metrics. Even if the overall path has been downgraded to 3B, 3A.8 must still run first.
> - **3A.8 returns 403 / empty**: the report should suggest a manual `top -bn1 | head -15`; do NOT abort the workflow.
> - **3A.9 GPU metrics must all be fired**; a single failure must not cancel the rest. Failed items are labeled `"N/A — query restricted"`.
> - **[MetricName is locked, byte-for-byte]** — for every `describe-metric-last` call (especially 3A.9 GPU metrics), use the literal `MetricName` from the table above. Do NOT change case, add prefixes/suffixes, swap the namespace, or invent variants such as `gpu_temperature` / `GPUUtilization` / `instance.gpu.temp`. **If the FIRST attempt returns `400 metric not exist` / `404`, STOP immediately** — the metric does not exist for this instance/region; mark it `"N/A — query restricted"` and continue. Do NOT loop with name variants.
>
> Full ruleset: **[references/degradation-and-validation.md § 2](references/degradation-and-validation.md#2-step-3a--error-handling-rules)**.

For CPU, take the latest plus the avg/max within the window; for other metrics take the latest. Empty data → label `"N/A"`.

### Step 3B: ECS API Fallback Path

Read **[inspection-commands.md § Step 3B](references/inspection-commands.md#step-3b-ecs-api-fallback-path)**.

| Metric | Available | Source |
|--------|:--:|--------|
| CPU / Memory* / Network / IO BPS+IOPS | ✓ | DescribeInstanceMonitorData |
| Per-disk BPS + IOPS + Latency | ✓ | DescribeDiskMonitorData |
| System Load / Disk Usage % | ✗ | Not available (label `"N/A — requires CloudMonitor agent"`) |
| Process-level CPU / Memory (Top 5) | ✗ | 3A path only |
| GPU temperature / utilization / memory | ✗ | 3A path only |

\* Memory is unavailable for some instance families.

> **[MUST — HARD STOP] Entering 3B**: the moment 3B is selected, **abort every `cms describe-metric-last` call**. CloudMonitor is unreachable on this path; re-issuing any `cms` command inside 3B is forbidden and will be flagged as a Skill failure. The path switch is one-way: 3A → 3B, never back.
>
> **[MUST] The 3B path MUST call all three ECS APIs — capacity-only is a Skill failure:**
> 1. `aliyun ecs describe-instance-monitor-data` — instance-level CPU / Memory / Network / IO
> 2. `aliyun ecs describe-disks` — disk list + capacity
> 3. `aliyun ecs describe-disk-monitor-data` — **per-disk BPS / IOPS / Latency**, called per `DiskId`
>
> **[MUST] Mandatory parallel template** — fire all three ECS APIs in **one single shell invocation**. Splitting the batch into separate tool calls is a Skill failure:
> ```bash
> aliyun ecs describe-instance-monitor-data --region-id $REGION --instance-id $INSTANCE_ID \
>   --start-time $START --end-time $END --period 60 \
>   > /tmp/ecs_3b_imd.json &
> aliyun ecs describe-disks --region-id $REGION --instance-id $INSTANCE_ID \
>   > /tmp/ecs_3b_disks.json &
> for d in $DISK_IDS; do
>   aliyun ecs describe-disk-monitor-data --region-id $REGION --disk-id "$d" \
>     --start-time $START --end-time $END --period 60 \
>     > "/tmp/ecs_3b_dmd_${d}.json" &
> done
> wait
> ```
> Self-check after `wait`: `/tmp/ecs_3b_imd.json`, `/tmp/ecs_3b_disks.json`, **and at least one `/tmp/ecs_3b_dmd_*.json`** must all be present and non-empty. If any of the three commands is missing from the executed shell history, abort the run as a Skill failure.
>
> **Unavailable metrics MUST be declared explicitly in the report** (label them `"N/A — fallback path triggered by permission limit"` in `dimensions[]`); do not silently omit them. **GPU instances on the 3B path must still attempt the 3A.9 GPU queries**; mark them unavailable only when CMS is fully out of reach.
>
> Full call list and metric-loss declaration rules: **[references/degradation-and-validation.md § 3](references/degradation-and-validation.md#3-step-3b--mandatory-call-list-for-the-fallback-path)**.

### Step 4: Disk Capacity (independent step, parallel with 3A/3B)

> **[Independent parallel step]** This step is independent of whichever monitoring path was chosen. **Regardless of 3A or 3B, `aliyun ecs describe-disks` MUST be executed** to obtain disk-capacity information. Skipping it on the fallback path is forbidden.

Read **[inspection-commands.md § Step 4](references/inspection-commands.md#step-4-disk-capacity)**. Per disk, extract: `DiskId` / `Size` / `Category` / `Type` (system|data) / `Device` / `Status`.

On the CloudMonitor path, merge the 3A.7 disk-usage % by mount point with the disk info gathered here.

### Step 5: Anomaly Detection

Threshold table:

| Metric | ⚠️ Warning | 🔴 Critical |
|--------|----------|-----------|
| CPU usage | > 80% avg | > 95% avg |
| System load | > CPU cores | > 2× CPU cores |
| Memory usage | > 80% | > 95% |
| Disk usage | > 80% | > 95% |
| Disk IOPS / BPS | Approaching instance limit | Above instance limit |
| GPU temperature | > 75°C | > 85°C |
| GPU utilization / memory | > 80% | > 95% |

Every anomaly must come with concrete remediation. If 3A.8 process-level queries were triggered, fold the Top-5 process tables into the root-cause analysis.

### Step 6: Render the HTML Report

> Since 2026-05-12, the LLM **emits structured JSON only**; [scripts/render_report.py](scripts/render_report.py) renders the HTML, cutting end-to-end latency by ~50%.

**Step 6.1 — Build the JSON**

LLM-mandatory fields: `assessment.health_score` / `grade` / `grade_label` / `one_liner` / `narrative` / `dimensions[]` / `anomalies[]` / `cost_evaluation` / `cost_suggestion` / `recommendations.{immediate,short_term,long_term}[]`.

Full schema: `python3 scripts/render_report.py --schema`.

> **[MUST] JSON construction and validation:**
> - **Required fields cannot be empty**: `dimensions[].value` / `anomalies[].detail` / `narrative` must not be empty strings; for empty data fill `"N/A"`, never `null`.
> - **[Data-loss guard]** Before writing `dimensions[]` / `metrics.*`, **traverse every API response file you produced** (`/tmp/ecs_3b_*.json`, the `cms describe-metric-last` payloads, etc.). If a metric carries a valid numeric value in the raw response, you MUST surface that value; **silently overwriting it as `null` or `"N/A"` is a Skill failure** (e.g. system-load values returned by 3A.2 must reach `metrics.load.*` and the corresponding `dimensions[]` row). The only legitimate triggers for `"N/A"` are: (a) API returned empty `Datapoints` / empty array, (b) HTTP `403` / `404` / `InvalidAuthorization`, or (c) the metric appears on the Step 3B unavailable list. **`null` is never permitted** under any circumstance — use `"N/A"`.
> - **Type constraints**: `dimensions[].value` / `current` must be plain numbers or `"N/A"`. Range strings such as `"99-100%"` or `"around 50%"` are forbidden.
> - **Unit enforcement**: disk latency in `μs` (NOT `ms`), network in `bits/s`, IO throughput in `bytes/s`.
> - **Grading logic**: `grade` / `grade_label` must strictly follow `health_score` (e.g., `>=90` → A, `[40,59]` → D, `<40` → F). A low score combined with a `one_liner` like "everything is fine" is forbidden.
> - **Hard guard**: if any `metrics.disk_latency.*` or `disks[].latency_*` field carries an `ms` suffix or has a value < 1, abort and fix immediately. The raw microsecond value from the API must pass through unchanged — never apply your own arithmetic conversion.
>
> Grade-mapping table and full pre-validation checklist: **[references/degradation-and-validation.md § 4](references/degradation-and-validation.md#4-step-61--json-pre-validation-checklist)**.

> **[MUST] `--validate` is mandatory before rendering:**
> ```bash
> python3 scripts/render_report.py --validate --input /tmp/ecs_inspect_data.json
> ```
> A non-zero exit code means the JSON must be fixed and re-validated until it passes — **never render with broken data**.

**Step 6.2 — Invoke the renderer**

> **[MUST] The LLM is forbidden from writing the HTML template or hand-assembling the report.** All structured data MUST flow strictly through `python3 scripts/render_report.py`. If `render_report.py` fails, output the full error log and tell the user how to fix it; **never fall back to manually generated HTML**. A render failure is a Skill failure.

```bash
cat > /tmp/ecs_inspect_data.json <<'JSON_EOF'
{ ... structured data produced by the LLM ... }
JSON_EOF

python3 scripts/render_report.py \
  --input /tmp/ecs_inspect_data.json \
  --output "ecs-${INSTANCE_ID}-inspection-report-$(date +%Y%m%d-%H%M%S).html"
```

If the script returns a non-zero exit code:
1. Print the full stderr.
2. Cross-check the JSON against the schema (`python3 scripts/render_report.py --schema`).
3. Fix the JSON and retry once.
4. If it still fails, return the error to the user and run Step 7 to exit.

**Step 6.3 — Naming convention**: `ecs-{INSTANCE_ID}-inspection-report-{YYYYMMDD-HHMMSS}.html`, saved to the workspace root.

### Step 7: Cleanup & Disable AI-Mode ([MUST] every exit point)

> [MUST] On every exit — success, failure, cancel, or any exception — **always** run:
> ```bash
> aliyun configure ai-mode disable 2>/dev/null || true
> rm -f /tmp/ecs_inspect_*.json
> ```
> A residual AI-mode contaminates the next session, so disabling it is mandatory. This skill is read-only — no cloud-side cleanup is needed.

---

## Success Verification

End-to-end acceptance:

1. The instance exists and `Status=Running` ✓
2. Step 3A or 3B returned at least one valid metric ✓
3. Step 4 returned at least the system disk ✓
4. The Step 6 HTML file is > 5 KB ✓
5. Step 7 has disabled AI-mode ✓

If any item fails, tell the user the failure reason. **Never fabricate data.**

---

## Cleanup

This skill is read-only — there are no cloud resources to reclaim. Step 7 already covers the local cleanup:

- `aliyun configure ai-mode disable`
- Remove the `/tmp/ecs_inspect_*.json` intermediate files

The HTML report stays in the workspace root; the user decides whether to keep it.

---

## Command Tables

Full CLI command list and field semantics: **[references/inspection-commands.md](references/inspection-commands.md)**. Quick view of the common product/action pairs:

| Product | Command | Purpose |
|---------|---------|---------|
| ecs | `aliyun ecs describe-instances` | Instance existence + spec |
| ecs | `aliyun ecs describe-disks` | Disk capacity + mount mapping |
| ecs | `aliyun ecs describe-instance-monitor-data` | Instance monitoring data (fallback path) |
| ecs | `aliyun ecs describe-disk-monitor-data` | Per-disk monitoring data (fallback path) |
| cms | `aliyun cms describe-monitoring-agent-statuses` | Agent-status decision |
| cms | `aliyun cms describe-metric-last` | Full metric query (primary path) |

---

## Best Practices

1. **Always confirm parameters first** — never start running without Instance ID and Region ID.
2. **Always parallelize** — running 13+ metric queries serially makes a single inspection an order of magnitude slower.
3. **CloudMonitor first** — the full metric set is only available on the 3A path; 3B is a fallback, not a default.
4. **Empty data is `"N/A"`** — no fabrication, no extrapolation, no "close enough".
5. **Process queries only when CPU/Memory > 80%** — the process-level API is expensive; skip it when there is no anomaly.
6. **CMS plugin is required for kebab-case** — once `aliyun-cli-cms` 0.3.0+ is installed, CMS supports plugin-mode kebab-case. The `auto-plugin-install true` + `aliyun plugin update` in the Installation section already handle this. The plugin notice at the top of `aliyun cms --help` confirms it is active.
7. **AI-mode must be disabled** — Step 7 must be executed at every exit point so AI-mode does not leak into the next session.
8. **The LLM does not assemble HTML** — the LLM only produces JSON; template assembly is delegated to render_report.py. **A render failure is a Skill failure** — return the error reason and remediation to the user; never bypass the script and emit HTML by hand.

---

## References

| File | Purpose |
|------|---------|
| [references/inspection-commands.md](references/inspection-commands.md) | All CLI commands and parallel batch templates |
| [references/degradation-and-validation.md](references/degradation-and-validation.md) | Permission-fallback execution sequence + JSON pre-validation rules |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission list + custom policy + failure handling |
| [scripts/render_report.py](scripts/render_report.py) | HTML rendering script (stdlib only) |
| [scripts/requirements.txt](scripts/requirements.txt) | Canonical Python dependency declaration for `scripts/` |
