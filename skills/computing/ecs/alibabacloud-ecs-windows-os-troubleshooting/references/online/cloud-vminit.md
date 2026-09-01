# Cloud Vminit Diagnostics

## Function Description

Diagnoses Windows vminit service installation status, service enablement status, initialization log errors, and user-data execution failures. vminit is the Alibaba Cloud ECS instance initialization service, responsible for network configuration, password reset, disk expansion, user-data script execution, etc. Covers 4 known root causes. Covers stage P5 (Shell/user desktop, vminit part) of the boot/session stage model defined in SKILL.md.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Network not auto-configured after new instance creation, metadata not retrieved | Step 1 (vminit service status) |
| Network configuration lost after instance restart, password reset not effective | Step 1 (vminit service status) |
| VirtIO driver installation failed, registry access error, password setting failed, disk expansion failed | Step 2 (vminit initialization log) |
| Custom script not executed or errors after instance creation or restart | Step 1 (vminit service status) -> Step 2 (vminit initialization log) -> Step 3 (user-data interface) |

## Diagnostic Steps

### Step 1: vminit Service Status Check

**Data Collection**:

> Collection target: Obtain vminit service installation status, running status, startup type, and executable file path

**Analysis Approach**:

- PowerShell script: [cloud-vminit.ps1](references/online/scripts/cloud-vminit.ps1) Section Step 1

1. Check whether vminit service is installed:
   - Normal: Service exists
   - Abnormal: Get-CimInstance cannot find the service -> **Root cause**: vminit not installed, **Severity**: Critical
   - Explanation: vminit not installed means instance initialization functionality is missing, network configuration, password reset, disk expansion and other functions cannot work

2. Check whether vminit service can run:
   - Normal: Service status is Running or Stopped
   - Abnormal: Service exists but startup type is Disabled -> **Root cause**: vminit service cannot run, **Severity**: Critical

3. Check whether executable file exists (based on the `ExePath` / `Exists` fields from the collection output above):
   - Normal: `Exists = True`, `ExePath` points to a real existing vminit.exe
   - Abnormal: `Exists = False` (resolved `ExePath` path does not exist) -> **Root cause**: vminit service cannot run (executable file missing), **Severity**: Critical
   - Explanation: `Win32_Service.PathName` raw value e.g. `C:\ProgramData\aliyun\vminit\vminit.exe service`, includes command-line parameters, **must not** Test-Path directly, MUST first strip outer quotes / trailing parameters to keep only the `.exe` path before verification

### Step 2: vminit Initialization Log Check

**Data Collection**:

> Collection target: Read the complete content of the latest vminit log file, identify errors by rules during analysis phase

**Analysis Approach**:

- PowerShell script: [cloud-vminit.ps1](references/online/scripts/cloud-vminit.ps1) Section Step 2

1. Check whether log file exists:
   - Normal: Log file exists and has content
   - Abnormal: Outputs `No vminit log file found`, indicating vminit may have never run successfully

2. Identify known error keywords in log content (refer to Alibaba Cloud official documentation):
   - File and disk: `extend_disk_error` (disk expansion failed), `online_disk_error` (disk online failed), `import_disk_error` (dynamic disk import failed), `format_disk_error` (disk format failed), `no_system_disk` (no system disk or system disk corrupted)
   - Registry: `registry_access_error` (registry access error)
   - Driver: `install_virtio_error` (VirtIO installation failed), `disk_cannot_extend` (disk cannot expand), `disk_data_loss` (disk data loss), `netkvm_start_fail_onmoc` (old network card driver)
   - Management command: `unknown_operation` (unknown management command), `config_passwd_error` (password change failed), `start_assist_error` (cloud assistant startup failed), `config_ntp_error` (NTP configuration failed), `meta_server_error` (Meta Server connection failed)
   - Others: `sysprep_not_ready` (Sysprep not completed), `unknown_win_version` (unknown system version)
   - Userdata: Log contains `userdata`, `user_data` related error records (execution failed, timeout, cache exception)

   - Normal: No matching error keywords
   - Abnormal (non-userdata keyword matched) -> **Root cause**: vminit initialization log error, **Severity**: Warning (subcategorized by matched keyword)
   - Abnormal (userdata/user_data error context matched) -> **Root cause**: user-data script execution failed, **Severity**: Warning
   - Abnormal (log exists but no userdata/user_data records) -> **Root cause**: vminit did not trigger userdata execution, **Severity**: Warning
   - Common causes (userdata type): Cache not cleared after system disk replacement, script syntax error, missing dependency environment

### Step 3: user-data Interface Check

**Data Collection**:

> Collection target: Check whether MetaServer user-data interface returns content

**Analysis Approach**:

- PowerShell script: [cloud-vminit.ps1](references/online/scripts/cloud-vminit.ps1) Section Step 3

1. Check MetaServer user-data interface return:
   - Normal: HTTP 200 and Content-Length > 0, indicating user-data is configured
   - Abnormal (404 or empty content): User has not configured user-data, not a vminit issue
   - Abnormal (timeout or connection failure): MetaServer unreachable -> go to cloud-metaserver.md

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Chain successor | Log contains install_virtio_error | -> [cloud-driver.md](references/online/cloud-driver.md) (troubleshoot VirtIO driver installation issues) |
| Chain successor | Log contains meta_server_error | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (troubleshoot metadata service connectivity) |
| Chain successor | Log contains extend_disk_error | -> [storage-disk.md](references/online/storage-disk.md) (troubleshoot disk status) |
| Conditional jump | user-data interface timeout or connection failure | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (troubleshoot MetaServer reachability) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [cloud-vminit.md](references/online/fixes/cloud-vminit.md).
