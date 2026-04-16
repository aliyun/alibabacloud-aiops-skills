---
name: alibabacloud-ecs-gpu-diagnosis
description: >
  Diagnose Alibaba Cloud ECS GPU instances to detect GPU device status, driver issues, and hardware failures.
  Use this Skill when users report GPU instance anomalies, deep learning task failures, GPU not visible, or when troubleshooting GPU hardware issues.
  Supports automatic Alibaba Cloud CLI installation, diagnosis report creation, and polling for diagnosis results.
license: Apache-2.0
compatibility: >
  Requires Alibaba Cloud CLI (aliyun) installed and configured with AccessKey.
  Supported regions: cn-hangzhou, cn-shanghai, cn-beijing, cn-shenzhen, etc.
metadata:
  domain: aiops
  owner: ecs-team
  contact: ecs-agent@alibaba-inc.com
---

## Usage Instructions

Initiate diagnosis on a specified ECS GPU instance to detect GPU device status and output diagnosis results.

## Execution Constraints

- All steps MUST be executed in order; skipping steps is NOT permitted
- Each step MUST be verified as successful before proceeding to the next
- Inform the user of the current step being executed
- If any step fails, user confirmation MUST be obtained before continuing

### Prerequisites

1. **Check Alibaba Cloud CLI Environment**
   - Execute `which aliyun` or `aliyun --version` to check if CLI is installed
   - If not installed, inform the user that Alibaba Cloud CLI needs to be installed and provide installation guidance from `references/cli-installation.md`:
     - macOS: Homebrew installation or manual installation (Intel/Apple Silicon)
     - Linux: Download installation package for corresponding architecture (x86_64/ARM64)
     - Windows: Download installation package and configure PATH, or use PowerShell installation
   - After installation, run `aliyun version` to confirm version >= 3.0.299
   - Confirm CLI is configured with AccessKey: `aliyun configure`
   - **Permission Reminder**: Remind the user that the current RAM user needs the permissions to execute GPU diagnosis from `references/ram-policies.md` :

2. **Obtain Required Parameters**
   - Check if `INSTANCE_ID` is provided (ECS instance ID, format MUST match this regular expression ^i-[a-z0-9]{20}$ )
   - Check if `REGION_ID` is provided (region ID, like cn-shanghai)
   - If either parameter is missing, ask the user:
     - "Please provide the ECS instance ID to diagnose (format: i-bp1xxxxx)"
     - "Please provide the region ID where the instance is located (e.g., cn-shanghai, cn-hangzhou)"

3. **Validate Parameters**
   - **Validate INSTANCE_ID format**: Check if `INSTANCE_ID` matches the regex pattern `^i-[a-z0-9]{20}$`
     - If validation fails, inform the user: "Invalid instance ID format. Instance ID must match the pattern ^i-[a-z0-9]{20}$"
   - **Validate REGION_ID**: Query available regions using DescribeRegions API to verify the region is valid:
     ```bash
     aliyun ecs DescribeRegions --user-agent AlibabaCloud-Agent-Skills
     ```
     - Extract the `Regions.Region[].RegionId` list from the response
     - Check if the provided `REGION_ID` exists in the list
     - If region is invalid, inform the user: "Invalid region ID. Please provide a valid region ID from the available regions list."

4. **Check Instance Operating System Type**
   - Before creating a diagnosis report, query instance information to confirm the OS type:
     ```bash
     aliyun ecs DescribeInstances  --user-agent AlibabaCloud-Agent-Skills --RegionId ${REGION_ID} --InstanceIds '["${INSTANCE_ID}"]'
     ```
   - Extract the `Instances.Instance[0].OSType` field from the response
   - **If `OSType` is "linux"**: Continue with the subsequent diagnosis process
   - **If `OSType` is not "linux"**: Notify the user and terminate the process:
     ```
     The current instance ${INSTANCE_ID} has operating system ${OSType}.
     This Skill currently only supports Linux operating system instances, other operating systems are not supported.
     No further diagnosis process is needed.
     ```

### Execute Diagnosis

1. **Create Diagnostic Report**

   Use the following command to initiate GPU diagnosis:

   ```bash
   aliyun ecs CreateDiagnosticReport \
     --user-agent AlibabaCloud-Agent-Skills \
     --RegionId '${REGION_ID}' \
     --ResourceId '${INSTANCE_ID}' \
     --MetricSetId 'dms-instanceGPUdevice' \
     --output cols=ReportId
   ```

   Extract `ReportId` from the output and save it for subsequent queries.

2. **Poll Diagnostic Results**

   Use the following command to query the diagnosis report status:

   ```bash
   aliyun ecs DescribeDiagnosticReports \
     --user-agent AlibabaCloud-Agent-Skills \
     --RegionId '${REGION_ID}' \
     --ReportIds.1 '${REPORT_ID}'
   ```

   Handle based on the returned `Status` field:

   - **Status = "Finished"**: Diagnosis complete, parse the `Issues` field content
     - If `Issues` is empty or does not exist, report "GPU diagnosis normal, no anomalies detected"
     - If `Issues` contains content, extract each Issue's `IssueId`, `MetricId`, `Severity`, and `MetricCategory`, and output diagnosis results and recommended actions according to the IssueId mapping table below
   - **Status = "InProgress"**: Diagnosis in progress, wait 5 seconds before querying again
   - **Status = "Failed"**: Diagnosis failed, report the failure status to the user

   Set timeout mechanism: poll up to 60 times (approximately 5 minutes), if still not complete, prompt the user to query manually later.

### Output Description

After diagnosis is complete, the output should include:
- Instance ID and region
- Diagnostic report ID
- GPU device status summary
- Discovered Issues (if any)
- Recommended remediation measures (inferred from Issues content)

### Diagnostic Result Analysis

The `Issues` returned in the diagnosis report is an array, where each Issue contains `IssueId`, `MetricId`, `Severity`, and `MetricCategory` fields. Output diagnosis description and handling measures according to the IssueId mapping table below:

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

**Output Format Example**:

```
Diagnosis Complete! Instance: i-bp1xxxxxxxxx (cn-shanghai)
Report ID: dr-xxxxxxxx

1 anomaly found:

[1] GuestOS.GPU.DriverNotInstalled
    Severity: Warn
    Diagnostic Description: Detect GPU driver installation status
    Handling Measures: User needs to install driver

Diagnostic Recommendations:
- Please install the corresponding version of NVIDIA GPU driver
- Installation Guide: https://help.aliyun.com/document_detail/108460.html
```

**Special Reminder**: When the exception handling measure is "O&M notification will be sent to user", append the following reminder to the output:
```
⚠️ Important Reminder:
- Alibaba Cloud will send you O&M event notifications
- Please go to the ECS console to view event details
- Pay attention to whether you receive O&M events and handle them as required
```

If `Issues` is an empty array or does not exist, output:
```
Diagnosis Complete! Instance: i-bp1xxxxxxxxx (cn-shanghai)
Report ID: dr-xxxxxxxx

GPU diagnosis normal, no anomalies detected.
```

### Edge Case Handling

- **Instance does not exist**: CLI will return an error, capture and inform the user that the instance ID may be incorrect
- **Region error**: Prompt user to confirm the region where the instance is located
- **Non-GPU specification**: If the instance is not a GPU specification, diagnosis may have no results, prompt user to confirm instance type
- **Insufficient permissions**: If permission error is returned, prompt user to check AccessKey permissions
- **Network timeout**: Set command execution timeout (recommended 30 seconds), retry after timeout or prompt user to check network

### Example Workflow

```
User: Help me diagnose this GPU server i-bp1xxxxxxxxx

Agent:
1. Check CLI is installed
2. Ask for region (user did not provide)
3. User replies: cn-shanghai
4. Check instance OS type is Linux
5. Execute CreateDiagnosticReport, get ReportId: dr-xxxxxxxx
6. Poll DescribeDiagnosticReports
7. Status=InProgress, wait 5 seconds...
8. Query again, Status=Finished
9. Output Issues content to user
```
