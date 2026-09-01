$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Shutdown Timeout Configuration and Auto-Termination Policy ---
try {
    $ctl = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control"
    $desk = Get-ItemProperty -Path "HKCU:\Control Panel\Desktop"
    [PSCustomObject]@{
        WaitToKillServiceTimeout = $ctl.WaitToKillServiceTimeout
        WaitToKillAppTimeout    = $desk.WaitToKillAppTimeout
        HungAppTimeout          = $desk.HungAppTimeout
        AutoEndTasks            = $desk.AutoEndTasks
    } | Format-List
} catch {
    Write-Host ("ERROR step1 shutdown-timeouts: " + $_.Exception.Message)
}

try {
    Get-ChildItem -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Group Policy\State\Machine\Scripts\Shutdown" | ForEach-Object {
        $s = Get-ItemProperty -Path $_.PSPath
        [PSCustomObject]@{Scope='Machine'; Script=$s.Script; Parameters=$s.Parameters}
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 shutdown-scripts: " + $_.Exception.Message)
}

# --- Step 2: Pending Reboot Operation Status ---
try {
    $sm = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager"
    $renameOps = $sm.PendingFileRenameOperations
    if ($renameOps) { $renameOps }
} catch {
    Write-Host ("ERROR step2 pending-rename: " + $_.Exception.Message)
}

try {
    $cbs = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing"
    if ($cbs.RebootPending -eq 1) {
        [PSCustomObject]@{Key='Component Based Servicing'; RebootPending=$cbs.RebootPending} | Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step2 cbs-reboot-pending: " + $_.Exception.Message)
}

if (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired") {
    [PSCustomObject]@{RebootRequired=$true} | Format-Table -AutoSize
}

try {
    Get-ChildItem -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Sessions" | ForEach-Object {
        $po = Get-ItemProperty -Path $_.PSPath -Name PendingOperations
        if ($po.PendingOperations -gt 0) {
            $to = Get-ItemProperty -Path $_.PSPath -Name TotalOperations
            [PSCustomObject]@{Session=$_.PSChildName; Total=$to.TotalOperations; Pending=$po.PendingOperations}
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 cbs-sessions: " + $_.Exception.Message)
}

# --- Step 3: Boot Duration and Uptime Analysis ---
try {
    Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime, @{Name='UptimeDays';Expression={[math]::Round(((Get-Date) - $_.LastBootUpTime).TotalDays, 2)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 os-uptime: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=100} -MaxEvents 20 | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 boot-duration-events: " + $_.Exception.Message)
}

# --- Step 4: Shutdown/Reboot Event Analysis ---
try {
    Get-WinEvent -FilterHashtable @{LogName='System'; Id=6006,1074,6008,41} -MaxEvents 20 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 shutdown-events: " + $_.Exception.Message)
}

# --- Step 5: Boot Phase Breakdown ---
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=101} -MaxEvents 5 | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 boot-phase-events: " + $_.Exception.Message)
}

# --- Step 6: Shutdown Duration Analysis ---
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=200} -MaxEvents 5 | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 shutdown-duration-events: " + $_.Exception.Message)
}
