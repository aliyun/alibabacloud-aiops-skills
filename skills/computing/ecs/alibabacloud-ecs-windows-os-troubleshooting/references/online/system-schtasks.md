# Task Scheduler Diagnostics

## Overview

Diagnoses the Windows Task Scheduler service and its related task execution issues. Covers Task Scheduler service status, task startup failures, tasks not running as expected, invalid credentials, trigger configuration errors, missing dependency files, task corruption and cache anomalies.

**Input**: User problem description (required), task name/error code/event ID (optional, used to narrow down investigation scope)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| All scheduled tasks not executing | Step 1 (Task Scheduler service status) -> Step 8 (Task corruption and cache repair) |
| Specific task startup failure (Event ID 101) | Step 2 (Task history log) -> Step 4 (Task credential check) -> Step 6 (Dependency program path) |
| Task not running at expected time | Step 3 (Task status and last run result) -> Step 5 (Trigger configuration validation) -> Step 7 (Power and conditions settings) |
| Password error or invalid account prompt | Step 4 (Task credential check) |
| Task trigger conditions not met | Step 5 (Trigger configuration validation) |
| Task executable not found | Step 6 (Dependency program path) |
| SPP Software Protection task failed | Step 2 (Task history log) -> Step 4 (Task credential check) -> [system-activation.md](references/online/system-activation.md) |
| Task Scheduler service cannot start | Step 1 (Task Scheduler service status) -> Step 8 (Task corruption and cache repair) |

## Diagnostic Steps

### Step 1: Task Scheduler Service Status

**Data Collection**:

> Collection target: Running status, startup type, and dependency service status of the Task Scheduler service (Schedule)

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 1

**Analysis Approach**:

1. Check service running status:
   - Normal: Status = Running
   - Abnormal: Status = Stopped -> **Root cause**: Task Scheduler service not running, causing all scheduled tasks to fail execution, **Severity**: Critical

2. Check service startup type:
   - Normal: StartType is not Disabled
   - Abnormal: StartType = Disabled -> **Root cause**: Task Scheduler service disabled, **Severity**: Critical

3. Check dependency service (RPC):
   - If the RPC service is not running, Task Scheduler cannot start either -> **Root cause**: RPC dependency service not running, causing Task Scheduler to fail to start, **Severity**: Critical

> If the service fails to start or cannot start, proceed to Step 8 to investigate task corruption issues.

### Step 2: Task History Log Check

**Data Collection**:

> Collection target: Recent task execution failure events (Event ID 101/102/201/322) in the Task Scheduler operational log, and whether task history recording is enabled

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 2
- TaskScheduler/Operational is a non-standard event channel; when the collector does not support this channel, fallback to user manually executing Get-WinEvent

**Analysis Approach**:

0. Task Scheduler Operational log not enabled:
   - This is **not an anomaly finding**; Windows Server not enabling this log by default is normal behavior
   - Output as a **configuration recommendation**: "Recommend enabling the Task Scheduler Operational log for future troubleshooting of task scheduling issues"
   - **Severity**: Info (recommendation only, not treated as Warning or anomaly)

1. Check Event ID 101 (task startup failure):
   - Extract error code (e.g., 0x80070005, 0x80070569)
   - 0x80070005 -> Access denied -> **Root cause**: Task credentials invalid or insufficient permissions, **Severity**: Critical
   - 0x80070569 -> Logon failure -> **Root cause**: The account password configured for the task has changed or the account is disabled, **Severity**: Critical
   - 0x8004131F -> Task instance already running -> May be due to task configured as "do not start new instance"
   - Other error codes -> Record error information, continue with subsequent steps for investigation

2. Check Event ID 102 (task startup success):
   - If the task frequently fails to start but has success records, it may be an intermittent issue (e.g., network dependency, resource contention)

3. Check Event ID 201 (operation completed):
   - Check task exit code (non-zero indicates program execution anomaly)

4. Check Event ID 322 (task trigger failure):
   - Trigger conditions not met -> **Root cause**: Task trigger configuration error or expired, **Severity**: Warning

> If Event ID 101 is found with error code 0x80070569, see -> [identity-account.md](references/online/identity-account.md) (account status check)

### Step 3: Task Status and Last Run Result

**Data Collection**:

> Collection target: Current status, last run time, next run time, and last run result of the specified task

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 3
- Get-ScheduledTaskInfo LastRunTime/NextRunTime/LastTaskResult details may fallback to user manual execution if collector Content does not include them

1. Check task status (State):
   - Ready: Normal, waiting for trigger
   - Running: Currently executing
   - Disabled: Disabled -> **Root cause**: Task manually disabled, **Severity**: Warning
   - Queued: Queued waiting for execution

2. Check LastTaskResult (last run result):
   - 0: Success
   - 1: Generic error
   - 0x80070005: Access denied -> **Root cause**: Insufficient permissions, **Severity**: Critical
   - 0x80070569: Logon failure -> **Root cause**: Invalid credentials, **Severity**: Critical
   - 0x41301: Task is running
   - 0x41303: Task not running -> **Root cause**: Task not triggered at expected time, **Severity**: Warning
   - 0x8004131F: Task instance already running
   - 0x80041002: Task not found (may have been deleted or corrupted)

3. Check NextRunTime:
   - If there is a clear next run time, the trigger configuration is normal
   - If empty or no value, the trigger may have expired -> proceed to Step 5

### Step 4: Task Credential Check

**Data Collection**:

> Collection target: Run account, logon type, and run level configured for the task

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 4

1. Check UserId (run account):
   - Format should be: `DOMAIN\User` or `NT AUTHORITY\SYSTEM` or `NT AUTHORITY\LOCAL SERVICE` or `NT AUTHORITY\NETWORK SERVICE`
   - If the account does not exist or has been disabled -> **Root cause**: The account configured for the task is invalid, **Severity**: Critical

2. Check LogonType (logon type):
   - Password: Requires password (interactive or service account), task will fail after password change
   - S4U: No password required (Service for User), local resource access only, no network authentication support
   - Interactive: Requires interactive logon
   - Group: Runs using group identity
   - If configured as Password but password has changed -> **Root cause**: Task credentials expired, **Severity**: Critical

3. Check RunLevel (run level):
   - Highest: Administrator privileges
   - LeastPrivilege: Standard user privileges
   - If the task requires administrator privileges but is configured as LeastPrivilege, execution may fail

4. Verify account status:
   > If the task is configured with a specific user account (not SYSTEM/LOCAL SERVICE/NETWORK SERVICE), check whether the account is locked or disabled:
   ```powershell
   $userName = "<UserName>"
   Get-LocalUser -Name $userName -ErrorAction SilentlyContinue | Select-Object Name, Enabled, AccountExpires, PasswordExpires | Format-Table -AutoSize
   ```

> If the account is locked or disabled, see -> [identity-account.md](references/online/identity-account.md) (account unlock and reset)

### Step 5: Trigger Configuration Validation

**Data Collection**:

> Collection target: Trigger type, trigger time, enabled status, expiration time, and repeat execution configuration of the task

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 5
- Trigger details (type/boundary times/repeat configuration) may fallback to user manual execution if collector Content does not include them

1. Check trigger type:
   - MSFT_TaskTimeTrigger: One-time time trigger
   - MSFT_TaskDailyTrigger: Daily trigger
   - MSFT_TaskWeeklyTrigger: Weekly trigger
   - MSFT_TaskLogonTrigger: Trigger at logon
   - MSFT_TaskBootTrigger: Trigger at boot
   - MSFT_TaskEventTrigger: Event trigger

2. Check Enabled status:
   - True: Trigger enabled
   - False: Trigger disabled -> **Root cause**: Trigger disabled, task will not execute, **Severity**: Warning

3. Check StartBoundary (start time):
   - If StartBoundary is a past time and is a TimeTrigger (one-time), the task will not trigger again -> **Root cause**: One-time trigger expired, **Severity**: Warning
   - If StartBoundary is a future time, the task has not reached execution time yet

4. Check EndBoundary (end time):
   - If EndBoundary has passed, the trigger has expired -> **Root cause**: Trigger has exceeded end time, **Severity**: Warning

5. Check Repetition (repeat execution):
   - If repeat execution is configured, check whether Interval and Duration are reasonable

### Step 6: Dependency Program Path Check

**Data Collection**:

> Collection target: Execution program path, arguments, and working directory configured for the task, and whether the program file exists

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 6

1. Check whether the program path exists:
   - PathExists = True: Program file exists
   - PathExists = False -> **Root cause**: The program file the task depends on does not exist or the path is incorrect, **Severity**: Critical

2. Check program file permissions:
   > If the file exists but the task execution fails, check whether the task run account has execution permissions:
   ```powershell
   $exePath = "<ProgramPath>"
   $acl = Get-Acl -Path $exePath
   $acl.Access | Where-Object { $_.IdentityReference -match "<UserId>" } | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
   ```

3. Check WorkingDirectory (working directory):
   - If a working directory is configured but the directory does not exist, some programs will fail to execute

4. Check Arguments (arguments):
   - Whether file paths included in the arguments are valid
   - Whether the argument syntax is correct (e.g., PowerShell scripts require `-ExecutionPolicy Bypass -File` prefix)

> If the program file is missing, it needs to be restored from backup or the related software reinstalled

### Step 7: Power and Conditions Settings Check

**Data Collection**:

> Collection target: Power conditions, idle conditions, network conditions, and other condition settings of the task

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 7

1. Check DisallowStartIfOnBatteries (do not start on battery):
   - True: Task will not trigger when the laptop is on battery -> May cause the task to not run

2. Check StopIfGoingOnBatteries (stop when switching to battery):
   - True: Task will be terminated when switching to battery while running

3. Check WakeToRun (wake computer to run):
   - False: Task will not wake the system to execute when the computer is sleeping

4. Check StartWhenAvailable (run as soon as possible if missed):
   - True: Will execute as soon as possible after missing the trigger time
   - False: Skips execution after missing the trigger time -> May cause the task to appear "not running"

5. Check ExecutionTimeLimit (execution time limit):
   - If the task execution time exceeds the limit, it will be forcibly terminated -> May cause long-running tasks to be interrupted

6. Check MultipleInstances (multiple instance policy):
   - IgnoreNew: If the task is already running, new triggers will be ignored
   - Parallel: Allows parallel execution
   - Queue: Queued for execution

### Step 8: Task Corruption and Cache Repair

**Data Collection**:

> Collection target: Task Scheduler task file integrity, task cache status, SPP task configuration (Network Service permissions)

**Analysis Approach**:

- PowerShell script: [system-schtasks.ps1](references/online/scripts/system-schtasks.ps1) Section Step 8

1. Check task XML file corruption:
   - If unparseable XML files are found -> **Root cause**: Task definition file corrupted, may cause the Task Scheduler service to fail to start or tasks to fail to load, **Severity**: Critical
   - Corrupted task files cause "Task Scheduler service is not available" error

2. Check SPP task Network Service permissions:
   - NETWORK SERVICE inherits read and execute permissions for SPP task files through the Users/Authenticated Users group by default
   - **Only flag as anomaly when an explicit Deny rule exists** (absence of an explicit ACE does not imply no permissions)
   - If Deny rules are found -> **Root cause**: SPP task files have explicit deny rules, preventing NETWORK SERVICE access, causing Software Protection tasks to fail to reschedule, **Severity**: Critical
   - No Deny rules -> Permissions normal, no attention needed

3. Check Task Scheduler service anomaly events:
   - Event ID 7034: Service terminated unexpectedly
   - Event ID 7023: Service terminated with error (event includes error details)
   - Event ID 7024: Service terminated with service-specific error code
   - If service crash events are found -> **Root cause**: Task Scheduler service crashed due to corrupted task files or missing system files, **Severity**: Critical

> If SPP task failure is found and is activation-related, see -> [system-activation.md](references/online/system-activation.md)

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 2/4 finds task account locked or disabled | -> [identity-account.md](references/online/identity-account.md) |
| Conditional jump | Step 2 finds SPP Software Protection task failed | -> [system-activation.md](references/online/system-activation.md) |
| Conditional jump | Step 6 finds insufficient program file permissions | -> [identity-permission.md](references/online/identity-permission.md) |
| Conditional jump | Step 4 finds account password expired and needs reset | -> [identity-account.md](references/online/identity-account.md) |
| Parameterized reference | Step 2 finds network-related error code, suspecting firewall blocking | -> [networking-firewall.md](references/online/networking-firewall.md) (check whether outbound rules block task outbound connections) |
| Chain successor | All steps in this file executed, no root cause confirmed | -> [system-management.md](references/online/system-management.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [system-schtasks.md](references/online/fixes/system-schtasks.md).
