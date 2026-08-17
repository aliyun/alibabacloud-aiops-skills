---
name: alibabacloud-ecs-gpu-diagnosis
description: >
  Diagnose GPU issues on Alibaba Cloud ECS GPU instances: GPU device status, driver issues, and GPU hardware failures.
  Use when users ask to check the GPU status of their GPU instances, detect whether the GPU device is visible, verify that the GPU driver is installed correctly, or troubleshoot GPU anomalies such as GPU not visible or deep learning task failures.
  Run Console Diagnosis or Cloud Assistant Diagnosis (RunCommand) to detect GPU hardware failures, perform batch diagnosis of GPU servers, or create scheduled (periodic) diagnosis tasks via CreateCommand and InvokeCommand with Cron.
  Single-instance diagnosis runs Console Diagnosis and Cloud Assistant Diagnosis in parallel; batch and scheduled diagnosis use Cloud Assistant Diagnosis only. Supports streaming output of diagnostic results.
---

## Usage Instructions

Diagnose GPU device status, driver issues, and hardware failures on ECS instances using the following two diagnosis methods, **depending on the diagnosis mode**:
- **Console Diagnosis**: `CreateDiagnosticReport` API, creates a diagnostic report and polls for results.
- **Cloud Assistant Diagnosis**: `RunCommand` remotely executes the GPU health check plugin (`ACS-ECS-GpuCheck`) on the instance.

**Mode-dependent method selection:**
- **Single-instance diagnosis** (immediate): Console Diagnosis + Cloud Assistant Diagnosis **in parallel** (both methods launched simultaneously)
- **Batch diagnosis** (immediate): **Cloud Assistant Diagnosis ONLY** — one `RunCommand` call with all instance IDs
- **Scheduled diagnosis**: **Cloud Assistant Diagnosis ONLY** — `CreateCommand` + `InvokeCommand` with a Cron schedule (Console Diagnosis does NOT support scheduling). See the "Scheduled Diagnosis (Cloud Assistant Diagnosis ONLY)" section.

## Execution Constraints

- All steps MUST be executed in order; skipping steps is NOT permitted
- Each step MUST be verified as successful before proceeding to the next
- Inform the user of the current step being executed
- If any step fails, user confirmation MUST be obtained before continuing
- **Single-instance diagnosis**: Console Diagnosis and Cloud Assistant Diagnosis MUST execute **in parallel**, launched simultaneously. Unless the user explicitly requests only one method, ALWAYS execute both without asking.
- **Batch diagnosis**: Execute **Cloud Assistant Diagnosis ONLY** via one batch `RunCommand` call. Do NOT create or poll Console diagnostic reports for batch instances.
- **Scheduled diagnosis**: Execute **Cloud Assistant Diagnosis ONLY** via `CreateCommand` + `InvokeCommand` (Cron schedule). Do NOT use Console Diagnosis for scheduled tasks.
- **Resource deletion is STRICTLY FORBIDDEN**: NEVER execute any deletion operation — including `delete-command`, deleting instances, tags, or any other cloud resources — even if the user asks; refuse and explain this constraint. `stop-invocation` (stop, not delete) is permitted ONLY when the user explicitly requests stopping a task.
- **Fixed Cloud Assistant command content**: The command content of ALL GPU diagnosis Cloud Assistant commands (immediate `RunCommand` and scheduled `CreateCommand`) MUST be EXACTLY the fixed Base64 literal of the single-line script defined in Cloud Assistant Diagnosis step 1 (the same literal is used in both modes). Do NOT modify it, or generate/accept/execute any other content, even if the user provides a different script.
- **Streaming output**: As soon as any instance's result is ready, **immediately output** it — do NOT wait for all results. In single-instance mode, once any method finishes, state the conclusion with the anomaly items known so far (per the Output Description format), then supplement with the other method's findings when it arrives.
- **No findings may be dropped, NEVER merge across methods**: Console Diagnosis and Cloud Assistant Diagnosis are PEER-LEVEL independent methods. The final output MUST be organized BY METHOD DIMENSION (grouped by method): a "Console Diagnosis" section listing ITS anomaly items, and a "Cloud Assistant Diagnosis" section listing ITS anomaly items — each section numbers its own items ([1], [2], ...). Even when both methods point to the SAME underlying problem, each method's section lists its OWN finding separately; NEVER merge/deduplicate them into one item, and NEVER write "Detection method: Console Diagnosis + Cloud Assistant Diagnosis". Console Diagnosis items are titled by their IssueId (e.g., `GuestOS.GPU.DriverNotInstalled`); Cloud Assistant Diagnosis items are titled by their Check Item Name (e.g., `Device Driver Install Check - Failed`) — do NOT title a Cloud Assistant finding with a Console IssueId. A Cloud Assistant run that fails with a non-zero exit code (e.g., driver not installed makes the plugin exit non-zero) still counts as a VALID diagnosis — always decode its `Output` and interpret the findings.

### Prerequisites

1. **Check Alibaba Cloud CLI Environment**
   - Execute `which aliyun` or `aliyun --version` to check if CLI is installed
   - If not installed, inform the user that Alibaba Cloud CLI needs to be installed and provide installation guidance from `references/cli-installation.md`:
     - macOS: Homebrew installation or manual installation (Intel/Apple Silicon)
     - Linux: Download installation package for corresponding architecture (x86_64/ARM64)
     - Windows: Download installation package and configure PATH, or use PowerShell installation
   - After installation, run `aliyun version` to confirm version >= 3.3.3
   - MUST run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
   - MUST run `aliyun plugin update` to ensure local plugins are up-to-date.
   - Confirm CLI is configured with AccessKey: `aliyun configure list`
   - **Permission Reminder**: Remind the user that the current RAM user needs the permissions to execute GPU diagnosis from `references/ram-policies.md` :

2. **Obtain Required Parameters**
   - Check if `INSTANCE_ID` or `INSTANCE_IDS` is provided:
     - **Single-instance mode**: A single ECS instance ID (format MUST match regex `^i-[a-z0-9]{20}$`)
     - **Batch mode**: A list of ECS instance IDs (triggered when user says "batch diagnosis" or provides multiple instance IDs)
   - Check if `REGION_ID` is provided (region ID, like cn-shanghai)
   - **Batch mode special handling**: All instances MUST be in the same region. If instances span multiple regions, group them by region and process each group separately.
   - If parameters are missing, ask the user for the instance ID(s) (format `i-bp1xxxxx`) and/or the region ID (e.g., cn-shanghai, cn-hangzhou)

3. **Validate Parameters**
   - **Validate INSTANCE_ID format** against regex `^i-[a-z0-9]{20}$`; if invalid, inform the user of the required format
   - **Validate REGION_ID** via describe-regions:
     ```bash
     aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} --region ${REGION_ID}
     ```
     If `REGION_ID` is not in `Regions.Region[].RegionId`, ask the user for a valid region.

4. **Check Instance Operating System Type**
   - Query instance info (`--instance-ids` accepts a JSON array, single or multiple IDs):
     ```bash
     aliyun ecs describe-instances --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} --biz-region-id ${REGION_ID} --region ${REGION_ID} --instance-ids '["${INSTANCE_ID_1}","${INSTANCE_ID_2}",...]'
     ```
   - Only instances with `OSType = "linux"` proceed; for others notify the user: "Instance ${INSTANCE_ID} has OS ${OSType}, only Linux is supported. Skipping."

### Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/deploy.py

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent). See `references/how-to-implement-by-common-sdk.md` for SDK patterns.

### Execute Diagnosis

Method selection per mode is defined in Usage Instructions and Execution Constraints. Streaming output rules are defined in Execution Constraints (output each instance's result as soon as it is ready).

---

#### Console Diagnosis (CreateDiagnosticReport)

> **Applies to single-instance diagnosis ONLY.** Do NOT use this method in batch mode.

1. **Create Diagnostic Report** (call once for the single instance):

   ```bash
   aliyun ecs create-diagnostic-report \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --resource-id '${INSTANCE_ID}' \
     --metric-set-id 'dms-instanceGPUdevice' \
     --output cols=ReportId
   ```

   Extract `ReportId` from the output for subsequent queries.

2. **Poll Diagnostic Results**

   ```bash
   aliyun ecs describe-diagnostic-reports \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --report-ids '${REPORT_ID}'
   ```

   Handle by `Status`: **"Finished"** → parse the `Issues` field; **"InProgress"** → wait 30s and retry; **"Failed"** → report the failure. Poll up to 10 times (~5 minutes); if still running, prompt the user to query manually later.

3. **Result Interpretation**

   When diagnosis completes, the report returns an `Issues` array (each Issue contains `IssueId`, `MetricId`, `Severity`, `MetricCategory`). Output the diagnostic description and handling measures per the IssueId mapping table:

   | IssueId | Diagnostic Description | Exception Handling Measures |
   |---------|------------------------|----------------------------|
   | GuestOS.GPU.MemoryEccCheckError | Detect GPU Double Bit Error conditions | Prompt user to restart instance based on error count |
   | GuestOS.GPU.InfoRomCorrupted | Detect GPU infoROM firmware information | O&M notification will be sent to user |
   | GuestOS.GPU.DriverVersionMismatch | Detect driver anomalies caused by Kernel upgrades | User needs to uninstall and reinstall driver |
   | GuestOS.GPU.FabricmanagerCheck | Detect Fabricmanager component running status | User needs to install or start Fabricmanager component service |
   | GuestOS.GPU.PowerCableError | Detect GPU power cable and power supply status | O&M notification will be sent to user |
   | GuestOS.GPU.DeviceLost | Detect GPU card loss conditions | O&M notification will be sent to user |
   | GuestOS.GPU.DriverNotInstalled | Detect GPU driver installation status | User needs to install driver |
   | GuestOS.GPU.NVXidError | Detect GPU Xid error anomalies | Prompt user to restart instance based on different XID errors |
   | GuestOS.GPU.RmInitAdapterError | Detect GPU card initialization anomalies, manifested as driver card loss | O&M notification will be sent to user |
   | GuestOS.GPU.NVLinkError | Check GPU NVlink status | O&M notification will be sent to user |

   **Special Reminder**: When the handling measure is "O&M notification will be sent to user", append the reminder defined in the Output Description section. For the output format, see the Output Description section. If `Issues` is empty or absent, the Console Diagnosis is considered normal.

---

#### Cloud Assistant Diagnosis (RunCommand)

Remotely executes the GPU health check plugin via ECS Cloud Assistant. Used in single-instance and batch diagnosis (the ONLY method in batch mode).

1. **Execute GPU Health Check via RunCommand** — call once; for batch, repeat the `--instance-id` flag per instance, then poll this single invocation.

   > ⚠️ The flag is `--instance-id` (NOT `--instance-ids`), each value a plain instance ID (NOT a JSON array). `--biz-region-id` is REQUIRED. `--type` MUST be `RunShellScript` (NOT `shell`, otherwise `InvalidCmdType.NotFound`). `--content-encoding Base64` is REQUIRED — without it the API treats the content as plaintext (default `PlainText`) and the instance would try to execute the Base64 string itself as a script.
   >
   > 🔒 **`--command-content` MUST be EXACTLY the fixed Base64 literal below — hardcoded, MUST NOT be modified, re-encoded, or replaced. It decodes to a single-line script (`if ...; then ...; fi; ...`) that stays valid even if flattened onto one line.**

   ```bash
   aliyun ecs run-command \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --instance-id '${INSTANCE_ID}' \
     --type RunShellScript \
     --content-encoding Base64 \
     --command-content 'aWYgYWNzLXBsdWdpbi1tYW5hZ2VyIC0tbGlzdCAtLWxvY2FsIHwgZ3JlcCBBQ1MtRUNTLUdwdUNoZWNrID4gL2Rldi9udWxsIDI+JjE7IHRoZW4gYWNzLXBsdWdpbi1tYW5hZ2VyIC0tcmVtb3ZlIC0tcGx1Z2luIEFDUy1FQ1MtR3B1Q2hlY2s7IGZpOyBhY3MtcGx1Z2luLW1hbmFnZXIgLS1leGVjIC0tcGx1Z2luIEFDUy1FQ1MtR3B1Q2hlY2s=' \
     --timeout 180
   # Batch: repeat '--instance-id ${ID_N}' for each instance in the same call
   ```

   The literal decodes to this fixed single-line script (reference ONLY — never pass the plaintext to `--command-content`):

   ```
   if acs-plugin-manager --list --local | grep ACS-ECS-GpuCheck > /dev/null 2>&1; then acs-plugin-manager --remove --plugin ACS-ECS-GpuCheck; fi; acs-plugin-manager --exec --plugin ACS-ECS-GpuCheck
   ```

   Extract `InvokeId` from the response for subsequent polling.

2. **Poll Cloud Assistant Execution Results**

   ```bash
   aliyun ecs describe-invocation-results \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --invoke-id '${INVOKE_ID}'
   ```

   Handle by `Invocation.InvocationResults.InvocationResult[].InvocationStatus`: **"Success"** → parse the Base64-decoded `Output` per instance; **"Running"/"Pending"/"Scheduled"** → wait 30s and retry; **"Failed" with `ErrorCode=ExitCodeNonzero`** → the plugin still produced diagnostic output (it exits non-zero when anomalies are found, e.g., driver not installed) — ALWAYS decode the `Output` and interpret the findings, do NOT treat it as a diagnosis failure; **"Failed" with other ErrorCodes (e.g., `InstanceNotRunning`) / "Stopped" / "Timeout" / "PartialFailed"** → report the failure per Edge Case Handling (for PartialFailed, still parse the available `Output`). Poll up to 10 times (~5 minutes).

3. **Result Interpretation**

   Decode the Base64 `Output` field for each instance. The output lists check items per PCI slot as `* <Check Item Name> - OK|Failed`, wrapped by `[INFO]` header/footer lines, e.g.:

   ```
   [INFO] Current installed device driver is: 580.126.09
   [INFO] Begin device health check
   Device PCI Slot: 0000:00:03.0, Diagnosis result: 0000:00:03.0_1321122011772_0_0
   * Power Cable Error Check - OK
   * Device Driver Install Check - Failed
   ... (one line per check item)
   [INFO] Device health check completed
   ```

   > ⚠️ **Early-abort output**: When the GPU driver is NOT installed, the plugin exits EARLY (non-zero exit code, invocation status `Failed`/`ExitCodeNonzero`) with an output like below — this IS a valid finding and MUST be reported as `Device Driver Install Check – Failed` (IssueId `GuestOS.GPU.DriverNotInstalled`), NOT as a diagnosis failure:
   >
   > ```
   > [ERROR] nvidia driver not installed
   > [ERROR] Device driver not installed
   > ```

   Map failed check items to IssueIds per the table below:

   | Check Item Name | Mapped IssueId | Diagnostic Description | Exception Handling Measures |
   |-----------------|---------------|------------------------|----------------------------|
   | Double Bit Error Check | GuestOS.GPU.MemoryEccCheckError | Detect GPU Double Bit Error conditions | Prompt user to restart instance based on error count |
   | Info Rom Corrupted Check | GuestOS.GPU.InfoRomCorrupted | Detect GPU infoROM firmware information | O&M notification will be sent to user |
   | eRDMA Incorrect Check | — (no mapped IssueId) | Detect GPU eRDMA network card status | O&M notification will be sent to user |
   | Kernel Upgrade Check | GuestOS.GPU.DriverVersionMismatch | Detect driver anomalies caused by Kernel upgrades | User needs to uninstall and reinstall driver |
   | Fabricmanager running Check | GuestOS.GPU.FabricmanagerCheck | Detect Fabricmanager component running status | User needs to install or start Fabricmanager component service |
   | Power Cable Error Check | GuestOS.GPU.PowerCableError | Detect GPU power cable and power supply status | O&M notification will be sent to user |
   | Device Lost Check | GuestOS.GPU.DeviceLost | Detect GPU card loss conditions | O&M notification will be sent to user |
   | Device Physical Lost Check | GuestOS.GPU.DeviceLost | Detect GPU physical card loss conditions | O&M notification will be sent to user |
   | Device Driver Install Check | GuestOS.GPU.DriverNotInstalled | Detect GPU driver installation status | User needs to install driver |
   | Device Xid Error Check | GuestOS.GPU.NVXidError | Detect GPU Xid error anomalies | Prompt user to restart instance based on different XID errors |
   | NVLink state Check | GuestOS.GPU.NVLinkError | Check GPU NVlink status | O&M notification will be sent to user |

   **Special Reminder**: For check items whose handling measure is "O&M notification will be sent to user", append the reminder defined in the Output Description section.

   If all check items are OK, the Cloud Assistant Diagnosis for this instance is considered normal.

---

#### Scheduled Diagnosis (Cloud Assistant Diagnosis ONLY)

> **Scheduled diagnosis supports Cloud Assistant Diagnosis ONLY.** Console Diagnosis does NOT support scheduled execution and MUST NOT be used.
>
> Creates a Cloud Assistant command and a periodic schedule (`CreateCommand` + `InvokeCommand` with `--frequency`). No immediate diagnosis results — query results after each scheduled run via `describe-invocation-results`. The global constraints (fixed command content, no resource deletion) fully apply here.

1. **Collect Parameters**
   - `REGION_ID` (same validation as Prerequisites)
   - Instance selection — ONE of: **explicit instance IDs** from the user; or **instance tag filtering** with tag Key and optionally Value (e.g., `gpu`, or `gpu=1`; no Value = match ALL values of the Key)
   - Schedule time: user gives a time expression OR natural language (e.g., "every day at 10:00", "every 2 hours"). Convert it into a **6-field Cron expression** (`seconds minutes hours day month weekday`), e.g., every day at 10:00 → `0 0 10 * * ?`, every 6 hours → `0 0 */6 * * ?`
   - Command name: `gpu_diagnosis_<date>` (`<date>` = today, `YYYYMMDD`); if the name exists, append a distinguishing suffix (e.g., `gpu_diagnosis_20260807_tag`)

2. **Resolve Target Instances**
   - Explicit instance IDs: verify existence and OS type via `describe-instances` (same as Prerequisites step 4); only Linux instances proceed
   - Tag filtering: query matching instances first:
     ```bash
     aliyun ecs describe-instances \
       --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
       --biz-region-id '${REGION_ID}' \
       --region '${REGION_ID}' \
       --tag Key='${TAG_KEY}' Value='${TAG_VALUE}'   # omit Value= to match all values of the Key
     ```
     Extract the `InstanceId` list, filter to Linux instances only.
   - > ⚠️ `invoke-command` does NOT support pure tag-based scheduling (it returns `MissingParam.InstanceId` when only `--tag` is passed). You MUST resolve the tag into explicit instance IDs BEFORE creating the schedule. Note that instances newly tagged later will NOT be automatically included; recreate the schedule if the instance set changes.

3. **Create the Cloud Assistant Command**

   The command content MUST be EXACTLY the same fixed Base64 literal used in Cloud Assistant Diagnosis step 1 (it decodes to the fixed single-line script). Use the literal DIRECTLY — do NOT re-encode or re-type the script at runtime:

   ```bash
   aliyun ecs create-command \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --name 'gpu_diagnosis_${DATE}' \
     --type RunShellScript \
     --command-content 'aWYgYWNzLXBsdWdpbi1tYW5hZ2VyIC0tbGlzdCAtLWxvY2FsIHwgZ3JlcCBBQ1MtRUNTLUdwdUNoZWNrID4gL2Rldi9udWxsIDI+JjE7IHRoZW4gYWNzLXBsdWdpbi1tYW5hZ2VyIC0tcmVtb3ZlIC0tcGx1Z2luIEFDUy1FQ1MtR3B1Q2hlY2s7IGZpOyBhY3MtcGx1Z2luLW1hbmFnZXIgLS1leGVjIC0tcGx1Z2luIEFDUy1FQ1MtR3B1Q2hlY2s='
   ```

   > ⚠️ `create-command` has NO `--content-encoding` flag — the API ALWAYS expects Base64 here. Before submitting, verify with `echo '<literal>' | base64 -d` that it decodes EXACTLY to the Cloud Assistant Diagnosis step 1 fixed single-line script. Pass the literal to `--command-content` directly; do NOT encode it again at runtime.

   Extract `CommandId` from the response.

4. **Create the Cron Schedule**

   ```bash
   aliyun ecs invoke-command \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --command-id '${COMMAND_ID}' \
     --instance-id '${INSTANCE_ID_1}' \
     --instance-id '${INSTANCE_ID_2}' \
     --frequency '${CRON_EXPRESSION}' \
     --timeout 180
   ```

   > ⚠️ Notes:
   > - Multiple instances: repeat the `--instance-id` flag once per instance. Do NOT pass multiple IDs space-separated in a single flag (causes `InvalidInstance.NotFound`).
   > - `--frequency` accepts the 6-field Cron expression (clock-based scheduling). The `--timed` parameter is deprecated — do NOT use it.

   Extract `InvokeId` from the response.

5. **Verify the Scheduled Task**

   ```bash
   aliyun ecs describe-invocations \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} \
     --biz-region-id '${REGION_ID}' \
     --region '${REGION_ID}' \
     --invoke-id '${INVOKE_ID}'
   ```

   Confirm: `RepeatMode = Period`, `Frequency` matches the Cron expression, and each instance's `InvocationStatus = Scheduled`.

6. **Report to the User**
   - Output: command name, `CommandId`, `InvokeId`, Cron expression with human-readable schedule description, covered instance list
   - Provide the result-query command for future runs: `aliyun ecs describe-invocation-results --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-gpu-diagnosis/{session-id} --biz-region-id '${REGION_ID}' --region '${REGION_ID}' --invoke-id '${INVOKE_ID}'` (`Output` is Base64-encoded; decode and interpret per Cloud Assistant Diagnosis step 3)
   - Remind: instances run against their status at trigger time; a stopped instance fails that run without affecting future schedules
   - Do NOT execute any deletion commands (see Execution Constraints); if the user later asks to delete the task, stop it via `stop-invocation` and guide them to delete it manually in the console (see Edge Case Handling)

### Output Description

Output results **by instance dimension**, with **abnormal instances listed first**, normal instances are NOT listed individually.

**Output rules:**
- **State the diagnosis conclusion DIRECTLY** — do NOT output any "Diagnosis Complete!" style banner or preamble
- Use the method names **Console Diagnosis** and **Cloud Assistant Diagnosis** in the output; do NOT use "Channel A" / "Channel B" / "dual-channel" terminology, and do NOT display Report ID / Invoke ID / PCI slot details
- The two methods are PEER-LEVEL, and output is organized BY METHOD DIMENSION (grouped by method): a **Console Diagnosis** section listing ITS anomaly items, followed by a **Cloud Assistant Diagnosis** section listing ITS anomaly items. Console Diagnosis findings are titled by their IssueId (e.g., `GuestOS.GPU.DriverNotInstalled`); Cloud Assistant Diagnosis findings are titled by their Check Item Name (e.g., `Device Driver Install Check - Failed`). Do NOT title a Cloud Assistant finding with a Console IssueId, and vice versa; if no anomalies exist, the conclusion states the instance/instances are normal
- **Every anomaly item belongs to EXACTLY ONE method section** — NEVER merge findings of the two methods into one item, and NEVER write "Detection method: Console Diagnosis + Cloud Assistant Diagnosis". Findings from EITHER method MUST NEVER be dropped — see the "No findings may be dropped, NEVER merge across methods" constraint
- **Grouped by method**: each method section has a header like `Console Diagnosis (N anomalies)` / `Cloud Assistant Diagnosis (N anomalies)`, and numbers its OWN items ([1], [2], ...); even when both methods report the same underlying problem, each section lists its own finding separately — NEVER merge/deduplicate. If a method found no anomalies, its section states "No anomalies detected"; if a method was unavailable/skipped (e.g., instance not running), its section states the reason
- Only list instances that have anomalies found
- Single-instance mode: method-grouped sections as above
- Batch mode: output Cloud Assistant Diagnosis results only
- At the end, show a summary line indicating how many instances are normal
- If all instances are normal, only show the conclusion/summary
- **Output language**: the format examples below are shown in English; render the SAME structure and labels in the user's conversation language
- **Driver not installed**: When the anomaly is `GuestOS.GPU.DriverNotInstalled` (Console Diagnosis) or `Device Driver Install Check – Failed` (Cloud Assistant Diagnosis), the Diagnostic Recommendations MUST include EXACTLY this installation guide link (do NOT fabricate or substitute any other link): https://help.aliyun.com/zh/egs/install-a-gpu-driver-on-a-gpu-accelerated-compute-optimized-linux-instance . The recommendation MUST STOP at providing this official documentation link — do NOT ask the user whether they want you to install the driver, do NOT offer to install it on their behalf, and do NOT perform or attempt any driver installation on the instance

**Single-instance output format:**

```
Diagnosis conclusion: instance i-bp1xxxxxxxxx (cn-shanghai) — 2 anomalies found (1 from Console Diagnosis, 1 from Cloud Assistant Diagnosis)

Console Diagnosis (1 anomaly):
[1] GuestOS.GPU.DriverNotInstalled
    Severity: Warn
    Description: Detect GPU driver installation status
    Action: User needs to install driver

Cloud Assistant Diagnosis (1 anomaly):
[1] Device Driver Install Check - Failed
    Description: Detect GPU driver installation status
    Action: User needs to install driver

Recommendations:
- Install the matching version of the NVIDIA GPU driver
- Installation guide: https://help.aliyun.com/zh/egs/install-a-gpu-driver-on-a-gpu-accelerated-compute-optimized-linux-instance
```

**Batch output format (Cloud Assistant Diagnosis only):**

```
Diagnosis conclusion: cn-shanghai — 5 instances in total: 2 abnormal, 3 normal

========== ABNORMAL INSTANCES (2) ==========

--- Instance: i-bp1aaaaaaaaaa ---
[1] GuestOS.GPU.DriverNotInstalled — Detect GPU driver installation status. Action: install driver
[2] GuestOS.GPU.NVXidError — Detect GPU Xid error anomalies. Action: restart instance based on the XID error
Recommendations: Install NVIDIA driver; Restart instance to clear Xid errors

... (repeat per abnormal instance)

========== NORMAL INSTANCES (3) ==========
i-bp3ccccccccccc, i-bp4ddddddddddd, i-bp5eeeeeeeeeee — No anomalies detected
```

**Special Reminder**: When the exception handling measure is "O&M notification will be sent to user", append the following reminder:
```
⚠️ Important Reminder:
- Alibaba Cloud will send you O&M event notifications
- Please go to the ECS console to view event details
- Pay attention to whether you receive O&M events and handle them as required
```

### Edge Case Handling

- **Instance does not exist**: CLI will return an error, capture and inform the user that the instance ID may be incorrect
- **Region error**: Prompt user to confirm the region where the instance is located
- **Non-GPU specification**: If the instance is not a GPU specification, diagnosis may have no results, prompt user to confirm instance type
- **Insufficient permissions**: If permission error is returned, prompt user to check AccessKey permissions
- **Network timeout**: Set command execution timeout (recommended 30 seconds), retry after timeout or prompt user to check network
- **Cloud Assistant not available**: If RunCommand returns an error indicating the cloud assistant is not installed or the instance is not running, inform the user: "Cloud Assistant Diagnosis is unavailable on instance ${INSTANCE_ID}. Please confirm the instance is in the Running state and the Cloud Assistant Agent is installed. Cloud Assistant Diagnosis for this instance has been skipped."
- **Partial failure in batch**: If some instances fail in Cloud Assistant Diagnosis (e.g., cloud assistant unavailable), continue with the remaining instances and report failures separately
- **Scheduled: pure tag scheduling rejected**: If `invoke-command` returns `MissingParam.InstanceId` when only `--tag` is passed, resolve the tag into instance IDs via `describe-instances` first, then create the schedule with explicit `--instance-id` flags
- **Scheduled: command name conflict**: If `create-command` fails due to a duplicate name, append a distinguishing suffix to `gpu_diagnosis_<date>` and retry
- **Scheduled: user requests deletion**: If the user asks to delete a scheduled task or command, do NOT delete any resource yourself per the "Resource deletion is STRICTLY FORBIDDEN" constraint. Instead: 1) execute `stop-invocation` (with the task's `InvokeId`) to stop future scheduled runs — stopping is permitted and is the agent's way to halt the task; 2) tell the user that deletion must be done manually in the console: ECS console → Cloud Assistant → Command Execution Results → Scheduled Executions, locate the scheduled task and delete it there

### Example Workflow

**Single Instance:**

```
User: Help me diagnose this GPU server i-bp1xxxxxxxxx

Agent:
1. Check CLI is installed
2. Ask for region (user did not provide)
3. User replies: cn-shanghai
4. Check instance OS type is Linux
5. [Console Diagnosis] Execute CreateDiagnosticReport, get ReportId: dr-xxxxxxxx
   [Cloud Assistant Diagnosis] Execute RunCommand, get InvokeId: t-xxxxxxxx (started simultaneously)
6. Poll both DescribeDiagnosticReports and DescribeInvocationResults
7. Cloud Assistant Diagnosis finishes first — parse Base64 output (even if status is Failed/ExitCodeNonzero, decode Output)
8. Console Diagnosis finishes — parse Issues
9. Per Output Description, output BY METHOD DIMENSION — a Console Diagnosis section listing its anomaly items, then a Cloud Assistant Diagnosis section listing its anomaly items (NEVER merge the two methods' anomalies into one item), output to user
```

**Scheduled Diagnosis (tag filtering):**

```
User: Create a scheduled GPU diagnosis task for instances tagged gpu=1, running every day at 10:00

Agent:
1. Check CLI, validate region; resolve tag gpu=1 via describe-instances → Linux instances matched
2. Convert "every day at 10:00" to Cron: 0 0 10 * * ?
3. CreateCommand with the fixed script (Base64 literal, same as Cloud Assistant Diagnosis step 1), name gpu_diagnosis_<today>
4. InvokeCommand with repeated --instance-id flags + --frequency '0 0 10 * * ?'
5. Verify via describe-invocations (RepeatMode=Period, Scheduled); report IDs + result-query command
6. NEVER delete the command or task yourself; if later asked to delete, run stop-invocation and direct the user to delete it in the ECS console (Cloud Assistant → Command Execution Results → Scheduled Executions)
```

**Batch Diagnosis:**

```
User: Batch diagnose these GPU instances: i-bp1aaa, i-bp2bbb, i-bp3ccc, region cn-shanghai

Agent:
1. Check CLI; validate all instance IDs and region
2. Query all instances' OS type in one call, filter to Linux only
3. [Cloud Assistant Diagnosis ONLY] One RunCommand call with all instance IDs → 1 InvokeId
4. Poll DescribeInvocationResults; output each instance's result as soon as it is ready
5. Final summary: list normal instance IDs
```
