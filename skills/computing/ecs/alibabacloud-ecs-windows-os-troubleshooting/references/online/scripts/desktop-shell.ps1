$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check Login Shell Configuration ---
try {
    $shellSystem = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell').Shell
    Write-Host "System Shell (HKLM): $shellSystem"
} catch {
    Write-Host ("ERROR step1 system-shell: " + $_.Exception.Message)
}
try {
    $shellUser = (Get-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Shell').Shell
    if ($shellUser) {
        Write-Host "User Shell (HKCU): $shellUser"
    } else {
        Write-Host "User Shell (HKCU): Not set (using system default)"
    }
} catch {
    Write-Host ("ERROR step1 user-shell: " + $_.Exception.Message)
}
try {
    $userinit = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'Userinit').Userinit
    Write-Host "Userinit: $userinit"
} catch {
    Write-Host ("ERROR step1 userinit: " + $_.Exception.Message)
}

# --- Step 2: Check Explorer.exe Process Status ---
try {
    $explorer = Get-Process -Name explorer
    if ($explorer) {
        $explorer | Select-Object Id, ProcessName, CPU, WorkingSet64, StartTime | Format-List
        Write-Host "Explorer.exe is running ($($explorer.Count) instance(s))"
    } else {
        Write-Host "WARNING: Explorer.exe is NOT running"
    }
} catch {
    Write-Host ("ERROR step2 explorer-process: " + $_.Exception.Message)
}
try {
    # Filter ProviderName in FilterHashtable -- the Application log is high-volume, so
    # pulling the latest N entries and filtering afterwards misses explorer crashes days ago.
    Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; Level=2; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 30 |
        Where-Object { $_.Message -like '*explorer*' } |
        Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 explorer-eventlog: " + $_.Exception.Message)
}

# --- Step 3: Check Taskbar/Start Menu Response ---
try {
    $shellHost = Get-Process -Name ShellExperienceHost
    $startMenu = Get-Process -Name StartMenuExperienceHost
    Write-Host "ShellExperienceHost: $(if ($shellHost) { 'Running' } else { 'Not running' })"
    Write-Host "StartMenuExperienceHost: $(if ($startMenu) { 'Running' } else { 'Not running' })"
} catch {
    Write-Host ("ERROR step3 shell-hosts: " + $_.Exception.Message)
}
try {
    $taskbarSettings = Get-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3'
    if ($taskbarSettings) {
        Write-Host "Taskbar settings registry key exists"
    }
} catch {
    Write-Host ("ERROR step3 taskbar-settings: " + $_.Exception.Message)
}
try {
    $appReadiness = Get-Service -Name AppReadiness
    if ($appReadiness) {
        Write-Host "AppReadiness Service: Status=$($appReadiness.Status), StartType=$($appReadiness.StartType)"
    }
} catch {
    Write-Host ("ERROR step3 app-readiness: " + $_.Exception.Message)
}

# --- Step 4: Check DWM Status ---
try {
    Get-Service -Name 'UxSms' | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 uxsms: " + $_.Exception.Message)
}
try {
    $dwm = Get-Process -Name dwm
    if ($dwm) {
        Write-Host "dwm.exe is running (PID: $($dwm.Id))"
    } else {
        Write-Host "WARNING: dwm.exe is NOT running"
    }
} catch {
    Write-Host ("ERROR step4 dwm-process: " + $_.Exception.Message)
}

# --- Step 5: Check DPI Scaling ---
try {
    $logPixels = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'LogPixels').LogPixels
    $dpiScaling = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name 'AppliedDPI').AppliedDPI
    Write-Host "LogPixels: $logPixels (96=100%, 120=125%, 144=150%, 192=200%)"
    Write-Host "AppliedDPI: $dpiScaling"
} catch {
    Write-Host ("ERROR step5 dpi-registry: " + $_.Exception.Message)
}
try {
    $perMonitorDPI = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'DpiScalingVer').DpiScalingVer
    Write-Host "DpiScalingVer: $perMonitorDPI"
    $dpiAware = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'Win8DpiScaling').Win8DpiScaling
    Write-Host "Win8DpiScaling: $dpiAware (0=DPI-aware apps, 1=use display scaling)"
} catch {
    Write-Host ("ERROR step5 dpi-scaling-ver: " + $_.Exception.Message)
}

# --- Step 6: Check Console Session Status ---
try {
    $qsession = query session 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step6 query-session: exit=$LASTEXITCODE $(($qsession | Out-String).Trim())" }
    $qsession
} catch {
    Write-Host ("ERROR step6 query-session: " + $_.Exception.Message)
}
