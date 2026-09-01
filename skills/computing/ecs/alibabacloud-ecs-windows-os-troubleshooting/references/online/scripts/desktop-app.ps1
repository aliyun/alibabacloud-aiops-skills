$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check .NET Framework Status ---
try {
    $ndpPath = 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP'
    $v4Full = Get-ItemProperty -Path "$ndpPath\v4\Full"
    if ($v4Full) {
        $releaseMap = @{528040='.NET 4.8'; 461808='.NET 4.7.2'; 461308='.NET 4.7.1'; 460798='.NET 4.7'; 394802='.NET 4.6.2'; 394254='.NET 4.6.1'; 393295='.NET 4.6'; 379893='.NET 4.5.2'; 378675='.NET 4.5.1'; 378389='.NET 4.5'}
        $friendlyName = ''
        foreach ($r in ($releaseMap.GetEnumerator() | Sort-Object Key -Descending)) {
            if ($v4Full.Release -ge $r.Key) { $friendlyName = $r.Value; break }
        }
        Write-Host ".NET Framework 4.x: Version=$($v4Full.Version), Release=$($v4Full.Release) ($friendlyName)"
    } else {
        Write-Host ".NET Framework 4.x: Not installed"
    }
} catch {
    Write-Host ("ERROR step1 netfx4-registry: " + $_.Exception.Message)
}
try {
    $ndpPath = 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP'
    $v35 = Get-ItemProperty -Path "$ndpPath\v3.5"
    if ($v35) {
        Write-Host ".NET Framework 3.5: Version=$($v35.Version), Install=$($v35.Install)"
    } else {
        Write-Host ".NET Framework 3.5: Not installed"
    }
} catch {
    Write-Host ("ERROR step1 netfx35-registry: " + $_.Exception.Message)
}

# --- Step 2: Check MSI Install/Uninstall Status ---
try {
    Get-Service -Name msiserver | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 msiserver: " + $_.Exception.Message)
}
try {
    # Filter ProviderName in FilterHashtable -- the Application log is high-volume, so
    # pulling the latest N entries and filtering afterwards misses installer errors days ago.
    Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='MsiInstaller'; Level=2,3; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 30 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 msi-eventlog: " + $_.Exception.Message)
}
try {
    $pending = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name 'PendingFileRenameOperations').PendingFileRenameOperations
    if ($pending) {
        Write-Host "PendingFileRenameOperations: $($pending.Count) entries (may need reboot)"
    } else {
        Write-Host "No pending file rename operations"
    }
} catch {
    Write-Host ("ERROR step2 pending-rename: " + $_.Exception.Message)
}

# --- Step 3: Check COM/DCOM Component Registration ---
try {
    Get-Service -Name 'RpcSs' | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 rpcss: " + $_.Exception.Message)
}
try {
    Get-WinEvent -FilterHashtable @{LogName='System'; Id=10016} -MaxEvents 5 |
        Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 dcom-eventlog: " + $_.Exception.Message)
}
try {
    $ole = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Ole'
    if ($ole) {
        Write-Host "DCOM EnableDCOM: $($ole.EnableDCOM)"
        Write-Host "DCOM LegacyAuthenticationLevel: $($ole.LegacyAuthenticationLevel)"
    }
} catch {
    Write-Host ("ERROR step3 ole-registry: " + $_.Exception.Message)
}
