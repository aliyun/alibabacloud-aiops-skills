$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Session Timeline Reconstruction ---

try {
    # Default window: last 30 days. LSM events are high-frequency (every logon/reconnect/
    # disconnect), so an unbounded "latest N" query can easily miss the user-reported
    # disconnect point; MUST narrow StartTime around it when provided.
    $disconnStart = (Get-Date).AddDays(-30)
} catch {
    Write-Host ("ERROR step1 window-start: " + $_.Exception.Message)
}

try {
    # LSM/Operational info level events (timeline reconstruction: 21 logon -> 22 shell start -> 25 reconnect -> 40 disconnect reason code -> 24 disconnect confirmation)
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational'
        Id = 21, 22, 24, 25, 40, 41, 42
        StartTime = $disconnStart
    } -MaxEvents 200 |
        Select-Object TimeCreated, Id, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 lsm-timeline: " + $_.Exception.Message)
}

try {
    # Session connect/disconnect timestamps (cross-align DisconnectTime with event 40 disconnect time to confirm the target session and duration)
    $qsession = query session 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step1 query-session: exit=$LASTEXITCODE $(($qsession | Out-String).Trim())" }
    $qsession
} catch {
    Write-Host ("ERROR step1 query-session: " + $_.Exception.Message)
}

# --- Step 2: Disconnect Reason Code Decoding and Determination ---

try {
    # Dynamically extract event 40 reason code and decode (value is HRESULT, low 16 bits converted to Win32 error code then decoded with net helpmsg)
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational'
        Id = 40
        StartTime = $disconnStart
    } -MaxEvents 20 | ForEach-Object {
        $evt = $_
        if ($evt.Message -match '(?:Reason\s*(?:code)?[:=]?\s*)?(\d{6,10})') {
            $code = [int]$Matches[1]
            $win32 = $code -band 0xFFFF
            $helpmsg = net helpmsg $win32 2>&1
            if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 net-helpmsg($win32): exit=$LASTEXITCODE $(($helpmsg | Out-String).Trim())" }
            [PSCustomObject]@{
                TimeCreated = $evt.TimeCreated
                ReasonCode  = $code
                Hex         = '0x{0:X8}' -f $code
                Win32Code   = $win32
                Description = ($helpmsg -join ' ').Trim()
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 reason-decode: " + $_.Exception.Message)
}

# --- Step 3: Server-Side Active Disconnect Configuration Check ---

try {
    # WinStation timeout/keep-alive configuration (all 0 -> server will not actively disconnect due to timeout)
    $ts = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"
    $ts | Select-Object MaxIdleTime, MaxConnectionTime, MaxDisconnectionTime, KeepAliveTimeout | Format-List
} catch {
    Write-Host ("ERROR step3 winstation-timeouts: " + $_.Exception.Message)
}

try {
    # Timeout/keep-alive override under Group Policy path (KeepAliveInterval is the "configure keep-alive connection interval" policy value, in milliseconds)
    $policyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
    if (Test-Path $policyPath) {
        Get-ItemProperty -Path $policyPath |
            Select-Object MaxIdleTime, MaxConnectionTime, MaxDisconnectionTime, KeepAliveInterval |
            Format-List
    } else {
        Write-Output "(no Group Policy Terminal Services overrides configured)"
    }
} catch {
    Write-Host ("ERROR step3 gpo-timeouts: " + $_.Exception.Message)
}

# --- Step 4: Link Layer Cross-Verification ---

try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'System'
        ProviderName = 'netkvm', 'TCPIP', 'NDIS', 'TermDD'
        Level = 1, 2, 3
        StartTime = $disconnStart
    } -MaxEvents 50 |
        Select-Object TimeCreated, ProviderName, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 link-layer-events: " + $_.Exception.Message)
}

try {
    Get-NetAdapter |
        Select-Object Name, Status, LinkSpeed, DriverDescription, DriverVersion |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 net-adapter: " + $_.Exception.Message)
}

# --- Step 5: Protocol Stack Debug Log Deep Dive (Optional) ---

# Optional prerequisite (recommended for the user to execute in an administrator PowerShell, reproduce the issue once before collecting):
#
#   wevtutil sl Microsoft-Windows-TerminalServices-RDPCoreTS/Debug /e:true /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-RDPCoreTS/Analytic /e:true /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-LocalSessionManager/Debug /e:true /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-RemoteConnectionManager/Debug /e:true /q:true
#
# Recommended to disable after troubleshooting is complete:
#
#   wevtutil sl Microsoft-Windows-TerminalServices-RDPCoreTS/Debug /e:false /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-RDPCoreTS/Analytic /e:false /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-LocalSessionManager/Debug /e:false /q:true
#   wevtutil sl Microsoft-Windows-TerminalServices-RemoteConnectionManager/Debug /e:false /q:true

# When a Debug/Analytic channel is not enabled, Get-WinEvent throws "no events found" /
# "the specified channel could not be found"; the catch prints it as an explicit finding
# instead of silently skipping.

try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TerminalServices-RDPCoreTS/Debug'
        Level = 2, 3
    } -MaxEvents 50 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 rdpcorets-debug (channel likely not enabled): " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TerminalServices-LocalSessionManager/Debug'
        Level = 2, 3
    } -MaxEvents 50 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 lsm-debug (channel likely not enabled): " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TerminalServices-RemoteConnectionManager/Debug'
        Level = 2, 3
    } -MaxEvents 50 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 rcm-debug (channel likely not enabled): " + $_.Exception.Message)
}
