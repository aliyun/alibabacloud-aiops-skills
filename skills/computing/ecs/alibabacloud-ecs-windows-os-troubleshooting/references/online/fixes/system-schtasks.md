# Task Scheduler Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Task Scheduler Service Not Running

**Fix Action**:

```powershell
# 1. Check current service status
Get-Service -Name 'Schedule' | Format-Table -AutoSize

# 2. If disabled, change the startup type first
Set-Service -Name 'Schedule' -StartupType Automatic

# 3. Start the service
Start-Service -Name 'Schedule'

# 4. Verify service status
Get-Service -Name 'Schedule' | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

**Verification**:

```powershell
Get-Service -Name 'Schedule'
```

Expected result: Status = Running, StartType = Automatic

**Risk notes**:

- **Session impact**: After starting the service, all pending scheduled tasks will be triggered immediately.
- **Persistence scope**: Service startup type is set to Automatic, retained after reboot.
- **Rollback command**: `Stop-Service -Name 'Schedule' -Force; Set-Service -Name 'Schedule' -StartupType Disabled`
- **Note**: Starting the Task Scheduler service affects all scheduled tasks that depend on this service; it is recommended to perform this operation during off-peak hours.

---

### Root cause: Task Startup Failure

**Fix Action**:

```powershell
$taskName = "<TaskName>"

# 1. View detailed task error information
Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 100 -ErrorAction SilentlyContinue | Where-Object {
    $_.Id -eq 101 -and $_.Message -match $taskName
} | Select-Object TimeCreated, Message | Format-List

# 2. If credential issue (error code 0x80070569), update task password
# Note: the correct password is required
$task = Get-ScheduledTask -TaskName $taskName
$userId = $task.Principal.UserId
$password = Read-Host "Enter password for $userId" -AsSecureString
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))

# Update task credentials
Set-ScheduledTask -TaskName $taskName -User $userId -Password $plainPassword

# 3. If permission issue (error code 0x80070005), run the task with administrator privileges
Set-ScheduledTask -TaskName $taskName -Principal (New-ScheduledTaskPrincipal -UserId $userId -RunLevel Highest)
```

**Verification**:

```powershell
# Manually run the task for testing
Start-ScheduledTask -TaskName "<TaskName>"

# Check if the task started successfully
Start-Sleep -Seconds 5
Get-ScheduledTask -TaskName "<TaskName>" | Select-Object State | Format-Table -AutoSize
```

Expected result: State = Ready (returns to Ready after execution completes)

**Risk notes**:

- **Session impact**: None; modifying task credentials does not affect currently running task instances.
- **Persistence scope**: Written to task configuration, retained after reboot.
- **Rollback command**: `Set-ScheduledTask -TaskName '<TaskName>' -User '<OriginalUser>' -Password '<OriginalPassword>'`
- **Note**: Updating task credentials requires knowing the correct password; an incorrect password will cause the task to continue failing.

---

### Root cause: Invalid Task Credentials

**Fix Action**:

```powershell
$taskName = "<TaskName>"
$userId = "<UserId>"

# 1. Check account status
Get-LocalUser -Name $userId.Split('\')[-1] -ErrorAction SilentlyContinue | Select-Object Name, Enabled, PasswordExpired | Format-Table -AutoSize

# 2. If account is disabled, enable it
Enable-LocalUser -Name $userId.Split('\')[-1]

# 3. If password expired, prompt user to change password
# Or reset password with administrator privileges
# $newPassword = Read-Host "Enter new password" -AsSecureString
# Set-LocalUser -Name $userId.Split('\')[-1] -Password $newPassword

# 4. Update task credentials
$password = Read-Host "Enter current password for $userId" -AsSecureString
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
Set-ScheduledTask -TaskName $taskName -User $userId -Password $plainPassword
```

**Verification**:

```powershell
# Manually run the task
Start-ScheduledTask -TaskName "<TaskName>"
Start-Sleep -Seconds 3
Get-ScheduledTask -TaskName "<TaskName>" | Get-ScheduledTaskInfo | Select-Object LastTaskResult | Format-Table -AutoSize
```

Expected result: LastTaskResult = 0, task executed successfully

**Risk notes**:

- **Session impact**: Resetting the password will invalidate all current login sessions for that account.
- **Persistence scope**: Password reset and task credential update both take effect permanently.
- **Rollback command**: Reset the password back to the original value (original password must be recorded).
- **Note**: Resetting the password affects all login sessions for that account and other tasks that depend on those credentials.

---

### Root cause: Trigger Configuration Error

**Fix Action**:

```powershell
$taskName = "<TaskName>"

# 1. View current triggers
Get-ScheduledTask -TaskName $taskName | Select-Object -ExpandProperty Triggers | Format-List

# 2. Disable old triggers
$task = Get-ScheduledTask -TaskName $taskName
$task.Triggers | ForEach-Object { $_.Enabled = $false }
Set-ScheduledTask -InputObject $task

# 3. Add new trigger (example: run daily at 9:00)
$trigger = New-ScheduledTaskTrigger -Daily -At "9:00"
$task = Get-ScheduledTask -TaskName $taskName
$task.Triggers.Add($trigger)
Set-ScheduledTask -InputObject $task
```

**Verification**:

```powershell
# View updated triggers
Get-ScheduledTask -TaskName "<TaskName>" | Select-Object -ExpandProperty Triggers | Select-Object StartBoundary, Enabled | Format-Table -AutoSize

# View next run time
Get-ScheduledTask -TaskName "<TaskName>" | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime | Format-Table -AutoSize
```

Expected result: NextRunTime shows a clear future time, Enabled = True

**Risk notes**:

- **Session impact**: None; trigger modification does not affect currently running task instances.
- **Persistence scope**: Written to task configuration, retained after reboot.
- **Rollback command**: Restore original trigger configuration: `Set-ScheduledTask -InputObject $task` (task XML must be backed up in advance).
- **Note**: Modifying triggers changes task execution time; confirm it does not affect business processes.

---

### Root cause: Missing Task Dependency Program

**Fix Action**:

```powershell
$taskName = "<TaskName>"

# 1. View the program path configured for the task
$task = Get-ScheduledTask -TaskName $taskName
$action = $task.Actions[0]
Write-Output "Program: $($action.Execute)"
Write-Output "Arguments: $($action.Arguments)"

# 2. Check if the program exists
if (-not (Test-Path $action.Execute)) {
    Write-Output "ERROR: Program not found: $($action.Execute)"

    # 3. Try to search for the program in the system
    $exeName = [System.IO.Path]::GetFileName($action.Execute)
    $found = Get-ChildItem -Path "C:\" -Recurse -Filter $exeName -ErrorAction SilentlyContinue | Select-Object -First 5

    if ($found) {
        Write-Output "Found possible locations:"
        $found | ForEach-Object { Write-Output $_.FullName }

        # 4. Update task program path (execute after confirming the correct path)
        # $correctPath = "<CorrectPath>"
        # Set-ScheduledTask -TaskName $taskName -Action (New-ScheduledTaskAction -Execute $correctPath -Argument $action.Arguments)
    } else {
        Write-Output "Program not found in system. Need to reinstall or restore from backup."
    }
}
```

**Verification**:

```powershell
# Verify the program path has been updated
$task = Get-ScheduledTask -TaskName "<TaskName>"
Test-Path $task.Actions[0].Execute

# Manually run the task
Start-ScheduledTask -TaskName "<TaskName>"
```

Expected result: Test-Path returns True, task executed successfully

**Risk notes**:

- **Session impact**: None; modifying the task program path does not affect already running instances.
- **Persistence scope**: Written to task configuration, retained after reboot.
- **Rollback command**: `Set-ScheduledTask -TaskName '<TaskName>' -Action (New-ScheduledTaskAction -Execute '<OriginalPath>' -Argument '<OriginalArgs>')`
- **Note**: If the program file has been deleted and there is no backup, the related software needs to be reinstalled.

---

### Root cause: Corrupted Task File

**Fix Action**:

```powershell
# 1. Locate corrupted task files
$taskPath = "$env:SystemRoot\System32\Tasks"
$corruptedFiles = @()
Get-ChildItem -Path $taskPath -Recurse -File | ForEach-Object {
    try {
        [xml]$xml = Get-Content $_.FullName -ErrorAction Stop
    } catch {
        $corruptedFiles += $_.FullName
        Write-Output "CORRUPTED: $($_.FullName)"
    }
}

# 2. Export registry information of corrupted tasks (for subsequent reconstruction)
# Tasks also exist in registry: HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\TaskCache\Tree
foreach ($file in $corruptedFiles) {
    $taskName = [System.IO.Path]::GetFileNameWithoutExtension($file)
    Write-Output "Corrupted task: $taskName"

    # 3. Delete corrupted task file (confirmation required)
    # Remove-Item -Path $file -Force
    # Write-Output "Deleted corrupted task file: $file"
}

# 4. Restart Task Scheduler service
# Restart-Service -Name 'Schedule' -Force
```

**Verification**:

```powershell
# Verify service status
Get-Service -Name 'Schedule' | Select-Object Name, Status, StartType | Format-Table -AutoSize

# Verify task list is normal
Get-ScheduledTask | Select-Object TaskName, State | Format-Table -AutoSize
```

Expected result: Task Scheduler service is running normally, task list displays normally

**Risk notes**:

- **Session impact**: Restarting the Task Scheduler service briefly interrupts all currently running scheduled tasks.
- **Persistence scope**: Deleting task files is a permanent operation and cannot be automatically recovered.
- **Rollback command**: Re-import from backed-up task XML file: `Register-ScheduledTask -TaskName '<TaskName>' -Xml (Get-Content '<BackupPath>' -Raw)`
- **Note**: Deleting corrupted task files will cause the loss of that task configuration. It is recommended to export the task XML backup first before deleting the corrupted file. After deletion, the task needs to be recreated.

---

### Root cause: Missing SPP Task Permissions

**Fix Action**:

```powershell
# 1. Locate SPP task files
$sppTaskPath = "$env:SystemRoot\System32\Tasks\Microsoft\Windows\SoftwareProtectionPlatform"

# 2. Add ReadAndExecute permission for NETWORK SERVICE
if (Test-Path $sppTaskPath) {
    Get-ChildItem -Path $sppTaskPath -File | ForEach-Object {
        $acl = Get-Acl -Path $_.FullName
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "NT AUTHORITY\NETWORK SERVICE",
            "ReadAndExecute",
            "Allow"
        )
        $acl.AddAccessRule($rule)
        Set-Acl -Path $_.FullName -AclObject $acl
        Write-Output "Added NETWORK SERVICE ReadAndExecute permission to $($_.FullName)"
    }
} else {
    Write-Output "SPP task directory not found: $sppTaskPath"
}

# 3. Confirm SPP tasks exist and are correctly configured
Get-ScheduledTask -TaskPath "\Microsoft\Windows\SoftwareProtectionPlatform\" -ErrorAction SilentlyContinue | Select-Object TaskName, State | Format-Table -AutoSize
```

**Verification**:

```powershell
# Verify permissions have been added
$sppTaskPath = "$env:SystemRoot\System32\Tasks\Microsoft\Windows\SoftwareProtectionPlatform"
Get-ChildItem -Path $sppTaskPath -File | ForEach-Object {
    $acl = Get-Acl -Path $_.FullName
    $acl.Access | Where-Object { $_.IdentityReference -match "NETWORK SERVICE" } | Select-Object IdentityReference, FileSystemRights | Format-Table -AutoSize
}

# Verify sppsvc service is running normally
Get-Service -Name 'sppsvc' | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: NETWORK SERVICE has ReadAndExecute permission, sppsvc service is running normally

**Risk notes**:

- **Session impact**: None; adding file permissions does not affect running services.
- **Persistence scope**: File ACL modifications take effect permanently.
- **Rollback command**: Remove the added permission rule: `$acl.RemoveAccessRule($rule); Set-Acl -Path '<FilePath>' -AclObject $acl`
- **Note**: Modifying SPP task file permissions may affect the Windows activation process; ensure only necessary permissions are added. If the issue persists, refer to the system-activation diagnostic section
