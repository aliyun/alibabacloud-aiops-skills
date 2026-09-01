$ProgressPreference = 'SilentlyContinue'

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: VSS Service and Dependency Service Check ---

try {
    $serviceNames = @('VSS', 'EventSystem', 'RpcSs', 'DcomLaunch', 'CryptSvc', 'swprv')
    Get-Service -Name $serviceNames |
        Select-Object Name, DisplayName, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 vss-services: " + $_.Exception.Message)
}

# --- Step 2: VSS Writer Status Check ---

try {
    $writers = vssadmin list writers 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 vssadmin-writers: exit=$LASTEXITCODE $(($writers | Out-String).Trim())" }
    $writers
} catch {
    Write-Host ("ERROR step2 vssadmin-writers: " + $_.Exception.Message)
}

# --- Step 3: VSS Provider Check ---

try {
    $providers = vssadmin list providers 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 vssadmin-providers: exit=$LASTEXITCODE $(($providers | Out-String).Trim())" }
    $providers
} catch {
    Write-Host ("ERROR step3 vssadmin-providers: " + $_.Exception.Message)
}

# --- Step 4: VSS Snapshot and Storage Space Check ---

try {
    $shadows = vssadmin list shadows 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step4 vssadmin-shadows: exit=$LASTEXITCODE $(($shadows | Out-String).Trim())" }
    $shadows
} catch {
    Write-Host ("ERROR step4 vssadmin-shadows: " + $_.Exception.Message)
}

try {
    $shadowStorage = vssadmin list shadowstorage 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step4 vssadmin-shadowstorage: exit=$LASTEXITCODE $(($shadowStorage | Out-String).Trim())" }
    $shadowStorage
} catch {
    Write-Host ("ERROR step4 vssadmin-shadowstorage: " + $_.Exception.Message)
}

# --- Step 5: VSS Event Log Analysis ---

try {
    Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='VSS'; Level=1,2,3; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 30 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 vss-events: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='volsnap'; Level=1,2,3; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 volsnap-events: " + $_.Exception.Message)
}

# --- Step 6: Backup Software Status Check ---

try {
    # Get-WindowsFeature exists only on Server SKUs; on client SKUs the cmdlet itself
    # is missing and the error below is the explicit finding.
    Get-WindowsFeature -Name Windows-Server-Backup |
        Select-Object Name, InstallState |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 windows-server-backup: " + $_.Exception.Message)
}

try {
    # The Backup operational log does not exist unless Windows Server Backup is installed
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Backup'; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 backup-events (log may not exist): " + $_.Exception.Message)
}
