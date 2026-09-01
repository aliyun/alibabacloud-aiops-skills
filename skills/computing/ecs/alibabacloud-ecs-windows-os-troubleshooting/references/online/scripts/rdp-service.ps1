$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: TermService Service Status Check ---

try {
    Get-Service -Name TermService | Select-Object Name, Status, StartType | Format-Table -AutoSize
    Get-Service -Name TermService -RequiredServices | Select-Object Name, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 termservice: " + $_.Exception.Message)
}

# --- Step 2: RDP Listener (WinStation) and Port Check ---
# Note: MUST enumerate all WinStations subkeys (excluding Console), not just RDP-Tcp

$winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
try {
    $stations = Get-ChildItem -Path $winStationsPath |
        Where-Object { $_.PSChildName -ne "Console" }
} catch {
    Write-Host ("ERROR step2 winstations-enum: " + $_.Exception.Message)
}

# 1. WinStation registry configuration
try {
    $stations | ForEach-Object {
        $props = Get-ItemProperty -Path $_.PSPath
        [PSCustomObject]@{
            StationName       = $_.PSChildName
            PortNumber        = $props.PortNumber
            fEnableWinStation = $props.fEnableWinStation
            WdName            = $props.WdName
            MaxInstanceCount  = $props.MaxInstanceCount
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 winstation-config: " + $_.Exception.Message)
}

# 2. Port consistency check for EACH WinStation (configured port vs actual listening port)
try {
    $stations | ForEach-Object {
        $props = Get-ItemProperty -Path $_.PSPath
        $configuredPort = $props.PortNumber
        $stationName = $_.PSChildName
        if ($configuredPort) {
            $listening = Get-NetTCPConnection -LocalPort $configuredPort -State Listen
            $actualService = if ($listening) {
                ($listening | ForEach-Object {
                    (Get-CimInstance Win32_Service -Filter "ProcessId=$($_.OwningProcess)").Name
                }) -join ','
            } else { $null }
            $isListening = [bool]$listening
            [PSCustomObject]@{
                StationName    = $stationName
                ConfiguredPort = $configuredPort
                IsListening    = $isListening
                ServiceName    = $actualService
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 port-consistency: " + $_.Exception.Message)
}

# 3. Session Listener status (qwinsta)
try {
    $qwinsta = qwinsta 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 qwinsta: exit=$LASTEXITCODE $(($qwinsta | Out-String).Trim())" }
    $qwinsta
} catch {
    Write-Host ("ERROR step2 qwinsta: " + $_.Exception.Message)
}

# 4. WinStation registry ACL check (BUILTIN\Users read permission)
try {
    $stations | ForEach-Object {
        $acl = Get-Acl -Path $_.PSPath
        $usersAccess = $acl.Access | Where-Object { $_.IdentityReference -match 'BUILTIN\\Users' }
        [PSCustomObject]@{
            StationName = $_.PSChildName
            UsersAccess = if ($usersAccess) { $usersAccess.RegistryRights } else { 'NO_ACCESS' }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 winstation-acl: " + $_.Exception.Message)
}

# 5. TerminalServices session-layer event log
# 261 = listener received a connection (information level, healthy evidence); 1035/1036/1042/1103 = abnormal events
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational'; Id=261,1035,1036,1042,1103} |
        Select-Object TimeCreated, Id, Message -First 20 | Format-List
} catch {
    Write-Host ("ERROR step2 rcm-eventlog: " + $_.Exception.Message)
}

# 6. Enumeration completeness verification
Write-Output "Total WinStations found (excluding Console): $($stations.Count)"

# --- Step 3: RDP Enablement Status and Group Policy Check ---

try {
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" | Select-Object fDenyTSConnections | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 fdenytsconnections: " + $_.Exception.Message)
}

try {
    $gpPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
    if (Test-Path $gpPath) {
        Get-ItemProperty -Path $gpPath | Select-Object fDenyTSConnections, SecurityLayer, UserAuthentication, MaxInstanceCount, fDisableCdm, fDisableClip | Format-List
    } else {
        Write-Output "(no Group Policy Terminal Services overrides configured)"
    }
} catch {
    Write-Host ("ERROR step3 gp-terminal-services: " + $_.Exception.Message)
}

# --- Step 4: UMBus Device Enumeration Check ---

try {
    Get-PnpDevice -Class 'System' | Where-Object {$_.FriendlyName -like '*UMBus*'} | Select-Object FriendlyName, Status, Class | Format-Table -AutoSize
    Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Remote Desktop*' -or $_.FriendlyName -like '*Terminal*'} | Select-Object FriendlyName, Status, Class | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 pnp-devices: " + $_.Exception.Message)
}
