$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

$taskName = "*"

# --- Step 1: Task Scheduler Service Status ---
try {
    Get-Service -Name 'Schedule' | Select-Object Name, Status, StartType, DependentServices | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 schedule-service: " + $_.Exception.Message)
}
try {
    Get-Service -Name 'RpcSs' | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 rpcss: " + $_.Exception.Message)
}
try {
    # RpcLocator was removed from recent Windows builds; its absence is a version fact, not a fault
    Get-Service -Name 'RpcLocator' | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 rpclocator (service may not exist on this build): " + $_.Exception.Message)
}

# --- Step 2: Task History Log Check ---
try {
    $operationalLog = Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 1
    Write-Output "Task Scheduler Operational log is enabled, last event: $($operationalLog.TimeCreated)"
} catch {
    Write-Output "INFO: Task Scheduler Operational log may be disabled - no events found (recommend enabling for future troubleshooting)"
}
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; Id=101,102,201,322} -MaxEvents 100 | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 task-events: " + $_.Exception.Message)
}

# --- Step 3: Task Status and Last Run Result ---
try {
    Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, TaskPath, State | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 task-states: " + $_.Exception.Message)
}
try {
    Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo | Select-Object TaskName, TaskPath, LastRunTime, NextRunTime, LastTaskResult | Format-List
} catch {
    Write-Host ("ERROR step3 task-info: " + $_.Exception.Message)
}

# --- Step 4: Task Credential Check ---
try {
    Get-ScheduledTask -TaskName $taskName | ForEach-Object {
        [PSCustomObject]@{
            TaskName  = $_.TaskName
            UserId    = $_.Principal.UserId
            LogonType = $_.Principal.LogonType
            RunLevel  = $_.Principal.RunLevel
            GroupId   = $_.Principal.GroupId
        }
    } | Format-List
} catch {
    Write-Host ("ERROR step4 task-credentials: " + $_.Exception.Message)
}

# --- Step 5: Trigger Configuration Validation ---
try {
    Get-ScheduledTask -TaskName $taskName | ForEach-Object {
        $t = $_
        $t.Triggers | ForEach-Object {
            [PSCustomObject]@{
                TaskName           = $t.TaskName
                TriggerType        = $_.CimClass.CimClassName
                Enabled            = $_.Enabled
                StartBoundary      = $_.StartBoundary
                EndBoundary        = $_.EndBoundary
                ExecutionTimeLimit = $_.ExecutionTimeLimit
                RepetitionInterval = $_.Repetition.Interval
                RepetitionDuration = $_.Repetition.Duration
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 task-triggers: " + $_.Exception.Message)
}

# --- Step 6: Dependency Program Path Check ---
try {
    Get-ScheduledTask -TaskName $taskName | ForEach-Object {
        $t = $_
        $t.Actions | ForEach-Object {
            $action = $_
            $pathExists = $null
            try { $pathExists = Test-Path -Path $action.Execute } catch { $pathExists = $null }
            [PSCustomObject]@{
                TaskName         = $t.TaskName
                ActionPath       = $action.Execute
                Arguments        = $action.Arguments
                WorkingDirectory = $action.WorkingDirectory
                PathExists       = $pathExists
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 action-paths: " + $_.Exception.Message)
}

# --- Step 7: Power and Condition Settings Check ---
try {
    Get-ScheduledTask -TaskName $taskName | ForEach-Object {
        $t = $_
        $t.Settings | Select-Object @{N='TaskName';E={$t.TaskName}}, AllowHardTerminate, DeleteExpiredTaskAfter, DisallowStartIfOnBatteries, ExecutionTimeLimit, Hidden, MultipleInstances, Priority, RestartCount, RestartInterval, StartWhenAvailable, StopIfGoingOnBatteries, WakeToRun
    } | Format-List
} catch {
    Write-Host ("ERROR step7 task-settings: " + $_.Exception.Message)
}

# --- Step 8: Task Corruption and Cache Repair ---
try {
    # -ErrorAction Continue: access-denied on protected task subfolders is printed and
    # enumeration continues -- errors are surfaced, not swallowed.
    $taskPath = "$env:SystemRoot\System32\Tasks"
    Get-ChildItem -Path $taskPath -Recurse -File -ErrorAction Continue | ForEach-Object {
        try {
            [xml]$xml = Get-Content $_.FullName -ErrorAction Stop
        } catch {
            Write-Output "CORRUPTED: $($_.FullName) - $($_.Exception.Message)"
        }
    }
} catch {
    Write-Host ("ERROR step8 task-files-scan: " + $_.Exception.Message)
}

try {
    $sppTaskPath = "$env:SystemRoot\System32\Tasks\Microsoft\Windows\SoftwareProtectionPlatform"
    if (Test-Path $sppTaskPath) {
        Get-ChildItem -Path $sppTaskPath -File | ForEach-Object {
            try {
                $acl = Get-Acl -Path $_.FullName
                $denyRules = $acl.Access | Where-Object {
                    $_.AccessControlType -eq 'Deny' -and
                    ($_.IdentityReference -match 'NETWORK SERVICE|Everyone|Users|Authenticated Users')
                }
                if ($denyRules) {
                    Write-Output "BLOCKED: Explicit DENY rule found on $($_.FullName):"
                    $denyRules | Select-Object IdentityReference, FileSystemRights, AccessControlType | Format-Table -AutoSize
                } else {
                    Write-Output "OK: No explicit DENY rules on $($_.FullName)"
                }
            } catch {
                Write-Host ("ERROR step8 spp-task-acl($($_.Name)): " + $_.Exception.Message)
            }
        }
    } else {
        Write-Output "SPP task directory not found: $sppTaskPath"
    }
} catch {
    Write-Host ("ERROR step8 spp-task-acl: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'; Id=7034,7023,7024} -MaxEvents 20 | Where-Object {
        $_.Message -match 'Schedule|Task Scheduler'
    } | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step8 scm-events: " + $_.Exception.Message)
}
